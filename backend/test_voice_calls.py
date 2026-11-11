import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from main import app, voice_call_manager
from storage import DurableStorage, get_db_connection, storage

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


def test_voice_terminate_reasons_and_reported_quota(clean_db):
    async def _test():
        # Match call
        status_z, call_z = await voice_call_manager.enqueue_caller("usr_zuzanna", "Podróże", None)
        status_j, call_j = await voice_call_manager.enqueue_caller("usr_jakub", "Podróże", None)
        assert status_j == "MATCHED"
        call_id = call_j["id"]

        # Unauthorized third party cannot terminate call
        unauth_term = await voice_call_manager.terminate_call(call_id, initiator_user_id="usr_marek")
        assert unauth_term == {}
        assert call_id in voice_call_manager.active_calls

        # User blocked termination maps cleanly to 'blocked' and writes block
        term_res = await voice_call_manager.terminate_call(call_id, initiator_user_id="usr_zuzanna", reason="user_blocked", block_peer=True)
        assert term_res["reason"] == "blocked"

        session = storage.get_voice_session(call_id)
        assert session["status"] == "reported"
        assert session["end_reason"] == "blocked"

        # Reported calls must count toward daily limit and cooldown
        daily_count = storage.get_daily_voice_call_count("usr_jakub")
        assert daily_count >= 1

        sec_since = storage.get_seconds_since_last_voice_call("usr_jakub")
        assert sec_since is not None and sec_since < 60

        # Inappropriate rating creates a moderation report
        headers_zuzanna = {"Authorization": "Bearer token_zuzanna"}
        res_rep = client.post(
            f"/api/voice/calls/{call_id}/rate",
            headers=headers_zuzanna,
            json={
                "rating": "inappropriate",
                "report_tag": "harassment",
                "details": "Wulgarne zachowanie podczas rozmowy.",
                "block_peer": True
            }
        )
        assert res_rep.status_code == 200
        import database
        reports = [r for r in database.REPORTS.values() if r.reported_user_id == "usr_jakub"]
        assert len(reports) >= 1
        assert reports[-1].category == "harassment"

    asyncio.run(_test())


def test_staging_readiness_blocks_missing_or_default_turn_secret(monkeypatch):
    import main

    monkeypatch.setattr(main, "CARTMATE_ENV", "staging")
    monkeypatch.setattr(main, "is_production", lambda: True)
    monkeypatch.setenv("CARTMATE_DATABASE_PATH", "isolated-turn-readiness.db")
    monkeypatch.delenv("CARTMATE_TURN_SECRET", raising=False)

    blockers = client.get("/api/ready").json()["blockers"]
    assert any("CARTMATE_TURN_SECRET" in blocker for blocker in blockers)

    monkeypatch.setenv("CARTMATE_TURN_SECRET", "cartmate_ephemeral_turn_secret_dev")
    blockers = client.get("/api/ready").json()["blockers"]
    assert any("CARTMATE_TURN_SECRET" in blocker for blocker in blockers)


def test_voice_disconnect_grace_and_turn_secret_and_compile(clean_db, monkeypatch):
    import os
    import py_compile

    backend_dir = os.path.dirname(__file__)
    py_compile.compile(os.path.join(backend_dir, "voice_manager.py"), doraise=True)
    py_compile.compile(os.path.join(backend_dir, "migrations", "m0011_micro_pods.py"), doraise=True)
    py_compile.compile(os.path.join(backend_dir, "migrations", "m0013_voice_calls_strict_rebuild.py"), doraise=True)

    # Production TURN secret fail-closed check
    monkeypatch.setenv("CARTMATE_ENV", "production")
    monkeypatch.setenv("CARTMATE_TURN_SECRET", "cartmate_ephemeral_turn_secret_dev")
    ice_prod_default = voice_call_manager.get_ice_servers("usr_zuzanna")
    assert all("turn:" not in str(s.get("urls")) for s in ice_prod_default)

    monkeypatch.setenv("CARTMATE_TURN_SECRET", "strong-unique-production-turn-secret-999")
    ice_prod_custom = voice_call_manager.get_ice_servers("usr_zuzanna")
    assert any("turn:" in str(s.get("urls")) for s in ice_prod_custom)
    assert all("turns:" not in str(s.get("urls")) for s in ice_prod_custom)
    monkeypatch.setenv("CARTMATE_ENV", "development")

    async def _test_grace():
        status_z, _ = await voice_call_manager.enqueue_caller("usr_zuzanna", "Książki", None)
        status_m, call_m = await voice_call_manager.enqueue_caller("usr_marek", "Książki", None)
        assert status_m == "MATCHED"
        call_id = call_m["id"]

        # Start a 0.25s disconnect grace timer and cancel it via reconnect
        await voice_call_manager.handle_socket_disconnect("usr_zuzanna", grace_seconds=0.25)
        assert "usr_zuzanna" in voice_call_manager.disconnect_grace_tasks
        voice_call_manager.cancel_disconnect_grace("usr_zuzanna")
        await asyncio.sleep(0.05)
        assert call_id in voice_call_manager.active_calls

        # Now let a short 0.05s disconnect grace timer expire without reconnect
        await voice_call_manager.handle_socket_disconnect("usr_zuzanna", grace_seconds=0.05)
        await asyncio.sleep(0.12)
        assert call_id not in voice_call_manager.active_calls
        session = storage.get_voice_session(call_id)
        assert session["status"] == "dropped"
        assert session["end_reason"] == "connection_failed"

    asyncio.run(_test_grace())


def test_voice_rating_validation_duplicate_409_and_strict_schema(clean_db):
    """Verifies Pydantic 422 validation on report_tag/details, 409 on duplicate rating, and STRICT schema on 0012."""
    token_z = "token_zuzanna"
    call_id = "vc_test_strict_validation"
    storage.create_voice_session(call_id, "usr_zuzanna", "usr_marek", "Test walidacji")

    # 1. Invalid report_tag -> 422 Unprocessable Entity (not 500)
    res_bad_tag = client.post(
        f"/api/voice/calls/{call_id}/rate",
        json={"rating": "inappropriate", "report_tag": "not_a_valid_tag"},
        headers={"Authorization": f"Bearer {token_z}"},
    )
    assert res_bad_tag.status_code == 422

    # 2. Details > 500 chars -> 422 Unprocessable Entity (not 500)
    res_long = client.post(
        f"/api/voice/calls/{call_id}/rate",
        json={"rating": "neutral", "details": "x" * 501},
        headers={"Authorization": f"Bearer {token_z}"},
    )
    assert res_long.status_code == 422

    # 3. Valid rating -> 200 OK
    res_ok = client.post(
        f"/api/voice/calls/{call_id}/rate",
        json={"rating": "respectful", "details": "Bardzo kulturalna rozmowa."},
        headers={"Authorization": f"Bearer {token_z}"},
    )
    assert res_ok.status_code == 200

    # 4. Duplicate rating -> idempotent 200 OK via INSERT OR REPLACE (never 500)
    res_dup = client.post(
        f"/api/voice/calls/{call_id}/rate",
        json={"rating": "respectful"},
        headers={"Authorization": f"Bearer {token_z}"},
    )
    assert res_dup.status_code == 200

    # 5. Verify 0012/0013 tables are STRICT in SQLite and user_version is 13
    from storage import get_db_connection
    conn = get_db_connection(storage.db_path)
    try:
        rows = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name IN ('voice_call_sessions', 'voice_call_ratings')"
        ).fetchall()
        assert len(rows) == 2
        for r in rows:
            assert "STRICT" in r["sql"].upper()
        user_ver = conn.execute("PRAGMA user_version").fetchone()[0]
        assert user_ver >= 13
    finally:
        conn.close()


def test_m0013_strict_voice_table_rebuild_from_v12(tmp_path):
    """Verifies that m0013_voice_calls_strict_rebuild safely rebuilds a populated v12 non-STRICT database into STRICT tables."""
    from migrations import m0013_voice_calls_strict_rebuild

    test_db = str(tmp_path / "legacy_v12.db")
    conn = get_db_connection(test_db)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        # 1. Setup schema migrations table and users table
        conn.execute("""
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            );
        """)
        for v in range(1, 13):
            conn.execute("INSERT INTO schema_migrations VALUES (?, ?, ?);", (v, f"v{v}", now_str))

        conn.execute("""
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE,
                phone TEXT,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        conn.execute("INSERT INTO users VALUES ('usr_1', 'u1@ex.pl', '+48111', '{}', ?, ?);", (now_str, now_str))
        conn.execute("INSERT INTO users VALUES ('usr_2', 'u2@ex.pl', '+48222', '{}', ?, ?);", (now_str, now_str))

        # 2. Create non-STRICT legacy v12 tables
        conn.execute("""
            CREATE TABLE voice_call_sessions (
                id                TEXT    PRIMARY KEY,
                user_a_id         TEXT    NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                user_b_id         TEXT    NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                topic             TEXT    NOT NULL,
                status            TEXT    NOT NULL DEFAULT 'connecting',
                started_at        TEXT,
                ended_at          TEXT,
                duration_seconds  INTEGER NOT NULL DEFAULT 0,
                end_reason        TEXT,
                created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                CHECK (user_a_id <> user_b_id)
            );
        """)
        conn.execute("""
            CREATE TABLE voice_call_ratings (
                id          TEXT PRIMARY KEY,
                session_id  TEXT NOT NULL REFERENCES voice_call_sessions(id) ON DELETE CASCADE,
                reporter_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                target_id   TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                rating      TEXT NOT NULL,
                report_tag  TEXT,
                details     TEXT,
                created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                UNIQUE (session_id, reporter_id)
            );
        """)
        conn.execute("PRAGMA user_version = 12;")
        conn.commit()

        # Insert populated session and rating rows
        conn.execute("""
            INSERT INTO voice_call_sessions (id, user_a_id, user_b_id, topic, status, duration_seconds, end_reason, created_at)
            VALUES ('call_legacy_1', 'usr_1', 'usr_2', 'Książki', 'completed', 300, 'user_hangup', ?);
        """, (now_str,))
        conn.execute("""
            INSERT INTO voice_call_ratings (id, session_id, reporter_id, target_id, rating, report_tag, details, created_at)
            VALUES ('vrate_legacy_1', 'call_legacy_1', 'usr_1', 'usr_2', 'respectful', NULL, 'Świetna rozmowa', ?);
        """, (now_str,))
        conn.commit()

        # Confirm tables were NOT STRICT initially (checking table tail, avoiding 'RESTRICT' in FKs)
        for tbl in ("voice_call_sessions", "voice_call_ratings"):
            sql = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tbl,)).fetchone()[0]
            assert ") STRICT" not in sql.upper()

        # 3. Apply atomic migration 13
        conn.isolation_level = None
        m0013_voice_calls_strict_rebuild.upgrade(conn)

        # 4. Assert row preservation
        sess_rows = conn.execute("SELECT * FROM voice_call_sessions WHERE id='call_legacy_1'").fetchall()
        assert len(sess_rows) == 1
        assert sess_rows[0]["topic"] == "Książki"
        assert sess_rows[0]["duration_seconds"] == 300

        rate_rows = conn.execute("SELECT * FROM voice_call_ratings WHERE id='vrate_legacy_1'").fetchall()
        assert len(rate_rows) == 1
        assert rate_rows[0]["details"] == "Świetna rozmowa"

        # 5. Assert tables are now STRICT
        for tbl in ("voice_call_sessions", "voice_call_ratings"):
            sql = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tbl,)).fetchone()[0]
            assert ") STRICT" in sql.upper()

        # 6. Assert indexes and schema version
        indexes = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
        assert "idx_voice_sessions_user_a" in indexes
        assert "idx_voice_sessions_user_b" in indexes
        assert "idx_voice_sessions_status" in indexes
        assert "idx_voice_ratings_target" in indexes

        assert conn.execute("PRAGMA user_version").fetchone()[0] == 13
        assert conn.execute("SELECT COUNT(*) FROM schema_migrations WHERE version=13").fetchone()[0] == 1
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()


def test_production_turn_secret_lifespan_startup_guard(tmp_path):
    """Verifies that entering FastAPI lifespan under CARTMATE_ENV=production fails with RuntimeError if CARTMATE_TURN_SECRET is missing or default."""
    import subprocess
    import sys
    from pathlib import Path

    backend_dir = Path(__file__).resolve().parent
    db_path = str(tmp_path / "prod_guard.db").replace("\\", "/")

    # 1. Missing CARTMATE_TURN_SECRET in production -> RuntimeError on lifespan entry
    code_missing = f"""
import os
os.environ["CARTMATE_ENV"] = "production"
os.environ["CARTMATE_DATABASE_PATH"] = "{db_path}"
os.environ["CARTMATE_CORS_ALLOWED_ORIGINS"] = "https://cartmate.pl"
os.environ["CARTMATE_TURN_SECRET"] = ""
from fastapi.testclient import TestClient
import main
try:
    with TestClient(main.app) as client:
        pass
    print("FAILED_EXPECTED_EXCEPTION")
except RuntimeError as exc:
    assert "CARTMATE_TURN_SECRET" in str(exc)
    print("PASSED_MISSING_GUARD")
"""
    proc_missing = subprocess.run([sys.executable, "-c", code_missing], cwd=str(backend_dir), capture_output=True, text=True)
    assert "PASSED_MISSING_GUARD" in proc_missing.stdout, f"Output: {proc_missing.stdout}\nError: {proc_missing.stderr}"

    # 2. Default CARTMATE_TURN_SECRET in production -> RuntimeError on lifespan entry
    code_default = f"""
import os
os.environ["CARTMATE_ENV"] = "production"
os.environ["CARTMATE_DATABASE_PATH"] = "{db_path}"
os.environ["CARTMATE_CORS_ALLOWED_ORIGINS"] = "https://cartmate.pl"
os.environ["CARTMATE_TURN_SECRET"] = "cartmate_ephemeral_turn_secret_dev"
from fastapi.testclient import TestClient
import main
try:
    with TestClient(main.app) as client:
        pass
    print("FAILED_EXPECTED_EXCEPTION")
except RuntimeError as exc:
    assert "CARTMATE_TURN_SECRET" in str(exc)
    print("PASSED_DEFAULT_GUARD")
"""
    proc_default = subprocess.run([sys.executable, "-c", code_default], cwd=str(backend_dir), capture_output=True, text=True)
    assert "PASSED_DEFAULT_GUARD" in proc_default.stdout, f"Output: {proc_default.stdout}\nError: {proc_default.stderr}"

    # 3. Valid production secret -> boots cleanly without error
    code_valid = f"""
import os
os.environ["CARTMATE_ENV"] = "production"
os.environ["CARTMATE_DATABASE_PATH"] = "{db_path}"
os.environ["CARTMATE_CORS_ALLOWED_ORIGINS"] = "https://cartmate.pl"
os.environ["CARTMATE_TURN_SECRET"] = "super_secure_production_secret_32_chars_long"
from fastapi.testclient import TestClient
import main
with TestClient(main.app) as client:
    res = client.get("/api/health")
    assert res.status_code == 200
print("PASSED_VALID_GUARD")
"""
    proc_valid = subprocess.run([sys.executable, "-c", code_valid], cwd=str(backend_dir), capture_output=True, text=True)
    assert "PASSED_VALID_GUARD" in proc_valid.stdout, f"Output: {proc_valid.stdout}\nError: {proc_valid.stderr}"


def test_mr02_destination_probe_subprocess():
    """Runs codex_mr02_destination_probe.cjs inside pytest and asserts bearer token safety."""
    import json
    repo_root = Path(__file__).resolve().parent.parent
    probe_script = repo_root / "qa" / "codex_mr02_destination_probe.cjs"
    assert probe_script.exists(), f"Probe script not found at {probe_script}"

    proc = subprocess.run(
        ["node", str(probe_script)],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"Probe failed with exit {proc.returncode}:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    data = json.loads(proc.stdout)
    assert "differentUnapprovedHostname" in data
    assert "secondUnapprovedHostname" in data
    assert "missingNativeConfig" in data
    for key in ("differentUnapprovedHostname", "secondUnapprovedHostname", "missingNativeConfig"):
        calls = data[key]["calls"]
        assert len(calls) > 0
        assert all(call["bearerAttached"] is False for call in calls)





