"""
Regression tests for the E00/E01 completion-review defects (F02-F07).

Each test reproduces a defect found during the 2026-09-29 completion review
(NEXT_MODEL_EXECUTION_PLAN.md, section "Confirmed defects to fix first") and
pins the fixed behavior. They run against the development fixture database
via TestClient, consistent with the rest of the local suite.

F02: /api/ai/shadow-audit must be moderator-only and must not retain
     free-text summaries or provider blobs in audit entries.
F03: trip broadcasts must never carry another participant's follow-up;
     REST responses expose only the caller's own follow-up entry.
F04: a blocked pair must never be silently auto-joined into a group when a
     hotspot reaches its vote threshold.
F05: every report category offered by the frontend must be accepted by the
     backend enum (contract parity).
F06: legacy out-of-region pings must not be listed or joined; chat REST/WS
     writes into out-of-region rooms must be denied.
F07: suspended users and their listings must not be discoverable.
"""

import json
import uuid

import pytest
from fastapi.testclient import TestClient

import database
from config import MODERATOR_USER_IDS
from jev_service import jev_service
from main import app
import main

client = TestClient(app)

AUTH_ZUZANNA = {"Authorization": "Bearer token_zuzanna"}
AUTH_JAKUB = {"Authorization": "Bearer token_jakub"}
AUTH_ANIA = {"Authorization": "Bearer token_ania"}


@pytest.fixture
def deployed_region_member(monkeypatch):
    """Exercise deployed route guards without accepting demo auth or fake age proof."""
    user = database.USERS["usr_zuzanna"]
    monkeypatch.setattr(main, "is_production", lambda: True)
    monkeypatch.setattr(main, "AGE_ASSURANCE_TRUSTED_PROVIDERS", frozenset({"qa-contract"}))
    monkeypatch.setattr(user, "age_assurance_provider", "qa-contract")
    monkeypatch.setattr(user, "adult_verified_at", "2026-01-01T00:00:00+00:00")
    monkeypatch.setattr(user, "adult_verification_expires_at", "2099-01-01T00:00:00+00:00")
    token = f"cmt_f06_{uuid.uuid4().hex}"
    main.persist_active_session(token, user.id)
    headers = {"Authorization": f"Bearer {token}"}
    yield headers
    client.post("/api/auth/logout", headers=headers)


def _cleanup_hotspot(spot_id: str):
    database.HOTSPOTS.pop(spot_id, None)
    database.BLOCKED_USERS.clear()


def _reset_service_audit():
    jev_service._shadow_audit_log.clear()


# ---------------------------------------------------------------------------
# F02 — Jev shadow audit privacy
# ---------------------------------------------------------------------------


def test_f02_shadow_audit_is_moderator_only():
    _reset_service_audit()
    # Populate at least one audit entry through a public classification call.
    client.post(
        "/api/ai/classify-intent",
        headers=AUTH_ZUZANNA,
        json={"text": "Idziemy na kawe do Makro w Katowicach"},
    )
    ordinary = client.get("/api/ai/shadow-audit", headers=AUTH_ZUZANNA)
    if "usr_zuzanna" in MODERATOR_USER_IDS:
        pytest.skip("test fixture configures usr_zuzanna as moderator; run with a non-moderator user")
    assert ordinary.status_code == 403


def test_f02_shadow_audit_entries_contain_no_free_text():
    _reset_service_audit()
    marker_text = "herold.example+audit@privacy-test.pl"
    client.post(
        "/api/ai/classify-intent",
        headers=AUTH_ZUZANNA,
        json={"text": f"Zapisz mnie na kawe {marker_text} prosze"},
    )
    entries = list(jev_service._shadow_audit_log)
    assert entries, "expected at least one shadow audit entry"
    blob = json.dumps(entries)
    assert marker_text not in blob, "raw user input leaked into shadow audit"
    assert "baseline_decision" not in blob and "jev_decision" not in blob, (
        "audit entries must not retain model decision blobs"
    )
    for entry in entries:
        assert isinstance(entry.get("baseline_is_safe"), (bool, type(None)))
        assert isinstance(entry.get("jev_agreement_status"), str)


# ---------------------------------------------------------------------------
# F03 — private follow-up disclosure
# ---------------------------------------------------------------------------


def _seed_mutual_followups():
    trip = database.TRIPS["trip_makro_01"]
    trip.status = database.TripStatus.COMPLETED
    trip.rendezvous_verified = True
    trip.host_checked_in = True
    trip.companion_checked_in = True
    trip.follow_ups = {
        trip.host.id: {"would_meet_again": False, "feedback": "HOST-PRIVATE-FEEDBACK-XYZ", "positive_tags": []},
        trip.companion.id: {"would_meet_again": True, "feedback": "COMPANION-PRIVATE-FEEDBACK-ABC", "positive_tags": []},
    }
    return trip


def test_f03_rest_response_hides_other_participant_follow_up():
    trip = _seed_mutual_followups()
    res = client.get("/api/trips/trip_makro_01", headers=AUTH_ZUZANNA)
    assert res.status_code == 200
    follow_ups = res.json()["follow_ups"]
    assert set(follow_ups.keys()) == {trip.companion.id}, "only the caller's own entry may be visible"
    assert "HOST-PRIVATE-FEEDBACK-XYZ" not in res.text


def test_f03_broadcast_response_carries_no_follow_ups():
    trip = _seed_mutual_followups()
    from main import build_trip_response

    broadcast = build_trip_response(trip).model_dump()
    assert broadcast["follow_ups"] == {}, "broadcasts must not include any follow-up entries"
    assert "HOST-PRIVATE-FEEDBACK-XYZ" not in json.dumps(broadcast)
    assert "COMPANION-PRIVATE-FEEDBACK-ABC" not in json.dumps(broadcast)

    host_view = build_trip_response(trip, trip.host.id).model_dump()
    assert set(host_view["follow_ups"].keys()) == {trip.host.id}


# ---------------------------------------------------------------------------
# F04 — blocked pair silently joined by third-party vote
# ---------------------------------------------------------------------------


def test_f04_blocked_pair_not_grouped_at_threshold():
    jakub = database.USERS["usr_jakub"]
    zuzanna = database.USERS["usr_zuzanna"]
    ania = database.USERS["usr_ania"]
    spot_id = None
    try:
        # Create the spot through the API like a real user would.
        created = client.post(
            "/api/hotspots",
            headers=AUTH_JAKUB,
            json={
                "city": "Katowice",
                "name": "F04 Regression Spot",
                "address": "Rynek 1, Katowice",
                "description": "Coffee outing for blocked-pair regression",
            },
        )
        assert created.status_code == 200, created.text
        spot_id = created.json()["id"]
        spot = database.HOTSPOTS[spot_id]
        spot.threshold = 3
        database.save_hotspot(spot)

        # Jakub (creator, already voted) and Zuzanna vote first — no blocks yet.
        voted_z = client.put(f"/api/hotspots/{spot_id}/vote", headers=AUTH_ZUZANNA)
        assert voted_z.status_code == 200

        # NOW a block appears between two existing voters (e.g. set after a
        # report). The vote-time check cannot catch this retroactively.
        database.BLOCKED_USERS.add((jakub.id, zuzanna.id))
        database.BLOCKED_USERS.add((zuzanna.id, jakub.id))

        # Third voter (Ania) reaches the threshold; formation must not
        # silently join the blocked pair into one group/chat.
        res = client.put(f"/api/hotspots/{spot_id}/vote", headers=AUTH_ANIA)
        assert res.status_code == 200

        refreshed = database.HOTSPOTS.get(spot_id)
        if refreshed.group_formed:
            outing = database.OUTINGS.get(refreshed.outing_id)
            participants = set(outing.participant_ids) if outing else set()
            assert not (jakub.id in participants and zuzanna.id in participants), (
                "a blocked pair must never be placed in the same auto-formed group"
            )
        else:
            assert refreshed.outing_id is None, "no group may be formed while a blocked pair dominates the voters"
    finally:
        if spot_id:
            outing = database.HOTSPOTS.get(spot_id)
            if outing and outing.outing_id:
                database.OUTINGS.pop(outing.outing_id, None)
                database.CHAT_ROOMS.pop(f"room_{outing.outing_id}", None)
            database.HOTSPOTS.pop(spot_id, None)
        database.BLOCKED_USERS.clear()


# ---------------------------------------------------------------------------
# F05 — frontend report categories must match the backend enum
# ---------------------------------------------------------------------------


def test_f05_all_frontend_report_categories_accepted():
    from models import ReportCategory

    frontend_offers = [
        "harassment",
        "unsafe_behavior",
        "no_show",
        "safety_risk",
        "spam",
        "fake_profile",
        "financial_fraud",
        "other",
    ]
    backend_enum = {c.value for c in ReportCategory}
    for category in frontend_offers:
        assert category in backend_enum, f"frontend offers category '{category}' missing from backend enum"

    invalid_legacy = ["inappropriate_content", "commercial_spam", "misrepresentation"]
    for category in invalid_legacy:
        res = client.post(
            "/api/reports",
            headers=AUTH_ZUZANNA,
            json={
                "reported_user_id": "usr_jakub",
                "category": category,
                "details": "contract parity regression",
            },
        )
        assert res.status_code == 422, f"legacy invalid category '{category}' must be rejected"


# ---------------------------------------------------------------------------
# F06 — region enforcement on listing, joining and chat writes
# ---------------------------------------------------------------------------


def _insert_legacy_out_of_region_ping():
    from models import LivePingSchema, PingStatus as PingStatusEnum

    ping_id = "png_f06_legacy_warsaw"
    host = database.USERS["usr_jakub"]
    ping = LivePingSchema(
        id=ping_id,
        host=host,
        category="cafe",
        destination_name="Warszawa Legacy Cafe",
        destination_lat=52.2297,
        destination_lng=21.0122,
        address="ul. Legacy 1, Warszawa",
        intent_tags=[],
        notes="",
        women_only=False,
        status=PingStatusEnum.ACTIVE,
        created_at="2026-01-01T00:00:00+00:00",
        expires_at="2099-01-01T00:00:00+00:00",
        remaining_seconds=9999,
        join_requests_count=0,
    )
    database.PINGS[ping_id] = ping
    return ping_id


def test_f06_legacy_out_of_region_ping_not_listed_or_joinable(deployed_region_member):
    ping_id = _insert_legacy_out_of_region_ping()
    try:
        listed = client.get("/api/pings", headers=deployed_region_member)
        assert listed.status_code == 200
        assert all(p["id"] != ping_id for p in listed.json()), "out-of-region ping must not be listed"

        joined = client.post(
            f"/api/pings/{ping_id}/join",
            headers=deployed_region_member,
            json={"message": "chcialabym dolaczyc"},
        )
        assert joined.status_code == 404, "out-of-region ping must not be joinable"
    finally:
        database.PINGS.pop(ping_id, None)


def test_f06_out_of_region_chat_room_not_writable(deployed_region_member):
    from models import ChatRoomSchema

    room_id = "chat_f06_legacy_warsaw"
    database.CHAT_ROOMS.pop(room_id, None)
    try:
        room = ChatRoomSchema(
            id=room_id,
            scope="outing",
            target_id="out_legacy_warsaw",
            participant_ids=["usr_jakub", "usr_zuzanna"],
            messages=[],
            created_at="2026-01-01T00:00:00+00:00",
        )
        # Legacy out-of-region outing record so the room resolves to Warsaw.
        from models import OutingSchema

        outing = OutingSchema(
            id="out_legacy_warsaw",
            hotspot_id="spot_legacy",
            hotspot_name="Legacy Warszawa",
            category="cafe",
            emoji="☕",
            city="Warszawa",
            address="ul. Legacy 1",
            participant_ids=["usr_jakub", "usr_zuzanna"],
            participant_avatars=[],
            chat_room_id=room_id,
            created_at="2026-01-01T00:00:00+00:00",
        )
        database.OUTINGS[outing.id] = outing
        database.CHAT_ROOMS[room_id] = room

        res = client.post(
            f"/api/chat/rooms/{room_id}/messages",
            headers=deployed_region_member,
            json={"text": "wiadomosc testowa"},
        )
        assert res.status_code == 404, "writes into out-of-region rooms must be denied"
        assert not room.messages, "no message may be persisted to an out-of-region room"
        ticket_response = client.post("/api/auth/ws-ticket", headers=deployed_region_member)
        assert ticket_response.status_code == 200
        ticket = ticket_response.json()["ticket"]
        with client.websocket_connect(f"/ws?ticket={ticket}", headers={"origin": "https://testserver"}) as socket:
            assert socket.receive_json()["type"] == "connection.ready"
            socket.send_json({"action": "subscribe", "scope": f"chat:{room_id}"})
            assert socket.receive_json()["type"] == "error"
            socket.send_json({"action": "chat_message", "room_id": room_id, "text": "bypass"})
            assert socket.receive_json()["type"] == "error"
        assert not room.messages, "WebSocket must not persist a legacy out-of-region chat message"
    finally:
        database.CHAT_ROOMS.pop(room_id, None)
        database.OUTINGS.pop("out_legacy_warsaw", None)


# ---------------------------------------------------------------------------
# F07 — suspended users hidden from discovery
# ---------------------------------------------------------------------------


def test_f07_suspended_user_hidden_from_directory_and_pings():
    ania = database.USERS["usr_ania"]
    was_suspended = ania.is_suspended
    ping_id = "png_f07_ania_host"
    from models import LivePingSchema, PingStatus as PingStatusEnum

    ping = LivePingSchema(
        id=ping_id,
        host=ania,
        category="quick",
        destination_name="Biedronka Katowice",
        destination_lat=50.2649,
        destination_lng=19.0238,
        address="ul. Testowa 2, Katowice",
        intent_tags=[],
        notes="",
        women_only=False,
        status=PingStatusEnum.ACTIVE,
        created_at="2026-01-01T00:00:00+00:00",
        expires_at="2099-01-01T00:00:00+00:00",
        remaining_seconds=9999,
        join_requests_count=0,
    )
    database.PINGS[ping_id] = ping
    try:
        ania.is_suspended = True
        directory = client.get("/api/users/all", headers=AUTH_ZUZANNA)
        assert directory.status_code == 200
        assert all(u["id"] != ania.id for u in directory.json()), "suspended user must not be listed"

        listed = client.get("/api/pings", headers=AUTH_ZUZANNA)
        assert listed.status_code == 200
        assert all(p["id"] != ping_id for p in listed.json()), "suspended host's listing must not be discoverable"
    finally:
        ania.is_suspended = was_suspended
        database.PINGS.pop(ping_id, None)


# Restore seeded trip state mutated by F03 helpers after the module runs.


def test_zzz_restore_seeded_trip_state():
    trip = database.TRIPS["trip_makro_01"]
    trip.status = database.TripStatus.SCHEDULED
    trip.rendezvous_verified = False
    trip.follow_ups = {}
