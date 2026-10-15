import uuid
import sqlite3
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
import pytest

import database
import main
from models import PingStatus, RequestStatus
from storage import DurableStorage


client = TestClient(main.app)
HOST = {"Authorization": "Bearer token_jakub"}
COMPANION = {"Authorization": "Bearer token_ania"}


def test_live_ping_and_join_request_survive_rehydration(tmp_path, monkeypatch):
    isolated = DurableStorage(str(tmp_path / "core-journey.db"))
    monkeypatch.setattr(database, "storage", isolated)
    ping_id = None
    trip_id = None
    try:
        created = client.post("/api/pings", headers=HOST, json={
            "category": "grocery",
            "destination_name": f"Katowice test {uuid.uuid4().hex[:8]}",
            "destination_lat": 50.2649,
            "destination_lng": 19.0238,
            "address": "Public meeting point, Katowice",
            "intent_tags": ["#groceries"],
            "ttl_minutes": 45,
        })
        assert created.status_code == 200
        ping_id = created.json()["id"]
        assert ping_id in isolated.load_pings()

        requested = client.post(f"/api/pings/{ping_id}/join", headers=COMPANION)
        assert requested.status_code == 200
        request_id = requested.json()["id"]
        assert [r["id"] for r in isolated.load_join_requests()[ping_id]] == [request_id]

        database.PINGS.pop(ping_id)
        database.JOIN_REQUESTS.pop(ping_id)
        database.hydrate_from_storage()
        assert database.PINGS[ping_id].status == PingStatus.ACTIVE
        assert database.JOIN_REQUESTS[ping_id][0].id == request_id

        accepted = client.post(
            f"/api/pings/{ping_id}/requests/{request_id}/accept", headers=HOST
        )
        assert accepted.status_code == 200
        trip_id = accepted.json()["id"]
        database.PINGS.pop(ping_id)
        database.JOIN_REQUESTS.pop(ping_id)
        database.TRIPS.pop(trip_id)
        database.hydrate_from_storage()
        assert database.PINGS[ping_id].status == PingStatus.MATCHED
        assert database.JOIN_REQUESTS[ping_id][0].status == RequestStatus.ACCEPTED
        assert trip_id in database.TRIPS
    finally:
        if ping_id:
            database.PINGS.pop(ping_id, None)
            database.JOIN_REQUESTS.pop(ping_id, None)
        if trip_id:
            database.TRIPS.pop(trip_id, None)
            database.CHAT_ROOMS.pop(f"room_{trip_id}", None)


def test_city_events_and_hotspot_responses_do_not_expose_participants(tmp_path, monkeypatch):
    isolated = DurableStorage(str(tmp_path / "privacy.db"))
    monkeypatch.setattr(database, "storage", isolated)
    broadcast = AsyncMock()
    monkeypatch.setattr(main.ws_manager, "broadcast", broadcast)
    ping_id = None
    spot_id = None
    try:
        created = client.post("/api/pings", headers=HOST, json={
            "category": "grocery",
            "destination_name": "Katowice public meeting point",
            "destination_lat": 50.2649,
            "destination_lng": 19.0238,
            "address": "Rynek, Katowice",
            "intent_tags": [],
        })
        assert created.status_code == 200
        ping_id = created.json()["id"]
        event = broadcast.await_args
        assert event.args[1] == "ping.created"
        assert set(event.args[2]) == {"ping_id", "city"}
        broadcast.reset_mock()

        waved = client.post(f"/api/pings/{ping_id}/wave", headers=COMPANION)
        assert waved.status_code == 200
        broadcast.assert_not_awaited()

        spot = client.post("/api/hotspots", headers=HOST, json={
            "city": "Katowice",
            "name": "Public cafe test",
            "address": "Rynek, Katowice",
            "description": "Short coffee outing",
        })
        assert spot.status_code == 200
        spot_id = spot.json()["id"]
        assert spot.json()["user_voted"] is True
        assert "voter_ids" not in spot.json()

        voted = client.put(f"/api/hotspots/{spot_id}/vote", headers=COMPANION)
        assert voted.status_code == 200
        assert "voter_ids" not in voted.json()
        event = broadcast.await_args
        assert event.args[1] == "hotspot.voted"
        assert set(event.args[2]) == {"spot_id", "city"}

        removed = client.delete(f"/api/hotspots/{spot_id}/vote", headers=COMPANION)
        assert removed.status_code == 200
        assert removed.json()["user_voted"] is False
        assert (spot_id, "usr_ania") not in isolated.load_hotspot_votes()

        monkeypatch.setattr(
            database, "is_user_blocked", lambda viewer, other: other == "usr_jakub"
        )
        hidden = client.get("/api/hotspots?city=Katowice", headers=COMPANION)
        assert hidden.status_code == 200
        own_spot = next(item for item in hidden.json() if item["id"] == spot_id)
        assert own_spot["voter_avatars"] == []
        assert "voter_ids" not in own_spot
    finally:
        if ping_id:
            database.PINGS.pop(ping_id, None)
            database.JOIN_REQUESTS.pop(ping_id, None)
        if spot_id:
            database.HOTSPOTS.pop(spot_id, None)


def test_deployed_join_message_must_not_be_in_url(monkeypatch):
    session = f"cmt_test_{uuid.uuid4().hex}"
    main.persist_active_session(session, "usr_ania")
    monkeypatch.setattr(main, "is_production", lambda: True)
    # Isolate the URL-contract assertion from the separate 18+ admission gate.
    monkeypatch.setattr(main, "AGE_ASSURANCE_TRUSTED_PROVIDERS", frozenset({"qa-contract"}))
    monkeypatch.setattr(database.USERS["usr_ania"], "age_assurance_provider", "qa-contract")
    monkeypatch.setattr(database.USERS["usr_ania"], "adult_verified_at", datetime.now(timezone.utc).isoformat())
    monkeypatch.setattr(database.USERS["usr_ania"], "adult_verification_expires_at", "2099-01-01T00:00:00+00:00")
    try:
        response = client.post(
            "/api/pings/png_makro_01/join",
            headers={"Authorization": f"Bearer {session}"},
            params={"message": "private meeting details"},
        )
        assert response.status_code == 400
        assert "JSON body" in response.json()["detail"]
    finally:
        main.ACTIVE_SESSIONS.pop(session, None)
        main.SESSION_EXPIRIES.pop(session, None)


def test_acceptance_transaction_rolls_back_on_trip_insert_failure(tmp_path):
    isolated = DurableStorage(str(tmp_path / "atomic-acceptance.db"))
    ping = database.PINGS["png_makro_01"].model_copy(update={
        "id": f"png_{uuid.uuid4().hex[:8]}",
        "status": PingStatus.ACTIVE,
    })
    request = database.JOIN_REQUESTS["png_makro_01"][0].model_copy(update={
        "id": f"req_{uuid.uuid4().hex[:8]}",
        "ping_id": ping.id,
        "status": RequestStatus.PENDING,
    })
    isolated.persist_ping(ping.model_dump())
    isolated.persist_join_request(request.model_dump())

    existing_trip = database.TRIPS["trip_makro_01"].model_dump()
    isolated.persist_trip(existing_trip)
    matched = ping.model_copy(update={"status": PingStatus.MATCHED})
    accepted = request.model_copy(update={"status": RequestStatus.ACCEPTED})
    room = database.CHAT_ROOMS["chat_trip_makro_01"].model_dump()
    room["id"] = f"room_{uuid.uuid4().hex[:8]}"
    room["messages"] = []

    with pytest.raises(sqlite3.IntegrityError):
        isolated.persist_join_acceptance(
            matched.model_dump(), [accepted.model_dump()], existing_trip, room
        )
    assert isolated.load_pings()[ping.id]["status"] == "active"
    assert isolated.load_join_requests()[ping.id][0]["status"] == "pending"
    assert room["id"] not in isolated.load_chat_rooms()


def test_deployment_rejects_unproven_identity_or_social_claims():
    user = database.USERS["usr_zuzanna"].model_dump()
    user.update({
        "trust_tier": "Bronze",
        "is_id_verified": False,
        "is_selfie_verified": False,
        "is_background_checked": False,
        "instagram_verified": False,
        "linkedin_verified": False,
        "tiktok_verified": False,
        "facebook_verified": False,
    })
    database.assert_no_unproven_verification_claims({"real_user": user})
    user["is_id_verified"] = True
    with pytest.raises(RuntimeError, match="unproven verification claim"):
        database.assert_no_unproven_verification_claims({"real_user": user})
    user["is_id_verified"] = False
    user["instagram_verified"] = True
    with pytest.raises(RuntimeError, match="unproven verification claim"):
        database.assert_no_unproven_verification_claims({"real_user": user})


def test_server_rejects_unsafe_and_out_of_region_public_content():
    unsafe_ping = client.post("/api/pings", headers=HOST, json={
        "category": "grocery",
        "destination_name": "Katowice cafe",
        "destination_lat": 50.2649,
        "destination_lng": 19.0238,
        "address": "Rynek 1, Katowice",
        "intent_tags": [],
        "notes": "Szukam seksu za pieniądze",
    })
    assert unsafe_ping.status_code == 422

    out_of_region = client.post("/api/hotspots", headers=HOST, json={
        "city": "Warszawa",
        "name": "Public cafe",
        "address": "Rynek 1, Warszawa",
        "description": "Coffee outing",
    })
    assert out_of_region.status_code == 422

    unsafe_hotspot = client.post("/api/hotspots", headers=HOST, json={
        "city": "Katowice",
        "name": "Public cafe",
        "address": "Rynek 1, Katowice",
        "description": "Sprzedam narkotyki",
    })
    assert unsafe_hotspot.status_code == 422

    oversized_name = client.post("/api/hotspots", headers=HOST, json={
        "city": "Katowice",
        "name": "x" * 141,
        "address": "Rynek 1, Katowice",
        "description": "Coffee outing",
    })
    assert oversized_name.status_code == 422
