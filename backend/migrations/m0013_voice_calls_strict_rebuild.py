"""Migration 0013: Strict Voice Call Tables Rebuild (schema v12 -> v13).

Rebuilds voice_call_sessions and voice_call_ratings as STRICT tables for any
existing v12 database, preserving all rows, indexes, and foreign keys.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

FROM_VERSION = 12
TO_VERSION = 13
SQL_FILE = Path(__file__).with_name("0013_voice_calls_strict_rebuild.sql")
MIN_SQLITE = (3, 37, 0)  # STRICT tables


class MigrationError(RuntimeError):
    """A precondition failed or the migration could not be applied."""


def split_statements(script: str) -> list[str]:
    """Split a SQL script into complete statements."""
    statements: list[str] = []
    buffer = ""
    for line in script.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                statements.append(statement)
            buffer = ""
    leftover = [ln for ln in buffer.splitlines() if ln.strip() and not ln.strip().startswith("--")]
    if leftover:
        raise MigrationError(f"unterminated SQL at the end of {SQL_FILE.name}: {leftover[0][:80]!r}")
    return statements


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MigrationError(message)


def upgrade(conn: sqlite3.Connection) -> None:
    """Apply migration 0013 atomically, or raise MigrationError and change nothing."""
    _require(
        sqlite3.sqlite_version_info >= MIN_SQLITE,
        f"SQLite >= {'.'.join(map(str, MIN_SQLITE))} is required for STRICT tables "
        f"(this Python links SQLite {sqlite3.sqlite_version})",
    )
    _require(not conn.in_transaction, "upgrade() needs a connection with no open transaction")

    statements = split_statements(SQL_FILE.read_text(encoding="utf-8"))

    # In SQLite, PRAGMA foreign_keys = OFF must run outside of a transaction.
    conn.execute("PRAGMA foreign_keys = OFF;")
    _require(conn.execute("PRAGMA foreign_keys").fetchone()[0] == 0, "PRAGMA foreign_keys must be OFF before rebuild")

    conn.execute("BEGIN IMMEDIATE")
    try:
        has_migrations_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone() is not None

        if has_migrations_table:
            row = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
            version = row[0] if (row and row[0] is not None) else 0
        else:
            version = conn.execute("PRAGMA user_version").fetchone()[0]

        _require(version == FROM_VERSION, f"expected schema version {FROM_VERSION}, found {version}")

        # Check existing table presence and capture row counts
        tbl_names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        _require("voice_call_sessions" in tbl_names, "voice_call_sessions table does not exist")
        _require("voice_call_ratings" in tbl_names, "voice_call_ratings table does not exist")
        stale = sorted({"voice_call_sessions_new", "voice_call_ratings_new"} & tbl_names)
        _require(not stale, f"stale rebuild tables already exist: {', '.join(stale)}")

        pre_sessions = conn.execute("SELECT COUNT(*) FROM voice_call_sessions").fetchone()[0]
        pre_ratings = conn.execute("SELECT COUNT(*) FROM voice_call_ratings").fetchone()[0]

        for stmt in statements:
            conn.execute(stmt)

        post_sessions = conn.execute("SELECT COUNT(*) FROM voice_call_sessions").fetchone()[0]
        post_ratings = conn.execute("SELECT COUNT(*) FROM voice_call_ratings").fetchone()[0]

        _require(post_sessions == pre_sessions, f"session count mismatch after rebuild: {pre_sessions} -> {post_sessions}")
        _require(post_ratings == pre_ratings, f"rating count mismatch after rebuild: {pre_ratings} -> {post_ratings}")

        # Assert STRICT mode on both tables (matching ") STRICT" to avoid "RESTRICT" in FK definitions)
        for tbl in ("voice_call_sessions", "voice_call_ratings"):
            sql_row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tbl,)).fetchone()
            _require(sql_row and ") STRICT" in sql_row[0].upper(), f"table {tbl} is not STRICT")

        # Assert foreign key integrity
        violations_s = conn.execute("PRAGMA foreign_key_check(voice_call_sessions)").fetchall()
        _require(not violations_s, f"foreign_key_check failed on voice_call_sessions: {violations_s[:3]}")
        violations_r = conn.execute("PRAGMA foreign_key_check(voice_call_ratings)").fetchall()
        _require(not violations_r, f"foreign_key_check failed on voice_call_ratings: {violations_r[:3]}")

        if has_migrations_table:
            now_iso = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                (TO_VERSION, "voice_calls_strict_rebuild", now_iso),
            )
        conn.execute(f"PRAGMA user_version = {TO_VERSION}")
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON;")
