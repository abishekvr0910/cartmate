#!/usr/bin/env python3
"""
Automated local backup/restore mechanics drill using a small sample schema.
This does not prove production recovery time or all real CartMate tables.
"""

import shutil
import sqlite3
import tempfile
import json
import os
import subprocess
import sys
from contextlib import closing
from pathlib import Path
import pytest

from cartmate_backup import create_online_backup
from cartmate_restore import restore_backup


@pytest.fixture
def workspace_tmp_path():
    ops_dir = Path(__file__).resolve().parent
    temp_dir = Path(tempfile.mkdtemp(prefix="cartmate_dr_test_", dir=ops_dir))
    try:
        yield temp_dir
    finally:
        if temp_dir.resolve().parent != ops_dir:
            raise RuntimeError("Refusing to clean up outside the ops directory")
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_disaster_recovery_drill():
    """
    Simulates a local recovery drill:
    1. Create a sample SQLite database.
    2. Populate with users, trips, pings, and sessions.
    3. Take an online backup while DB is live.
    4. Simulate data loss / catastrophic truncation.
    5. Restore from backup.
    6. Verify the seeded sample records match.
    """
    ops_dir = Path(__file__).resolve().parent
    temp_dir = Path(tempfile.mkdtemp(prefix="cartmate_dr_test_", dir=ops_dir))
    try:
        live_db = temp_dir / "live_cartmate.db"
        backups_dir = temp_dir / "backups"
        recovered_db = temp_dir / "recovered_cartmate.db"

        # 1. Initialize schema and sample data in live_db
        conn = sqlite3.connect(live_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute(
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                trust_tier INTEGER DEFAULT 0
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE trips (
                id TEXT PRIMARY KEY,
                host_id TEXT NOT NULL,
                destination_name TEXT NOT NULL,
                status TEXT NOT NULL
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            """
        )

        # Seed records
        sample_users = [
            ("usr_1", "Zuzanna Śląska", "+48600111222", 1),
            ("usr_2", "Jakub Katowicki", "+48600333444", 2),
            ("usr_3", "Ania Gliwice", "+48600555666", 0),
        ]
        cursor.executemany("INSERT INTO users VALUES (?, ?, ?, ?);", sample_users)

        sample_trips = [
            ("trip_01", "usr_2", "Makro Cash & Carry Katowice", "scheduled"),
            ("trip_02", "usr_1", "Silesia City Center", "completed"),
        ]
        cursor.executemany("INSERT INTO trips VALUES (?, ?, ?, ?);", sample_trips)

        sample_sessions = [
            ("cmt_tok_alpha", "usr_1", "2026-09-27T10:00:00Z", "2026-09-28T10:00:00Z"),
            ("cmt_tok_beta", "usr_2", "2026-09-27T11:00:00Z", "2026-09-28T11:00:00Z"),
        ]
        cursor.executemany("INSERT INTO sessions VALUES (?, ?, ?, ?);", sample_sessions)
        conn.commit()

        # 2. Take online backup while live
        backup_file, manifest_file = create_online_backup(
            db_path=live_db,
            backup_dir=backups_dir,
            tag="drill_test",
        )

        assert backup_file.exists()
        assert manifest_file.exists()
        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert "pods" in manifest_data["counts"]
        assert "voice_call_sessions" in manifest_data["counts"]

        # 3. Simulate catastrophic disaster: truncate users and corrupt trips in live_db
        cursor.execute("DELETE FROM users;")
        cursor.execute("UPDATE trips SET status = 'CORRUPTED';")
        conn.commit()
        conn.close()

        # Verify disaster took effect on live_db
        check_conn = sqlite3.connect(live_db)
        assert check_conn.execute("SELECT count(*) FROM users;").fetchone()[0] == 0
        check_conn.close()

        # 4. Execute Restore into recovered_db
        restore_success = restore_backup(
            backup_file=backup_file,
            target_db=recovered_db,
        )
        assert restore_success is True

        # 5. Verify restored database records match exactly
        rest_conn = sqlite3.connect(recovered_db)
        rest_cursor = rest_conn.cursor()

        rest_users = rest_cursor.execute("SELECT id, name, phone, trust_tier FROM users ORDER BY id;").fetchall()
        assert rest_users == sample_users

        rest_trips = rest_cursor.execute("SELECT id, host_id, destination_name, status FROM trips ORDER BY id;").fetchall()
        assert rest_trips == sample_trips

        rest_sessions = rest_cursor.execute("SELECT token, user_id, created_at, expires_at FROM sessions ORDER BY token;").fetchall()
        assert rest_sessions == sample_sessions

        rest_conn.close()
        print("Local recovery drill passed: seeded sample records match.")
    finally:
        if temp_dir.resolve().parent != ops_dir:
            raise RuntimeError("Refusing to clean up outside the ops directory")
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_restore_refuses_missing_manifest_live_wal_and_requires_offline_confirmation(workspace_tmp_path):
    tmp_path = workspace_tmp_path
    source = tmp_path / "source.db"
    with closing(sqlite3.connect(source)) as conn:
        conn.execute("CREATE TABLE users (id TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE trips (id TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO users VALUES ('original')")
        conn.execute("INSERT INTO trips VALUES ('trip')")
        conn.commit()
    backup, manifest = create_online_backup(source, tmp_path / "backups", tag="safety")
    target = tmp_path / "target.db"
    with closing(sqlite3.connect(target)) as conn:
        conn.execute("CREATE TABLE users (id TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE trips (id TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO users VALUES ('before_restore')")
        conn.commit()

    with pytest.raises(RuntimeError, match="confirm-offline"):
        restore_backup(backup, target)
    with closing(sqlite3.connect(target)) as conn:
        assert conn.execute("SELECT id FROM users").fetchone()[0] == "before_restore"

    live_conn = sqlite3.connect(target)
    try:
        live_conn.execute("PRAGMA journal_mode=WAL")
        live_conn.execute("INSERT INTO trips VALUES ('live_wal')")
        live_conn.commit()
        with pytest.raises(RuntimeError, match="WAL/SHM"):
            restore_backup(backup, target, confirm_offline=True)
    finally:
        live_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        live_conn.execute("PRAGMA journal_mode=DELETE")
        live_conn.close()

    assert restore_backup(backup, target, confirm_offline=True)
    with closing(sqlite3.connect(target)) as conn:
        assert conn.execute("SELECT id FROM users").fetchone()[0] == "original"
    rollback_files = list(tmp_path.glob("target_rollback_pre_restore_*.db"))
    assert len(rollback_files) == 1
    assert rollback_files[0].with_suffix(".json").is_file()
    with closing(sqlite3.connect(rollback_files[0])) as conn:
        assert conn.execute("SELECT id FROM users").fetchone()[0] == "before_restore"
        assert conn.execute("SELECT id FROM trips").fetchone()[0] == "live_wal"

    original_manifest = manifest.read_text(encoding="utf-8")
    tampered_manifest = json.loads(original_manifest)
    tampered_manifest["sha256"] = "0" * 64
    manifest.write_text(json.dumps(tampered_manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        restore_backup(backup, target, confirm_offline=True)
    manifest.write_text(original_manifest, encoding="utf-8")

    manifest.unlink()
    with pytest.raises(ValueError, match="manifest"):
        restore_backup(backup, target, confirm_offline=True)


def test_real_schema_offline_recovery_preserves_every_table(workspace_tmp_path):
    """Restore a disposable CartMate schema, not just the runbook's sample tables."""
    tmp_path = workspace_tmp_path
    source = tmp_path / "real_cartmate.db"
    recovered = tmp_path / "recovered_cartmate.db"
    backend_dir = Path(__file__).resolve().parents[1] / "backend"
    script = """
from fastapi.testclient import TestClient
import database, main
client = TestClient(main.app)
headers = {'Authorization': 'Bearer token_zuzanna'}
report = client.post('/api/reports', headers=headers, json={
    'reported_user_id': 'usr_ania', 'category': 'other',
    'details': 'Disposable recovery drill report',
    'outing_id': 'out_cafe_nero_01', 'evidence_chat_message_id': 'msg_01',
})
assert report.status_code == 200, report.text
block = client.post('/api/users/usr_marek/block', headers=headers, json={'reason': 'recovery drill'})
assert block.status_code == 200, block.text
"""
    env = os.environ.copy()
    env.update({"CARTMATE_ENV": "development", "CARTMATE_DATABASE_PATH": str(source)})
    completed = subprocess.run(
        [sys.executable, "-c", script], cwd=backend_dir, env=env,
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    def snapshot(db_path: Path) -> dict[str, list[tuple]]:
        with closing(sqlite3.connect(db_path)) as conn:
            table_names = [row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )]
            return {
                name: sorted((tuple(row) for row in conn.execute(f'SELECT * FROM "{name}"')), key=repr)
                for name in table_names
            }

    expected = snapshot(source)
    assert expected["reports"] and expected["user_blocks"]
    with closing(sqlite3.connect(source)) as conn:
        assert "outing_id" in [column[1] for column in conn.execute("PRAGMA table_info(reports)")]
    backup, manifest = create_online_backup(source, tmp_path / "backups", tag="real_schema")
    assert backup.is_file() and manifest.is_file()
    with closing(sqlite3.connect(source)) as conn:
        conn.execute("DELETE FROM reports")
        conn.commit()
    assert snapshot(source) != expected

    assert restore_backup(backup, recovered, confirm_offline=True)
    assert snapshot(recovered) == expected


if __name__ == "__main__":
    test_disaster_recovery_drill()
    print("ALL DISASTER RECOVERY DRILL CHECKS PASSED.")
