"""Closed-pilot admission tests; no real SMS or user data."""

import secrets
import sqlite3
import os
import logging
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

import main
from storage import DurableStorage, get_db_connection, pilot_invite_hash, storage
from sanitizer import SensitiveDataLogFilter
from config import OPERATIONAL_THRESHOLDS


def future_expiry():
    return (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()


def test_invite_is_single_use_revocable_and_atomic(tmp_path):
    db = DurableStorage(str(tmp_path / "pilot-invites.db"))
    code = db.issue_pilot_invite(future_expiry())
    assert db.is_pilot_invite_available(code)

    db.persist_user_with_pilot_invite(
        {"id": "usr_pilot_1", "email": "first@example.invalid", "phone": "+48600111001", "phone_verified_at": datetime.now(timezone.utc).isoformat()},
        code,
    )
    assert db.is_pilot_member("usr_pilot_1")
    assert not db.is_pilot_invite_available(code)
    with pytest.raises(ValueError):
        db.persist_user_with_pilot_invite(
            {"id": "usr_pilot_2", "email": "second@example.invalid", "phone": "+48600111002", "phone_verified_at": datetime.now(timezone.utc).isoformat()},
            code,
        )

    duplicate_code = db.issue_pilot_invite(future_expiry())
    with pytest.raises(sqlite3.IntegrityError):
        db.persist_user_with_pilot_invite(
            {"id": "usr_pilot_3", "email": "first@example.invalid", "phone": "+48600111003", "phone_verified_at": datetime.now(timezone.utc).isoformat()},
            duplicate_code,
        )
    assert db.is_pilot_invite_available(duplicate_code), "Failed account creation must not consume an invite"

    revoked_code = db.issue_pilot_invite(future_expiry())
    assert db.revoke_pilot_invite(revoked_code)
    assert not db.is_pilot_invite_available(revoked_code)
    assert not db.revoke_pilot_invite(revoked_code)

    expired_code = db.issue_pilot_invite(future_expiry())
    conn = get_db_connection(db.db_path)
    try:
        conn.execute(
            "UPDATE pilot_invites SET expires_at = ? WHERE code_hash = ?",
            ("2000-01-01T00:00:00+00:00", pilot_invite_hash(expired_code)),
        )
        conn.commit()
    finally:
        conn.close()
    assert not db.is_pilot_invite_available(expired_code)


def test_invite_concurrent_redemption_has_one_winner(tmp_path):
    db = DurableStorage(str(tmp_path / "pilot-race.db"))
    code = db.issue_pilot_invite(future_expiry())
    barrier = Barrier(2)

    def redeem(index):
        barrier.wait()
        try:
            db.persist_user_with_pilot_invite(
                {
                    "id": f"usr_race_{index}",
                    "email": f"race{index}@example.invalid",
                    "phone": f"+4860011200{index}",
                    "phone_verified_at": datetime.now(timezone.utc).isoformat(),
                },
                code,
            )
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(redeem, (1, 2)))
    assert sorted(results) == [False, True]
    assert sum(db.is_pilot_member(f"usr_race_{index}") for index in (1, 2)) == 1


def test_production_invites_cannot_be_disabled_by_environment_flag():
    env = os.environ.copy()
    env.update({"CARTMATE_ENV": "production", "CARTMATE_DEPLOYMENT": "0", "CARTMATE_PILOT_INVITES_ENABLED": "0"})
    checked = subprocess.run(
        [sys.executable, "-c", "from config import PILOT_INVITES_ENABLED; print(PILOT_INVITES_ENABLED)"],
        cwd=os.path.dirname(__file__),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert checked.stdout.strip() == "True"


def test_pilot_invite_redacted_from_formatted_log_arguments():
    code = "CM-" + "A" * 24
    record = logging.LogRecord("cartmate.test", logging.INFO, __file__, 1, "invite=%s", (code,), None)
    SensitiveDataLogFilter().filter(record)
    assert code not in record.getMessage()
    assert "[REDACTED_PILOT_INVITE]" in record.getMessage()


def test_pilot_requires_invite_and_preserves_member_login(monkeypatch):
    monkeypatch.setattr(main, "PILOT_INVITES_ENABLED", True)
    client = TestClient(main.app)
    suffix = f"{secrets.randbelow(900000000) + 100000000:09d}"
    phone = f"+48{suffix}"
    code = storage.issue_pilot_invite(future_expiry())

    assert client.post("/api/auth/otp/request", json={"identifier": phone}).status_code == 403
    requested = client.post("/api/auth/otp/request", json={"identifier": phone, "invite_code": code})
    assert requested.status_code == 200
    otp = requested.json()["dev_code"]
    assert otp and otp.isdigit()
    assert client.post("/api/auth/otp/verify", json={"identifier": phone, "code": otp}).status_code == 403

    registered = client.post("/api/auth/register", json={
        "name": "Pilot Member", "email": f"pilot.{suffix}@example.invalid", "phone": phone,
        "gender": "other", "city": "Katowice", "otp_code": otp, "invite_code": code,
    })
    assert registered.status_code == 200, registered.text
    assert registered.json()["user"]["avatar"] == ""
    user_id = registered.json()["user"]["id"]
    token = registered.json()["token"]
    assert storage.is_pilot_member(user_id)
    assert client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert not storage.is_pilot_invite_available(code)

    other_phone = f"+48{secrets.randbelow(900000000) + 100000000:09d}"
    assert client.post("/api/auth/otp/request", json={"identifier": other_phone, "invite_code": code}).status_code == 403

    login_request = client.post("/api/auth/otp/request", json={"identifier": phone})
    assert login_request.status_code == 200
    login_otp = login_request.json()["dev_code"]
    login = client.post("/api/auth/otp/verify", json={"identifier": phone, "code": login_otp})
    assert login.status_code == 200


def test_one_invite_cannot_fan_out_unlimited_otp_messages(monkeypatch):
    monkeypatch.setattr(main, "PILOT_INVITES_ENABLED", True)
    client = TestClient(main.app)
    code = storage.issue_pilot_invite(future_expiry())
    phone_prefix = f"{secrets.randbelow(90_000) + 10_000:05d}"
    for index in range(OPERATIONAL_THRESHOLDS.rate_limit_otp_requests_per_15m):
        sent = client.post("/api/auth/otp/request", json={
            "identifier": f"+48{phone_prefix}{index:04d}", "invite_code": code,
        })
        assert sent.status_code == 200, sent.text
    blocked = client.post("/api/auth/otp/request", json={
        "identifier": f"+48{phone_prefix}9999", "invite_code": code,
    })
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_pilot_rejects_existing_uninvited_sessions(monkeypatch):
    monkeypatch.setattr(main, "PILOT_INVITES_ENABLED", True)
    client = TestClient(main.app)
    assert client.get("/api/users/me", headers={"Authorization": "Bearer token_jakub"}).status_code == 403


def test_pilot_readiness_rejects_unadmitted_moderator(monkeypatch):
    monkeypatch.setattr(main, "PILOT_INVITES_ENABLED", True)
    monkeypatch.setattr(main, "MODERATOR_USER_IDS", frozenset({"usr_zuzanna"}))
    client = TestClient(main.app)
    ready = client.get("/api/ready")
    assert ready.status_code == 503
    assert any("moderator" in blocker for blocker in ready.json()["blockers"])
