"""Regressions for the 2026-09-30 integration review findings."""

import os
import subprocess
import sys
import textwrap
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import database
import main
from storage import storage


client = TestClient(main.app)


def test_legacy_warsaw_hotspot_and_outing_stay_closed_after_cold_hydration(tmp_path):
    """A persisted pre-boundary record must not reopen any live group path."""
    script = textwrap.dedent("""
        from fastapi.testclient import TestClient
        import database
        import main

        spot = next(iter(database.HOTSPOTS.values())).model_copy(deep=True, update={
            'id': 'spot_legacy_warsaw', 'city': 'Warszawa',
            'voter_ids': ['usr_jakub'], 'voter_avatars': [database.USERS['usr_jakub'].avatar],
            'votes_count': 1, 'group_formed': False, 'outing_id': None,
        })
        outing = next(iter(database.OUTINGS.values())).model_copy(deep=True, update={
            'id': 'outing_legacy_warsaw', 'city': 'Warszawa',
            'participant_ids': ['usr_zuzanna', 'usr_jakub'],
        })
        database.save_hotspot(spot)
        database.save_outing(outing)
        database.HOTSPOTS.pop(spot.id)
        database.OUTINGS.pop(outing.id)
        database.hydrate_from_storage()
        assert spot.id in database.HOTSPOTS and outing.id in database.OUTINGS

        main.is_production = lambda: True
        # A local test-only proof isolates region checks; the real app trusts
        # no age provider until one is approved and integrated.
        main.AGE_ASSURANCE_TRUSTED_PROVIDERS = frozenset({'qa-contract'})
        user = database.USERS['usr_zuzanna']
        user.age_assurance_provider = 'qa-contract'
        user.adult_verified_at = '2026-01-01T00:00:00+00:00'
        user.adult_verification_expires_at = '2099-01-01T00:00:00+00:00'
        token = 'cmt_region_guard_regression'
        main.persist_active_session(token, 'usr_zuzanna')
        client = TestClient(main.app)
        headers = {'Authorization': f'Bearer {token}'}
        listed = client.get('/api/hotspots?city=Warszawa', headers=headers)
        assert listed.status_code == 200 and not listed.json()
        assert client.put(f'/api/hotspots/{spot.id}/vote', headers=headers).status_code == 404
        assert client.delete(f'/api/hotspots/{spot.id}/vote', headers=headers).status_code == 404
        assert client.get(f'/api/outings/{outing.id}', headers=headers).status_code == 404
        assert client.post(f'/api/outings/{outing.id}/join', headers=headers).status_code == 404
        assert database.HOTSPOTS[spot.id].voter_ids == ['usr_jakub']
    """)
    env = os.environ.copy()
    env.update({
        "CARTMATE_ENV": "development",
        "CARTMATE_DATABASE_PATH": str(tmp_path / "cold-region.db"),
    })
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=os.path.dirname(__file__),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_block_disconnects_existing_socket_and_denies_rejoin():
    room_id = "chat_trip_makro_01"
    try:
        with client.websocket_connect("/ws?token=token_jakub") as socket:
            assert socket.receive_json()["type"] == "connection.ready"
            socket.send_json({"action": "subscribe", "scope": f"chat:{room_id}"})
            assert socket.receive_json()["type"] == "subscription.confirmed"

            blocked = client.post(
                "/api/users/usr_jakub/block",
                headers={"Authorization": "Bearer token_zuzanna"},
                json={"reason": "review regression"},
            )
            assert blocked.status_code == 200
            with pytest.raises(WebSocketDisconnect):
                socket.receive_json()

        assert not main.is_scope_authorized_for_user(f"chat:{room_id}", "usr_jakub")
        assert not main.is_scope_authorized_for_user("trip:trip_makro_01", "usr_zuzanna")
        history = client.get(
            f"/api/chat/rooms/{room_id}",
            headers={"Authorization": "Bearer token_jakub"},
        )
        assert history.status_code == 403
    finally:
        database.unblock_user("usr_zuzanna", "usr_jakub")


def test_revoke_other_sessions_keeps_current_session_and_revokes_peers():
    current = f"cmt_review_current_{uuid.uuid4().hex}"
    other = f"cmt_review_other_{uuid.uuid4().hex}"
    main.persist_active_session(current, "usr_zuzanna")
    main.persist_active_session(other, "usr_zuzanna")
    headers = {"Authorization": f"Bearer {current}"}
    try:
        revoked = client.post("/api/auth/revoke-other-sessions", headers=headers)
        assert revoked.status_code == 200
        assert revoked.json()["revoked_count"] >= 1
        assert client.get("/api/users/me", headers=headers).status_code == 200
        assert client.get(
            "/api/users/me", headers={"Authorization": f"Bearer {other}"}
        ).status_code == 401
        assert current in {s["token"] for s in storage.get_active_sessions_for_user("usr_zuzanna")}
        assert other not in {s["token"] for s in storage.get_active_sessions_for_user("usr_zuzanna")}
    finally:
        client.post("/api/auth/logout", headers=headers)


def test_deployed_live_admission_rejects_missing_untrusted_and_expired_age_proof(monkeypatch):
    token = f"cmt_age_regression_{uuid.uuid4().hex}"
    main.persist_active_session(token, "usr_zuzanna")
    headers = {"Authorization": f"Bearer {token}"}
    user = database.USERS["usr_zuzanna"]
    monkeypatch.setattr(main, "is_production", lambda: True)
    try:
        status = client.get("/api/users/me/admission", headers=headers)
        assert status.status_code == 200
        assert status.json()["live_access"] is False
        assert client.get("/api/pings", headers=headers).status_code == 403
        assert client.get("/api/users/all", headers=headers).status_code == 403
        assert client.post("/api/auth/ws-ticket", headers=headers).status_code == 403
        ticket = f"age_ticket_{uuid.uuid4().hex}"
        main.WS_TICKETS[ticket] = (token, datetime.now(timezone.utc) + timedelta(seconds=30))
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f"/ws?ticket={ticket}") as socket:
                socket.receive_json()

        now = datetime.now(timezone.utc)
        monkeypatch.setattr(user, "adult_verified_at", now.isoformat())
        monkeypatch.setattr(user, "adult_verification_expires_at", (now + timedelta(days=1)).isoformat())
        monkeypatch.setattr(user, "age_assurance_provider", "self_asserted")
        assert client.get("/api/pings", headers=headers).status_code == 403

        monkeypatch.setattr(main, "AGE_ASSURANCE_TRUSTED_PROVIDERS", frozenset({"qa-contract"}))
        assert client.get("/api/pings", headers=headers).status_code == 403
        monkeypatch.setattr(user, "age_assurance_provider", "qa-contract")
        monkeypatch.setattr(user, "adult_verification_expires_at", (now - timedelta(seconds=1)).isoformat())
        assert client.get("/api/pings", headers=headers).status_code == 403

        monkeypatch.setattr(user, "adult_verification_expires_at", (now + timedelta(days=1)).isoformat())
        assert client.get("/api/users/me/admission", headers=headers).json()["live_access"] is True
        assert client.get("/api/pings", headers=headers).status_code == 200
    finally:
        client.post("/api/auth/logout", headers=headers)
