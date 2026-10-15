"""Independent recovery-boundary diagnostic using synthetic, disposable state.

Run: python qa/codex_recovery_boundary_probe.py
Exit 0: all observed boundaries hold; 1: findings reproduced; 2: incomplete.
No live DB, listener, external provider, real person or application edits.
The parent bounds execution to 45 seconds and prints only sanitized evidence.
"""

import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MARKER = "CODEX_RECOVERY_BOUNDARIES="


def probe():
    from datetime import datetime, timedelta, timezone
    from unittest.mock import patch

    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect
    from models import UserPrivateSchema
    from storage import get_db_connection, storage

    expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    operator = UserPrivateSchema(
        id="usr_codex_recovery_operator", name="Synthetic Operator", avatar="", bio="",
        trust_tier="Bronze", gender="unspecified", city="Katowice",
        email="operator@review.invalid", phone="",
    )
    storage.redeem_operator_activation(
        storage.issue_operator_activation(expiry, intended_for="Synthetic Operator"),
        operator.model_dump(),
    )
    import main

    operator_session = "cmt_" + secrets.token_hex(20)
    main.persist_active_session(operator_session, operator.id)
    operator_headers = {"Authorization": "Bearer " + operator_session}
    observations = {}

    with TestClient(main.app, raise_server_exceptions=False) as client:
        def enroll(name):
            code = storage.issue_operator_activation(expiry, intended_for=name)
            response = client.post("/api/auth/redeem-operator-activation", json={
                "activation_token": code, "name": name, "city": "Katowice",
            })
            assert response.status_code == 200
            account = response.json()
            headers = {"Authorization": "Bearer " + account["token"]}
            challenge = client.post("/api/users/me/age-check-challenge", headers=headers)
            assert challenge.status_code == 200
            attestation = client.post(
                f"/api/moderation/users/{account['user']['id']}/adult-attestation",
                headers=operator_headers, json={
                    "method": "physical_identity_document", "confirmed_over_18": True,
                    "subject_present": True, "subject_consented": True,
                    "account_bound": True, "account_challenge": challenge.json()["challenge"],
                },
            )
            assert attestation.status_code == 200
            return account, headers

        def issue_recovery(account):
            return storage.issue_operator_recovery(
                target_user_id=account["user"]["id"], expires_at=expiry,
                operator_id=operator.id, intended_for="Synthetic recovery subject",
            )

        def redeem_recovery(code):
            return client.post("/api/auth/redeem-operator-recovery", json={"recovery_token": code})

        host, host_headers = enroll("Synthetic Host")
        companion, companion_headers = enroll("Synthetic Companion")
        ping_response = client.post("/api/pings", headers=host_headers, json={
            "category": "grocery", "destination_name": "Biedronka Katowice",
            "destination_lat": 50.2649, "destination_lng": 19.0238,
            "address": "Katowice", "intent_tags": ["zakupy"], "ttl_minutes": 45,
        })
        assert ping_response.status_code == 200
        ping_id = ping_response.json()["id"]
        join_response = client.post(f"/api/pings/{ping_id}/join", headers=companion_headers,
                                    json={"message": "Synthetic coordination test"})
        assert join_response.status_code == 200
        accept = client.post(f"/api/pings/{ping_id}/requests/{join_response.json()['id']}/accept",
                             headers=host_headers)
        assert accept.status_code == 200
        room_id = accept.json()["chat_room_id"]
        ticket_response = client.post("/api/auth/ws-ticket", headers=host_headers)
        assert ticket_response.status_code == 200

        with client.websocket_connect(
            f"/ws?ticket={ticket_response.json()['ticket']}",
            headers={"Origin": "https://recovery.cartmate.example"},
        ) as old_socket:
            assert old_socket.receive_json()["type"] == "connection.ready"
            old_socket.send_json({"action": "subscribe", "scope": f"chat:{room_id}"})
            assert old_socket.receive_json()["type"] == "subscription.confirmed"

            control = client.post(f"/api/chat/rooms/{room_id}/messages", headers=companion_headers,
                                  json={"text": "Synthetic message before recovery"})
            assert control.status_code == 200
            control_frame = old_socket.receive_json()
            assert control_frame["type"] == "chat.message"
            assert control_frame["payload"]["id"] == control.json()["id"]
            observations["active_socket_positive_control"] = True

            # Real recovery route, followed by a NEW private message from the
            # other ordinary member. No in-memory session or WS guard changes.
            recovery = redeem_recovery(issue_recovery(host))
            assert recovery.status_code == 200
            restored = recovery.json()
            restored_headers = {"Authorization": "Bearer " + restored["token"]}
            observations["same_account_recovered"] = restored["user"]["id"] == host["user"]["id"]
            observations["old_rest_session_status"] = client.get("/api/users/me", headers=host_headers).status_code
            observations["restored_rest_session_status"] = client.get("/api/users/me", headers=restored_headers).status_code
            sent = client.post(f"/api/chat/rooms/{room_id}/messages", headers=companion_headers,
                               json={"text": "Synthetic private message after recovery"})
            assert sent.status_code == 200
            message_id = sent.json()["id"]
            # Wake the receive loop AFTER the broadcast to bound a quiet-socket
            # check. Its eventual denial must not conceal an already leaked frame.
            old_socket.send_json({"action": "ping"})
            leaked = False
            closed_code = None
            for _ in range(8):
                try:
                    frame = old_socket.receive_json()
                except WebSocketDisconnect as rejection:
                    closed_code = rejection.code
                    break
                if frame.get("type") == "chat.message" and frame["payload"]["id"] == message_id:
                    leaked = True
            observations["revoked_socket_received_new_private_message"] = leaked
            observations["revoked_socket_eventual_close_code"] = closed_code

        # Fault injection only at the session persistence boundary in this
        # isolated process. It models an exception, not a physical disk crash.
        failure_code = issue_recovery(host)
        with patch.object(main, "persist_active_session", side_effect=RuntimeError("synthetic persistence failure")):
            failed = redeem_recovery(failure_code)
        prior_status = client.get("/api/users/me", headers=restored_headers).status_code
        retry = redeem_recovery(failure_code)
        conn = get_db_connection(storage.db_path)
        try:
            session_count = conn.execute("SELECT COUNT(*) FROM sessions WHERE user_id = ?",
                                         (host["user"]["id"],)).fetchone()[0]
        finally:
            conn.close()
        observations.update({
            "recovery_session_persistence_failure_status": failed.status_code,
            "prior_session_after_failed_recovery_status": prior_status,
            "same_recovery_code_retry_status": retry.status_code,
            "host_sessions_after_failed_recovery_and_retry": session_count,
        })
        # Negative control: recovery must NEVER restore a revoked admission.
        revoked_code = issue_recovery(companion)
        assert storage.revoke_operator_admission(companion["user"]["id"])
        observations["revoked_admission_recovery_status"] = redeem_recovery(revoked_code).status_code

    failures = []
    if not observations["same_account_recovered"] or observations["old_rest_session_status"] != 401:
        failures.append("recovery_account_or_rest_boundary")
    if observations["restored_rest_session_status"] != 200:
        failures.append("replacement_session_not_usable")
    if observations["revoked_socket_received_new_private_message"]:
        failures.append("private_message_after_session_revocation")
    if observations["revoked_socket_eventual_close_code"] != 1008:
        failures.append("revoked_socket_not_closed_by_policy")
    if observations["same_recovery_code_retry_status"] != 200:
        failures.append("failed_recovery_burns_code_without_retry")
    if observations["revoked_admission_recovery_status"] != 403:
        failures.append("revoked_admission_restored")
    observations["findings"] = failures
    print(MARKER + json.dumps(observations, sort_keys=True))
    return int(bool(failures))


def main():
    if os.environ.get("CODEX_RECOVERY_ISOLATED_CHILD") == "1":
        sys.path.insert(0, str(ROOT / "backend"))
        return probe()
    with tempfile.TemporaryDirectory(prefix="cartmate-codex-recovery-") as scratch:
        env = os.environ.copy()
        env.update({
            "CODEX_RECOVERY_ISOLATED_CHILD": "1", "CARTMATE_ENV": "staging",
            "CARTMATE_DEPLOYMENT": "0", "CARTMATE_DATABASE_PATH": str(Path(scratch) / "probe.db"),
            "CARTMATE_OPERATOR_PILOT_ENABLED": "1", "CARTMATE_MANUAL_AGE_PILOT_ENABLED": "1",
            "CARTMATE_PILOT_INVITES_ENABLED": "0", "CARTMATE_MODERATOR_USER_IDS": "usr_codex_recovery_operator",
            "CARTMATE_CORS_ALLOWED_ORIGINS": "https://recovery.cartmate.example",
            "CARTMATE_STAGING_ALLOWED_PHONES": "", "CARTMATE_DEFAULT_REGION": "silesia",
            "CARTMATE_FRONTEND_DIST": "", "OTP_PROVIDER": "console", "SOS_PROVIDER": "disabled",
            "SOS_WEBHOOK_SECRET": secrets.token_urlsafe(24), "JEV_MODE": "disabled",
            "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
        })
        try:
            completed = subprocess.run(
                [sys.executable, str(Path(__file__).resolve())], cwd=ROOT / "backend", env=env,
                capture_output=True, text=True, timeout=45, check=False,
            )
        except subprocess.TimeoutExpired:
            print("Recovery probe incomplete: bounded child timed out; no acceptance result.")
            return 2
        results = [line for line in completed.stdout.splitlines() if line.startswith(MARKER)]
        if not results:
            import re
            print("Recovery probe incomplete: isolated setup/runtime failed; no acceptance result.")
            locations = re.findall(r'File "([^"]+)", line (\d+)', completed.stderr)
            print("Trace locations: " + ", ".join(f"{Path(name).name}:{line}" for name, line in locations[-4:]))
            errors = completed.stderr.strip().splitlines()
            if errors:
                print("Exception type: " + errors[-1].split(":", 1)[0])
            return 2
        print(results[-1])
        return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
