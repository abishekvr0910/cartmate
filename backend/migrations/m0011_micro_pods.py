"""Migration 0011: Micro-Pods anchored in Third Places (schema v10 -> v11).

Call ``upgrade(conn)`` from the storage.py migration runner at startup, before
the app serves traffic. The function fails closed. It refuses to run unless all
of these hold:

* SQLite is new enough for STRICT tables and has the JSON functions;
* the connection has foreign keys ON and no open transaction (use Python's
  default transaction mode or ``autocommit=True``; an ``autocommit=False``
  connection always holds a transaction open and is rejected);
* the database is exactly at ``PRAGMA user_version = 10``;
* ``users.id`` is an INTEGER PRIMARY KEY;
* none of the new table, view or trigger names already exist.

Every statement in ``0011_micro_pods.sql`` then runs inside one
``BEGIN IMMEDIATE`` transaction, which holds the single write lock from the
version check to the commit. The new tables get a foreign-key check, and only
then is ``user_version`` set to 11 and the transaction committed. Any error
rolls the whole transaction back, so the database stays at version 10.

Take a backup first (for example ``VACUUM INTO 'cartmate-pre-0011.db'``).
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

FROM_VERSION = 10
TO_VERSION = 11
SQL_FILE = Path(__file__).with_name("0011_micro_pods.sql")
MIN_SQLITE = (3, 37, 0)  # STRICT tables

_CREATE = re.compile(
    r"^\s*CREATE\s+(?:UNIQUE\s+)?(TABLE|VIEW|TRIGGER|INDEX)\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE | re.MULTILINE,
)


class MigrationError(RuntimeError):
    """A precondition failed or the migration could not be applied."""


def split_statements(script: str) -> list[str]:
    """Split a SQL script into complete statements, keeping trigger bodies intact."""
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


def _users_pk_is_valid(conn: sqlite3.Connection) -> bool:
    columns = conn.execute("PRAGMA table_info(users)").fetchall()
    pk_columns = [col for col in columns if col[5] > 0]  # (cid, name, type, notnull, dflt, pk)
    return len(pk_columns) == 1 and pk_columns[0][1] == "id" and pk_columns[0][2].upper() in ("TEXT", "VARCHAR", "STRING", "INTEGER")


def created_objects(statements: list[str]) -> list[tuple[str, str]]:
    """(kind, name) for every CREATE TABLE/VIEW/TRIGGER/INDEX in the script."""
    found: list[tuple[str, str]] = []
    for statement in statements:
        match = _CREATE.search(statement)
        if match:
            found.append((match.group(1).upper(), match.group(2)))
    return found


def _existing_names(conn: sqlite3.Connection, names: list[str]) -> list[str]:
    rows = conn.execute(
        f"SELECT name FROM sqlite_master WHERE name IN ({','.join('?' * len(names))})", names
    ).fetchall()
    return sorted(row[0] for row in rows)


def upgrade(conn: sqlite3.Connection) -> None:
    """Apply migration 0011 atomically, or raise MigrationError and change nothing."""
    _require(
        sqlite3.sqlite_version_info >= MIN_SQLITE,
        f"SQLite >= {'.'.join(map(str, MIN_SQLITE))} is required for STRICT tables "
        f"(this Python links SQLite {sqlite3.sqlite_version})",
    )
    _require(not conn.in_transaction, "upgrade() needs a connection with no open transaction")
    _require(conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1, "PRAGMA foreign_keys must be ON")
    try:
        conn.execute("SELECT json_valid('[]')").fetchone()
    except sqlite3.OperationalError as exc:
        raise MigrationError("this SQLite build lacks the JSON functions") from exc

    statements = split_statements(SQL_FILE.read_text(encoding="utf-8"))
    objects = created_objects(statements)
    new_tables = [name for kind, name in objects if kind == "TABLE"]

    conn.execute("BEGIN IMMEDIATE")  # take the write lock before reading the version
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
        _require(_users_pk_is_valid(conn), "users.id must be a TEXT or INTEGER PRIMARY KEY")
        clashes = _existing_names(conn, [name for _, name in objects])
        _require(not clashes, f"schema objects already exist: {', '.join(clashes)}")

        for statement in statements:
            conn.execute(statement)

        for table in new_tables:
            violations = conn.execute(f"PRAGMA foreign_key_check({table})").fetchall()
            _require(not violations, f"foreign_key_check failed on {table}: {violations[:3]}")

        if has_migrations_table:
            conn.execute(
                "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))",
                (TO_VERSION, "micro_pods_third_places"),
            )
        conn.execute(f"PRAGMA user_version = {TO_VERSION}")
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
