"""Isolated Staging Test Harness for CartMate QA.

Runs FastAPI with staging-like deployment guards against the production React bundle,
intercepting OTP dispatches with a local capture adapter (no real SMS, no OTP in API responses,
no hardcoded bypasses, and no demo tokens).
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

QA_DIR = Path(__file__).resolve().parent
REPO_ROOT = QA_DIR.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
# Never reset a fixed path that might contain a previous run's data.
QA_RUNTIME = tempfile.TemporaryDirectory(prefix="cartmate-staging-qa-")
DB_PATH = Path(QA_RUNTIME.name) / "cartmate.db"
OTP_CAPTURE_FILE = Path(QA_RUNTIME.name) / "otp-capture.json"

# Ensure backend can be imported
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure production bundle exists
if not FRONTEND_DIST.exists():
    raise RuntimeError(f"Frontend dist not found at '{FRONTEND_DIST}'. Run 'npm run build' in frontend first.")

# Configure environment with strict staging deployment guards
os.environ["CARTMATE_ENV"] = "staging"
os.environ["CARTMATE_DEPLOYMENT"] = "1"
os.environ["CARTMATE_DATABASE_PATH"] = str(DB_PATH)
os.environ["CARTMATE_CORS_ALLOWED_ORIGINS"] = "https://staging.cartmate.example"
os.environ["CARTMATE_MODERATOR_USER_IDS"] = "usr_zuzanna"
os.environ["CARTMATE_STAGING_ALLOWED_PHONES"] = "+48600111001,+48600111002"
os.environ["OTP_PROVIDER"] = "smsapi"
os.environ["SMSAPI_API_TOKEN"] = ""
os.environ["SOS_WEBHOOK_SECRET"] = "staging_webhook_secret_min_16_chars_long"
os.environ["CARTMATE_DEFAULT_REGION"] = "silesia"
os.environ["CARTMATE_FRONTEND_DIST"] = str(FRONTEND_DIST)

# Configure capture-only OTP adapter before importing application
import auth_providers

class LocalCaptureOtpProvider:
    """Capture-only OTP adapter confined to local test harness."""

    async def send_otp(self, identifier: str, code: str) -> bool:
        clean_id = identifier.strip().lower()
        data = {}
        if OTP_CAPTURE_FILE.exists():
            try:
                data = json.loads(OTP_CAPTURE_FILE.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data[clean_id] = code
        OTP_CAPTURE_FILE.write_text(json.dumps(data), encoding="utf-8")
        return True


auth_providers.get_otp_provider = lambda: LocalCaptureOtpProvider()

# Import FastAPI application
import database
import main
from fastapi import APIRouter, HTTPException
from rate_limiter import rate_limiter
from storage import get_db_connection, storage

app = main.app
# This adapter exists only in the disposable loopback QA harness. The shipped
# backend trusts no age provider until a genuine reviewed integration exists.
main.AGE_ASSURANCE_TRUSTED_PROVIDERS = frozenset({"qa-local"})

qa_router = APIRouter(prefix="/_qa")


@qa_router.get("/latest-otp")
def get_latest_otp(phone: str):
    """Retrieve the latest captured OTP for an allowlisted phone number."""
    clean_phone = phone.strip().lower()
    if not OTP_CAPTURE_FILE.exists():
        raise HTTPException(404, "No OTP codes captured yet.")
    try:
        data = json.loads(OTP_CAPTURE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(500, f"Error reading capture file: {e}")
    code = data.get(clean_phone)
    if not code:
        raise HTTPException(404, f"No OTP captured for phone '{clean_phone}'. Captured: {list(data.keys())}")
    return {"phone": clean_phone, "code": code}


@qa_router.post("/strip-phone-verification")
def strip_phone_verification(phone: str):
    """Simulate a controlled session lacking phone OTP provenance."""
    user = database.find_user_by_identifier(phone)
    if not user:
        raise HTTPException(404, f"User with phone '{phone}' not found.")
    user.phone_verified_at = None
    storage.persist_user(user.model_dump())
    return {"status": "ok", "user_id": user.id, "phone": phone, "phone_verified_at": None}


@qa_router.post("/grant-age-proof")
def grant_local_age_proof(phone: str):
    """Simulate a positive provider callback for isolated browser tests only."""
    user = database.find_user_by_identifier(phone)
    if not user or not user.phone_verified_at:
        raise HTTPException(403, "An SMS-confirmed local test member is required.")
    now = datetime.now(timezone.utc)
    user.age_assurance_provider = "qa-local"
    user.adult_verified_at = now.isoformat()
    user.adult_verification_expires_at = (now + timedelta(days=1)).isoformat()
    storage.persist_user(user.model_dump())
    return {"status": "local_test_proof", "user_id": user.id}


@qa_router.post("/reset-state")
def reset_state():
    """Reset only this harness's disposable database and in-memory caches."""
    conn = get_db_connection(storage.db_path)
    try:
        # Delete dependents before parents; rollback on any SQL error.
        for table in (
            "otp_challenges", "otp_events",
            "chat_messages", "chat_rooms", "sessions", "revoked_sessions",
            "pilot_memberships", "pilot_invites",
            "join_requests", "pings", "sos_records", "trips", "hotspot_votes",
            "hotspots", "outings", "reports", "user_blocks",
            "shopping_buddies", "users",
        ):
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    database.USERS.clear()
    database.PINGS.clear()
    database.JOIN_REQUESTS.clear()
    database.TRIPS.clear()
    database.HOTSPOTS.clear()
    database.OUTINGS.clear()
    database.CHAT_ROOMS.clear()
    database.BLOCKED_USERS.clear()
    database.REPORTS.clear()
    database.SHOPPING_BUDDIES.clear()
    main.ACTIVE_SESSIONS.clear()
    main.SESSION_EXPIRIES.clear()
    main.REVOKED_TOKENS.clear()
    main.WS_TICKETS.clear()
    rate_limiter.clear()
    main.PILOT_INVITES_ENABLED = False

    OTP_CAPTURE_FILE.unlink(missing_ok=True)

    return {"status": "reset_successful"}


@qa_router.post("/pilot-invites/enable-and-issue")
def enable_pilot_invites():
    """Enable production-like admission on this disposable local harness only."""
    main.PILOT_INVITES_ENABLED = True
    code = storage.issue_pilot_invite((datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())
    return {"invite_code": code}


# Include qa_router and position it before the StaticFiles catch-all mount
app.include_router(qa_router)
mount_idx = next((i for i, r in enumerate(app.router.routes) if type(r).__name__ == "Mount"), None)
if mount_idx is not None:
    qa_routes = [r for r in app.router.routes if getattr(r, "path", "").startswith("/_qa")]
    for r in qa_routes:
        app.router.routes.remove(r)
    for r in reversed(qa_routes):
        app.router.routes.insert(mount_idx, r)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("CARTMATE_STAGING_PORT", "8008"))
    print(f"Starting CartMate Staging QA Harness on http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
