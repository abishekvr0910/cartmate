"""Isolated Operator Pilot Test Harness for CartMate QA.

Runs FastAPI in staging mode with operator pilot enabled against the production React bundle.
Uses an ephemeral SQLite database and bootstraps an operator account before process startup
so CARTMATE_MODERATOR_USER_IDS is configured via environment without in-memory mutation.
"""

import json
import os
import secrets
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

QA_DIR = Path(__file__).resolve().parent
REPO_ROOT = QA_DIR.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"

if not FRONTEND_DIST.exists():
    raise RuntimeError(f"Frontend dist not found at '{FRONTEND_DIST}'. Run 'npm run build' in frontend first.")

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Create ephemeral disposable directory and database or reuse provided path
db_env = os.getenv("CARTMATE_DATABASE_PATH")
if db_env:
    DB_PATH = Path(db_env)
    QA_RUNTIME = None
else:
    QA_RUNTIME = tempfile.TemporaryDirectory(prefix="cartmate-op-qa-")
    DB_PATH = Path(QA_RUNTIME.name) / "operator_pilot.db"

OPERATOR_USER_ID = "usr_operator_qa"
OPERATOR_SESSION_TOKEN = f"cmt_{secrets.token_hex(20)}"
port_str = os.getenv("CARTMATE_OPERATOR_PILOT_PORT", "8010")

# Configure environment BEFORE importing backend modules
os.environ["CARTMATE_ENV"] = "staging"
os.environ["CARTMATE_DEPLOYMENT"] = "0"
os.environ["CARTMATE_DATABASE_PATH"] = str(DB_PATH)
os.environ["CARTMATE_CORS_ALLOWED_ORIGINS"] = (
    f"https://staging.cartmate.example,http://127.0.0.1:{port_str},http://localhost:{port_str},http://127.0.0.1:8010,http://localhost:8010"
)
os.environ["CARTMATE_MODERATOR_USER_IDS"] = OPERATOR_USER_ID
os.environ["CARTMATE_STAGING_ALLOWED_PHONES"] = "+48600111001,+48600111002"
os.environ["CARTMATE_OPERATOR_PILOT_ENABLED"] = "1"
os.environ["CARTMATE_MANUAL_AGE_PILOT_ENABLED"] = "1"
os.environ["OTP_PROVIDER"] = "console"
os.environ["SOS_PROVIDER"] = "disabled"
os.environ["SOS_WEBHOOK_SECRET"] = "staging_webhook_secret_min_16_chars_long"
os.environ["CARTMATE_DEFAULT_REGION"] = "silesia"
os.environ["CARTMATE_FRONTEND_DIST"] = str(FRONTEND_DIST)
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

# Initialize database storage and seed operator account if not already present
from storage import DurableStorage
store = DurableStorage(str(DB_PATH))

now_iso = datetime.now(timezone.utc).isoformat()
exp_iso = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

if not store.get_user(OPERATOR_USER_ID):
    # Issue and redeem operator token for bootstrapping
    op_tok = store.issue_operator_activation(exp_iso, intended_for="Operator QA", operator_id="system_init")
    operator_user_dict = {
        "id": OPERATOR_USER_ID,
        "name": "Operator Jan",
        "avatar": "",
        "bio": "Pilot Operator",
        "trust_tier": "Bronze",
        "gender": "male",
        "city": "Katowice",
        "email": f"{OPERATOR_USER_ID}@pilot.cartmate.invalid",
        "phone": "",
        "phone_verified_at": None,
        "adult_verified_at": now_iso,
        "adult_verification_expires_at": exp_iso,
        "age_assurance_provider": "in_person_operator",
        "assurance_marker": "operator_in_person",
        "operator_admitted_at": now_iso,
    }
    store.redeem_operator_activation(op_tok, operator_user_dict)

# Now import FastAPI application
import database
import main
from fastapi import APIRouter, HTTPException

app = main.app

from models import UserPrivateSchema, TrustTier
database.USERS[OPERATOR_USER_ID] = UserPrivateSchema(
    id=OPERATOR_USER_ID,
    name="Operator Jan",
    avatar="",
    bio="Pilot Operator",
    trust_tier=TrustTier.BRONZE,
    gender="male",
    city="Katowice",
    email=f"{OPERATOR_USER_ID}@pilot.cartmate.invalid",
    phone="",
    phone_verified_at=None,
    adult_verified_at=now_iso,
    adult_verification_expires_at=exp_iso,
    age_assurance_provider="in_person_operator",
    assurance_marker="operator_in_person",
    operator_admitted_at=now_iso,
)
if not any(s.get("token") == OPERATOR_SESSION_TOKEN for s in store.get_active_sessions_for_user(OPERATOR_USER_ID)):
    main.persist_active_session(OPERATOR_SESSION_TOKEN, OPERATOR_USER_ID)

qa_router = APIRouter(prefix="/_op_qa")


@qa_router.post("/issue-token")
def issue_token(intended_for: str = "Test Subject"):
    """Issue a fresh single-use CMACT-... activation token."""
    expiry = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    raw_token = store.issue_operator_activation(expiry, intended_for=intended_for, operator_id=OPERATOR_USER_ID)
    return {"token": raw_token, "intended_for": intended_for, "expires_at": expiry}


@qa_router.post("/reset-rate-limits")
def reset_rate_limits():
    """Reset rate limiter between isolated test runs."""
    import rate_limiter
    rate_limiter.rate_limiter.clear()
    return {"status": "ok"}


@qa_router.post("/issue-recovery-token")
def issue_recovery_token(user_id: str, intended_for: str = "Test Subject"):
    """Issue a fresh single-use CMREC-... recovery token for an existing user."""
    expiry = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    raw_token = store.issue_operator_recovery(
        target_user_id=user_id,
        expires_at=expiry,
        operator_id=OPERATOR_USER_ID,
        intended_for=intended_for,
    )
    return {"token": raw_token, "target_user_id": user_id, "expires_at": expiry}


@qa_router.get("/operator-credentials")
def get_operator_credentials():
    """Return bootstrapped operator user ID and session token for test runner."""
    return {
        "user_id": OPERATOR_USER_ID,
        "token": OPERATOR_SESSION_TOKEN,
        "name": "Operator Jan",
        "city": "Katowice",
    }


# Include QA router ahead of StaticFiles mount
app.include_router(qa_router)
mount_idx = next((i for i, r in enumerate(app.router.routes) if type(r).__name__ == "Mount"), None)
if mount_idx is not None:
    op_qa_routes = [r for r in app.router.routes if getattr(r, "path", "").startswith("/_op_qa")]
    for r in op_qa_routes:
        app.router.routes.remove(r)
    for r in reversed(op_qa_routes):
        app.router.routes.insert(mount_idx, r)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("CARTMATE_OPERATOR_PILOT_PORT", "8010"))
    print(f"Starting CartMate Operator Pilot QA Harness on http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
