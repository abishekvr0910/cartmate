"""Ops utility to idempotently seed verified pilot Third Places into any CartMate SQLite database."""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path


def seed_verified_third_places(conn: sqlite3.Connection) -> int:
    """Inserts verified pilot Third Places across Katowice, Gliwice, and Chorzów if not already present."""
    migration_sql = Path(__file__).resolve().parent.parent / "backend" / "migrations" / "0014_seed_pilot_third_places.sql"
    if not migration_sql.exists():
        raise FileNotFoundError(f"Missing migration script: {migration_sql}")

    sql_text = migration_sql.read_text(encoding="utf-8")
    cursor = conn.cursor()
    cursor.executescript(sql_text)
    conn.commit()

    count = cursor.execute("SELECT COUNT(*) FROM third_places WHERE is_active = 1").fetchone()[0]
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed verified pilot Third Places across Katowice, Gliwice, and Chorzów")
    parser.add_argument(
        "--db",
        default=os.getenv("CARTMATE_DATABASE_PATH", str(Path(__file__).resolve().parent.parent / "backend" / "cartmate.db")),
        help="Path to SQLite database",
    )
    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        total = seed_verified_third_places(conn)
        print(f"Successfully ensured verified Third Places. Total active places: {total}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
