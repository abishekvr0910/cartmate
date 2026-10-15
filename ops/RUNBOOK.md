# CartMate Operations Runbook: Backup & Disaster Recovery

This runbook covers consistent online backups and **offline** recovery for the single-instance CartMate SQLite deployment. A local drill passing does not prove production recovery time, encryption, or offsite durability.

**2026-09-30 local drill:** `python -m pytest ops/test_disaster_recovery.py -q` passed 3/3, including a disposable real-schema backup/restore comparison across every CartMate table (group/report context included). The restored file was local and offline. No offsite encryption/upload, hosted Render volume, credential separation, rollback after a live incident, or recovery-time objective has been proved. Record those separately in `staging/REHEARSAL_EVIDENCE.md` before live recruitment.

## Architecture

- **Engine:** SQLite in Write-Ahead Logging (`WAL`) mode.
- **Backup Mechanism:** Transactionally consistent page-by-page copy via Python `conn.backup()` (`cartmate_backup.py`). SQLite may briefly coordinate with writers.
- **Verification:** SHA-256 checksum, manifest, row counts, and `PRAGMA integrity_check`. The manifest is not signed and does not authenticate who made the backup.
- **Restoration Safety:** Requires an explicit target, offline confirmation, a matching manifest, no WAL/SHM sidecars, an online-API rollback snapshot, and same-directory atomic replacement.

---

## 1. Taking a Manual Online Backup

To take a consistent online backup without stopping the backend:

```bash
cd S:\APPs\cartmate\ops
python cartmate_backup.py --tag manual
```

Options:
- `--db <path>`: Source database path. Without it, uses `CARTMATE_DATABASE_PATH` if set, otherwise `../backend/cartmate.db`. In deployment, pass an explicit absolute path and verify the manifest's `source_db`.
- `--out <path>`: Output directory (defaults to `./backups/`).
- `--tag <name>`: Label for the backup (e.g. `pre_migration`, `daily`, `pilot_launch`).

Output artifacts:
1. `cartmate_backup_<tag>_<timestamp>.db` (SQLite database snapshot).
2. `cartmate_backup_<tag>_<timestamp>.json` (Audit manifest with SHA-256 checksum and row counts).

---

## 2. Automated Scheduled Backups (Cron / Task Scheduler)

For a single-instance staging deployment, schedule backups every 6 hours. The examples below only start a backup; **retention, encryption, restricted access, and offsite copying must be configured separately** before live user data is stored.

### Linux Cron (Production / Staging)
```cron
# Run every 6 hours
0 */6 * * * /usr/bin/python3 /opt/cartmate/ops/cartmate_backup.py --tag automated >> /var/log/cartmate_backups.log 2>&1
```

### Windows Task Scheduler (PowerShell)
```powershell
python S:\APPs\cartmate\ops\cartmate_backup.py --tag automated
```

---

## 3. Disaster Recovery / Restoring from Backup

Stop every backend process using the target database and confirm that its `-wal` and `-shm` sidecars are absent after clean shutdown/checkpoint. Do not delete sidecars manually: they can contain committed data. Confirm the exact source and destination paths; never restore into a running app. Then restore:

```bash
cd S:\APPs\cartmate\ops
python cartmate_restore.py --backup ./backups/cartmate_backup_manual_20260927_122011.db --target ../backend/cartmate.db --confirm-offline
```

Safety features:
1. Requires and verifies the SHA-256 checksum against the adjacent `.json` manifest.
2. Performs `PRAGMA integrity_check` on the backup file *before* touching the live database.
3. Creates a transactionally consistent rollback snapshot of the existing database (`cartmate_rollback_pre_restore_<timestamp>.db`).
4. Refuses restoration if `-wal` or `-shm` exists; it never unlinks them.
5. Stages and atomically replaces the database, then checks integrity and row counts.

The rollback snapshot and its manifest are local and contain sensitive user/session data; protect them like the primary database. If restore or startup validation fails, keep the service stopped and restore the rollback snapshot through the same verified procedure. The tool does not automatically decide to roll back for you.

---

## 4. Running the Disaster Recovery Drill

To prove backup and recovery viability in CI or during pre-flight release audits:

```bash
python -m pytest ops/test_disaster_recovery.py -q
```
The drill runs only on generated databases under `ops/`; it never targets `backend/cartmate.db`. A production release still needs an encrypted offsite restore exercise, measured recovery time, and a named operator.
