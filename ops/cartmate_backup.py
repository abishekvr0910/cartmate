#!/usr/bin/env python3
"""
CartMate Disaster Recovery & Online Backup Utility.
Performs consistent online SQLite backups using the sqlite3.backup API.
SQLite may briefly coordinate with writers while copying pages.
"""

import argparse
import hashlib
import json
import logging
import os
import re
import secrets
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cartmate.ops.backup")

DEFAULT_DB_PATH = Path(
    os.environ.get("CARTMATE_DATABASE_PATH")
    or Path(__file__).resolve().parent.parent / "backend" / "cartmate.db"
)
DEFAULT_BACKUP_DIR = Path(__file__).resolve().parent / "backups"


def calculate_sha256(file_path: Path) -> str:
    """Calculates SHA-256 checksum of a file."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def create_online_backup(
    db_path: Optional[Path] = None,
    backup_dir: Optional[Path] = None,
    tag: str = "scheduled",
) -> Tuple[Path, Path]:
    """
    Performs a transactionally consistent online backup of the CartMate SQLite database.
    SQLite may briefly coordinate with active writers during the copy.
    Returns (backup_db_path, manifest_path).
    """
    src_db = (Path(db_path) if db_path else DEFAULT_DB_PATH).resolve()
    dest_dir = (Path(backup_dir) if backup_dir else DEFAULT_BACKUP_DIR).resolve()

    if not src_db.is_file():
        raise FileNotFoundError(f"Source database not found at {src_db}")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", tag):
        raise ValueError("Backup tag must contain only letters, digits, _ or - (max 40 characters)")

    dest_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    backup_filename = f"cartmate_backup_{tag}_{timestamp}_{secrets.token_hex(4)}.db"
    dest_db = dest_dir / backup_filename
    manifest_path = dest_db.with_suffix(".json")

    logger.info(f"Initiating online backup from '{src_db}' to '{dest_db}'...")

    # Connect to source in read-only URI mode to guarantee zero modification to source
    src_conn = sqlite3.connect(f"{src_db.as_uri()}?mode=ro", uri=True)
    try:
        dest_conn = sqlite3.connect(dest_db)
        try:
            with dest_conn:
                src_conn.backup(dest_conn, pages=100, sleep=0.01)
        finally:
            dest_conn.close()
        logger.info("Database pages successfully mirrored.")
    finally:
        src_conn.close()

    # Calculate checksum and generate audit manifest
    checksum = calculate_sha256(dest_db)
    file_size_bytes = dest_db.stat().st_size

    # Quick integrity check on the newly created backup
    verify_conn = sqlite3.connect(dest_db)
    try:
        cursor = verify_conn.cursor()
        integrity_result = cursor.execute("PRAGMA integrity_check;").fetchone()
        if not integrity_result or integrity_result[0] != "ok":
            raise RuntimeError(f"Backup failed integrity check: {integrity_result}")
        user_count = cursor.execute("SELECT count(*) FROM users;").fetchone()[0]
        trip_count = cursor.execute("SELECT count(*) FROM trips;").fetchone()[0]
        try:
            pod_count = cursor.execute("SELECT count(*) FROM pods;").fetchone()[0]
        except sqlite3.OperationalError:
            pod_count = 0
        try:
            voice_session_count = cursor.execute("SELECT count(*) FROM voice_call_sessions;").fetchone()[0]
        except sqlite3.OperationalError:
            voice_session_count = 0
        logger.info(
            f"Integrity check passed. Stats: {user_count} users, {trip_count} trips, "
            f"{pod_count} pods, {voice_session_count} voice sessions."
        )
    finally:
        verify_conn.close()

    manifest = {
        "backup_file": backup_filename,
        "source_db": str(src_db.resolve()),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "tag": tag,
        "sha256": checksum,
        "size_bytes": file_size_bytes,
        "integrity_status": "ok",
        "counts": {
            "users": user_count,
            "trips": trip_count,
            "pods": pod_count,
            "voice_call_sessions": voice_session_count,
        },
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Backup manifest saved to '{manifest_path}'.")
    logger.info(f"SUCCESS: Online backup complete -> {dest_db} (SHA256: {checksum[:12]}...)")
    return dest_db, manifest_path


def main():
    parser = argparse.ArgumentParser(description="CartMate Online SQLite Backup Tool")
    parser.add_argument("--db", type=str, default=None, help="Path to source cartmate.db")
    parser.add_argument("--out", type=str, default=None, help="Output directory for backups")
    parser.add_argument("--tag", type=str, default="manual", help="Tag for backup (e.g. pre_migration, manual)")
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else None
    out_dir = Path(args.out) if args.out else None

    try:
        create_online_backup(db_path, out_dir, tag=args.tag)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
