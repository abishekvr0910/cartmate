"""The server reports the voice-hours policy that is actually in force.

Four states exist: `unrestricted` (no window enforced, as on staging), `open` and `closed`
(an enforced 18:00-23:00 Europe/Warsaw window), and `unavailable` (enforced, but Warsaw time
cannot be resolved, so calls stay closed). Cooldowns and daily limits are separate rules.
"""

import asyncio
import zoneinfo
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

import voice_manager
from main import app, voice_call_manager
from storage import get_db_connection
from test_voice_calls import clean_db  # noqa: F401  (shared fixture: disposable database and users)

client = TestClient(app)
HEADERS = {"Authorization": "Bearer token_zuzanna"}
WARSAW = ZoneInfo("Europe/Warsaw")
SCHEDULED_HOURS = {"start": "18:00", "end": "23:00", "timezone": "Europe/Warsaw"}


@pytest.fixture
def window_env(monkeypatch):
    """Starts every test from a known policy: development, no explicit enforcement."""
    monkeypatch.setenv("CARTMATE_ENV", "development")
    monkeypatch.delenv("CARTMATE_VOICE_WINDOW_ENFORCED", raising=False)
    return monkeypatch


@pytest.fixture
def freeze_clock(monkeypatch):
    class FrozenDatetime(datetime):
        frozen_at = datetime(2026, 11, 16, 12, 0, tzinfo=WARSAW)

        @classmethod
        def now(cls, tz=None):
            return cls.frozen_at.astimezone(tz) if tz else cls.frozen_at

    monkeypatch.setattr(voice_manager, "datetime", FrozenDatetime)

    def _freeze(moment: datetime) -> None:
        FrozenDatetime.frozen_at = moment

    return _freeze


@pytest.fixture
def timezone_data_missing(monkeypatch):
    def _missing(key):
        raise zoneinfo.ZoneInfoNotFoundError(f"No time zone found with key {key}")

    monkeypatch.setattr(zoneinfo, "ZoneInfo", _missing)


def _record_completed_call(db_path: str, call_id: str, ended: datetime) -> None:
    stamp = ended.strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = get_db_connection(db_path)
    conn.execute(
        "INSERT INTO voice_call_sessions (id, user_a_id, user_b_id, topic, status, created_at, ended_at, duration_seconds) "
        "VALUES (?, 'usr_zuzanna', 'usr_jakub', 'test', 'completed', ?, ?, 300);",
        (call_id, stamp, stamp),
    )
    conn.commit()
    conn.close()


def test_unenforced_environments_are_unrestricted(window_env, freeze_clock):
    freeze_clock(datetime(2026, 11, 16, 3, 0, tzinfo=WARSAW))  # 03:00, far outside 18:00-23:00

    for environment in ("development", "staging"):
        window_env.setenv("CARTMATE_ENV", environment)
        policy = voice_manager.describe_voice_window()
        assert policy == {
            "window_state": "unrestricted",
            "window_open": True,
            "window_enforced": False,
            "window_hours": None,
            "window_schedule": None,
        }, environment
        assert voice_manager.is_voice_window_open() is True


def test_unenforced_window_ignores_missing_timezone_data(window_env, timezone_data_missing):
    assert voice_manager.get_voice_window_state() == "unrestricted"


@pytest.mark.parametrize("enforcement", ["flag", "production"])
def test_enforced_window_is_open_then_closed_by_warsaw_time(window_env, freeze_clock, enforcement):
    if enforcement == "flag":
        window_env.setenv("CARTMATE_VOICE_WINDOW_ENFORCED", "1")
    else:
        window_env.setenv("CARTMATE_ENV", "production")

    freeze_clock(datetime(2026, 11, 16, 19, 30, tzinfo=WARSAW))
    assert voice_manager.describe_voice_window() == {
        "window_state": "open",
        "window_open": True,
        "window_enforced": True,
        "window_hours": SCHEDULED_HOURS,
        "window_schedule": "Codziennie 18:00 - 23:00",
    }

    freeze_clock(datetime(2026, 11, 16, 12, 0, tzinfo=WARSAW))
    closed = voice_manager.describe_voice_window()
    assert closed["window_state"] == "closed"
    assert closed["window_open"] is False
    assert closed["window_hours"] == SCHEDULED_HOURS
    assert voice_manager.is_voice_window_open() is False


@pytest.mark.parametrize("enforcement", ["flag", "production"])
def test_enforced_window_without_timezone_data_is_unavailable_and_closed(window_env, timezone_data_missing, enforcement):
    if enforcement == "flag":
        window_env.setenv("CARTMATE_VOICE_WINDOW_ENFORCED", "1")
    else:
        window_env.setenv("CARTMATE_ENV", "production")

    policy = voice_manager.describe_voice_window()
    assert policy["window_state"] == "unavailable"
    assert policy["window_open"] is False
    assert policy["window_enforced"] is True
    assert voice_manager.is_voice_window_open() is False


@pytest.mark.parametrize(
    "utc_moment, expected",
    [
        # Winter (CET, UTC+1): the window is 17:00-22:00 UTC.
        (datetime(2026, 12, 1, 16, 59, tzinfo=timezone.utc), "closed"),
        (datetime(2026, 12, 1, 17, 0, tzinfo=timezone.utc), "open"),
        (datetime(2026, 12, 1, 21, 59, tzinfo=timezone.utc), "open"),
        (datetime(2026, 12, 1, 22, 0, tzinfo=timezone.utc), "closed"),
        # Summer (CEST, UTC+2): the window is 16:00-21:00 UTC.
        (datetime(2026, 7, 1, 15, 59, tzinfo=timezone.utc), "closed"),
        (datetime(2026, 7, 1, 16, 0, tzinfo=timezone.utc), "open"),
        (datetime(2026, 7, 1, 20, 59, tzinfo=timezone.utc), "open"),
        (datetime(2026, 7, 1, 21, 0, tzinfo=timezone.utc), "closed"),
        # The evening before and the evening of the spring change (29 March 2026).
        (datetime(2026, 3, 28, 16, 30, tzinfo=timezone.utc), "closed"),
        (datetime(2026, 3, 29, 16, 30, tzinfo=timezone.utc), "open"),
        # The evening before and the evening of the autumn change (25 October 2026).
        (datetime(2026, 10, 24, 16, 30, tzinfo=timezone.utc), "open"),
        (datetime(2026, 10, 25, 16, 30, tzinfo=timezone.utc), "closed"),
    ],
)
def test_window_boundaries_follow_warsaw_daylight_saving(window_env, freeze_clock, utc_moment, expected):
    window_env.setenv("CARTMATE_VOICE_WINDOW_ENFORCED", "1")
    freeze_clock(utc_moment)
    assert voice_manager.get_voice_window_state() == expected


def test_status_endpoint_reports_each_window_state(clean_db, window_env, freeze_clock):  # noqa: F811
    unrestricted = client.get("/api/voice/status", headers=HEADERS).json()
    assert unrestricted["window_state"] == "unrestricted"
    assert unrestricted["window_open"] is True
    assert unrestricted["window_enforced"] is False
    assert unrestricted["window_hours"] is None
    assert unrestricted["window_schedule"] is None

    window_env.setenv("CARTMATE_VOICE_WINDOW_ENFORCED", "1")
    freeze_clock(datetime(2026, 11, 16, 19, 30, tzinfo=WARSAW))
    opened = client.get("/api/voice/status", headers=HEADERS).json()
    assert opened["window_state"] == "open"
    assert opened["window_open"] is True
    assert opened["window_hours"] == SCHEDULED_HOURS

    freeze_clock(datetime(2026, 11, 16, 9, 0, tzinfo=WARSAW))
    closed = client.get("/api/voice/status", headers=HEADERS).json()
    assert closed["window_state"] == "closed"
    assert closed["window_open"] is False
    assert closed["window_hours"] == SCHEDULED_HOURS


def test_status_endpoint_reports_unavailable_when_timezone_data_is_missing(
    clean_db, window_env, timezone_data_missing  # noqa: F811
):
    window_env.setenv("CARTMATE_VOICE_WINDOW_ENFORCED", "1")
    data = client.get("/api/voice/status", headers=HEADERS).json()
    assert data["window_state"] == "unavailable"
    assert data["window_open"] is False
    # The rest of the status is still served, so the screen can explain itself.
    assert data["daily_limit"] == 3


@pytest.mark.parametrize("window", ["unrestricted", "open"])
def test_cooldown_and_daily_limit_apply_whenever_calls_are_allowed(clean_db, window_env, freeze_clock, window):  # noqa: F811
    if window == "open":
        window_env.setenv("CARTMATE_VOICE_WINDOW_ENFORCED", "1")
        freeze_clock(datetime(2026, 11, 16, 19, 30, tzinfo=WARSAW))
    now = datetime.now(timezone.utc)

    _record_completed_call(clean_db, "vcall_recent", now - timedelta(seconds=60))
    status = client.get("/api/voice/status", headers=HEADERS).json()
    assert status["window_state"] == window
    assert 0 < status["cooldown_remaining_seconds"] <= 600
    assert status["daily_calls_used"] == 1
    result, _ = asyncio.run(voice_call_manager.enqueue_caller("usr_zuzanna", "test", None))
    assert result.startswith("COOLDOWN_ACTIVE_")

    _record_completed_call(clean_db, "vcall_2", now - timedelta(hours=2))
    _record_completed_call(clean_db, "vcall_3", now - timedelta(hours=3))
    conn = get_db_connection(clean_db)
    old = (now - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("UPDATE voice_call_sessions SET ended_at = ?, created_at = ? WHERE id = 'vcall_recent';", (old, old))
    conn.commit()
    conn.close()

    status = client.get("/api/voice/status", headers=HEADERS).json()
    assert status["cooldown_remaining_seconds"] == 0
    assert status["daily_calls_used"] == 3
    result, _ = asyncio.run(voice_call_manager.enqueue_caller("usr_zuzanna", "test", None))
    assert result == "DAILY_LIMIT_REACHED"


def test_closed_window_still_reports_cooldown_and_usage(clean_db, window_env, freeze_clock):  # noqa: F811
    window_env.setenv("CARTMATE_VOICE_WINDOW_ENFORCED", "1")
    freeze_clock(datetime(2026, 11, 16, 9, 0, tzinfo=WARSAW))
    _record_completed_call(clean_db, "vcall_recent", datetime.now(timezone.utc) - timedelta(seconds=60))

    status = client.get("/api/voice/status", headers=HEADERS).json()
    assert status["window_state"] == "closed"
    assert 0 < status["cooldown_remaining_seconds"] <= 600
    assert status["daily_calls_used"] == 1

    result, call = asyncio.run(voice_call_manager.enqueue_caller("usr_zuzanna", "test", None))
    assert result == "WINDOW_CLOSED"
    assert call is None
    assert "usr_zuzanna" not in voice_call_manager.queue


def test_refusal_message_matches_the_reason_calls_are_closed(window_env, freeze_clock, monkeypatch):
    window_env.setenv("CARTMATE_VOICE_WINDOW_ENFORCED", "1")
    freeze_clock(datetime(2026, 11, 16, 9, 0, tzinfo=WARSAW))
    assert "18:00 - 23:00" in voice_manager.voice_window_refusal_message()

    def _missing(key):
        raise zoneinfo.ZoneInfoNotFoundError(key)

    monkeypatch.setattr(zoneinfo, "ZoneInfo", _missing)
    message = voice_manager.voice_window_refusal_message()
    assert "niedostępne" in message
    assert "18:00" not in message
