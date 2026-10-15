"""Regression for activity-first ordinary outings; run only on a disposable DB."""

import asyncio
import logging
import uuid

import pytest
from fastapi.testclient import TestClient

import database
from jev_service import jev_service
from main import app
from models import ActivityCategory, PingStatus, TripStatus
from sanitizer import SensitiveDataLogFilter, apply_sanitized_logging


client = TestClient(app)
HOST = {"Authorization": "Bearer token_jakub"}
COMPANION = {"Authorization": "Bearer token_zuzanna"}
OUTSIDER = {"Authorization": "Bearer token_ania"}
ACTIVITY_FIRST_CATEGORIES = ("study", "fitness", "walk", "food", "social", "quick")


def make_ping(category: str):
    return client.post("/api/pings", headers=HOST, json={
        "category": category,
        "destination_name": f"Public meeting point {uuid.uuid4().hex[:8]}",
        "destination_lat": 50.2649,
        "destination_lng": 19.0238,
        "address": "Katowice centrum, public entrance",
        "intent_tags": [],
        "ttl_minutes": 45,
        "notes": "Meet at the named public entrance and agree on details.",
        "women_only": False,
    })


@pytest.mark.parametrize("category", ACTIVITY_FIRST_CATEGORIES)
def test_activity_categories_create_and_discover_with_existing_privacy(category):
    response = make_ping(category)
    assert response.status_code == 200, response.text
    ping = response.json()
    try:
        assert ping["category"] == category
        assert "phone" not in ping["host"]
        assert "email" not in ping["host"]
        visible = client.get(f"/api/pings?category={category}", headers=COMPANION)
        assert visible.status_code == 200, visible.text
        assert any(item["id"] == ping["id"] for item in visible.json())
        assert client.post(f"/api/pings/{ping['id']}/join", headers=HOST, json={"message": "Hello"}).status_code == 400
    finally:
        stored = database.PINGS[ping["id"]]
        stored.status = PingStatus.EXPIRED
        database.save_ping(stored)


def test_unrecognized_activity_fails_contract_validation():
    response = make_ping("private_home_visit")
    assert response.status_code == 422


def test_social_trip_starts_with_neutral_terms_and_no_shared_spend():
    response = make_ping("social")
    assert response.status_code == 200, response.text
    ping = response.json()
    trip_id = None
    try:
        request = client.post(
            f"/api/pings/{ping['id']}/join", headers=COMPANION,
            json={"message": "A public conversation sounds good."},
        )
        assert request.status_code == 200, request.text
        denied = client.post(
            f"/api/pings/{ping['id']}/requests/{request.json()['id']}/accept",
            headers=OUTSIDER,
        )
        assert denied.status_code == 403

        accepted = client.post(
            f"/api/pings/{ping['id']}/requests/{request.json()['id']}/accept",
            headers=HOST,
        )
        assert accepted.status_code == 200, accepted.text
        trip = accepted.json()
        trip_id = trip["id"]
        assert trip["plan_details"]["what"].startswith("Wspólne wyjście:")
        assert "zakupy" not in trip["plan_details"]["what"].lower()
        assert trip["plan_details"]["cost_policy"] == "no_expected_spend"
        assert "Publiczny punkt" in trip["rendezvous_spot"]
        assert client.post(f"/api/trips/{trip_id}/checkin", headers=HOST).status_code in (400, 409)

        plan = {
            "what": "Conversation at a public place",
            "when": "Tomorrow at 18:00, public main entrance",
            "estimated_duration_minutes": 45,
            "cost_policy": "no_expected_spend",
            "estimated_cost_pln": 1,
        }
        assert client.put(f"/api/trips/{trip_id}/plan", headers=HOST, json=plan).status_code == 422
        assert client.put(f"/api/trips/{trip_id}/plan", headers=OUTSIDER, json={**plan, "estimated_cost_pln": 0}).status_code == 403
        assert client.put(f"/api/trips/{trip_id}/plan", headers=HOST, json={**plan, "estimated_cost_pln": 0}).status_code == 422
        valid = client.put(f"/api/trips/{trip_id}/plan", headers=HOST, json={
            **plan,
            "estimated_cost_pln": 0,
            "meeting_point": "Public square by the main library entrance",
        })
        assert valid.status_code == 200, valid.text
        assert valid.json()["plan_details"]["estimated_cost_pln"] == 0
        assert valid.json()["rendezvous_spot"] == "Public square by the main library entrance"
    finally:
        if trip_id:
            stored_trip = database.TRIPS[trip_id]
            stored_trip.status = TripStatus.CANCELLED
            database.save_trip(stored_trip)
        stored_ping = database.PINGS[ping["id"]]
        stored_ping.status = PingStatus.EXPIRED
        database.save_ping(stored_ping)


@pytest.mark.parametrize("text,category", [
    ("Chcę się uczyć w bibliotece", ActivityCategory.STUDY),
    ("Idę na trening", ActivityCategory.FITNESS),
    ("Chętnie pójdę na spacer", ActivityCategory.WALK),
    ("Spotkajmy się na obiad", ActivityCategory.FOOD),
    ("Chcę porozmawiać w publicznym miejscu", ActivityCategory.SOCIAL),
])
def test_activity_classification_remains_advisory(text, category):
    result = asyncio.run(jev_service.classify_ping_intent(text))
    assert result.category == category
    assert result.is_safe


def test_websocket_ticket_never_appears_in_server_log_record():
    apply_sanitized_logging()
    record = logging.LogRecord(
        "uvicorn.error", logging.INFO, __file__, 1,
        'WebSocket "%s" [accepted]', ("/ws?ticket=exampleSecretTicket123",), None,
    )
    for log_filter in logging.getLogger("uvicorn.error").filters:
        log_filter.filter(record)
    assert "exampleSecretTicket123" not in record.getMessage()
    assert "[REDACTED_WS_TICKET]" in record.getMessage()
