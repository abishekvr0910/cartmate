"""Independent local diagnostic; no live DB, provider calls, or network listener.

Run from the repository root: python qa/codex_private_pilot_probe.py
Exit 1 means a review finding was reproduced, not a passing acceptance suite.
The parent launches a bounded subprocess against a temporary SQLite database.
Only sanitized observations are printed; app code is never edited.
"""

import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def swallowed_rejection_assertions() -> int:
    """Run the actual two negative-test blocks against an accepting test double.

    This is test-sensitivity analysis, NOT an application authorization bypass.
    No working source, route or security guard is modified.
    """
    import ast
    from contextlib import nullcontext

    source = ast.parse((ROOT / "backend" / "test_private_pilot_review.py").read_text(encoding="utf-8"))
    function = next(n for n in source.body if isinstance(n, ast.FunctionDef)
                    and n.name == "test_rt06_websocket_tickets_origins_and_frames")
    call = next(n for n in ast.walk(function) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name) and n.func.id == "run_isolated_probe")
    script = ast.parse(ast.literal_eval(call.args[1]))

    class AcceptingClient:
        @staticmethod
        def websocket_connect(*args, **kwargs):
            return nullcontext(object())

    swallowed = 0
    for block in (n for n in script.body if isinstance(n, ast.Try)):
        # Supply no real credentials or network objects to these isolated blocks.
        scope = {"client": AcceptingClient(), "ticket": "synthetic", "ticket2": "synthetic"}
        try:
            exec(compile(ast.Module(body=[block], type_ignores=[]), "<rejection-test-sensitivity>", "exec"), scope)
        except AssertionError:
            continue  # Correct test behavior: unexpected acceptance was detected.
        swallowed += 1
    return swallowed


def probe() -> int:
    from datetime import datetime, timedelta, timezone
    import secrets
    from unittest.mock import patch

    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect
    from models import UserPrivateSchema
    from storage import get_db_connection, storage

    # Synthetic trusted operator fixture; no adult flags or bypasses are granted.
    expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    operator = UserPrivateSchema(
        id="usr_codex_review_operator", name="Review Operator", avatar="", bio="",
        trust_tier="Bronze", gender="unspecified", city="Katowice",
        email="operator@review.invalid", phone="",
    )
    storage.redeem_operator_activation(
        storage.issue_operator_activation(expiry, intended_for="Review operator"),
        operator.model_dump(),
    )
    import main

    operator_session = "cmt_" + secrets.token_hex(20)
    main.persist_active_session(operator_session, operator.id)
    client = TestClient(main.app, raise_server_exceptions=False)
    operator_headers = {"Authorization": "Bearer " + operator_session}

    def activation(name):
        return storage.issue_operator_activation(expiry, intended_for=name)

    def redeem(code, name="Review Participant"):
        return client.post("/api/auth/redeem-operator-activation", json={
            "activation_token": code, "name": name, "city": "Katowice",
        })

    code = activation("Review Participant")
    enrolled = redeem(code)
    assert enrolled.status_code == 200
    account = enrolled.json()
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

    ticket_response = client.post("/api/auth/ws-ticket", headers=headers)
    assert ticket_response.status_code == 200
    ticket = ticket_response.json()["ticket"]
    origin_result = "accepted"
    try:
        with client.websocket_connect(
            f"/ws?ticket={ticket}", headers={"Origin": "http://127.0.0.1:8010"},
        ) as ws:
            assert ws.receive_json()["type"] == "connection.ready"
    except WebSocketDisconnect as rejection:
        origin_result = f"rejected:{rejection.code}"

    # Positive control: the same real account works with the configured origin.
    control_ticket = client.post("/api/auth/ws-ticket", headers=headers).json()["ticket"]
    with client.websocket_connect(
        f"/ws?ticket={control_ticket}", headers={"Origin": "https://staging.cartmate.example"},
    ) as ws:
        assert ws.receive_json()["type"] == "connection.ready"

    logout = client.post("/api/auth/logout", headers=headers)
    after_logout = client.get("/api/users/me", headers=headers)
    replay = redeem(code)
    recovery_code = storage.issue_operator_recovery(
        target_user_id=account["user"]["id"],
        expires_at=expiry,
        operator_id=operator.id,
        intended_for="Review Participant",
    )
    replacement = client.post("/api/auth/redeem-operator-recovery", json={
        "recovery_token": recovery_code,
    })
    assert replacement.status_code == 200
    same_account = replacement.json()["user"]["id"] == account["user"]["id"]

    # Fault injection is confined to this disposable subprocess. It models a
    # persistence error after activation has committed, not a real disk failure.
    failed_code = activation("Review interrupted activation")
    with patch.object(main, "persist_active_session", side_effect=RuntimeError("synthetic persistence failure")):
        failed_response = redeem(failed_code, "Review interrupted activation")
    retry_response = redeem(failed_code, "Review interrupted activation")
    conn = get_db_connection(storage.db_path)
    try:
        stranded = conn.execute(
            "SELECT COUNT(*) FROM operator_admissions a "
            "JOIN users u ON u.id=a.user_id "
            "LEFT JOIN sessions s ON s.user_id=a.user_id "
            "WHERE json_extract(u.data_json, '$.name') = ? AND s.user_id IS NULL",
            ("Review interrupted activation",),
        ).fetchone()[0]
    finally:
        conn.close()

    result = {
        "negative_ws_tests_swallow_unexpected_acceptance": swallowed_rejection_assertions(),
        "browser_harness_origin": origin_result,
        "configured_https_origin_positive_control": "connection.ready",
        "logout_status": logout.status_code,
        "old_session_status": after_logout.status_code,
        "consumed_activation_replay_status": replay.status_code,
        "fresh_activation_recovers_same_account": same_account,
        "session_persistence_failure_status": failed_response.status_code,
        "retry_after_persistence_failure_status": retry_response.status_code,
        "admitted_accounts_stranded_without_session": stranded,
    }
    print("CODEX_PROBE=" + json.dumps(result, sort_keys=True))
    return int(origin_result != "accepted" or not same_account or stranded > 0
               or result["negative_ws_tests_swallow_unexpected_acceptance"] > 0)


def main() -> int:
    if os.environ.get("CODEX_REVIEW_ISOLATED_CHILD") == "1":
        sys.path.insert(0, str(ROOT / "backend"))
        return probe()
    with tempfile.TemporaryDirectory(prefix="cartmate-codex-review-") as scratch:
        env = os.environ.copy()
        env.update({
            "CODEX_REVIEW_ISOLATED_CHILD": "1", "CARTMATE_ENV": "staging",
            "CARTMATE_DEPLOYMENT": "0", "CARTMATE_DATABASE_PATH": str(Path(scratch) / "probe.db"),
            "CARTMATE_OPERATOR_PILOT_ENABLED": "1", "CARTMATE_MANUAL_AGE_PILOT_ENABLED": "1",
            "CARTMATE_PILOT_INVITES_ENABLED": "0", "CARTMATE_MODERATOR_USER_IDS": "usr_codex_review_operator",
            "CARTMATE_CORS_ALLOWED_ORIGINS": "https://staging.cartmate.example,http://127.0.0.1:8010",
            "CARTMATE_STAGING_ALLOWED_PHONES": "", "CARTMATE_DEFAULT_REGION": "silesia",
            "CARTMATE_FRONTEND_DIST": "", "OTP_PROVIDER": "console", "SOS_PROVIDER": "disabled",
            "SOS_WEBHOOK_SECRET": secrets.token_urlsafe(24),
            "JEV_MODE": "disabled", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
        })
        completed = subprocess.run(
            [sys.executable, str(Path(__file__).resolve())], cwd=ROOT / "backend",
            env=env, capture_output=True, text=True, timeout=45, check=False,
        )
        observations = [line for line in completed.stdout.splitlines() if line.startswith("CODEX_PROBE=")]
        if not observations:
            # Do not expose exception bodies or potentially sensitive logs.
            print("Probe incomplete: isolated setup/runtime failed; no acceptance result.")
            import re
            locations = re.findall(r'File "([^"]+)", line (\d+)', completed.stderr)
            print("Trace locations: " + ", ".join(f"{Path(name).name}:{line}" for name, line in locations[-4:]))
            error_lines = completed.stderr.strip().splitlines()
            if error_lines:
                print("Exception type: " + error_lines[-1].split(":", 1)[0])
            return 2
        print(observations[-1])
        return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
