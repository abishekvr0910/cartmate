#!/usr/bin/env python3
"""Offline SQLite restore with manifest verification and a rollback snapshot.

Stop every CartMate process before using this tool. The operator confirmation is a
guardrail, not a way to detect all active SQLite clients.
"""

import argparse
import hashlib
import json
import logging
import os
import re
import secrets
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cartmate.ops.restore")


def calculate_sha256(file_path: Path) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def assert_no_sidecars(target_path: Path) -> None:
    """Never unlink a WAL/SHM file: it may contain committed data or be in use."""
    sidecars = [Path(f"{target_path}{suffix}") for suffix in ("-wal", "-shm")]
    present = [str(path) for path in sidecars if path.exists()]
    if present:
        raise RuntimeError(
            "Restore refused: SQLite WAL/SHM sidecar exists. Stop all app processes "
            "and perform a clean checkpoint/shutdown before retrying: " + ", ".join(present)
        )


def verify_database(path: Path) -> tuple[int, int]:
    connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    try:
        result = connection.execute("PRAGMA integrity_check").fetchone()
        if result != ("ok",):
            raise RuntimeError(f"Database failed integrity_check: {result}")
        users = connection.execute("SELECT count(*) FROM users").fetchone()[0]
        trips = connection.execute("SELECT count(*) FROM trips").fetchone()[0]
        return users, trips
    finally:
        connection.close()


def restore_backup(
    backup_file: Path,
    target_db: Path,
    *,
    confirm_offline: bool = False,
) -> bool:
    """Verify and atomically replace an offline database from an adjacent manifest."""
    backup_path = Path(backup_file).resolve()
    target_path = Path(target_db).resolve()
    if backup_path == target_path:
        raise ValueError("Backup and target must be different files")
    if not backup_path.is_file():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    manifest_path = backup_path.with_suffix(".json")
    if not manifest_path.is_file():
        raise ValueError(f"Restore refused: required checksum manifest is missing: {manifest_path}")
    with manifest_path.open(encoding="utf-8") as source:
        manifest = json.load(source)
    expected_sha = manifest.get("sha256")
    if (
        manifest.get("backup_file") != backup_path.name
        or not isinstance(expected_sha, str)
        or not re.fullmatch(r"[0-9a-f]{64}", expected_sha)
        or manifest.get("size_bytes") != backup_path.stat().st_size
    ):
        raise ValueError("Restore refused: incomplete or mismatched backup manifest")
    if calculate_sha256(backup_path) != expected_sha:
        raise ValueError("Restore refused: backup checksum mismatch")
    backup_counts = verify_database(backup_path)
    counts = manifest.get("counts")
    if not isinstance(counts, dict) or (counts.get("users"), counts.get("trips")) != backup_counts:
        raise ValueError("Restore refused: backup row counts do not match manifest")

    if target_path.exists() and not confirm_offline:
        raise RuntimeError("Restore refused: existing target requires --confirm-offline after stopping the app")
    if target_path.exists() and not target_path.is_file():
        raise ValueError("Restore target is not a regular database file")
    assert_no_sidecars(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if target_path.exists():
        suffix = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        rollback_path = target_path.parent / (
            f"{target_path.stem}_rollback_pre_restore_{suffix}_{secrets.token_hex(4)}.db"
        )
        logger.info("Creating rollback snapshot at '%s'", rollback_path)
        source = sqlite3.connect(f"{target_path.as_uri()}?mode=ro", uri=True)
        try:
            rollback = sqlite3.connect(rollback_path)
            try:
                source.backup(rollback)
            finally:
                rollback.close()
        finally:
            source.close()
        rollback_counts = verify_database(rollback_path)
        rollback_manifest = {
            "backup_file": rollback_path.name,
            "source_db": str(target_path),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "tag": "pre_restore_rollback",
            "sha256": calculate_sha256(rollback_path),
            "size_bytes": rollback_path.stat().st_size,
            "integrity_status": "ok",
            "counts": {"users": rollback_counts[0], "trips": rollback_counts[1]},
        }
        with rollback_path.with_suffix(".json").open("w", encoding="utf-8") as output:
            json.dump(rollback_manifest, output, indent=2)
        assert_no_sidecars(target_path)

    staged_path = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{target_path.stem}_restore_", suffix=".db", dir=target_path.parent, delete=False
        ) as staged:
            staged_path = Path(staged.name)
        shutil.copyfile(backup_path, staged_path)
        if calculate_sha256(staged_path) != expected_sha:
            raise RuntimeError("Staged database checksum changed; target left untouched")
        assert_no_sidecars(target_path)
        os.replace(staged_path, target_path)
        staged_path = None
        if verify_database(target_path) != backup_counts:
            raise RuntimeError("Restored database row counts differ from the verified backup")
    finally:
        if staged_path is not None:
            staged_path.unlink(missing_ok=True)

    logger.info("Restore complete: %s users, %s trips", *backup_counts)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="CartMate offline SQLite restore")
    parser.add_argument("--backup", type=Path, required=True, help="Verified backup .db file")
    parser.add_argument("--target", type=Path, required=True, help="Explicit destination database path")
    parser.add_argument(
        "--confirm-offline", action="store_true",
        help="Confirm every CartMate process using the target has been stopped",
    )
    args = parser.parse_args()
    try:
        restore_backup(args.backup, args.target, confirm_offline=args.confirm_offline)
    except Exception as error:
        logger.error("Restore failed: %s", error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
