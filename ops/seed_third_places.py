"""Ops utility to idempotently seed the pilot Third Places into any CartMate SQLite database.

Seeded places are inserted unverified. `third_places.verified_at` means "checked in person"
and gates pod creation, so it is set per place by an operator only after a real visit; this
utility never sets it.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "backend" / "migrations"
# 0014 inserts the places with a placeholder verification stamp; 0016 withdraws exactly that
# placeholder. They are always applied together so a re-seed can never re-verify a place.
_SEED_SCRIPTS = ("0014_seed_pilot_third_places.sql", "0016_unverify_seeded_third_places.sql")


def seed_pilot_third_places(conn: sqlite3.Connection) -> int:
    """Inserts the pilot Third Places across Katowice, Gliwice, and Chorzów if not already present.

    Returns the number of active places. Places it inserts are unverified.
    """
    cursor = conn.cursor()
    for script_name in _SEED_SCRIPTS:
        script = _MIGRATIONS_DIR / script_name
        if not script.exists():
            raise FileNotFoundError(f"Missing migration script: {script}")
        cursor.executescript(script.read_text(encoding="utf-8"))
    conn.commit()

    count = cursor.execute("SELECT COUNT(*) FROM third_places WHERE is_active = 1").fetchone()[0]
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the pilot Third Places (unverified) across Katowice, Gliwice, and Chorzów")
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
        total = seed_pilot_third_places(conn)
        verified = conn.execute(
            "SELECT COUNT(*) FROM third_places WHERE is_active = 1 AND verified_at IS NOT NULL"
        ).fetchone()[0]
        print(f"Ensured pilot Third Places. Total active places: {total}; verified in person: {verified}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
