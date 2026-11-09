import asyncio
import os
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from main import app, voice_call_manager
from storage import DurableStorage, get_db_connection

client = TestClient(app)

@pytest.fixture
def clean_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_voice_calls.db")
    monkeypatch.setenv("CARTMATE_DATABASE_PATH", test_db)
    monkeypatch.setenv("CARTMATE_ENV", "development")
    from storage import storage
    old_db_path = storage.db_path
    storage.db_path = test_db
    storage._ensure_parent_dir()
    storage.apply_migrations()

    # Reset in-memory voice manager state
    voice_call_manager.queue.clear()
    voice_call_manager.active_calls.clear()
    voice_call_manager.user_to_call.clear()
    for task in voice_call_manager.call_timer_tasks.values():
        if not task.done():
            task.cancel()
    voice_call_manager.call_timer_tasks.clear()

    # Populate test users
    conn = get_db_connection(test_db)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("""
        INSERT INTO users (id, email, phone, data_json, created_at, updated_at)
        VALUES ('usr_zuzanna', 'zuzanna@example.pl', '+48601234567', '{"name":"Zuzanna", "city":"Katowice"}', ?, ?)
    """, (now_str, now_str))
    conn.execute("""
        INSERT INTO users (id, email, phone, data_json, created_at, updated_at)
        VALUES ('usr_jakub', 'jakub@example.pl', '+48502876543', '{"name":"Jakub", "city":"Gliwice"}', ?, ?)
    """, (now_str, now_str))
    conn.execute("""
        INSERT INTO users (id, email, phone, data_json, created_at, updated_at)
        VALUES ('usr_marek', 'marek@example.pl', '+48500111222', '{"name":"Marek", "city":"Katowice"}', ?, ?)
    """, (now_str, now_str))
    conn.commit()
    conn.close()

    yield test_db

    storage.db_path = old_db_path


def test_voice_status_endpoint(clean_db):
    headers_zuzanna = {"Authorization": "Bearer token_zuzanna"}
    res = client.get("/api/voice/status", headers=headers_zuzanna)
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == "usr_zuzanna"
    assert data["daily_calls_used"] == 0
    assert data["daily_limit"] == 3
    assert data["cooldown_remaining_seconds"] == 0
    assert data["is_in_queue"] is False
    assert data["active_call"] is None
    assert len(data["icebreakers"]) >= 3
    assert "ice_servers" in data
    assert any("stun:" in str(s) for s in data["ice_servers"])
    assert any("turn:" in str(s) for s in data["ice_servers"])


def test_voice_matching_flow(clean_db):
    async def _test():
        class MockWebSocket:
            def __init__(self, uid):
                self.uid = uid
                self.sent_messages = []

            async def send_text(self, text):
                self.sent_messages.append(text)

        ws_zuzanna = MockWebSocket("usr_zuzanna")
        ws_jakub = MockWebSocket("usr_jakub")

        # 1. Zuzanna enqueues
        status_1, data_1 = await voice_call_manager.enqueue_caller("usr_zuzanna", "Ulubiona książka", ws_zuzanna)
        assert status_1 == "QUEUED"
        assert data_1 is None
        assert "usr_zuzanna" in voice_call_manager.queue

        # 2. Jakub enqueues -> match triggered immediately
        status_2, call_data = await voice_call_manager.enqueue_caller("usr_jakub", "Ulubiona książka", ws_jakub)
        assert status_2 == "MATCHED"
        assert call_data is not None
        call_id = call_data["id"]
        assert call_id in voice_call_manager.active_calls
        assert voice_call_manager.get_peer_id(call_id, "usr_zuzanna") == "usr_jakub"
        assert voice_call_manager.get_peer_id(call_id, "usr_jakub") == "usr_zuzanna"

        # Queue should be empty now
        assert len(voice_call_manager.queue) == 0

        # 3. Simulate WebRTC signaling
        res_offer = await voice_call_manager.forward_signaling(call_id, "usr_zuzanna", "voice.call_offer", {"sdp": "v=0\r\no=..."})
        res_answer = await voice_call_manager.forward_signaling(call_id, "usr_jakub", "voice.call_answer", {"sdp": "v=0\r\na=..."})
        assert isinstance(res_offer, bool)
        assert isinstance(res_answer, bool)

        # 4. Mark call connected -> arms authoritative timer
        await voice_call_manager.handle_call_connected(call_id, "usr_zuzanna")
        assert voice_call_manager.active_calls[call_id]["status"] == "active"
        assert call_id in voice_call_manager.call_timer_tasks

        # 5. Terminate with 1-tap Block
        term_res = await voice_call_manager.terminate_call(call_id, initiator_user_id="usr_zuzanna", reason="user_hangup", block_peer=True)
        assert term_res["call_id"] == call_id
        assert call_id not in voice_call_manager.active_calls
        assert "usr_zuzanna" not in voice_call_manager.user_to_call
        assert "usr_jakub" not in voice_call_manager.user_to_call

        # Verify atomic block was written to user_blocks
        conn = get_db_connection(clean_db)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM user_blocks WHERE blocker_id = 'usr_zuzanna' AND blocked_id = 'usr_jakub';")
        assert cursor.fetchone() is not None
        conn.close()

    asyncio.run(_test())


def test_mutual_block_prevents_matching(clean_db):
    async def _test():
        conn = get_db_connection(clean_db)
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "INSERT INTO user_blocks (blocker_id, blocked_id, created_at) VALUES ('usr_marek', 'usr_zuzanna', ?);",
            (now_str,)
        )
        conn.commit()
        conn.close()

        # Marek enqueues
        status_m, _ = await voice_call_manager.enqueue_caller("usr_marek", "Gry planszowe", None)
        assert status_m == "QUEUED"

        # Zuzanna enqueues -> should NOT match Marek because Marek blocked Zuzanna
        status_z, _ = await voice_call_manager.enqueue_caller("usr_zuzanna", "Gry planszowe", None)
        assert status_z == "QUEUED"

        # Both remain in queue waiting for compatible non-blocked peers
        assert "usr_marek" in voice_call_manager.queue
        assert "usr_zuzanna" in voice_call_manager.queue

    asyncio.run(_test())


def test_daily_limit_and_cooldown_enforcement(clean_db):
    async def _test():
        now = datetime.now(timezone.utc)

        # 1. Simulate recent call 60 seconds ago -> active cooldown
        recent_ts = (now - timedelta(seconds=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn = get_db_connection(clean_db)
        conn.execute("""
            INSERT INTO voice_call_sessions (id, user_a_id, user_b_id, topic, status, created_at, ended_at, duration_seconds)
            VALUES ('vcall_recent', 'usr_zuzanna', 'usr_jakub', 'test', 'completed', ?, ?, 300);
        """, (recent_ts, recent_ts))
        conn.commit()
        conn.close()

        status, _ = await voice_call_manager.enqueue_caller("usr_zuzanna", "test", None)
        assert status.startswith("COOLDOWN_ACTIVE_")

        # 2. Simulate 3 calls completed in last 24h -> daily limit
        conn = get_db_connection(clean_db)
        t1 = (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        t2 = (now - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute("""
            INSERT INTO voice_call_sessions (id, user_a_id, user_b_id, topic, status, created_at, ended_at, duration_seconds)
            VALUES ('vcall_2', 'usr_zuzanna', 'usr_jakub', 'test', 'completed', ?, ?, 300);
        """, (t1, t1))
        conn.execute("""
            INSERT INTO voice_call_sessions (id, user_a_id, user_b_id, topic, status, created_at, ended_at, duration_seconds)
            VALUES ('vcall_3', 'usr_zuzanna', 'usr_jakub', 'test', 'completed', ?, ?, 300);
        """, (t2, t2))
        conn.commit()
        conn.close()

        # Clear cooldown by updating timestamp for recent to 15m ago
        old_ts = (now - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn = get_db_connection(clean_db)
        conn.execute("UPDATE voice_call_sessions SET ended_at = ?, created_at = ? WHERE id = 'vcall_recent';", (old_ts, old_ts))
        conn.commit()
        conn.close()

        status_limit, _ = await voice_call_manager.enqueue_caller("usr_zuzanna", "test", None)
        assert status_limit == "DAILY_LIMIT_REACHED"

    asyncio.run(_test())


def test_voice_rating_api_and_block(clean_db):
    conn = get_db_connection(clean_db)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("""
        INSERT INTO voice_call_sessions (id, user_a_id, user_b_id, topic, status, created_at, ended_at, duration_seconds)
        VALUES ('vcall_test_rate', 'usr_zuzanna', 'usr_jakub', 'Rozmowa', 'completed', ?, ?, 480);
    """, (now_str, now_str))
    conn.commit()
    conn.close()

    headers_zuzanna = {"Authorization": "Bearer token_zuzanna"}
    headers_marek = {"Authorization": "Bearer token_marek"}

    # 1. Unrelated party cannot rate
    res_unauth = client.post(
        "/api/voice/calls/vcall_test_rate/rate",
        headers=headers_marek,
        json={"rating": "respectful"}
    )
    assert res_unauth.status_code == 403

    # 2. Participant rates respectful
    res_rate = client.post(
        "/api/voice/calls/vcall_test_rate/rate",
        headers=headers_zuzanna,
        json={
            "rating": "respectful",
            "details": "Super kulturalna rozmowa o książkach."
        }
    )
    assert res_rate.status_code == 200
    assert res_rate.json()["success"] is True

    # Verify rating was saved in DB
    conn = get_db_connection(clean_db)
    cursor = conn.cursor()
    cursor.execute("SELECT rating, details FROM voice_call_ratings WHERE session_id = 'vcall_test_rate';")
    row = cursor.fetchone()
    assert row["rating"] == "respectful"
    assert "kulturalna" in row["details"]
    conn.close()
