"""Group interest, explicit consent, low-guilt exit and commit-failure regressions."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
import pytest

import database
import main
from storage import storage


client = TestClient(main.app)
Z = {"Authorization": "Bearer token_zuzanna"}
J = {"Authorization": "Bearer token_jakub"}
O = {"Authorization": "Bearer token_ola"}


def make_formed_group():
    created = client.post(
        "/api/hotspots",
        headers=Z,
        json={
            "city": "Katowice",
            "name": f"Group consent {uuid.uuid4().hex[:8]}",
            "category": "cafe",
            "emoji": "☕",
            "address": "Rynek 1, Katowice",
            "target_time": "Tomorrow 16:00",
            "description": "Public cafe meeting",
            "cost_policy": "Each pays for their own order",
        },
    )
    assert created.status_code == 200, created.text
    spot_id = created.json()["id"]
    for headers in (J, O):
        voted = client.put(f"/api/hotspots/{spot_id}/vote", headers=headers)
        assert voted.status_code == 200, voted.text
    return spot_id, voted.json()["outing_id"]


def test_vote_does_not_join_and_leaving_revokes_chat_access():
    spot_id, outing_id = make_formed_group()
    outing = database.OUTINGS[outing_id]
    room_id = outing.chat_room_id
    assert outing.participant_ids == []
    assert database.CHAT_ROOMS[room_id].participant_ids == []
    assert client.get(f"/api/outings/{outing_id}", headers=Z).status_code == 403
    assert client.get(f"/api/chat/rooms/{room_id}", headers=Z).status_code == 403
    assert not main.is_scope_authorized_for_user(f"chat:{room_id}", "usr_zuzanna")
    assert client.get("/api/hotspots", headers=Z).json()[-1]["user_joined"] is False

    first = client.post(f"/api/outings/{outing_id}/join", headers=Z)
    assert first.status_code == 200, first.text
    repeated = client.post(f"/api/outings/{outing_id}/join", headers=Z)
    assert repeated.status_code == 200
    assert repeated.json()["participant_ids"] == ["usr_zuzanna"]
    assert database.CHAT_ROOMS[room_id].participant_ids == ["usr_zuzanna"]

    left = client.post(f"/api/outings/{outing_id}/leave", headers=Z)
    assert left.status_code == 200 and left.json()["left"] is True
    assert client.post(f"/api/outings/{outing_id}/leave", headers=Z).status_code == 403
    assert client.get(f"/api/outings/{outing_id}", headers=Z).status_code == 403
    assert client.get(f"/api/chat/rooms/{room_id}", headers=Z).status_code == 403
    assert client.post(f"/api/chat/rooms/{room_id}/messages", headers=Z, json={"text": "not a member"}).status_code == 403
    assert not main.is_scope_authorized_for_user(f"outing:{outing_id}", "usr_zuzanna")
    assert database.HOTSPOTS[spot_id].voter_ids.count("usr_zuzanna") == 1
    unvoted = client.delete(f"/api/hotspots/{spot_id}/vote", headers=Z)
    assert unvoted.status_code == 200
    assert unvoted.json()["user_voted"] is False
    assert client.delete(f"/api/hotspots/{spot_id}/vote", headers=Z).status_code == 200


def test_group_join_rejects_blocked_member_and_db_failure_keeps_rosters(monkeypatch):
    _, outing_id = make_formed_group()
    assert client.post(f"/api/outings/{outing_id}/join", headers=Z).status_code == 200
    assert client.post("/api/users/usr_zuzanna/block", headers=J).status_code == 200
    try:
        assert client.post(f"/api/outings/{outing_id}/join", headers=J).status_code == 403
    finally:
        database.unblock_user("usr_jakub", "usr_zuzanna")

    room_id = database.OUTINGS[outing_id].chat_room_id
    before_outing = database.OUTINGS[outing_id].model_dump()
    before_room = database.CHAT_ROOMS[room_id].model_dump()

    def fail_commit(*args, **kwargs):
        raise RuntimeError("injected database failure")

    monkeypatch.setattr(storage, "persist_outing_membership", fail_commit)
    try:
        client.post(f"/api/outings/{outing_id}/join", headers=J)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Database failure must propagate")
    assert database.OUTINGS[outing_id].model_dump() == before_outing
    assert database.CHAT_ROOMS[room_id].model_dump() == before_room


def test_failed_group_formation_does_not_publish_partial_memory(monkeypatch):
    created = client.post(
        "/api/hotspots", headers=Z,
        json={
            "city": "Katowice", "name": f"Atomic group {uuid.uuid4().hex[:8]}",
            "category": "cafe", "emoji": "☕", "address": "Rynek 1, Katowice",
            "target_time": "Tomorrow 16:00", "description": "Public cafe meeting",
            "cost_policy": "Each pays their own order",
        },
    )
    assert created.status_code == 200
    spot_id = created.json()["id"]
    assert client.put(f"/api/hotspots/{spot_id}/vote", headers=J).status_code == 200
    before = database.HOTSPOTS[spot_id].model_dump()

    def fail_commit(*args, **kwargs):
        raise RuntimeError("injected database failure")

    monkeypatch.setattr(storage, "persist_hotspot_vote_and_group", fail_commit)
    try:
        client.put(f"/api/hotspots/{spot_id}/vote", headers=O)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Database failure must propagate")
    assert database.HOTSPOTS[spot_id].model_dump() == before


def test_group_message_report_is_bound_to_sender_and_survives_reporter_exit():
    _, outing_id = make_formed_group()
    assert client.post(f"/api/outings/{outing_id}/join", headers=J).status_code == 200
    assert client.post(f"/api/outings/{outing_id}/join", headers=Z).status_code == 200
    room_id = database.OUTINGS[outing_id].chat_room_id
    message = client.post(
        f"/api/chat/rooms/{room_id}/messages", headers=J,
        json={"text": "Message for group-report evidence"},
    )
    assert message.status_code == 200
    evidence_id = message.json()["id"]
    assert client.post(f"/api/outings/{outing_id}/leave", headers=Z).status_code == 200
    payload = {
        "reported_user_id": "usr_jakub", "category": "harassment",
        "details": "Please review the cited group message.",
        "outing_id": outing_id,
        "evidence_chat_message_id": evidence_id,
    }
    saved = client.post("/api/reports", headers=Z, json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()["outing_id"] == outing_id
    assert storage.load_reports()[saved.json()["id"]]["outing_id"] == outing_id
    wrong_sender = client.post(
        "/api/reports", headers=J,
        json={**payload, "reported_user_id": "usr_zuzanna"},
    )
    assert wrong_sender.status_code == 400
    outsider = client.post(
        "/api/reports", headers={"Authorization": "Bearer token_ania"},
        json=payload,
    )
    assert outsider.status_code == 403


def test_deployed_websocket_origin_is_exact_and_oversized_frame_closes(monkeypatch):
    token = f"cmt_group_ws_{uuid.uuid4().hex}"
    ticket = f"qa_ws_ticket_{uuid.uuid4().hex}"
    main.persist_active_session(token, "usr_zuzanna")
    user = database.USERS["usr_zuzanna"]
    monkeypatch.setattr(main, "is_production", lambda: True)
    monkeypatch.setattr(main, "AGE_ASSURANCE_TRUSTED_PROVIDERS", frozenset({"qa-contract"}))
    monkeypatch.setattr(user, "age_assurance_provider", "qa-contract")
    monkeypatch.setattr(user, "adult_verified_at", (datetime.now(timezone.utc) - timedelta(days=1)).isoformat())
    monkeypatch.setattr(user, "adult_verification_expires_at", (datetime.now(timezone.utc) + timedelta(days=1)).isoformat())
    try:
        main.WS_TICKETS[ticket] = (token, datetime.now(timezone.utc) + timedelta(seconds=30))
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f"/ws?ticket={ticket}", headers={"origin": "https://evil.example"}) as socket:
                socket.receive_json()
        # A rejected handshake cannot spend an otherwise valid one-time ticket.
        with client.websocket_connect(f"/ws?ticket={ticket}", headers={"origin": "https://testserver"}) as socket:
            assert socket.receive_json()["type"] == "connection.ready"
            socket.send_text("x" * 8193)
            with pytest.raises(WebSocketDisconnect) as error:
                socket.receive_json()
            assert error.value.code == 1009
    finally:
        client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
