"""Regression checks for OTP durability and post-match privacy boundaries."""

import asyncio
import logging

from fastapi.testclient import TestClient

import auth_providers
import database
import main
from sanitizer import SensitiveDataLogFilter
from storage import DurableStorage


def test_otp_survives_manager_restart_and_is_single_use(tmp_path, monkeypatch):
    phone = "+48600111223"
    store = DurableStorage(str(tmp_path / "otp.db"))
    captured = {}

    class CaptureProvider:
        async def send_otp(self, identifier, code):
            captured[identifier] = code
            return True

    monkeypatch.setattr(auth_providers, "get_otp_provider", lambda: CaptureProvider())
    first_process = auth_providers.OtpManager(store)
    sent = asyncio.run(first_process.request_otp(phone))
    assert sent["status"] == "sent"
    assert len(captured[phone]) == 6
    assert captured[phone].isdigit()

    second_process = auth_providers.OtpManager(DurableStorage(str(tmp_path / "otp.db")))
    assert asyncio.run(second_process.verify_otp(phone, captured[phone]))["valid"] is True
    assert asyncio.run(second_process.verify_otp(phone, captured[phone]))["valid"] is False


def test_otp_resend_cannot_reset_persisted_attempt_budget(tmp_path):
    phone = "+48600111224"
    store = DurableStorage(str(tmp_path / "otp-limits.db"))
    assert store.reserve_otp_challenge(phone, "123456", now=1000)["status"] == "reserved"
    assert store.reserve_otp_challenge(phone, "654321", now=1001)["status"] == "rate_limited"

    for remaining in (4, 3, 2, 1):
        failed = store.consume_otp_challenge(phone, "000000", now=1002)
        assert failed == {"status": "invalid", "attempts_left": remaining}

    restarted = DurableStorage(str(tmp_path / "otp-limits.db"))
    assert restarted.reserve_otp_challenge(phone, "654321", now=1061)["status"] == "reserved"
    assert restarted.consume_otp_challenge(phone, "000000", now=1062)["attempts_left"] == 4
    assert restarted.consume_otp_challenge(phone, "654321", now=1063)["status"] == "locked"
    assert restarted.reserve_otp_challenge(phone, "111111", now=1122)["status"] == "rate_limited"


def test_invite_sms_budget_survives_process_restart(tmp_path):
    db_path = str(tmp_path / "otp-invite-budget.db")
    first_process = DurableStorage(db_path)
    assert first_process.reserve_otp_send_budget("invite:one", 2, 900, now=1000) == (True, 0)
    second_process = DurableStorage(db_path)
    assert second_process.reserve_otp_send_budget("invite:one", 2, 900, now=1001) == (True, 0)
    assert second_process.reserve_otp_send_budget("invite:one", 2, 900, now=1002)[0] is False
    assert second_process.reserve_otp_send_budget("invite:one", 2, 900, now=1901) == (True, 0)


def test_blocked_trip_contacts_and_broadcasts_are_redacted():
    trip = database.TRIPS["trip_makro_01"]
    host_id, companion_id = trip.host.id, trip.companion.id
    original_blocks = {
        pair for pair in ((host_id, companion_id), (companion_id, host_id))
        if pair in database.BLOCKED_USERS
    }
    database.unblock_user(host_id, companion_id)
    database.unblock_user(companion_id, host_id)
    client = TestClient(main.app)
    host_headers = {"Authorization": "Bearer token_jakub"}
    companion_headers = {"Authorization": "Bearer token_zuzanna"}

    try:
        before = client.get(f"/api/trips/{trip.id}", headers=host_headers)
        assert before.status_code == 200
        assert before.json()["companion"]["phone"]
        assert main.build_trip_response(trip).companion.phone is None
        assert main.build_trip_response(trip).host.phone is None

        blocked = client.post(f"/api/users/{companion_id}/block", headers=host_headers)
        assert blocked.status_code == 200
        for headers in (host_headers, companion_headers):
            response = client.get(f"/api/trips/{trip.id}", headers=headers)
            assert response.status_code == 200
            assert response.json()["host"]["phone"] is None
            assert response.json()["companion"]["phone"] is None
    finally:
        for blocker_id, blocked_id in ((host_id, companion_id), (companion_id, host_id)):
            if (blocker_id, blocked_id) in original_blocks:
                database.block_user(blocker_id, blocked_id)
            else:
                database.unblock_user(blocker_id, blocked_id)


def test_log_filter_redacts_phone_code_and_token():
    record = logging.LogRecord(
        name="cartmate.test", level=logging.INFO, pathname=__file__, lineno=1,
        msg="OTP code=123456 for +48 600 111 222 Bearer cmt_1234567890abcdef",
        args=(), exc_info=None,
    )
    SensitiveDataLogFilter().filter(record)
    message = record.getMessage()
    assert "123456" not in message
    assert "600 111 222" not in message
    assert "cmt_1234567890abcdef" not in message
    assert "[REDACTED_CODE]" in message
    assert "[REDACTED_PHONE]" in message
