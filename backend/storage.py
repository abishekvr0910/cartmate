import json
import logging
import os
import sqlite3
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from config import OPERATIONAL_THRESHOLDS

logger = logging.getLogger("cartmate.storage")

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "cartmate.db")
DATABASE_PATH = os.getenv("CARTMATE_DATABASE_PATH", DEFAULT_DB_PATH)


def get_db_connection(db_path: str = DATABASE_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


# --- Versioned Database Migrations ---

MIGRATIONS: List[Tuple[int, str, str]] = [
    (
        1,
        "initial_core_schema",
        """
        -- Schema migrations tracking
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        );

        -- Users store
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            phone TEXT,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);

        -- Authentication sessions store
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            expires_at TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

        -- Outings and Trips
        CREATE TABLE IF NOT EXISTS outings (
            id TEXT PRIMARY KEY,
            destination_name TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS trips (
            id TEXT PRIMARY KEY,
            host_id TEXT NOT NULL,
            companion_id TEXT,
            status TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_trips_status ON trips(status);
        CREATE INDEX IF NOT EXISTS idx_trips_host ON trips(host_id);

        -- Emergency SOS records
        CREATE TABLE IF NOT EXISTS sos_records (
            id TEXT PRIMARY KEY,
            trip_id TEXT NOT NULL,
            message_id TEXT,
            status TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sos_trip ON sos_records(trip_id);
        CREATE INDEX IF NOT EXISTS idx_sos_message ON sos_records(message_id);

        -- Hotspots & Hotspot Votes
        CREATE TABLE IF NOT EXISTS hotspots (
            id TEXT PRIMARY KEY,
            city TEXT NOT NULL,
            data_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS hotspot_votes (
            spot_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (spot_id, user_id)
        );

        -- Live Shopping Pings
        CREATE TABLE IF NOT EXISTS pings (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            city TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Chat Rooms & Messages
        CREATE TABLE IF NOT EXISTS chat_rooms (
            id TEXT PRIMARY KEY,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            room_id TEXT NOT NULL,
            sender_id TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_chat_room ON chat_messages(room_id);
        """
    ),
    (
        2,
        "safety_blocks_reports_buddies_revocations",
        """
        -- User blocking relationships
        CREATE TABLE IF NOT EXISTS user_blocks (
            blocker_id TEXT NOT NULL,
            blocked_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (blocker_id, blocked_id)
        );
        CREATE INDEX IF NOT EXISTS idx_user_blocks_blocker ON user_blocks(blocker_id);
        CREATE INDEX IF NOT EXISTS idx_user_blocks_blocked ON user_blocks(blocked_id);

        -- Reports and moderation queue
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            reporter_id TEXT NOT NULL,
            reported_user_id TEXT NOT NULL,
            category TEXT NOT NULL,
            details TEXT NOT NULL,
            evidence_chat_message_id TEXT,
            trip_id TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            resolution_note TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
        CREATE INDEX IF NOT EXISTS idx_reports_reported_user ON reports(reported_user_id);

        -- Mutual shopping buddies
        CREATE TABLE IF NOT EXISTS shopping_buddies (
            user_id_1 TEXT NOT NULL,
            user_id_2 TEXT NOT NULL,
            established_at TEXT NOT NULL,
            shared_trips_count INTEGER DEFAULT 1,
            PRIMARY KEY (user_id_1, user_id_2)
        );

        -- Revoked sessions
        CREATE TABLE IF NOT EXISTS revoked_sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            revoked_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_revoked_sessions_user ON revoked_sessions(user_id);
        """
    ),
    (
        3,
        "moderation_action_attribution",
        "ALTER TABLE reports ADD COLUMN moderator_id TEXT;",
    ),
    (
        4,
        "durable_join_requests",
        """
        CREATE TABLE IF NOT EXISTS join_requests (
            id TEXT PRIMARY KEY,
            ping_id TEXT NOT NULL,
            applicant_id TEXT NOT NULL,
            status TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_join_requests_ping ON join_requests(ping_id);
        """,
    ),
    (
        5,
        "closed_pilot_invites",
        """
        CREATE TABLE IF NOT EXISTS pilot_invites (
            code_hash TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            redeemed_by_user_id TEXT,
            redeemed_at TEXT,
            revoked_at TEXT
        );
        CREATE TABLE IF NOT EXISTS pilot_memberships (
            user_id TEXT PRIMARY KEY,
            code_hash TEXT NOT NULL,
            admitted_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (code_hash) REFERENCES pilot_invites(code_hash)
        );
        """,
    ),
    (
        6,
        "durable_otp_challenges_and_limits",
        """
        CREATE TABLE IF NOT EXISTS otp_challenges (
            identifier_hash TEXT PRIMARY KEY,
            salt BLOB NOT NULL,
            code_digest BLOB NOT NULL,
            expires_at REAL NOT NULL,
            attempts_left INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS otp_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier_hash TEXT NOT NULL,
            kind TEXT NOT NULL,
            occurred_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_otp_events_identifier_kind_time
            ON otp_events(identifier_hash, kind, occurred_at);
        """,
    ),
    (
        7,
        "group_report_context",
        """
        ALTER TABLE reports ADD COLUMN outing_id TEXT;
        CREATE INDEX IF NOT EXISTS idx_reports_outing ON reports(outing_id);
        """,
    ),
    (
        8,
        "pilot_age_attestation_audit",
        """
        CREATE TABLE IF NOT EXISTS pilot_age_attestations (
            id TEXT PRIMARY KEY,
            subject_user_id TEXT NOT NULL,
            moderator_user_id TEXT NOT NULL,
            method TEXT NOT NULL,
            decision TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            expires_at TEXT,
            FOREIGN KEY (subject_user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (moderator_user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_pilot_age_attestations_subject
            ON pilot_age_attestations(subject_user_id, recorded_at);
        """,
    ),
    (
        9,
        "operator_activation_and_admission",
        """
        CREATE TABLE IF NOT EXISTS operator_activations (
            token_hash TEXT PRIMARY KEY,
            intended_for TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            consumed_at TEXT,
            consumed_by_user_id TEXT,
            revoked_at TEXT,
            created_by_operator TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_operator_activations_expires
            ON operator_activations(expires_at);

        CREATE TABLE IF NOT EXISTS operator_admissions (
            user_id TEXT PRIMARY KEY,
            token_hash TEXT NOT NULL,
            assurance_marker TEXT NOT NULL DEFAULT 'operator_in_person',
            admitted_at TEXT NOT NULL,
            revoked_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (token_hash) REFERENCES operator_activations(token_hash)
        );
        """,
    ),
    (
        10,
        "operator_account_recovery",
        """
        ALTER TABLE operator_activations ADD COLUMN target_user_id TEXT;
        CREATE INDEX IF NOT EXISTS idx_operator_activations_target_user
            ON operator_activations(target_user_id);
        """,
    ),
]


def pilot_invite_hash(code: str) -> str:
    normalized = code.strip().upper()
    if not re.fullmatch(r"CM-[A-F0-9]{24}", normalized):
        raise ValueError("Invalid pilot invite format")
    return hashlib.sha256(normalized.encode("ascii")).hexdigest()


def operator_activation_hash(token: str) -> str:
    normalized = token.strip().upper()
    if not re.fullmatch(r"CM(ACT|REC)-[A-F0-9]{24}", normalized):
        raise ValueError("Invalid operator activation token format")
    return hashlib.sha256(normalized.encode("ascii")).hexdigest()


class DurableStorage:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._ensure_parent_dir()
        self.apply_migrations()

    def _ensure_parent_dir(self):
        if self.db_path != ":memory:":
            parent = os.path.dirname(os.path.abspath(self.db_path))
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)

    def apply_migrations(self):
        conn = get_db_connection(self.db_path)
        try:
            # Create schema_migrations table if not exists
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                );
                """
            )
            conn.commit()

            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_migrations;")
            applied_versions = {row[0] for row in cursor.fetchall()}

            for version, name, sql in MIGRATIONS:
                if version not in applied_versions:
                    logger.info(f"Applying migration v{version}: {name}")
                    conn.executescript(sql)
                    now_str = datetime.now(timezone.utc).isoformat()
                    conn.execute(
                        "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?);",
                        (version, name, now_str),
                    )
                    conn.commit()
        finally:
            conn.close()

    def get_applied_migrations(self) -> List[dict]:
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT version, name, applied_at FROM schema_migrations ORDER BY version ASC;")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # --- OTP challenges and abuse limits ---

    @staticmethod
    def _otp_identifier_hash(identifier: str) -> str:
        return hashlib.sha256(identifier.strip().lower().encode("utf-8")).hexdigest()

    @staticmethod
    def _otp_code_digest(code: str, salt: bytes) -> bytes:
        # OTPs have little entropy; a salted, deliberately slow digest avoids
        # keeping usable codes in the SQLite backup or on disk.
        return hashlib.pbkdf2_hmac("sha256", code.encode("utf-8"), salt, 100_000)

    def reserve_otp_send_budget(
        self, key: str, max_requests: int, window_seconds: int, now: Optional[float] = None
    ) -> tuple[bool, int]:
        """Atomic send cap for shared invite codes, surviving process restarts."""
        now = datetime.now(timezone.utc).timestamp() if now is None else now
        key_hash = self._otp_identifier_hash(f"budget:{key}")
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            events = conn.execute(
                "SELECT occurred_at FROM otp_events WHERE identifier_hash = ? AND kind = 'budget' "
                "AND occurred_at > ? ORDER BY occurred_at",
                (key_hash, now - window_seconds),
            ).fetchall()
            if len(events) >= max_requests:
                return False, max(1, int(events[0]["occurred_at"] + window_seconds - now + 0.999))
            conn.execute(
                "INSERT INTO otp_events(identifier_hash, kind, occurred_at) VALUES (?, 'budget', ?)",
                (key_hash, now),
            )
            conn.commit()
            return True, 0
        finally:
            conn.close()

    def reserve_otp_challenge(self, identifier: str, code: str, now: Optional[float] = None) -> dict:
        now = datetime.now(timezone.utc).timestamp() if now is None else now
        identifier_hash = self._otp_identifier_hash(identifier)
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM otp_events WHERE occurred_at <= ?", (now - 900,))
            requests = conn.execute(
                "SELECT occurred_at FROM otp_events WHERE identifier_hash = ? AND kind = 'request' "
                "AND occurred_at > ? ORDER BY occurred_at",
                (identifier_hash, now - 600),
            ).fetchall()
            active_challenge = conn.execute(
                "SELECT 1 FROM otp_challenges WHERE identifier_hash = ? AND expires_at > ?",
                (identifier_hash, now),
            ).fetchone()
            if active_challenge and requests and now - requests[-1]["occurred_at"] < 60:
                return {"status": "rate_limited", "retry_after": max(1, int(requests[-1]["occurred_at"] + 60 - now + 0.999))}
            if len(requests) >= 3:
                return {"status": "rate_limited", "retry_after": max(1, int(requests[0]["occurred_at"] + 600 - now + 0.999))}
            failures = conn.execute(
                "SELECT occurred_at FROM otp_events WHERE identifier_hash = ? AND kind = 'failure' "
                "AND occurred_at > ? ORDER BY occurred_at",
                (identifier_hash, now - 900),
            ).fetchall()
            if len(failures) >= 5:
                return {"status": "rate_limited", "retry_after": max(1, int(failures[0]["occurred_at"] + 900 - now + 0.999))}

            salt = secrets.token_bytes(16)
            digest = self._otp_code_digest(code, salt)
            conn.execute(
                "INSERT INTO otp_challenges(identifier_hash, salt, code_digest, expires_at, attempts_left) "
                "VALUES (?, ?, ?, ?, 5) ON CONFLICT(identifier_hash) DO UPDATE SET "
                "salt=excluded.salt, code_digest=excluded.code_digest, expires_at=excluded.expires_at, "
                "attempts_left=5",
                (identifier_hash, salt, digest, now + 300),
            )
            conn.execute(
                "INSERT INTO otp_events(identifier_hash, kind, occurred_at) VALUES (?, 'request', ?)",
                (identifier_hash, now),
            )
            conn.commit()
            return {"status": "reserved"}
        finally:
            conn.close()

    def discard_otp_challenge(self, identifier: str, code: str) -> None:
        identifier_hash = self._otp_identifier_hash(identifier)
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT salt, code_digest FROM otp_challenges WHERE identifier_hash = ?",
                (identifier_hash,),
            ).fetchone()
            if row and hmac.compare_digest(row["code_digest"], self._otp_code_digest(code, row["salt"])):
                conn.execute("DELETE FROM otp_challenges WHERE identifier_hash = ?", (identifier_hash,))
            conn.commit()
        finally:
            conn.close()

    def invalidate_otp_challenge(self, identifier: str) -> None:
        conn = get_db_connection(self.db_path)
        try:
            conn.execute(
                "DELETE FROM otp_challenges WHERE identifier_hash = ?",
                (self._otp_identifier_hash(identifier),),
            )
            conn.commit()
        finally:
            conn.close()

    def consume_otp_challenge(self, identifier: str, code: str, now: Optional[float] = None) -> dict:
        now = datetime.now(timezone.utc).timestamp() if now is None else now
        identifier_hash = self._otp_identifier_hash(identifier)
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            failures = conn.execute(
                "SELECT occurred_at FROM otp_events WHERE identifier_hash = ? AND kind = 'failure' "
                "AND occurred_at > ? ORDER BY occurred_at",
                (identifier_hash, now - 900),
            ).fetchall()
            if len(failures) >= 5:
                return {"status": "locked", "retry_after": max(1, int(failures[0]["occurred_at"] + 900 - now + 0.999))}
            row = conn.execute(
                "SELECT salt, code_digest, expires_at, attempts_left FROM otp_challenges WHERE identifier_hash = ?",
                (identifier_hash,),
            ).fetchone()
            if not row:
                return {"status": "missing"}
            if now > row["expires_at"]:
                conn.execute("DELETE FROM otp_challenges WHERE identifier_hash = ?", (identifier_hash,))
                conn.commit()
                return {"status": "expired"}
            if row["attempts_left"] <= 0:
                return {"status": "locked", "retry_after": 900}
            digest = self._otp_code_digest(code, row["salt"])
            if hmac.compare_digest(row["code_digest"], digest):
                conn.execute("DELETE FROM otp_challenges WHERE identifier_hash = ?", (identifier_hash,))
                conn.commit()
                return {"status": "verified"}
            attempts_left = row["attempts_left"] - 1
            conn.execute(
                "UPDATE otp_challenges SET attempts_left = ? WHERE identifier_hash = ?",
                (attempts_left, identifier_hash),
            )
            conn.execute(
                "INSERT INTO otp_events(identifier_hash, kind, occurred_at) VALUES (?, 'failure', ?)",
                (identifier_hash, now),
            )
            conn.commit()
            return {"status": "invalid", "attempts_left": attempts_left}
        finally:
            conn.close()

    # --- Users Persistence ---

    def persist_user(self, user_dict: dict):
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            user_id = user_dict["id"]
            email = user_dict.get("email")
            phone = user_dict.get("phone")
            data_json = json.dumps(user_dict)
            conn.execute(
                """
                INSERT INTO users (id, email, phone, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    email=excluded.email,
                    phone=excluded.phone,
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at;
                """,
                (user_id, email, phone, data_json, now_str, now_str),
            )
            conn.commit()
        finally:
            conn.close()

    def record_pilot_age_attestation(
        self,
        user_dict: dict,
        moderator_user_id: str,
        method: str,
        decision: str,
        recorded_at: str,
        expires_at: Optional[str],
    ) -> None:
        """Atomically update eligibility and record a minimal operator audit.

        Document images, numbers, birth dates and names from the verifier are
        deliberately not accepted or stored here.
        """
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            updated = conn.execute(
                "UPDATE users SET data_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(user_dict), recorded_at, user_dict["id"]),
            )
            if updated.rowcount != 1:
                raise ValueError("The subject account must exist before an age attestation")
            conn.execute(
                "INSERT INTO pilot_age_attestations "
                "(id, subject_user_id, moderator_user_id, method, decision, recorded_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (secrets.token_hex(16), user_dict["id"], moderator_user_id, method, decision, recorded_at, expires_at),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def issue_pilot_invite(self, expires_at: str) -> str:
        expiry = datetime.fromisoformat(expires_at)
        if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
            raise ValueError("Pilot invite expiry must be a future timezone-aware timestamp")
        expiry = expiry.astimezone(timezone.utc)
        code = f"CM-{secrets.token_hex(12).upper()}"
        conn = get_db_connection(self.db_path)
        try:
            conn.execute(
                "INSERT INTO pilot_invites (code_hash, created_at, expires_at) VALUES (?, ?, ?)",
                (pilot_invite_hash(code), datetime.now(timezone.utc).isoformat(), expiry.isoformat()),
            )
            conn.commit()
            return code
        finally:
            conn.close()

    def is_pilot_invite_available(self, code: str) -> bool:
        try:
            code_hash = pilot_invite_hash(code)
        except ValueError:
            return False
        conn = get_db_connection(self.db_path)
        try:
            row = conn.execute(
                "SELECT 1 FROM pilot_invites WHERE code_hash = ? AND expires_at > ? "
                "AND redeemed_at IS NULL AND revoked_at IS NULL",
                (code_hash, datetime.now(timezone.utc).isoformat()),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def revoke_pilot_invite(self, code: str) -> bool:
        code_hash = pilot_invite_hash(code)
        conn = get_db_connection(self.db_path)
        try:
            result = conn.execute(
                "UPDATE pilot_invites SET revoked_at = ? WHERE code_hash = ? "
                "AND redeemed_at IS NULL AND revoked_at IS NULL",
                (datetime.now(timezone.utc).isoformat(), code_hash),
            )
            conn.commit()
            return result.rowcount == 1
        finally:
            conn.close()

    def is_pilot_member(self, user_id: str) -> bool:
        conn = get_db_connection(self.db_path)
        try:
            return conn.execute(
                """
                SELECT 1 FROM pilot_memberships WHERE user_id = ?
                UNION
                SELECT 1 FROM operator_admissions WHERE user_id = ? AND revoked_at IS NULL
                """,
                (user_id, user_id),
            ).fetchone() is not None
        finally:
            conn.close()

    def issue_operator_activation(
        self,
        expires_at: str,
        intended_for: str,
        operator_id: Optional[str] = None,
        target_user_id: Optional[str] = None,
    ) -> str:
        expiry = datetime.fromisoformat(expires_at)
        if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
            raise ValueError("Operator activation expiry must be a future timezone-aware timestamp")
        expiry = expiry.astimezone(timezone.utc)
        prefix = "CMREC" if target_user_id else "CMACT"
        raw_token = f"{prefix}-{secrets.token_hex(12).upper()}"
        token_hash = operator_activation_hash(raw_token)
        now_str = datetime.now(timezone.utc).isoformat()
        conn = get_db_connection(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO operator_activations (
                    token_hash, intended_for, created_at, expires_at, created_by_operator, target_user_id
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (token_hash, intended_for.strip(), now_str, expiry.isoformat(), operator_id, target_user_id),
            )
            conn.commit()
            return raw_token
        finally:
            conn.close()

    def get_user(self, user_id: str) -> Optional[dict]:
        conn = get_db_connection(self.db_path)
        try:
            row = conn.execute("SELECT data_json FROM users WHERE id = ?", (user_id,)).fetchone()
            return json.loads(row[0]) if row else None
        finally:
            conn.close()

    def issue_operator_recovery(
        self,
        target_user_id: str,
        expires_at: str,
        operator_id: Optional[str] = None,
        intended_for: str = "",
    ) -> str:
        """Issue an explicitly bound, one-use account recovery token for an admitted user."""
        user = self.get_user(target_user_id)
        if not user:
            raise ValueError("Target user does not exist")
        adm = self.get_operator_admission(target_user_id)
        if not adm or adm.get("revoked_at"):
            raise ValueError("Target user is not an active operator-admitted user")
        if not intended_for:
            intended_for = user.get("name", "")
        return self.issue_operator_activation(
            expires_at=expires_at,
            intended_for=intended_for,
            operator_id=operator_id,
            target_user_id=target_user_id,
        )

    def is_operator_activation_available(self, token: str) -> bool:
        try:
            token_hash = operator_activation_hash(token)
        except ValueError:
            return False
        conn = get_db_connection(self.db_path)
        try:
            row = conn.execute(
                """
                SELECT 1 FROM operator_activations
                WHERE token_hash = ? AND expires_at > ?
                  AND consumed_at IS NULL AND revoked_at IS NULL
                """,
                (token_hash, datetime.now(timezone.utc).isoformat()),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def revoke_operator_activation(self, token_or_hash: str) -> bool:
        normalized = token_or_hash.strip().upper()
        if re.fullmatch(r"CM(ACT|REC)-[A-F0-9]{24}", normalized):
            token_hash = hashlib.sha256(normalized.encode("ascii")).hexdigest()
        elif re.fullmatch(r"[A-F0-9]{64}", normalized):
            token_hash = normalized.lower()
        else:
            raise ValueError("Invalid activation token or hash format")

        conn = get_db_connection(self.db_path)
        try:
            result = conn.execute(
                """
                UPDATE operator_activations
                SET revoked_at = ?
                WHERE token_hash = ? AND consumed_at IS NULL AND revoked_at IS NULL
                """,
                (datetime.now(timezone.utc).isoformat(), token_hash),
            )
            conn.commit()
            return result.rowcount == 1
        finally:
            conn.close()

    def redeem_operator_activation(self, token: str, user_dict: dict) -> None:
        """Atomically consume one activation token and create the operator-admitted user."""
        token_hash = operator_activation_hash(token)
        if user_dict.get("phone_verified_at"):
            raise ValueError("Operator admission must not claim phone verification")
        now_str = datetime.now(timezone.utc).isoformat()
        user_dict["assurance_marker"] = "operator_in_person"
        user_dict["operator_admitted_at"] = now_str

        conn = get_db_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            updated = conn.execute(
                """
                UPDATE operator_activations
                SET consumed_at = ?, consumed_by_user_id = ?
                WHERE token_hash = ? AND expires_at > ?
                  AND consumed_at IS NULL AND revoked_at IS NULL
                """,
                (now_str, user_dict["id"], token_hash, now_str),
            )
            if updated.rowcount != 1:
                raise ValueError("Activation token is invalid, expired, already consumed, or revoked")

            conn.execute(
                """
                INSERT INTO users (id, email, phone, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_dict["id"], user_dict.get("email"), user_dict.get("phone"),
                    json.dumps(user_dict), now_str, now_str,
                ),
            )
            conn.execute(
                """
                INSERT INTO operator_admissions (user_id, token_hash, assurance_marker, admitted_at)
                VALUES (?, ?, 'operator_in_person', ?)
                """,
                (user_dict["id"], token_hash, now_str),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def redeem_operator_recovery(self, token: str) -> dict:
        """Atomically consume one operator recovery token and return the recovered user record."""
        token_hash = operator_activation_hash(token)
        now_str = datetime.now(timezone.utc).isoformat()
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT target_user_id FROM operator_activations
                WHERE token_hash = ? AND expires_at > ?
                  AND consumed_at IS NULL AND revoked_at IS NULL
                """,
                (token_hash, now_str),
            ).fetchone()
            if not row or not row[0]:
                raise ValueError("Recovery token is invalid, expired, already consumed, revoked, or not bound to an account")
            target_user_id = row[0]

            u_row = conn.execute("SELECT data_json FROM users WHERE id = ?", (target_user_id,)).fetchone()
            if not u_row:
                raise ValueError("Target user account not found")
            adm_row = conn.execute(
                "SELECT revoked_at FROM operator_admissions WHERE user_id = ?", (target_user_id,)
            ).fetchone()
            if not adm_row or adm_row[0]:
                raise ValueError("User admission has been revoked or is not active")

            updated = conn.execute(
                """
                UPDATE operator_activations
                SET consumed_at = ?, consumed_by_user_id = ?
                WHERE token_hash = ? AND consumed_at IS NULL AND revoked_at IS NULL AND expires_at > ?
                """,
                (now_str, target_user_id, token_hash, now_str),
            )
            if updated.rowcount != 1:
                raise ValueError("Recovery token could not be atomically consumed")
            conn.commit()
            return json.loads(u_row[0])
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def rollback_operator_activation_redemption(self, token: str, user_id: str) -> None:
        """Roll back an activation redemption if session persistence fails.
        Ensures the activation token is un-consumed and the user/admission records are removed,
        preventing stranded accounts without sessions.
        """
        try:
            token_hash = operator_activation_hash(token)
        except ValueError:
            return
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM operator_admissions WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.execute(
                """
                UPDATE operator_activations
                SET consumed_at = NULL, consumed_by_user_id = NULL
                WHERE token_hash = ? AND consumed_by_user_id = ?
                """,
                (token_hash, user_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def rollback_operator_recovery_redemption(self, token: str, user_id: str, session_token: Optional[str] = None) -> None:
        """Roll back a recovery token redemption if session creation/persistence fails.
        Un-consumes the recovery token and removes any partial session without deleting
        the underlying user account or affecting prior durable state.
        """
        try:
            token_hash = operator_activation_hash(token)
        except ValueError:
            return
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            if session_token:
                conn.execute("DELETE FROM sessions WHERE token = ?", (session_token,))
            conn.execute(
                """
                UPDATE operator_activations
                SET consumed_at = NULL, consumed_by_user_id = NULL
                WHERE token_hash = ? AND target_user_id = ?
                """,
                (token_hash, user_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_operator_admission(self, user_id: str) -> Optional[dict]:
        conn = get_db_connection(self.db_path)
        try:
            row = conn.execute(
                "SELECT user_id, token_hash, assurance_marker, admitted_at, revoked_at "
                "FROM operator_admissions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def is_operator_admitted(self, user_id: str) -> bool:
        adm = self.get_operator_admission(user_id)
        return (
            adm is not None
            and adm.get("revoked_at") is None
            and adm.get("assurance_marker") == "operator_in_person"
        )

    def revoke_operator_admission(self, user_id: str) -> bool:
        conn = get_db_connection(self.db_path)
        try:
            result = conn.execute(
                "UPDATE operator_admissions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
                (datetime.now(timezone.utc).isoformat(), user_id),
            )
            conn.commit()
            return result.rowcount == 1
        finally:
            conn.close()

    def persist_user_with_pilot_invite(self, user_dict: dict, code: str) -> None:
        """Consume one invite and create the verified user in a single transaction."""
        code_hash = pilot_invite_hash(code)
        if not user_dict.get("phone_verified_at"):
            raise ValueError("Pilot registration requires verified phone provenance")
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            now_str = datetime.now(timezone.utc).isoformat()
            updated = conn.execute(
                "UPDATE pilot_invites SET redeemed_by_user_id = ?, redeemed_at = ? "
                "WHERE code_hash = ? AND expires_at > ? AND redeemed_at IS NULL AND revoked_at IS NULL",
                (user_dict["id"], now_str, code_hash, now_str),
            )
            if updated.rowcount != 1:
                raise ValueError("Pilot invite is invalid, expired, redeemed, or revoked")
            conn.execute(
                "INSERT INTO users (id, email, phone, data_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    user_dict["id"], user_dict.get("email"), user_dict.get("phone"),
                    json.dumps(user_dict), now_str, now_str,
                ),
            )
            conn.execute(
                "INSERT INTO pilot_memberships (user_id, code_hash, admitted_at) VALUES (?, ?, ?)",
                (user_dict["id"], code_hash, now_str),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def load_users(self) -> Dict[str, dict]:
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, data_json FROM users;")
            users = {}
            for row in cursor.fetchall():
                users[row["id"]] = json.loads(row["data_json"])
            return users
        finally:
            conn.close()

    # --- Sessions Persistence ---

    def persist_session(self, token: str, user_id: str, expires_at: Optional[str] = None):
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            if expires_at is None:
                expires_at = (
                    datetime.now(timezone.utc)
                    + timedelta(hours=OPERATIONAL_THRESHOLDS.session_ttl_hours)
                ).isoformat()
            conn.execute(
                """
                INSERT INTO sessions (token, user_id, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(token) DO UPDATE SET
                    user_id=excluded.user_id,
                    expires_at=excluded.expires_at;
                """,
                (token, user_id, expires_at, now_str),
            )
            conn.commit()
        finally:
            conn.close()

    def remove_session(self, token: str):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("DELETE FROM sessions WHERE token = ?;", (token,))
            conn.commit()
        finally:
            conn.close()

    def load_sessions(self) -> Dict[str, str]:
        conn = get_db_connection(self.db_path)
        try:
            now = datetime.now(timezone.utc)
            cursor = conn.cursor()
            cursor.execute("SELECT token, user_id, expires_at FROM sessions;")
            sessions: Dict[str, str] = {}
            for row in cursor.fetchall():
                expires_at = row["expires_at"]
                if not expires_at:
                    continue
                try:
                    expiry = datetime.fromisoformat(expires_at)
                    if expiry.tzinfo is None:
                        expiry = expiry.replace(tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    continue
                if expiry > now:
                    sessions[row["token"]] = row["user_id"]
            return sessions
        finally:
            conn.close()

    def load_session_expiries(self) -> Dict[str, str]:
        conn = get_db_connection(self.db_path)
        try:
            now = datetime.now(timezone.utc)
            cursor = conn.cursor()
            cursor.execute("SELECT token, expires_at FROM sessions WHERE expires_at IS NOT NULL;")
            expiries: Dict[str, str] = {}
            for row in cursor.fetchall():
                try:
                    expiry = datetime.fromisoformat(row["expires_at"])
                    if expiry.tzinfo is None:
                        expiry = expiry.replace(tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    continue
                if expiry > now:
                    expiries[row["token"]] = row["expires_at"]
            return expiries
        finally:
            conn.close()

    # --- Trips Persistence ---

    def persist_trip(self, trip_dict: dict):
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            trip_id = trip_dict["id"]
            host_id = trip_dict["host"]["id"]
            companion_id = trip_dict["companion"]["id"] if trip_dict.get("companion") else None
            status = trip_dict.get("status", "scheduled")
            data_json = json.dumps(trip_dict)
            conn.execute(
                """
                INSERT INTO trips (id, host_id, companion_id, status, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    host_id=excluded.host_id,
                    companion_id=excluded.companion_id,
                    status=excluded.status,
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at;
                """,
                (trip_id, host_id, companion_id, status, data_json, now_str, now_str),
            )
            conn.commit()
        finally:
            conn.close()

    def load_trips(self) -> Dict[str, dict]:
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, data_json FROM trips;")
            trips = {}
            for row in cursor.fetchall():
                trips[row["id"]] = json.loads(row["data_json"])
            return trips
        finally:
            conn.close()

    # --- SOS Records Persistence ---

    def persist_sos_record(self, record_dict: dict):
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            rec_id = record_dict["id"]
            trip_id = record_dict.get("trip_id", "")
            message_id = record_dict.get("message_id")
            status = record_dict.get("status", "pending")
            data_json = json.dumps(record_dict)
            conn.execute(
                """
                INSERT INTO sos_records (id, trip_id, message_id, status, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    trip_id=excluded.trip_id,
                    message_id=excluded.message_id,
                    status=excluded.status,
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at;
                """,
                (rec_id, trip_id, message_id, status, data_json, now_str, now_str),
            )
            conn.commit()
        finally:
            conn.close()

    def load_sos_records(self) -> Dict[str, dict]:
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, data_json FROM sos_records;")
            records = {}
            for row in cursor.fetchall():
                records[row["id"]] = json.loads(row["data_json"])
            return records
        finally:
            conn.close()

    # --- Hotspots & Hotspot Votes ---

    def persist_hotspot(self, hotspot_dict: dict):
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            spot_id = hotspot_dict["id"]
            city = hotspot_dict.get("city", "Katowice")
            data_json = json.dumps(hotspot_dict)
            conn.execute(
                """
                INSERT INTO hotspots (id, city, data_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    city=excluded.city,
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at;
                """,
                (spot_id, city, data_json, now_str),
            )
            conn.commit()
        finally:
            conn.close()

    def persist_hotspot_vote(self, spot_id: str, user_id: str):
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT OR IGNORE INTO hotspot_votes (spot_id, user_id, created_at)
                VALUES (?, ?, ?);
                """,
                (spot_id, user_id, now_str),
            )
            conn.commit()
        finally:
            conn.close()

    def persist_hotspot_vote_and_group(
        self,
        hotspot_dict: dict,
        user_id: str,
        outing_dict: Optional[dict] = None,
        room_dict: Optional[dict] = None,
    ) -> None:
        """Commit the vote and optional group shell before publishing either in memory."""
        if (outing_dict is None) != (room_dict is None):
            raise ValueError("An outing and chat room must be committed together")
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """INSERT INTO hotspots (id, city, data_json, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET city=excluded.city,
                       data_json=excluded.data_json, updated_at=excluded.updated_at""",
                (hotspot_dict["id"], hotspot_dict["city"], json.dumps(hotspot_dict), now_str),
            )
            conn.execute(
                "INSERT OR IGNORE INTO hotspot_votes (spot_id, user_id, created_at) VALUES (?, ?, ?)",
                (hotspot_dict["id"], user_id, now_str),
            )
            if outing_dict is not None and room_dict is not None:
                conn.execute(
                    """INSERT INTO outings (id, destination_name, data_json, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (outing_dict["id"], outing_dict["hotspot_name"], json.dumps(outing_dict), now_str, now_str),
                )
                conn.execute(
                    """INSERT INTO chat_rooms (id, data_json, created_at, updated_at)
                       VALUES (?, ?, ?, ?)""",
                    (room_dict["id"], json.dumps(room_dict), now_str, now_str),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def persist_outing_membership(self, outing_dict: dict, room_dict: dict) -> None:
        """Keep the outing roster and chat authorization roster in one transaction."""
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            conn.execute("BEGIN IMMEDIATE")
            for table, row in (("outings", outing_dict), ("chat_rooms", room_dict)):
                conn.execute(
                    f"UPDATE {table} SET data_json = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(row), now_str, row["id"]),
                )
                if conn.execute("SELECT changes()").fetchone()[0] != 1:
                    raise RuntimeError(f"Missing {table} row for group membership update")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def remove_hotspot_vote(self, spot_id: str, user_id: str) -> None:
        conn = get_db_connection(self.db_path)
        try:
            conn.execute(
                "DELETE FROM hotspot_votes WHERE spot_id = ? AND user_id = ?;",
                (spot_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()

    def persist_hotspot_unvote(self, hotspot_dict: dict, user_id: str) -> None:
        """Commit vote withdrawal and public count together."""
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "UPDATE hotspots SET data_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(hotspot_dict), now_str, hotspot_dict["id"]),
            )
            if conn.execute("SELECT changes()").fetchone()[0] != 1:
                raise RuntimeError("Missing hotspot row for vote withdrawal")
            conn.execute(
                "DELETE FROM hotspot_votes WHERE spot_id = ? AND user_id = ?",
                (hotspot_dict["id"], user_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def load_hotspots(self) -> Dict[str, dict]:
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, data_json FROM hotspots;")
            spots = {}
            for row in cursor.fetchall():
                spots[row["id"]] = json.loads(row["data_json"])
            return spots
        finally:
            conn.close()

    def load_hotspot_votes(self) -> List[Tuple[str, str]]:
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT spot_id, user_id FROM hotspot_votes;")
            return [(row["spot_id"], row["user_id"]) for row in cursor.fetchall()]
        finally:
            conn.close()

    # --- Chat Rooms & Messages ---

    def persist_chat_room(self, room_dict: dict):
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            room_id = room_dict["id"]
            data_json = json.dumps(room_dict)
            conn.execute(
                """
                INSERT INTO chat_rooms (id, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at;
                """,
                (room_id, data_json, now_str, now_str),
            )
            conn.commit()
        finally:
            conn.close()

    def persist_chat_message(self, room_id: str, msg_dict: dict):
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            msg_id = msg_dict["id"]
            sender_id = msg_dict.get("sender_id", "")
            data_json = json.dumps(msg_dict)
            conn.execute(
                """
                INSERT OR REPLACE INTO chat_messages (id, room_id, sender_id, data_json, created_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (msg_id, room_id, sender_id, data_json, now_str),
            )
            conn.commit()
        finally:
            conn.close()

    def load_chat_rooms(self) -> Dict[str, dict]:
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, data_json FROM chat_rooms;")
            rooms = {}
            for row in cursor.fetchall():
                rooms[row["id"]] = json.loads(row["data_json"])
            return rooms
        finally:
            conn.close()

    # --- Pings & Outings ---

    def persist_ping(self, ping_dict: dict):
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            ping_id = ping_dict["id"]
            host = ping_dict.get("host", {})
            user_id = host.get("id", "")
            city = host.get("city", "Katowice")
            data_json = json.dumps(ping_dict)
            conn.execute(
                """
                INSERT INTO pings (id, user_id, city, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    user_id=excluded.user_id,
                    city=excluded.city,
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at;
                """,
                (ping_id, user_id, city, data_json, now_str, now_str),
            )
            conn.commit()
        finally:
            conn.close()

    def load_pings(self) -> Dict[str, dict]:
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, data_json FROM pings;")
            pings = {}
            for row in cursor.fetchall():
                pings[row["id"]] = json.loads(row["data_json"])
            return pings
        finally:
            conn.close()

    def persist_join_request(self, request_dict: dict) -> None:
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO join_requests
                    (id, ping_id, applicant_id, status, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status,
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at;
                """,
                (
                    request_dict["id"],
                    request_dict["ping_id"],
                    request_dict["applicant"]["id"],
                    request_dict["status"],
                    json.dumps(request_dict),
                    request_dict["created_at"],
                    now_str,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def load_join_requests(self) -> Dict[str, List[dict]]:
        conn = get_db_connection(self.db_path)
        try:
            rows = conn.execute(
                "SELECT ping_id, data_json FROM join_requests ORDER BY created_at, id;"
            ).fetchall()
            requests: Dict[str, List[dict]] = {}
            for row in rows:
                requests.setdefault(row["ping_id"], []).append(json.loads(row["data_json"]))
            return requests
        finally:
            conn.close()

    def persist_join_acceptance(
        self,
        ping_dict: dict,
        request_dicts: List[dict],
        trip_dict: dict,
        room_dict: dict,
    ) -> None:
        """Commit the match, requests, trip and chat room as one SQLite unit."""
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE;")
            persisted = conn.execute(
                "SELECT data_json FROM pings WHERE id = ?;", (ping_dict["id"],)
            ).fetchone()
            if not persisted or json.loads(persisted["data_json"]).get("status") != "active":
                raise ValueError("Ping is no longer available for acceptance")
            now_str = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "UPDATE pings SET data_json = ?, updated_at = ? WHERE id = ?;",
                (json.dumps(ping_dict), now_str, ping_dict["id"]),
            )
            for request_dict in request_dicts:
                conn.execute(
                    """
                    INSERT INTO join_requests
                        (id, ping_id, applicant_id, status, data_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        status=excluded.status,
                        data_json=excluded.data_json,
                        updated_at=excluded.updated_at;
                    """,
                    (
                        request_dict["id"], request_dict["ping_id"],
                        request_dict["applicant"]["id"], request_dict["status"],
                        json.dumps(request_dict), request_dict["created_at"], now_str,
                    ),
                )
            conn.execute(
                """
                INSERT INTO trips
                    (id, host_id, companion_id, status, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    trip_dict["id"], trip_dict["host"]["id"],
                    trip_dict["companion"]["id"], trip_dict["status"],
                    json.dumps(trip_dict), trip_dict["created_at"], now_str,
                ),
            )
            conn.execute(
                """
                INSERT INTO chat_rooms (id, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?);
                """,
                (room_dict["id"], json.dumps(room_dict), room_dict["created_at"], now_str),
            )
            for message in room_dict.get("messages", []):
                conn.execute(
                    """
                    INSERT INTO chat_messages (id, room_id, sender_id, data_json, created_at)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (
                        message["id"], room_dict["id"], message["sender_id"],
                        json.dumps(message), message["created_at"],
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def persist_outing(self, outing_dict: dict):
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            outing_id = outing_dict["id"]
            dest = outing_dict.get("destination_name", "")
            data_json = json.dumps(outing_dict)
            conn.execute(
                """
                INSERT INTO outings (id, destination_name, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    destination_name=excluded.destination_name,
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at;
                """,
                (outing_id, dest, data_json, now_str, now_str),
            )
            conn.commit()
        finally:
            conn.close()

    def load_outings(self) -> Dict[str, dict]:
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, data_json FROM outings;")
            outings = {}
            for row in cursor.fetchall():
                outings[row["id"]] = json.loads(row["data_json"])
            return outings
        finally:
            conn.close()

    # --- User Blocks Persistence ---

    def persist_block(self, blocker_id: str, blocked_id: str):
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT OR IGNORE INTO user_blocks (blocker_id, blocked_id, created_at)
                VALUES (?, ?, ?);
                """,
                (blocker_id, blocked_id, now_str),
            )
            conn.commit()
        finally:
            conn.close()

    def remove_block(self, blocker_id: str, blocked_id: str):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute(
                "DELETE FROM user_blocks WHERE blocker_id = ? AND blocked_id = ?;",
                (blocker_id, blocked_id),
            )
            conn.commit()
        finally:
            conn.close()

    def load_blocks(self) -> List[Tuple[str, str]]:
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT blocker_id, blocked_id FROM user_blocks;")
            return [(row["blocker_id"], row["blocked_id"]) for row in cursor.fetchall()]
        finally:
            conn.close()

    # --- Reports & Moderation Persistence ---

    def persist_report(self, report_dict: dict):
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO reports (id, reporter_id, reported_user_id, category, details, evidence_chat_message_id, trip_id, outing_id, status, resolution_note, moderator_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status,
                    resolution_note=excluded.resolution_note,
                    moderator_id=excluded.moderator_id,
                    updated_at=excluded.updated_at;
                """,
                (
                    report_dict["id"],
                    report_dict["reporter_id"],
                    report_dict["reported_user_id"],
                    report_dict["category"],
                    report_dict["details"],
                    report_dict.get("evidence_chat_message_id"),
                    report_dict.get("trip_id"),
                    report_dict.get("outing_id"),
                    report_dict.get("status", "pending"),
                    report_dict.get("resolution_note"),
                    report_dict.get("moderator_id"),
                    report_dict.get("created_at", now_str),
                    now_str,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def load_reports(self) -> Dict[str, dict]:
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reports ORDER BY created_at DESC;")
            reports = {}
            for row in cursor.fetchall():
                reports[row["id"]] = dict(row)
            return reports
        finally:
            conn.close()

    def update_report_status(
        self,
        report_id: str,
        status: str,
        resolution_note: Optional[str] = None,
        moderator_id: Optional[str] = None,
    ):
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                UPDATE reports
                SET status = ?, resolution_note = ?, moderator_id = ?, updated_at = ?
                WHERE id = ?;
                """,
                (status, resolution_note, moderator_id, now_str, report_id),
            )
            conn.commit()
        finally:
            conn.close()

    # --- Shopping Buddies Persistence ---

    def persist_shopping_buddy(self, user_id_1: str, user_id_2: str):
        u1, u2 = sorted([user_id_1, user_id_2])
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO shopping_buddies (user_id_1, user_id_2, established_at, shared_trips_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id_1, user_id_2) DO UPDATE SET
                    shared_trips_count = shared_trips_count + 1;
                """,
                (u1, u2, now_str),
            )
            conn.commit()
        finally:
            conn.close()

    def load_shopping_buddies(self) -> List[dict]:
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id_1, user_id_2, established_at, shared_trips_count FROM shopping_buddies;")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # --- Session Revocation & Lifecycle ---

    def revoke_session(self, token: str, user_id: str):
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT OR REPLACE INTO revoked_sessions (token, user_id, revoked_at)
                VALUES (?, ?, ?);
                """,
                (token, user_id, now_str),
            )
            conn.execute("DELETE FROM sessions WHERE token = ?;", (token,))
            conn.commit()
        finally:
            conn.close()

    def revoke_all_user_sessions(self, user_id: str):
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            cursor = conn.cursor()
            cursor.execute("SELECT token FROM sessions WHERE user_id = ?;", (user_id,))
            tokens = [row["token"] for row in cursor.fetchall()]
            for token in tokens:
                conn.execute(
                    "INSERT OR REPLACE INTO revoked_sessions (token, user_id, revoked_at) VALUES (?, ?, ?);",
                    (token, user_id, now_str),
                )
            conn.execute("DELETE FROM sessions WHERE user_id = ?;", (user_id,))
            conn.commit()
        finally:
            conn.close()

    def revoke_other_user_sessions(self, user_id: str, current_token: str) -> list[str]:
        """Atomically revoke persisted sessions except the authenticated caller."""
        conn = get_db_connection(self.db_path)
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT token FROM sessions WHERE user_id = ? AND token != ?;",
                (user_id, current_token),
            )
            tokens = [row["token"] for row in cursor.fetchall()]
            for token in tokens:
                cursor.execute(
                    "INSERT OR REPLACE INTO revoked_sessions (token, user_id, revoked_at) VALUES (?, ?, ?);",
                    (token, user_id, now_str),
                )
            cursor.execute(
                "DELETE FROM sessions WHERE user_id = ? AND token != ?;",
                (user_id, current_token),
            )
            conn.commit()
            return tokens
        finally:
            conn.close()

    def load_revoked_tokens(self) -> set:
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT token FROM revoked_sessions;")
            return {row["token"] for row in cursor.fetchall()}
        finally:
            conn.close()

    def get_active_sessions_for_user(self, user_id: str) -> List[dict]:
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT token, user_id, expires_at, created_at FROM sessions WHERE user_id = ?;", (user_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()


# Global storage instance
storage = DurableStorage()
