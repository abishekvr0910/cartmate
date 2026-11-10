import asyncio
import hashlib
import os
import json
import re
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from typing import Dict, List, Literal, Optional
from fastapi import FastAPI, Depends, Header, HTTPException, Query, Body, WebSocket, WebSocketDisconnect, status, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from geo_utils import haversine_distance_miles
from models import (
    ActivityCategory,
    AuthLoginRequest,
    AuthRegisterRequest,
    ConnectSocialRequest,
    JoinRequestSchema,
    LivePingCreate,
    LivePingSchema,
    PingStatus,
    RequestStatus,
    TripHandshakeVerifyRequest,
    TripItemSplit,
    TripItemSplitRequest,
    TripReviewRequest,
    TripSchema,
    TripResponseSchema,
    TripStatus,
    TrustTier,
    UserSchema,
    UserPublicSchema,
    UserPrivateSchema,
    TripParticipantUserSchema,
    HotspotSpotSchema,
    HotspotPublicSchema,
    HotspotCreateRequest,
    OutingSchema,
    ChatRoomSchema,
    ChatMessageSchema,
    WaveResponseSchema,
    IntentClassificationResult,
    ContentSafetyResult,
    RendezvousSuggestion,
    ClassifyIntentRequest,
    ScreenContentRequest,
    SuggestRendezvousRequest,
    OtpRequestSchema,
    OtpRequestResponse,
    OtpVerifySchema,
    SosTriggerRequest,
    SosAlertSchema,
    SosDeliveryReceiptWebhook,
    PlanDetailsSchema,
    PlanAcceptanceRequest,
    TripCancelRequest,
    TripFollowUpRequest,
    TripFollowUpResponse,
    ShoppingBuddySchema,
    BlockUserRequest,
    BlockedUserSchema,
    ReportCategory,
    CreateReportRequest,
    ReportSchema,
    ModerationActionRequest,
    ModerationQueueItem,
    SessionInfoSchema,
    RedeemOperatorActivationRequest,
    RedeemOperatorRecoveryRequest,
    to_public_user,
    to_trip_participant,
    to_trip_response,
)
import database
from websocket_manager import ws_manager
from jev_service import jev_service
from config import (
    CARTMATE_ENV,
    STAGING_ALLOWED_PHONE_NUMBERS,
    CARTMATE_DEFAULT_REGION,
    get_active_region,
    REGIONS_REGISTRY,
    is_city_in_launch_boundary,
    OTP_PROVIDER,
    SOS_PROVIDER,
    JEV_MODE,
    is_production,
    TWILIO_AUTH_TOKEN,
    TWILIO_STATUS_CALLBACK_URL,
    SOS_WEBHOOK_SECRET,
    MODERATOR_USER_IDS,
    MANUAL_AGE_PILOT_ENABLED,
    OPERATOR_PILOT_ENABLED,
    IS_ENV_EXPLICITLY_SET,
    VALID_ENVIRONMENTS,
    OPERATIONAL_THRESHOLDS,
    PILOT_INVITES_ENABLED,
    SMSAPI_API_TOKEN,
    TWILIO_ACCOUNT_SID,
    TWILIO_FROM_NUMBER,
)
from auth_providers import otp_manager
from sos_providers import sos_manager, verify_twilio_signature, verify_webhook_secret
from storage import pilot_invite_hash, operator_activation_hash, storage, get_db_connection
from voice_manager import VoiceCallManager
from rate_limiter import rate_limiter
from sanitizer import mask_phone, mask_token, mask_email, coarse_coordinates, apply_sanitized_logging

apply_sanitized_logging()

voice_call_manager = VoiceCallManager(ws_manager, storage)

app = FastAPI(
    title="CartMate API",
    description="Real-time activity-based companion platform API for grocery, shopping, and everyday errands in Poland.",
    version="1.0.0",
)

# 1. Restricted CORS Policy: production origins are strictly HTTPS; staging allows explicit HTTPS or explicit loopback test origins.
if CARTMATE_ENV == "production":
    ALLOWED_ORIGINS = [
        origin.strip().rstrip("/")
        for origin in os.getenv("CARTMATE_CORS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    if any(origin == "*" or not origin.startswith("https://") for origin in ALLOWED_ORIGINS):
        raise RuntimeError("CARTMATE_CORS_ALLOWED_ORIGINS must contain only explicit HTTPS origins in production.")
elif is_production():
    ALLOWED_ORIGINS = [
        origin.strip().rstrip("/")
        for origin in os.getenv("CARTMATE_CORS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    for origin in ALLOWED_ORIGINS:
        if origin == "*":
            raise RuntimeError("Wildcard origin is forbidden in staging.")
        if not (origin.startswith("https://") or origin.startswith("http://127.0.0.1:") or origin.startswith("http://localhost:")):
            raise RuntimeError("Staging origins must be explicit HTTPS or explicit loopback test origins.")
else:
    ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def build_trip_response(trip: TripSchema, current_user_id: Optional[str] = None) -> TripResponseSchema:
    resp = to_trip_response(trip, current_user_id)
    participants = {trip.host.id, trip.companion.id}
    contact_allowed = (
        current_user_id in participants
        and trip.host_accepted
        and trip.companion_accepted
        and not database.is_user_blocked(trip.host.id, trip.companion.id)
    )
    if contact_allowed:
        if resp.host and not resp.host.phone and resp.host.id in database.USERS:
            resp.host.phone = database.USERS[resp.host.id].phone
        if resp.companion and not resp.companion.phone and resp.companion.id in database.USERS:
            resp.companion.phone = database.USERS[resp.companion.id].phone
    else:
        # Blocking cannot retract a number already seen, but it must stop
        # future disclosures from both REST and real-time trip responses.
        resp.host.phone = None
        resp.companion.phone = None
    alert = sos_manager.get_alert_by_trip(trip.id)
    if alert:
        resp.sos_alert = SosAlertSchema(**alert)
    return resp


def build_hotspot_response(
    spot: HotspotSpotSchema, current_user: Optional[UserPrivateSchema]
) -> HotspotPublicSchema:
    """Expose a vote count and visible avatars, never the raw voter ID roster."""
    visible_avatars = []
    for voter_id, avatar in zip(spot.voter_ids, spot.voter_avatars):
        if current_user and database.is_user_blocked(current_user.id, voter_id):
            continue
        visible_avatars.append(avatar)
    data = spot.model_dump(exclude={"voter_ids", "voter_avatars"})
    return HotspotPublicSchema(
        **data,
        voter_avatars=visible_avatars,
        user_voted=bool(current_user and current_user.id in spot.voter_ids),
        user_joined=bool(
            current_user and spot.outing_id
            and (outing := database.OUTINGS.get(spot.outing_id))
            and current_user.id in outing.participant_ids
        ),
    )


def ping_in_live_region(ping: LivePingSchema) -> bool:
    if not is_production():
        return True
    region = get_active_region()
    distance_km = haversine_distance_miles(
        region.center_lat, region.center_lng, ping.destination_lat, ping.destination_lng
    ) * 1.609344
    return distance_km <= region.default_radius_km


def hotspot_in_live_region(spot: HotspotSpotSchema) -> bool:
    return not is_production() or is_city_in_launch_boundary(spot.city)


def outing_in_live_region(outing: OutingSchema) -> bool:
    return not is_production() or is_city_in_launch_boundary(outing.city)


def trip_in_live_region(trip: TripSchema) -> bool:
    return not is_production() or bool(
        (ping := database.PINGS.get(trip.ping_id)) and ping_in_live_region(ping)
    )


def chat_room_in_live_region(room: ChatRoomSchema) -> bool:
    if not is_production():
        return True
    if room.scope == "trip":
        trip = database.TRIPS.get(room.target_id)
        return bool(trip and trip_in_live_region(trip))
    if room.scope == "outing":
        outing = database.OUTINGS.get(room.target_id)
        return bool(outing and outing_in_live_region(outing))
    return False


def require_live_record(allowed: bool) -> None:
    if not allowed:
        raise HTTPException(status_code=404, detail="Outing is outside the active pilot region.")


async def assert_public_content_safe(text: str) -> None:
    """Enforce the deterministic screening baseline on server-authored UGC paths."""
    result = await jev_service.screen_content_safety(text)
    if not result.is_safe:
        raise HTTPException(status_code=422, detail="This content cannot be published. Edit the text or contact moderation.")


def is_scope_authorized_for_user(scope: str, user_id: str) -> bool:
    """
    Enforces strict scope authorization for real-time WebSocket subscriptions.
    Clients may only subscribe to:
      - 'user:<id>' if id == user_id
      - 'city:<city>' (public city feed)
      - 'chat:<room_id>' if user_id in room.participant_ids
      - 'trip:<trip_id>' if user_id in [host.id, companion.id]
      - 'outing:<outing_id>' if user_id in outing.participant_ids
    All other subscriptions are denied.
    """
    if not scope or not isinstance(scope, str):
        return False
    parts = scope.split(":", 1)
    if len(parts) == 1:
        return False
    prefix, target = parts[0], parts[1]
    
    if prefix == "user":
        return target == user_id
    elif prefix == "city":
        supported_cities = {
            city.name.strip().lower()
            for region in ([get_active_region()] if is_production() else REGIONS_REGISTRY.values())
            for city in region.cities
        }
        return target.strip().lower() in supported_cities
    elif prefix == "chat":
        room = database.CHAT_ROOMS.get(target)
        return bool(room and chat_room_in_live_region(room) and user_id in room.participant_ids
                    and not any(database.is_user_blocked(user_id, member_id)
                                for member_id in room.participant_ids if member_id != user_id))
    elif prefix == "trip":
        trip = database.TRIPS.get(target)
        return bool(trip and trip_in_live_region(trip) and user_id in [trip.host.id, trip.companion.id]
                    and not database.is_user_blocked(trip.host.id, trip.companion.id))
    elif prefix == "outing":
        outing = database.OUTINGS.get(target)
        return bool(outing and outing_in_live_region(outing) and user_id in outing.participant_ids
                    and not any(database.is_user_blocked(user_id, member_id)
                                for member_id in outing.participant_ids if member_id != user_id))
    elif prefix == "pod":
        try:
            pod_id = int(target)
            pod = storage.get_pod(pod_id)
            if not pod:
                return False
            confirmed_uids = [m["user_id"] for m in pod.get("members", []) if m.get("status") == "confirmed"]
            if user_id not in confirmed_uids:
                return False
            return not any(database.is_user_blocked(user_id, other_id) for other_id in confirmed_uids if other_id != user_id)
        except (ValueError, TypeError):
            return False
    return False


class AuthResponse(BaseModel):
    user: UserPrivateSchema
    token: str
    message: str


# 2. Cryptographic Session Token Store (token -> user_id)
DEMO_SESSIONS: Dict[str, str] = {
    "token_zuzanna": "usr_zuzanna",
    "token_jakub": "usr_jakub",
    "token_ania": "usr_ania",
    "token_mateusz": "usr_mateusz",
    "token_ola": "usr_ola",
    "token_marek": "usr_marek",
}

# Demo tokens are strictly gated to development mode:
ACTIVE_SESSIONS: Dict[str, str] = {} if is_production() else dict(DEMO_SESSIONS)
# Hydrate durable sessions from SQLite storage
ACTIVE_SESSIONS.update(storage.load_sessions())
SESSION_EXPIRIES: Dict[str, str] = storage.load_session_expiries()
REVOKED_TOKENS: set = storage.load_revoked_tokens()
# Browser WebSockets cannot set Authorization headers. Exchange an authenticated
# session for a short-lived, single-use ticket so long-lived tokens never enter
# WebSocket URLs or access logs.
WS_TICKET_TTL_SECONDS = 30
WS_TICKETS: Dict[str, tuple[str, datetime]] = {}
# A human-attested check is available only in explicitly enabled, invite-only
# staging. It is not a signed mObywatel API assertion and does not enable the
# broader production service. SMS and demo identity flags never prove age.
AGE_ASSURANCE_TRUSTED_PROVIDERS: frozenset[str] = (
    frozenset({"operator_mdowod_qr", "operator_physical_id"})
    if MANUAL_AGE_PILOT_ENABLED else frozenset()
)
AGE_CHECK_CHALLENGES: Dict[str, tuple[str, datetime]] = {}
AGE_CHECK_CHALLENGE_TTL_SECONDS = 300


def persist_active_session(token: str, user_id: str) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=OPERATIONAL_THRESHOLDS.session_ttl_hours)
    expiry_iso = expires_at.isoformat()
    ACTIVE_SESSIONS[token] = user_id
    SESSION_EXPIRIES[token] = expiry_iso
    storage.persist_session(token, user_id, expiry_iso)


def session_is_expired(token: str) -> bool:
    expiry_value = SESSION_EXPIRIES.get(token)
    if not expiry_value:
        # Only in-memory development fixtures may be non-expiring.
        return token not in DEMO_SESSIONS
    try:
        expires_at = datetime.fromisoformat(expiry_value)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        expires_at = datetime.min.replace(tzinfo=timezone.utc)
    if expires_at > datetime.now(timezone.utc):
        return False
    user_id = ACTIVE_SESSIONS.pop(token, "")
    SESSION_EXPIRIES.pop(token, None)
    REVOKED_TOKENS.add(token)
    storage.revoke_session(token, user_id)
    return True


def is_session_active_token(token: str) -> bool:
    """Validate whether a session token is active, unrevoked, and unexpired."""
    return bool(token and token in ACTIVE_SESSIONS and token not in REVOKED_TOKENS and not session_is_expired(token))


ws_manager.set_session_validator(is_session_active_token)


def require_user(
    authorization: Optional[str] = Header(None),
) -> UserPrivateSchema:
    """
    Strict FastAPI dependency for protected routes.
    Requires 'Authorization: Bearer <token>' header.
    Returns 401 Unauthorized if missing, malformed, expired, revoked, or if demo tokens are used in production.
    Returns 403 Forbidden if user is suspended or banned.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Brak autoryzacji. Wymagany nagłówek 'Authorization: Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split("Bearer ", 1)[1].strip()

    # Check session revocation list
    if token in REVOKED_TOKENS:
        raise HTTPException(
            status_code=401,
            detail="Sesja została unieważniona. Zaloguj się ponownie.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # In production mode, strictly reject demo tokens with 401 Unauthorized
    if is_production():
        if token.startswith("token_") or token in DEMO_SESSIONS:
            raise HTTPException(
                status_code=401,
                detail="Tokeny demonstracyjne są zablokowane w środowisku produkcyjnym.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    if not token or token not in ACTIVE_SESSIONS:
        raise HTTPException(
            status_code=401,
            detail="Nieprawidłowy lub wygasły token sesji CartMate. Zaloguj się ponownie.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if session_is_expired(token):
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = ACTIVE_SESSIONS[token]
    if user_id not in database.USERS:
        raise HTTPException(
            status_code=401,
            detail="Użytkownik powiązany z tą sesją nie został odnaleziony.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = database.USERS[user_id]

    # Human Moderation & Safety checks: Banned or suspended users cannot access protected APIs
    if user.is_banned:
        raise HTTPException(
            status_code=403,
            detail=f"Konto zablokowane na stałe: {user.suspension_reason or 'Poważne naruszenie zasad bezpieczeństwa społeczności.'}",
        )
    if user.is_suspended:
        raise HTTPException(
            status_code=403,
            detail=f"Konto zostało tymczasowo zawieszone: {user.suspension_reason or 'Trwa weryfikacja zgłoszenia przez moderatora.'}",
        )

    if PILOT_INVITES_ENABLED and not storage.is_pilot_member(user.id):
        raise HTTPException(status_code=403, detail="Konto nie zostało dopuszczone do zamkniętego pilotażu CartMate.")
    return user


def require_moderator(
    current_user: UserPrivateSchema = Depends(require_user),
) -> UserPrivateSchema:
    """Require explicit server-side moderator allowlisting for safety operations."""
    env_mods = {m.strip() for m in os.getenv("CARTMATE_MODERATOR_USER_IDS", "").split(",") if m.strip()}
    if current_user.id not in MODERATOR_USER_IDS and current_user.id not in env_mods:
        raise HTTPException(
            status_code=403,
            detail="Tylko upoważniony moderator może przeglądać kolejkę lub podejmować działania.",
        )
    return current_user


def optional_user(
    authorization: Optional[str] = Header(None),
) -> Optional[UserPrivateSchema]:
    """
    Optional dependency for routes that allow both public browsing and authenticated context.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split("Bearer ", 1)[1].strip()
    if token in REVOKED_TOKENS:
        return None
    if is_production() and (token.startswith("token_") or token in DEMO_SESSIONS):
        return None
    if not token or token not in ACTIVE_SESSIONS:
        return None
    if session_is_expired(token):
        return None
    user_id = ACTIVE_SESSIONS[token]
    user = database.USERS.get(user_id)
    if user and (user.is_banned or user.is_suspended):
        return None
    if user and PILOT_INVITES_ENABLED and not storage.is_pilot_member(user.id):
        return None
    return user


def is_adult_verified(user: UserPrivateSchema) -> bool:
    if not user.age_assurance_provider or user.age_assurance_provider not in AGE_ASSURANCE_TRUSTED_PROVIDERS:
        return False
    if user.age_assurance_provider.startswith("operator_"):
        user_phone_allowed = bool(user.phone_verified_at)
        user_operator_admitted = bool(
            CARTMATE_ENV == "staging"
            and OPERATOR_PILOT_ENABLED
            and user.assurance_marker == "operator_in_person"
            and storage.is_operator_admitted(user.id)
        )
        if not (user_phone_allowed or user_operator_admitted) or not storage.is_pilot_member(user.id):
            return False
    if not user.adult_verified_at or not user.adult_verification_expires_at:
        return False
    try:
        verified_at = datetime.fromisoformat(user.adult_verified_at)
        expires_at = datetime.fromisoformat(user.adult_verification_expires_at)
        if verified_at.tzinfo is None or expires_at.tzinfo is None:
            return False
        now = datetime.now(timezone.utc)
        return verified_at <= now < expires_at
    except (TypeError, ValueError):
        return False


def requires_live_age_admission(path: str, method: str) -> bool:
    """Keep safety/exit/account routes open while gating live social activity."""
    if path == "/api/users/all":
        return True
    if path.startswith("/api/outings/") and path.endswith("/leave"):
        return False
    if path.startswith("/api/pods/") and path.endswith("/leave"):
        return False
    if path.startswith("/api/voice/calls/") and path.endswith(("/hangup", "/rate")):
        return False
    if path.startswith(("/api/pings", "/api/hotspots", "/api/outings", "/api/chat", "/api/pods", "/api/voice")):
        return True
    if path.startswith("/api/trips/") and method in {"POST", "PUT", "DELETE"}:
        # A participant must always be able to leave, report, or call for help.
        return not path.endswith(("/cancel", "/sos", "/follow-up", "/review", "/complete"))
    return False


@app.middleware("http")
async def enforce_live_age_admission(request: Request, call_next):
    if is_production() and requires_live_age_admission(request.url.path, request.method):
        user = optional_user(request.headers.get("authorization"))
        if user and not is_adult_verified(user):
            return JSONResponse(
                status_code=403,
                content={"detail": "Udział w wyjściach wymaga zatwierdzonego potwierdzenia pełnoletności (18+). Ta weryfikacja nie jest jeszcze dostępna."},
            )
    return await call_next(request)


@app.get("/api/health")
def health_check():
    """
    Observability & Liveness Health Endpoint.
    Returns status, Silesian launch market details, provider selection, and stats.
    """
    return {
        "status": "ok",
        "version": "1.0.0",
        "environment": CARTMATE_ENV,
        "operator_pilot_enabled": (CARTMATE_ENV == "staging" and OPERATOR_PILOT_ENABLED),
        "launch_market": "Silesia (Śląsk), Poland",
        "default_city": "Katowice",
        "providers": {
            "otp": OTP_PROVIDER,
            "sos": SOS_PROVIDER,
            "jev_mode": JEV_MODE,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "realtime": ws_manager.get_stats(),
        "stats": {
            "users": len(database.USERS),
            "active_pings": len(database.PINGS),
            "trips": len(database.TRIPS),
            "hotspots": len(database.HOTSPOTS),
            "outings": len(database.OUTINGS),
            "chat_rooms": len(database.CHAT_ROOMS),
        },
    }


@app.get("/api/ready")
def launch_readiness_check():
    """Operational readiness for the closed Silesia pilot, not public launch approval."""
    blockers: List[str] = []
    if not is_production():
        blockers.append("Set CARTMATE_ENV to staging or production explicitly.")
    if CARTMATE_ENV == "staging" and OPERATOR_PILOT_ENABLED:
        pass
    elif OTP_PROVIDER == "console":
        blockers.append("Configure a production SMS OTP provider.")
    elif OTP_PROVIDER == "smsapi" and not SMSAPI_API_TOKEN:
        blockers.append("Configure SMSAPI credentials for OTP delivery.")
    elif OTP_PROVIDER == "twilio" and not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER):
        blockers.append("Configure complete Twilio credentials for OTP delivery.")
    if SOS_PROVIDER != "disabled":
        blockers.append("SMS SOS dispatch is disabled by launch policy until verified recipient consent is implemented. Set SOS_PROVIDER=disabled.")
    if not SOS_WEBHOOK_SECRET or len(SOS_WEBHOOK_SECRET) < 16:
        blockers.append("Configure a unique SOS_WEBHOOK_SECRET for authenticated delivery receipts.")
    active_moderator_ids = {
        user_id
        for user_id in MODERATOR_USER_IDS
        if user_id in database.USERS
        and not database.USERS[user_id].is_banned
        and not database.USERS[user_id].is_suspended
        and (not PILOT_INVITES_ENABLED or storage.is_pilot_member(user_id))
    }
    if not active_moderator_ids:
        blockers.append("Configure CARTMATE_MODERATOR_USER_IDS with at least one persisted, active, pilot-admitted human moderator account.")
    elif MANUAL_AGE_PILOT_ENABLED and len(active_moderator_ids) < 2:
        blockers.append("The operator-attested staging pilot needs two active moderators so neither participant approves their own age.")
    elif MANUAL_AGE_PILOT_ENABLED and sum(
        is_adult_verified(database.USERS[user_id]) for user_id in active_moderator_ids
    ) < 2:
        blockers.append("Two human moderators must have current 18+ attestations before the operator-attested pilot opens.")
    if not os.getenv("CARTMATE_DATABASE_PATH"):
        blockers.append("Configure an explicit persistent CARTMATE_DATABASE_PATH.")
    if CARTMATE_DEFAULT_REGION != "silesia":
        blockers.append("The closed pilot is approved only for the Silesia region.")
    if not AGE_ASSURANCE_TRUSTED_PROVIDERS:
        blockers.append("The approved 18+ age-assurance provider and verification flow are not configured.")
    turn_secret_env = os.getenv("CARTMATE_TURN_SECRET", "")
    if CARTMATE_ENV == "production" and (not turn_secret_env or turn_secret_env == "cartmate_ephemeral_turn_secret_dev"):
        blockers.append("Configure a unique CARTMATE_TURN_SECRET for production WebRTC TURN relay.")
    elif turn_secret_env == "cartmate_ephemeral_turn_secret_dev" and is_production():
        blockers.append("Configure a unique CARTMATE_TURN_SECRET for production WebRTC TURN relay.")
    # Direct 112 calling remains available while contact notification is disabled.

    return JSONResponse(
        status_code=503 if blockers else 200,
        content={
            "status": "blocked" if blockers else "ready",
            "environment": CARTMATE_ENV,
            "blockers": blockers,
            "scope": "closed_silesia_pilot",
            "ordinary_outings_require": (
                "operator_admission_or_sms_and_approved_18_plus_proof"
                if (CARTMATE_ENV == "staging" and OPERATOR_PILOT_ENABLED)
                else "sms_verified_phone_and_approved_18_plus_proof"
            ),
            "pilot_invite_required": PILOT_INVITES_ENABLED,
            "operator_pilot_enabled": (CARTMATE_ENV == "staging" and OPERATOR_PILOT_ENABLED),
            "age_assurance_available": bool(AGE_ASSURANCE_TRUSTED_PROVIDERS),
            "identity_verification_available": False,
            "women_only_outings_available": False,
            "release_approval_required": True,
        },
    )


@app.get("/api/config/regions")
def get_regions():
    """
    Returns the configurable regional launch boundary (Silesia) and secondary hubs.
    """
    active = get_active_region()
    return {
        "default_region": active.id if is_production() else CARTMATE_DEFAULT_REGION,
        "active_region": active.model_dump(),
        "all_regions": {active.id: active.model_dump()} if is_production()
        else {k: v.model_dump() for k, v in REGIONS_REGISTRY.items()},
    }


@app.get("/api/config/environment")
def get_environment_config():
    """
    Returns deployment environment status and verification metrics.
    """
    return {
        "environment": CARTMATE_ENV,
        "is_production": is_production(),
        "pilot_invite_required": PILOT_INVITES_ENABLED,
        "operator_pilot_enabled": (CARTMATE_ENV == "staging" and OPERATOR_PILOT_ENABLED),
        "age_assurance_required": is_production(),
        "age_assurance_available": bool(AGE_ASSURANCE_TRUSTED_PROVIDERS),
        "is_explicitly_set": IS_ENV_EXPLICITLY_SET,
        "valid_environments": sorted(list(VALID_ENVIRONMENTS)),
    }


# --- Authentication & Real Provider-Backed OTP Endpoints ---

def assert_staging_phone_allowed(identifier: str) -> None:
    if CARTMATE_ENV == "staging" and identifier.strip() not in STAGING_ALLOWED_PHONE_NUMBERS:
        raise HTTPException(status_code=403, detail="Ten numer nie jest dopuszczony do zamkni\u0119tych test\u00f3w CartMate.")


def assert_deployed_sms_phone(identifier: str) -> None:
    if is_production() and not re.fullmatch(r"\+48\d{9}", identifier.strip()):
        raise HTTPException(status_code=400, detail="Wymagany jest polski numer telefonu w formacie +48XXXXXXXXX.")


def assert_pilot_otp_admission(identifier: str, invite_code: Optional[str] = None) -> None:
    if not PILOT_INVITES_ENABLED:
        return
    existing = database.find_user_by_identifier(identifier)
    if existing:
        if not storage.is_pilot_member(existing.id):
            raise HTTPException(status_code=403, detail="Konto nie zostało dopuszczone do zamkniętego pilotażu CartMate.")
    elif not invite_code or not storage.is_pilot_invite_available(invite_code):
        raise HTTPException(status_code=403, detail="Do rejestracji w zamkniętym pilotażu potrzebny jest ważny kod zaproszenia.")


def assert_pilot_existing_member(identifier: str) -> None:
    if not PILOT_INVITES_ENABLED:
        return
    existing = database.find_user_by_identifier(identifier)
    if not existing or not storage.is_pilot_member(existing.id):
        raise HTTPException(status_code=403, detail="Nowe konto w pilotażu załóż przez rejestrację z kodem zaproszenia.")


def record_phone_verification(user: UserPrivateSchema) -> None:
    """Persist OTP provenance before issuing a session or allowing an outing."""
    previous = user.phone_verified_at
    user.phone_verified_at = datetime.now(timezone.utc).isoformat()
    try:
        storage.persist_user(user.model_dump())
    except Exception:
        user.phone_verified_at = previous
        raise


def assert_discovery_authenticated(current_user: Optional[UserPrivateSchema]) -> None:
    if is_production() and current_user is None:
        raise HTTPException(status_code=401, detail="Zaloguj si\u0119, aby zobaczy\u0107 osoby i wyj\u015bcia.")


@app.post("/api/auth/otp/request", response_model=OtpRequestResponse)
async def request_otp(payload: OtpRequestSchema):
    """
    Requests a provider-backed SMS / Email OTP code with server-side expiry,
    60-second resend cooldown, and rate-limiting.
    """
    if is_production() and "@" in payload.identifier:
        raise HTTPException(
            status_code=400,
            detail="Logowanie e-mailem nie jest dostępne. Użyj numeru telefonu, ponieważ skonfigurowany kanał OTP obsługuje SMS.",
        )
    assert_staging_phone_allowed(payload.identifier)
    assert_deployed_sms_phone(payload.identifier)
    rate_limiter.assert_allowed(
        f"otp_req:{payload.identifier.strip()}",
        OPERATIONAL_THRESHOLDS.rate_limit_otp_requests_per_15m,
        900,
        "wysłania kodu OTP",
    )
    assert_pilot_otp_admission(payload.identifier, payload.invite_code)
    if PILOT_INVITES_ENABLED and payload.invite_code and not database.find_user_by_identifier(payload.identifier):
        # One forwarded code must not fan out unlimited chargeable SMS messages
        # across many distinct phone numbers before it is redeemed.
        allowed, retry_after = storage.reserve_otp_send_budget(
            f"pilot_invite_otp:{pilot_invite_hash(payload.invite_code)}",
            OPERATIONAL_THRESHOLDS.rate_limit_otp_requests_per_15m,
            900,
        )
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Zbyt wiele prób wysłania kodu OTP dla zaproszenia. Spróbuj później.",
                headers={"Retry-After": str(retry_after)},
            )
    result = await otp_manager.request_otp(payload.identifier)
    if result.get("status") == "rate_limited":
        retry_after = result.get("resend_cooldown_seconds", 60)
        raise HTTPException(
            status_code=429,
            detail=result.get("error", "Zbyt wiele prób wysłania kodu. Odczekaj chwilę."),
            headers={"Retry-After": str(retry_after)},
        )
    if result.get("status") != "sent":
        raise HTTPException(
            status_code=503,
            detail="Bramka SMS jest niedostępna. Kod nie został wysłany; spróbuj później.",
        )
    return OtpRequestResponse(
        status=result["status"],
        resend_cooldown_seconds=result.get("resend_cooldown_seconds", 60),
        expires_in_seconds=result.get("expires_in_seconds", 300),
        identifier=result["identifier"],
        dev_code=result.get("dev_code"),
    )


@app.post("/api/auth/otp/verify", response_model=AuthResponse)
async def verify_otp(payload: OtpVerifySchema):
    """
    Server-side verification of OTP code with replay protection (single-use consumption),
    expiry checks, and brute-force lockout.
    """
    if is_production() and "@" in payload.identifier:
        raise HTTPException(
            status_code=400,
            detail="Wdrożone środowisko obsługuje kody OTP wysyłane SMS-em na numer telefonu.",
        )
    assert_staging_phone_allowed(payload.identifier)
    assert_deployed_sms_phone(payload.identifier)
    assert_pilot_existing_member(payload.identifier)
    rate_limiter.assert_allowed(
        f"otp_verify:{payload.identifier.strip()}",
        OPERATIONAL_THRESHOLDS.rate_limit_otp_verify_attempts_per_15m,
        900,
        "weryfikacji kodu OTP",
    )
    verification = await otp_manager.verify_otp(payload.identifier, payload.code)
    if not verification.get("valid"):
        raise HTTPException(
            status_code=400,
            detail=verification.get("error", "Nieprawidłowy lub wygasły kod weryfikacyjny OTP."),
        )

    user = database.find_user_by_identifier(payload.identifier)
    if not user:
        # Provision new Katowice / Silesia account upon first verified phone/email login
        raw_id = payload.identifier.strip()
        is_email = "@" in raw_id
        user = database.create_user(
            name=raw_id.split("@")[0] if is_email else f"Sąsiad {raw_id[-4:]}",
            # SQLite currently requires a unique email value; keep phone-only
            # accounts on a non-deliverable internal placeholder without
            # leaking phone digits or pretending an inbox was verified.
            email=raw_id if is_email else f"phone-{uuid.uuid4().hex}@cartmate.invalid",
            phone=raw_id if not is_email else "",
            gender="unspecified",
            city="Katowice",
            bio="Nowy użytkownik CartMate ze Śląska.",
        )

    if "@" not in payload.identifier:
        record_phone_verification(user)

    token = f"cmt_{secrets.token_hex(20)}"
    persist_active_session(token, user.id)
    return AuthResponse(
        user=user,
        token=token,
        message=f"Pomyślnie zweryfikowano kod OTP. Witaj, {user.name}!",
    )


@app.post("/api/auth/login", response_model=AuthResponse)
async def login(request: AuthLoginRequest):
    if is_production() and "@" in request.identifier:
        raise HTTPException(
            status_code=400,
            detail="Logowanie e-mailem nie jest dostępne. Użyj numeru telefonu, ponieważ skonfigurowany kanał OTP obsługuje SMS.",
        )
    assert_staging_phone_allowed(request.identifier)
    assert_deployed_sms_phone(request.identifier)
    assert_pilot_existing_member(request.identifier)
    rate_limiter.assert_allowed(
        f"otp_verify:{request.identifier.strip()}",
        OPERATIONAL_THRESHOLDS.rate_limit_otp_verify_attempts_per_15m,
        900,
        "logowania",
    )
    user = database.find_user_by_identifier(request.identifier)
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"Nie znaleziono konta dla '{request.identifier}'. Sprawdź dane lub zarejestruj się."
        )
    
    if not request.code or not request.code.strip():
        raise HTTPException(
            status_code=400,
            detail="Wymagane jest podanie kodu weryfikacyjnego SMS/OTP."
        )

    verification = await otp_manager.verify_otp(request.identifier, request.code)
    if not verification.get("valid"):
        raise HTTPException(
            status_code=401,
            detail=verification.get("error", "Nieprawidłowy kod weryfikacyjny OTP.")
        )

    if "@" not in request.identifier:
        record_phone_verification(user)

    token = f"cmt_{secrets.token_hex(20)}"
    persist_active_session(token, user.id)
    return AuthResponse(
        user=user,
        token=token,
        message=f"Witaj z powrotem, {user.name}!"
    )


@app.post("/api/auth/register", response_model=AuthResponse)
async def register(request: AuthRegisterRequest):
    assert_staging_phone_allowed(request.phone)
    assert_deployed_sms_phone(request.phone)
    if PILOT_INVITES_ENABLED and (
        not request.invite_code or not storage.is_pilot_invite_available(request.invite_code)
    ):
        raise HTTPException(status_code=403, detail="Do rejestracji w zamkniętym pilotażu potrzebny jest ważny kod zaproszenia.")
    if not is_city_in_launch_boundary(request.city):
        raise HTTPException(status_code=400, detail="Rejestracja jest obecnie dostępna tylko w aktywnym regionie pilotażowym.")
    if database.find_user_by_identifier(request.email):
        raise HTTPException(
            status_code=400,
            detail="Użytkownik o podanym adresie e-mail już istnieje w systemie. Zaloguj się."
        )
    if database.find_user_by_identifier(request.phone):
        raise HTTPException(
            status_code=400,
            detail="Użytkownik o podanym numerze telefonu już istnieje w systemie. Zaloguj się."
        )

    if not request.otp_code or not request.otp_code.strip():
        raise HTTPException(
            status_code=400,
            detail="Wymagane jest podanie jednorazowego kodu weryfikacyjnego OTP."
        )

    # Verify OTP against phone (primary) or email
    verification = await otp_manager.verify_otp(request.phone, request.otp_code)
    if not verification.get("valid"):
        if is_production() or PILOT_INVITES_ENABLED:
            raise HTTPException(status_code=401, detail="Nieprawidłowy lub wygasły kod SMS dla numeru telefonu.")
        verification_email = await otp_manager.verify_otp(request.email, request.otp_code)
        if not verification_email.get("valid"):
            raise HTTPException(
                status_code=401,
                detail=verification.get("error", "Nieprawidłowy lub wygasły kod weryfikacyjny OTP dla rejestracji.")
            )

    try:
        user = database.create_user(
            name=request.name,
            email=request.email,
            phone=request.phone,
            gender=request.gender,
            city=request.city or "Katowice",
            bio=request.bio or "Nowy użytkownik CartMate. Chętnie dołączę do zakupów!",
            campus_badge=request.campus_badge,
            phone_verified_at=datetime.now(timezone.utc).isoformat() if PILOT_INVITES_ENABLED else None,
            pilot_invite_code=request.invite_code if PILOT_INVITES_ENABLED else None,
        )
    except ValueError:
        raise HTTPException(status_code=403, detail="Kod zaproszenia wygasł, został użyty lub unieważniony.")
    if verification.get("valid") and not PILOT_INVITES_ENABLED:
        record_phone_verification(user)
    token = f"cmt_{secrets.token_hex(20)}"
    persist_active_session(token, user.id)
    return AuthResponse(
        user=user,
        token=token,
        message=f"Rejestracja pomyślna! Witamy w CartMate, {user.name}."
    )


async def revoke_user_sessions_everywhere(user_id: str, except_token: Optional[str] = None) -> None:
    """Revoke existing sessions for a user across durable database and in-memory caches, and close sockets."""
    AGE_CHECK_CHALLENGES.pop(user_id, None)
    if except_token:
        storage.revoke_other_user_sessions(user_id, except_token)
        tokens_to_remove = [tok for tok, uid in list(ACTIVE_SESSIONS.items()) if uid == user_id and tok != except_token]
    else:
        storage.revoke_all_user_sessions(user_id)
        tokens_to_remove = [tok for tok, uid in list(ACTIVE_SESSIONS.items()) if uid == user_id]

    for tok in tokens_to_remove:
        ACTIVE_SESSIONS.pop(tok, None)
        SESSION_EXPIRIES.pop(tok, None)
        REVOKED_TOKENS.add(tok)
        await ws_manager.close_session(tok)

    await ws_manager.close_user_except_session(user_id, except_session=except_token)


@app.post("/api/auth/redeem-operator-recovery", response_model=AuthResponse)
async def redeem_operator_recovery(
    request: RedeemOperatorRecoveryRequest,
    req: Request,
):
    """
    Operator-issued in-person account recovery for admitted staging participants.
    Restores access to the participant's original user account after logout or session loss.
    Strictly forbidden in production mode or when operator pilot flag is disabled.
    Revokes prior active sessions and closes old sockets to prevent concurrent access by stolen sessions.
    """
    if CARTMATE_ENV == "production":
        raise HTTPException(
            status_code=403,
            detail="Operator recovery is prohibited in production.",
        )
    if not is_production() or not OPERATOR_PILOT_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="Operator recovery is only permitted in the explicitly enabled staging pilot.",
        )

    client_ip = req.client.host if req.client else "unknown"
    rate_limiter.assert_allowed(
        f"redeem_recovery:{client_ip}",
        max_requests=5,
        window_seconds=900,
        action_description="odzyskiwania konta operatora",
    )

    token = request.recovery_token.strip()
    try:
        operator_activation_hash(token)
    except ValueError:
        raise HTTPException(status_code=422, detail="Nieprawidłowy format kodu odzyskiwania.")

    try:
        recovered_user_dict = storage.redeem_operator_recovery(token)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    user_id = recovered_user_dict["id"]
    recovered_user = UserPrivateSchema(**recovered_user_dict)
    database.USERS[user_id] = recovered_user

    session_token = f"cmt_{secrets.token_hex(20)}"
    try:
        persist_active_session(session_token, user_id)
    except Exception:
        storage.rollback_operator_recovery_redemption(token, user_id, session_token=session_token)
        ACTIVE_SESSIONS.pop(session_token, None)
        SESSION_EXPIRIES.pop(session_token, None)
        raise

    # Revoke all prior sessions and disconnect old sockets for this user
    await revoke_user_sessions_everywhere(user_id, except_token=session_token)

    return AuthResponse(
        user=recovered_user,
        token=session_token,
        message="Sesja konta została pomyślnie odzyskana przez operatora.",
    )


@app.post("/api/auth/redeem-operator-activation", response_model=AuthResponse)
async def redeem_operator_activation(
    request: RedeemOperatorActivationRequest,
    req: Request,
):
    """
    Operator-issued in-person admission for the closed staging friend pilot.
    Strictly forbidden in production mode or when operator pilot flag is disabled.
    Establishes operator_in_person assurance without faking SMS provenance.
    Does NOT verify age (18+ gate remains separate).
    """
    if CARTMATE_ENV == "production":
        raise HTTPException(
            status_code=403,
            detail="Operator activation is prohibited in production.",
        )
    if not is_production() or not OPERATOR_PILOT_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="Operator activation is only permitted in the explicitly enabled staging pilot.",
        )

    client_ip = req.client.host if req.client else "unknown"
    rate_limiter.assert_allowed(
        f"redeem_activation:{client_ip}",
        max_requests=5,
        window_seconds=900,
        action_description="aktywacji konta operatora",
    )

    token = request.activation_token.strip()
    try:
        token_hash = operator_activation_hash(token)
    except ValueError:
        raise HTTPException(status_code=422, detail="Nieprawidłowy format kodu aktywacyjnego.")

    # Check if this token is a bound account recovery token
    conn = get_db_connection(storage.db_path)
    try:
        row = conn.execute(
            "SELECT target_user_id FROM operator_activations WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
    finally:
        conn.close()

    if (row and row[0]) or token.upper().startswith("CMREC-"):
        # Explicit recovery token submitted to activation endpoint - recover existing account
        try:
            recovered_user_dict = storage.redeem_operator_recovery(token)
        except ValueError as e:
            raise HTTPException(status_code=403, detail=str(e))
        user_id = recovered_user_dict["id"]
        recovered_user = UserPrivateSchema(**recovered_user_dict)
        database.USERS[user_id] = recovered_user
        session_token = f"cmt_{secrets.token_hex(20)}"
        try:
            persist_active_session(session_token, user_id)
        except Exception:
            storage.rollback_operator_recovery_redemption(token, user_id, session_token=session_token)
            ACTIVE_SESSIONS.pop(session_token, None)
            SESSION_EXPIRIES.pop(session_token, None)
            raise
        await revoke_user_sessions_everywhere(user_id, except_token=session_token)
        return AuthResponse(
            user=recovered_user,
            token=session_token,
            message="Sesja konta została pomyślnie odzyskana przez operatora.",
        )

    if not is_city_in_launch_boundary(request.city):
        raise HTTPException(status_code=400, detail="Wybrane miasto znajduje się poza obszarem pilotażu (Metropolia GZM).")

    await assert_public_content_safe(request.name)
    if request.bio:
        await assert_public_content_safe(request.bio)

    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    now_str = datetime.now(timezone.utc).isoformat()

    new_user = UserPrivateSchema(
        id=user_id,
        name=request.name.strip(),
        avatar="",
        bio=request.bio.strip() if request.bio else "",
        trust_tier=TrustTier.BRONZE,
        gender=request.gender or "unspecified",
        city=request.city,
        email=f"{user_id}@pilot.cartmate.invalid",
        phone="",
        phone_verified_at=None,
        adult_verified_at=None,
        adult_verification_expires_at=None,
        age_assurance_provider=None,
        assurance_marker="operator_in_person",
        operator_admitted_at=now_str,
    )

    session_token = f"cmt_{secrets.token_hex(20)}"
    try:
        storage.redeem_operator_activation(token, new_user.model_dump())
        database.USERS[user_id] = new_user
        persist_active_session(session_token, user_id)
    except Exception as exc:
        storage.rollback_operator_activation_redemption(token, user_id)
        database.USERS.pop(user_id, None)
        ACTIVE_SESSIONS.pop(session_token, None)
        SESSION_EXPIRIES.pop(session_token, None)
        if isinstance(exc, HTTPException):
            raise
        if isinstance(exc, ValueError):
            raise HTTPException(status_code=403, detail=str(exc))
        raise

    return AuthResponse(
        user=new_user,
        token=session_token,
        message="Konto zostało pomyślnie aktywowane przez operatora. Weryfikacja 18+ jest wymagana przed udziałem w wyjściach.",
    )


@app.post("/api/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
        user_id = ACTIVE_SESSIONS.get(token, "")
        AGE_CHECK_CHALLENGES.pop(user_id, None)
        if token in ACTIVE_SESSIONS:
            del ACTIVE_SESSIONS[token]
        SESSION_EXPIRIES.pop(token, None)
        REVOKED_TOKENS.add(token)
        storage.revoke_session(token, user_id)
        await ws_manager.close_session(token)
    return {"status": "ok", "message": "Wylogowano pomyślnie. Sesja została unieważniona."}


@app.post("/api/auth/revoke-all-sessions")
async def revoke_all_sessions(current_user: UserPrivateSchema = Depends(require_user)):
    """
    Revokes all active sessions across all devices for current user.
    """
    revoked_count = 0
    AGE_CHECK_CHALLENGES.pop(current_user.id, None)
    for tok, uid in list(ACTIVE_SESSIONS.items()):
        if uid == current_user.id:
            REVOKED_TOKENS.add(tok)
            del ACTIVE_SESSIONS[tok]
            SESSION_EXPIRIES.pop(tok, None)
            revoked_count += 1
    storage.revoke_all_user_sessions(current_user.id)
    await ws_manager.close_user(current_user.id)
    return {
        "status": "ok",
        "revoked_count": revoked_count,
        "message": "Wszystkie aktywne sesje użytkownika zostały unieważnione.",
    }


@app.post("/api/auth/revoke-other-sessions")
async def revoke_other_sessions(
    authorization: Optional[str] = Header(None),
    current_user: UserPrivateSchema = Depends(require_user),
):
    """Revoke every other device while preserving the caller's session."""
    current_token = authorization.split("Bearer ", 1)[1].strip()
    AGE_CHECK_CHALLENGES.pop(current_user.id, None)
    tokens = set(storage.revoke_other_user_sessions(current_user.id, current_token))
    # Include any in-memory sessions that have not yet reached durable storage.
    tokens.update(
        token for token, user_id in ACTIVE_SESSIONS.items()
        if user_id == current_user.id and token != current_token
    )
    for token in tokens:
        ACTIVE_SESSIONS.pop(token, None)
        SESSION_EXPIRIES.pop(token, None)
        REVOKED_TOKENS.add(token)
        await ws_manager.close_session(token)
    return {"status": "ok", "revoked_count": len(tokens)}


@app.post("/api/auth/ws-ticket")
def issue_websocket_ticket(
    response: Response,
    authorization: Optional[str] = Header(None),
    current_user: UserPrivateSchema = Depends(require_user),
):
    """Issue one short-lived WebSocket credential for an authenticated session."""
    if is_production() and not is_adult_verified(current_user):
        raise HTTPException(status_code=403, detail="Live realtime access requires approved 18+ verification.")
    rate_limiter.assert_allowed(f"ws-ticket:{current_user.id}", 60, 60, "połączeń WebSocket")
    now = datetime.now(timezone.utc)
    for old_ticket, (_, expiry) in list(WS_TICKETS.items()):
        if expiry <= now:
            WS_TICKETS.pop(old_ticket, None)
    if len(WS_TICKETS) >= 1000:
        raise HTTPException(status_code=503, detail="Realtime connection capacity reached; retry shortly.")
    token = authorization.split("Bearer ", 1)[1].strip()
    ticket = secrets.token_urlsafe(32)
    WS_TICKETS[ticket] = (token, now + timedelta(seconds=WS_TICKET_TTL_SECONDS))
    response.headers["Cache-Control"] = "no-store"
    return {"ticket": ticket, "expires_in_seconds": WS_TICKET_TTL_SECONDS}


@app.get("/api/auth/sessions", response_model=List[SessionInfoSchema])
def get_user_sessions(current_user: UserPrivateSchema = Depends(require_user)):
    """
    Lists all known sessions for current user with masked tokens to avoid credential leakage.
    """
    sessions_data = storage.get_active_sessions_for_user(current_user.id)
    result = []
    for s in sessions_data:
        tok = s["token"]
        result.append(
            SessionInfoSchema(
                token_masked=mask_token(tok),
                user_id=s["user_id"],
                created_at=s["created_at"],
                expires_at=s.get("expires_at"),
                is_revoked=tok in REVOKED_TOKENS,
            )
        )
    return result


@app.post("/api/auth/switch-user", response_model=AuthResponse)
def switch_user(user_id: str):
    if is_production():
        raise HTTPException(
            status_code=403,
            detail="Przełączanie profili demo jest zablokowane w środowisku produkcyjnym."
        )
    if user_id not in database.USERS:
        raise HTTPException(status_code=404, detail="Użytkownik demo nie istnieje.")
    user = database.USERS[user_id]
    token = f"token_{user.id.replace('usr_', '')}"
    persist_active_session(token, user.id)
    return AuthResponse(
        user=user,
        token=token,
        message=f"Przełączono na profil {user.name} (środowisko deweloperskie)."
    )


@app.post("/api/users/switch/{user_id}", response_model=AuthResponse)
def switch_user_legacy(user_id: str):
    return switch_user(user_id)


@app.post("/api/testing/reset-seeded-trip")
def reset_seeded_trip():
    if is_production():
        raise HTTPException(
            status_code=403,
            detail="Reset wycieczki jest zablokowany w środowisku produkcyjnym."
        )
    if "trip_makro_01" in database.TRIPS:
        trip = database.TRIPS["trip_makro_01"]
        trip.host_accepted = True
        trip.companion_accepted = False
        trip.status = TripStatus.SCHEDULED
        trip.pin_attempts_left = 5
        trip.rendezvous_verified = False
        trip.sos_triggered = False
        trip.host_checked_in = False
        trip.companion_checked_in = False
        trip.chat_room_id = "chat_trip_makro_01"
        trip.items_split = [
            database.TripItemSplit(
                id="split_01",
                item_name="Oliwa Extra Virgin 5L (Makro Chef)",
                total_price_pln=139.90,
                payer_id="usr_jakub",
                host_owes_pln=0.0,
                companion_owes_pln=69.95,
                created_at="2026-09-28T00:00:00Z",
            )
        ]
        trip.total_split_pln = 139.90
        database.save_trip(trip)

    if "chat_trip_makro_01" in database.CHAT_ROOMS:
        room = database.CHAT_ROOMS["chat_trip_makro_01"]
        room.messages = [
            database.ChatMessageSchema(
                id="msg_trip_01",
                chat_room_id="chat_trip_makro_01",
                sender_id="usr_jakub",
                sender_name="Jakub Kamiński",
                sender_avatar=database.USERS["usr_jakub"].avatar,
                text="Cześć Zuzanna! Będę przy wejściu głównym za 10 minut.",
                created_at="2026-09-28T00:00:00Z",
                sequence=1,
            )
        ]
        database.save_chat_room(room)

    return {"status": "reset_successful"}


# --- User & Safety Identity Endpoints ---

@app.get("/api/users/me", response_model=UserPrivateSchema)
def get_current_user(current_user: UserPrivateSchema = Depends(require_user)):
    """
    Returns private profile exclusively to the authenticated user.
    """
    return current_user


@app.get("/api/users/me/admission")
def get_my_admission(current_user: UserPrivateSchema = Depends(require_user)):
    """Tell the member whether live participation is open without exposing proof data."""
    verified = is_adult_verified(current_user)
    return {
        "age_assurance_required": is_production(),
        "age_assurance_available": bool(AGE_ASSURANCE_TRUSTED_PROVIDERS),
        "manual_age_check_available": MANUAL_AGE_PILOT_ENABLED,
        "adult_verified": verified,
        "live_access": not is_production() or verified,
    }


@app.get("/api/users/all", response_model=List[UserPublicSchema])
def get_all_demo_users(current_user: Optional[UserPrivateSchema] = Depends(optional_user)):
    """
    Public directory: Strictly returns UserPublicSchema.
    Strips email, phone, and emergency contact to protect PII.
    Hides banned users and users blocked by or who blocked the current user.
    """
    assert_discovery_authenticated(current_user)
    results = []
    for u in database.USERS.values():
        # Suspended accounts must not appear in the member directory while
        # their case is pending; banned accounts are permanently hidden (F07).
        if u.is_banned or u.is_suspended:
            continue
        if current_user and database.is_user_blocked(current_user.id, u.id):
            continue
        results.append(to_public_user(u))
    return results


# --- Block & Report Tools ---

@app.post("/api/users/{target_user_id}/block")
async def block_user_endpoint(
    target_user_id: str,
    payload: BlockUserRequest = BlockUserRequest(),
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    Blocks a user bidirectionally. Blocked users cannot see live pings,
    cannot send waves or join requests, cannot chat, and are hidden from discovery.
    """
    if current_user.id == target_user_id:
        raise HTTPException(status_code=400, detail="Nie możesz zablokować samego siebie.")
    if target_user_id not in database.USERS:
        raise HTTPException(status_code=404, detail="Użytkownik nie został znaleziony.")

    database.block_user(current_user.id, target_user_id)
    separated_pids = storage.separate_blocked_user_from_pods(current_user.id, target_user_id)
    for pid in separated_pids:
        updated_pod = storage.get_pod(pid)
        if updated_pod:
            await ws_manager.broadcast(
                f"pod:{pid}",
                "pod.member_left",
                {
                    "pod_id": pid,
                    "user_id": current_user.id,
                    "confirmed_count": updated_pod["confirmed_count"],
                    "status": updated_pod["status"],
                },
            )
    active_call_id = voice_call_manager.user_to_call.get(current_user.id)
    if active_call_id and voice_call_manager.get_peer_id(active_call_id, current_user.id) == target_user_id:
        await voice_call_manager.terminate_call(active_call_id, initiator_user_id=current_user.id, reason="blocked", block_peer=True)
    # A live subscription was authorized before this block. Force both sides
    # to reconnect and recheck their current chat/trip/outing relationships.
    await ws_manager.close_user(current_user.id)
    await ws_manager.close_user(target_user_id)
    target = database.USERS[target_user_id]
    return {"status": "ok", "message": f"Użytkownik {target.name} został pomyślnie zablokowany."}


@app.delete("/api/users/{target_user_id}/block")
def unblock_user_endpoint(
    target_user_id: str,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    Unblocks a previously blocked user.
    """
    database.unblock_user(current_user.id, target_user_id)
    return {"status": "ok", "message": "Użytkownik został pomyślnie odblokowany."}


@app.get("/api/users/me/blocks", response_model=List[BlockedUserSchema])
def get_my_blocks(current_user: UserPrivateSchema = Depends(require_user)):
    """
    Returns list of users blocked by current user.
    """
    blocked_ids = database.get_blocked_users_for(current_user.id)
    result = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for bid in blocked_ids:
        u = database.USERS.get(bid)
        if u:
            result.append(BlockedUserSchema(user=to_public_user(u), blocked_at=now_iso))
    return result


@app.post("/api/reports", response_model=ReportSchema)
def create_report(
    payload: CreateReportRequest,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    Submits a user safety report for human moderation review.
    Rate-limited to prevent abuse.
    """
    rate_limiter.assert_allowed(
        f"report:{current_user.id}",
        OPERATIONAL_THRESHOLDS.rate_limit_reports_per_hour,
        3600,
        "składania zgłoszeń",
    )
    if current_user.id == payload.reported_user_id:
        raise HTTPException(status_code=400, detail="Nie możesz zgłosić samego siebie.")
    if payload.reported_user_id not in database.USERS:
        raise HTTPException(status_code=404, detail="Zgłaszany użytkownik nie istnieje.")

    now_iso = datetime.now(timezone.utc).isoformat()
    if payload.trip_id and payload.outing_id:
        raise HTTPException(status_code=400, detail="Choose one outing context for this report.")
    if payload.evidence_chat_message_id and not (payload.trip_id or payload.outing_id):
        raise HTTPException(status_code=400, detail="Chat evidence must reference its outing.")
    if payload.trip_id:
        report_trip = database.TRIPS.get(payload.trip_id)
        if not report_trip:
            raise HTTPException(status_code=404, detail="The referenced outing does not exist.")
        participant_ids = {report_trip.host.id, report_trip.companion.id}
        if current_user.id not in participant_ids or payload.reported_user_id not in participant_ids - {current_user.id}:
            raise HTTPException(status_code=403, detail="Only a trip participant can report its other participant.")
        if payload.evidence_chat_message_id:
            room = database.CHAT_ROOMS.get(report_trip.chat_room_id or "")
            if not room or not any(message.id == payload.evidence_chat_message_id and message.sender_id == payload.reported_user_id for message in room.messages):
                raise HTTPException(status_code=400, detail="The cited message must be by the reported member in this outing's chat.")
    if payload.outing_id:
        outing = database.OUTINGS.get(payload.outing_id)
        if not outing:
            raise HTTPException(status_code=404, detail="The referenced group does not exist.")
        participants = set(outing.participant_ids) | set(outing.former_participant_ids)
        if current_user.id not in participants or payload.reported_user_id not in participants:
            raise HTTPException(status_code=403, detail="Only group participants can report another group participant.")
        if payload.evidence_chat_message_id:
            room = database.CHAT_ROOMS.get(outing.chat_room_id)
            if not room or not any(message.id == payload.evidence_chat_message_id and message.sender_id == payload.reported_user_id for message in room.messages):
                raise HTTPException(status_code=400, detail="The cited message must be by the reported member in this group's chat.")

    report = ReportSchema(
        id=f"rep_{uuid.uuid4().hex[:8]}",
        reporter_id=current_user.id,
        reported_user_id=payload.reported_user_id,
        category=payload.category.value,
        details=payload.details.strip(),
        evidence_chat_message_id=payload.evidence_chat_message_id,
        trip_id=payload.trip_id,
        outing_id=payload.outing_id,
        status="pending",
        created_at=now_iso,
        updated_at=now_iso,
    )
    database.save_report(report)
    return report


@app.get("/api/moderation/queue", response_model=List[ReportSchema])
def get_moderation_queue(current_user: UserPrivateSchema = Depends(require_moderator)):
    """
    FIFO human moderation queue for reviewing reported safety violations.
    """
    return sorted(
        (r for r in database.REPORTS.values() if r.status == "pending"),
        key=lambda report: report.created_at,
    )


@app.get("/api/moderation/access")
def get_moderation_access(current_user: UserPrivateSchema = Depends(require_user)):
    """Expose only the caller's own server-authorized moderator capability."""
    return {"can_moderate": current_user.id in MODERATOR_USER_IDS}


class PilotAdultAttestationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["mdowod_qr", "physical_identity_document"]
    confirmed_over_18: Literal[True]
    subject_present: Literal[True]
    subject_consented: Literal[True]
    account_bound: Literal[True]
    account_challenge: str = Field(min_length=10, max_length=64)


@app.post("/api/users/me/age-check-challenge")
def issue_pilot_age_check_challenge(current_user: UserPrivateSchema = Depends(require_user)):
    """One-use proof that the subject can access their own signed-in account."""
    if not MANUAL_AGE_PILOT_ENABLED:
        raise HTTPException(status_code=503, detail="Pilot operator age checks are not enabled.")
    is_phone_allowed = bool(current_user.phone_verified_at and current_user.phone in STAGING_ALLOWED_PHONE_NUMBERS)
    is_operator_admitted = bool(
        OPERATOR_PILOT_ENABLED
        and current_user.assurance_marker == "operator_in_person"
        and storage.is_operator_admitted(current_user.id)
    )
    if not (is_phone_allowed or is_operator_admitted):
        raise HTTPException(status_code=403, detail="A pilot SMS-verified phone or operator admission is required.")
    code = secrets.token_urlsafe(12)
    now = datetime.now(timezone.utc)
    for user_id, (_, expiry) in list(AGE_CHECK_CHALLENGES.items()):
        if expiry <= now:
            AGE_CHECK_CHALLENGES.pop(user_id, None)
    expires_at = now + timedelta(seconds=AGE_CHECK_CHALLENGE_TTL_SECONDS)
    AGE_CHECK_CHALLENGES[current_user.id] = (
        hashlib.sha256(code.encode("ascii")).hexdigest(), expires_at,
    )
    return JSONResponse(
        {"account_code": current_user.id, "challenge": code, "expires_at": expires_at.isoformat()},
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/moderation/users/{user_id}/adult-attestation")
async def record_pilot_adult_attestation(
    user_id: str,
    payload: PilotAdultAttestationRequest,
    current_user: UserPrivateSchema = Depends(require_moderator),
):
    """Record a witnessed 18+ check; never receive identity-document data."""
    if not MANUAL_AGE_PILOT_ENABLED:
        raise HTTPException(status_code=503, detail="Pilot operator age checks are not enabled.")
    if current_user.id == user_id:
        raise HTTPException(status_code=403, detail="An operator cannot approve their own age.")
    mod_phone_allowed = bool(current_user.phone_verified_at and current_user.phone in STAGING_ALLOWED_PHONE_NUMBERS)
    mod_operator_admitted = bool(
        OPERATOR_PILOT_ENABLED
        and current_user.assurance_marker == "operator_in_person"
        and storage.is_operator_admitted(current_user.id)
    )
    if not (mod_phone_allowed or mod_operator_admitted):
        raise HTTPException(status_code=403, detail="The operator must use an admitted pilot account.")
    subject = database.USERS.get(user_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Pilot account not found.")
    subj_phone_allowed = bool(subject.phone_verified_at and subject.phone in STAGING_ALLOWED_PHONE_NUMBERS)
    subj_operator_admitted = bool(
        OPERATOR_PILOT_ENABLED
        and subject.assurance_marker == "operator_in_person"
        and storage.is_operator_admitted(user_id)
    )
    if (
        subject.is_banned or subject.is_suspended
        or not (subj_phone_allowed or subj_operator_admitted)
        or not storage.is_pilot_member(user_id)
    ):
        raise HTTPException(status_code=403, detail="Only an active, admitted pilot member can receive an attestation.")
    challenge = AGE_CHECK_CHALLENGES.get(user_id)
    digest = hashlib.sha256(payload.account_challenge.encode("utf-8")).hexdigest()
    if not challenge or challenge[1] <= datetime.now(timezone.utc) or not secrets.compare_digest(challenge[0], digest):
        raise HTTPException(status_code=403, detail="The signed-in account challenge is missing, expired, or incorrect.")
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=7)
    provider = "operator_mdowod_qr" if payload.method == "mdowod_qr" else "operator_physical_id"
    updated = subject.model_copy(update={
        "age_assurance_provider": provider,
        "adult_verified_at": now.isoformat(),
        "adult_verification_expires_at": expires_at.isoformat(),
    })
    storage.record_pilot_age_attestation(
        updated.model_dump(), current_user.id, payload.method, "confirmed_adult",
        now.isoformat(), expires_at.isoformat(),
    )
    AGE_CHECK_CHALLENGES.pop(user_id, None)
    database.USERS[user_id] = updated
    return {"adult_verified": True, "expires_at": expires_at.isoformat(), "method": payload.method}


@app.post("/api/moderation/users/{user_id}/adult-attestation/revoke")
async def revoke_pilot_adult_attestation(
    user_id: str,
    current_user: UserPrivateSchema = Depends(require_moderator),
):
    if not MANUAL_AGE_PILOT_ENABLED:
        raise HTTPException(status_code=503, detail="Pilot operator age checks are not enabled.")
    subject = database.USERS.get(user_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Pilot account not found.")
    now = datetime.now(timezone.utc).isoformat()
    updated = subject.model_copy(update={
        "age_assurance_provider": None,
        "adult_verified_at": None,
        "adult_verification_expires_at": None,
    })
    storage.record_pilot_age_attestation(
        updated.model_dump(), current_user.id, "operator_revoke", "revoked", now, None,
    )
    database.USERS[user_id] = updated
    await ws_manager.close_user(user_id)
    return {"adult_verified": False}


@app.post("/api/moderation/reports/{report_id}/action", response_model=ReportSchema)
async def take_moderation_action(
    report_id: str,
    payload: ModerationActionRequest,
    current_user: UserPrivateSchema = Depends(require_moderator),
):
    """
    Executes a human moderation action: dismiss, record an internal warning,
    suspend, or ban. "warn" does not notify the reported user.
    Suspending or banning a user immediately revokes all active sessions.
    """
    if report_id not in database.REPORTS:
        raise HTTPException(status_code=404, detail="Zgłoszenie nie zostało odnalezione.")
    report = database.REPORTS[report_id]

    if report.status != "pending":
        raise HTTPException(status_code=409, detail="This report has already been reviewed.")

    action = payload.action.lower().strip()
    if action not in {"dismiss", "warn", "suspend", "ban"}:
        raise HTTPException(
            status_code=400,
            detail="Nieprawidłowa akcja moderacyjna. Dozwolone: 'dismiss', 'warn', 'suspend', 'ban'."
        )

    resolution_note = payload.resolution_note.strip()
    if not resolution_note:
        raise HTTPException(status_code=400, detail="A moderator resolution note is required.")

    reported_user = database.USERS.get(report.reported_user_id)
    if action in {"suspend", "ban"} and reported_user:
        if action == "ban":
            reported_user.is_banned = True
        else:
            reported_user.is_suspended = True
        reported_user.suspension_reason = resolution_note

        # Immediately revoke all active sessions for banned/suspended user
        storage.revoke_all_user_sessions(reported_user.id)
        for tok, uid in list(ACTIVE_SESSIONS.items()):
            if uid == reported_user.id:
                REVOKED_TOKENS.add(tok)
                del ACTIVE_SESSIONS[tok]
                SESSION_EXPIRIES.pop(tok, None)

        storage.persist_user(reported_user.model_dump())
        await ws_manager.close_user(reported_user.id)

    database.update_report_status(report_id, action, resolution_note, current_user.id)
    return database.REPORTS[report_id]


@app.post("/api/users/verify-id", response_model=UserPrivateSchema)
def simulate_id_verification(current_user: UserPrivateSchema = Depends(require_user)):
    """
    Development-only simulation. Staging and production must use a genuine,
    configured identity-verification provider; never self-assert verified status.
    """
    if is_production():
        raise HTTPException(
            status_code=503,
            detail="Weryfikacja tożsamości nie jest jeszcze dostępna. Nie oznaczono konta jako zweryfikowanego.",
        )
    current_user.is_id_verified = True
    current_user.is_selfie_verified = True
    if current_user.trust_tier == TrustTier.BRONZE:
        current_user.trust_tier = TrustTier.SILVER
    return current_user


@app.post("/api/users/toggle-safe-haven", response_model=UserPrivateSchema)
def toggle_safe_haven(current_user: UserPrivateSchema = Depends(require_user)):
    """
    Toggles Women-Only Mode ('SafeHaven').
    Strictly requires verified identity and female gender.
    """
    if current_user.gender != "female":
        raise HTTPException(
            status_code=403,
            detail="SafeHaven jest dostępne wyłącznie dla zweryfikowanych kobiet."
        )
    if not current_user.is_id_verified:
        raise HTTPException(
            status_code=403,
            detail="Wymagana weryfikacja tożsamości (status Srebrny/Złoty) przed włączeniem SafeHaven."
        )
    current_user.safe_haven_enabled = not current_user.safe_haven_enabled
    return current_user


@app.post("/api/users/connect-social", response_model=UserPrivateSchema)
def connect_social_account(request: ConnectSocialRequest, current_user: UserPrivateSchema = Depends(require_user)):
    if is_production():
        raise HTTPException(
            status_code=503,
            detail="Weryfikacja kont społecznościowych nie jest jeszcze dostępna. Nie oznaczono profilu jako zweryfikowanego.",
        )
    provider = request.provider.lower().strip()
    raw_handle = request.handle.strip()
    
    if provider == "instagram":
        clean_handle = raw_handle if raw_handle.startswith("@") else f"@{raw_handle}"
        current_user.instagram_handle = clean_handle
        current_user.instagram_verified = True
    elif provider == "linkedin":
        clean_handle = raw_handle.replace("https://www.linkedin.com/in/", "").replace("https://linkedin.com/in/", "").strip("/")
        current_user.linkedin_handle = clean_handle
        current_user.linkedin_verified = True
    elif provider == "tiktok":
        clean_handle = raw_handle if raw_handle.startswith("@") else f"@{raw_handle}"
        current_user.tiktok_handle = clean_handle
        current_user.tiktok_verified = True
    elif provider == "facebook":
        current_user.facebook_handle = raw_handle
        current_user.facebook_verified = True
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider '{request.provider}'.")
        
    return current_user


@app.post("/api/users/disconnect-social/{provider}", response_model=UserPrivateSchema)
def disconnect_social_account(provider: str, current_user: UserPrivateSchema = Depends(require_user)):
    p = provider.lower().strip()
    if p == "instagram":
        current_user.instagram_handle = None
        current_user.instagram_verified = False
    elif p == "linkedin":
        current_user.linkedin_handle = None
        current_user.linkedin_verified = False
    elif p == "tiktok":
        current_user.tiktok_handle = None
        current_user.tiktok_verified = False
    elif p == "facebook":
        current_user.facebook_handle = None
        current_user.facebook_verified = False
    return current_user


# --- Live Pings Endpoints ---

@app.get("/api/pings", response_model=List[LivePingSchema])
def list_live_pings(
    user_lat: float = Query(50.2649, description="User current latitude (default: Katowice, Silesia)"),
    user_lng: float = Query(19.0238, description="User current longitude (default: Katowice, Silesia)"),
    radius_miles: float = Query(35.0, description="Discovery radius in miles"),
    category: Optional[str] = Query(None, description="Optional category filter"),
    safe_haven_only: bool = Query(False, description="Filter for Women-Only safe haven trips"),
    current_user: Optional[UserPrivateSchema] = Depends(optional_user),
):
    assert_discovery_authenticated(current_user)
    now = datetime.now(timezone.utc)
    results: List[LivePingSchema] = []

    for ping in database.PINGS.values():
        if ping.status != PingStatus.ACTIVE:
            continue

        # Region enforcement: legacy or out-of-area listings must not be
        # discoverable even if they exist in the database (F06).
        if not ping_in_live_region(ping):
            continue

        # Host eligibility: a suspended or banned host's listing must not be
        # discoverable, and the host's current state is rechecked on every
        # read rather than trusted from creation time (F07).
        host = database.USERS.get(ping.host.id)
        if not host or host.is_banned or host.is_suspended:
            continue

        # Check time-to-live expiry
        expires_at = datetime.fromisoformat(ping.expires_at)
        diff_seconds = int((expires_at - now).total_seconds())
        if diff_seconds <= 0:
            ping.status = PingStatus.EXPIRED
            database.save_ping(ping)
            continue

        ping.remaining_seconds = diff_seconds

        # SafeHaven filter check
        if ping.women_only:
            # Women-only visibility requires an authenticated, ID-verified woman.
            if not current_user or current_user.gender != "female" or not current_user.is_id_verified:
                continue
        if safe_haven_only and not ping.women_only:
            continue

        # Category filter
        if category and ping.category != category:
            continue

        # Block check: hide pings between blocked users
        if current_user and database.is_user_blocked(current_user.id, ping.host.id):
            continue

        # Compute real-time Haversine distance
        dist = haversine_distance_miles(
            user_lat, user_lng, ping.destination_lat, ping.destination_lng
        )
        if dist <= radius_miles:
            ping.distance_miles = round(dist, 1)
            ping.distance_km = round(dist * 1.60934, 1)
            ping.join_requests_count = len(database.JOIN_REQUESTS.get(ping.id, []))
            results.append(ping)

    # Sort results by nearest distance first
    results.sort(key=lambda x: x.distance_km or 999.0)
    return results


@app.post("/api/pings", response_model=LivePingSchema)
async def create_live_ping(
    payload: LivePingCreate,
    current_user: UserPrivateSchema = Depends(require_user),
):
    rate_limiter.assert_allowed(
        f"ping:{current_user.id}",
        OPERATIONAL_THRESHOLDS.rate_limit_pings_per_hour,
        3600,
        "tworzenia wyjścia",
    )
    # Ordinary closed-pilot outings require proven SMS number control or
    # operator in-person staging admission; this is not an identity check.
    # Women-only outings retain the stricter ID gate.
    is_operator_admitted = bool(
        CARTMATE_ENV == "staging"
        and OPERATOR_PILOT_ENABLED
        and current_user.assurance_marker == "operator_in_person"
        and storage.is_operator_admitted(current_user.id)
    )
    if is_production() and not (current_user.phone_verified_at or is_operator_admitted):
        raise HTTPException(
            status_code=403,
            detail="Potwierdź numer telefonu kodem SMS lub aktywacją operatora, zanim opublikujesz wyjście."
        )

    if payload.women_only and (current_user.gender != "female" or not current_user.is_id_verified):
        raise HTTPException(
            status_code=403,
            detail="Wyjścia tylko dla kobiet wymagają zweryfikowanej tożsamości i konta kobiety.",
        )

    region = get_active_region()
    distance_from_hub_km = haversine_distance_miles(
        region.center_lat,
        region.center_lng,
        payload.destination_lat,
        payload.destination_lng,
    ) * 1.609344
    if distance_from_hub_km > region.default_radius_km:
        raise HTTPException(status_code=422, detail="Miejsce wyjścia jest poza aktywnym regionem pilotażowym.")

    await assert_public_content_safe(" ".join(
        [payload.destination_name, payload.address, payload.notes or "", *payload.intent_tags]
    ))

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=payload.ttl_minutes)
    ping_id = f"png_{uuid.uuid4().hex[:8]}"

    new_ping = LivePingSchema(
        id=ping_id,
        host=to_public_user(current_user),
        category=payload.category,
        destination_name=payload.destination_name,
        destination_lat=payload.destination_lat,
        destination_lng=payload.destination_lng,
        address=payload.address,
        intent_tags=payload.intent_tags,
        notes=payload.notes or "",
        women_only=payload.women_only,
        status=PingStatus.ACTIVE,
        created_at=now.isoformat(),
        expires_at=expires_at.isoformat(),
        remaining_seconds=payload.ttl_minutes * 60,
        join_requests_count=0,
    )
    database.save_ping(new_ping)
    database.JOIN_REQUESTS[ping_id] = []

    # Never disclose women-only activity through the broad city event channel.
    if not new_ping.women_only:
        await ws_manager.broadcast(
            f"city:{current_user.city.lower()}",
            "ping.created",
            {"ping_id": new_ping.id, "city": current_user.city},
        )

    return new_ping


@app.post("/api/pings/{ping_id}/wave", response_model=WaveResponseSchema)
async def wave_at_ping(
    ping_id: str,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    Lightweight social action: wave at a neighbor's shopping ping.
    Sends instant WebSocket notification to the ping host and broadcasts
    to nearby radar participants.
    """
    if ping_id not in database.PINGS:
        raise HTTPException(status_code=404, detail="Shopping ping not found")
    ping = database.PINGS[ping_id]

    if ping.status != PingStatus.ACTIVE or datetime.fromisoformat(ping.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="This outing is no longer accepting waves.")
    if ping.host.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot wave at your own outing.")

    if ping.women_only and (current_user.gender != "female" or not current_user.is_id_verified):
        raise HTTPException(status_code=403, detail="Only an ID-verified woman can interact with this women-only outing.")

    if database.is_user_blocked(current_user.id, ping.host.id):
        raise HTTPException(status_code=403, detail="Nie możesz wchodzić w interakcję z tym użytkownikiem.")

    # A wave is a single invitation, not an unlimited push-notification channel.
    rate_limiter.assert_allowed(f"wave:{current_user.id}:{ping.id}", 1, 3600, "wysyłania powitania")

    now_iso = datetime.now(timezone.utc).isoformat()
    wave_payload = {
        "ping_id": ping.id,
        "from_user_id": current_user.id,
        "from_user_name": current_user.name,
        "from_user_avatar": current_user.avatar,
        "message": f"{current_user.name} pomachał(a) do Ciebie! 👋",
        "timestamp": now_iso,
    }

    # Waves are private interactions, never a city-wide disclosure.
    await ws_manager.send_to_user(ping.host.id, "ping.wave", wave_payload)

    return WaveResponseSchema(**wave_payload)


# --- Join Requests & Coordination ---

@app.get("/api/pings/{ping_id}/requests", response_model=List[JoinRequestSchema])
def get_ping_requests(
    ping_id: str,
    current_user: UserPrivateSchema = Depends(require_user),
):
    if ping_id not in database.PINGS:
        raise HTTPException(status_code=404, detail="Ping not found")
    ping = database.PINGS[ping_id]
    if ping.host.id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Tylko organizator wyjścia może przeglądać listę zgłoszeń."
        )
    return database.JOIN_REQUESTS.get(ping_id, [])


class JoinPingRequest(BaseModel):
    message: str = Field(default="Cześć! Chętnie dołączę do tego wyjścia!", min_length=1, max_length=500)


@app.post("/api/pings/{ping_id}/join", response_model=JoinRequestSchema)
async def request_to_join_ping(
    ping_id: str,
    payload: Optional[JoinPingRequest] = Body(None),
    legacy_message: Optional[str] = Query(None, alias="message"),
    current_user: UserPrivateSchema = Depends(require_user),
):
    if legacy_message is not None and is_production():
        raise HTTPException(status_code=400, detail="Send the join message in a JSON body, not the URL.")
    message = (legacy_message if legacy_message is not None else (payload or JoinPingRequest()).message).strip()
    if not message or len(message) > 500:
        raise HTTPException(status_code=422, detail="Join message must be between 1 and 500 characters.")
    if ping_id not in database.PINGS:
        raise HTTPException(status_code=404, detail="Ping not found")
    
    ping = database.PINGS[ping_id]

    # Region enforcement: a listing outside the active pilot region cannot be
    # joined, even if a legacy record exists (F06). Keep the 404-style denial
    # rather than confirming the record's existence.
    if not ping_in_live_region(ping):
        raise HTTPException(status_code=404, detail="Ping not found")

    if ping.status != PingStatus.ACTIVE or datetime.fromisoformat(ping.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="This outing is no longer accepting join requests.")

    if ping.host.id == current_user.id:
        raise HTTPException(status_code=400, detail="Nie możesz dołączyć do własnego wyjścia.")

    if database.is_user_blocked(current_user.id, ping.host.id):
        raise HTTPException(status_code=403, detail="Nie możesz wysłać prośby o dołączenie do tego użytkownika.")

    if ping.women_only and (current_user.gender != "female" or not current_user.is_id_verified):
        raise HTTPException(status_code=403, detail="To wyjście ma status Strefa Kobiet (tylko dla zweryfikowanych kobiet).")

    await assert_public_content_safe(message)

    existing_request = next(
        (join_request for join_request in database.JOIN_REQUESTS.get(ping_id, [])
         if join_request.applicant.id == current_user.id and join_request.status == RequestStatus.PENDING),
        None,
    )
    if existing_request:
        return existing_request

    req_id = f"req_{uuid.uuid4().hex[:8]}"
    join_req = JoinRequestSchema(
        id=req_id,
        ping_id=ping_id,
        applicant=to_public_user(current_user),
        message=message,
        status=RequestStatus.PENDING,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    database.save_join_request(join_req)
    return join_req


@app.post("/api/pings/{ping_id}/requests/{req_id}/accept", response_model=TripResponseSchema)
async def accept_join_request(
    ping_id: str,
    req_id: str,
    current_user: UserPrivateSchema = Depends(require_user),
):
    if ping_id not in database.PINGS:
        raise HTTPException(status_code=404, detail="Ping not found")
    
    ping = database.PINGS[ping_id]

    if ping.host.id != current_user.id:
        raise HTTPException(status_code=403, detail="Tylko gospodarz wyjścia może zaakceptować prośbę o dołączenie.")

    requests = database.JOIN_REQUESTS.get(ping_id, [])
    target_req = next((r for r in requests if r.id == req_id), None)
    if ping.status != PingStatus.ACTIVE or datetime.fromisoformat(ping.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="This outing is no longer accepting join requests.")
    if target_req is not None and target_req.status != RequestStatus.PENDING:
        raise HTTPException(status_code=409, detail="This join request has already been handled.")
    if not target_req:
        raise HTTPException(status_code=404, detail="Join request not found")

    if database.is_user_blocked(current_user.id, target_req.applicant.id):
        raise HTTPException(status_code=403, detail="Nie można nawiązać wyjścia z zablokowanym użytkownikiem.")

    companion_full = database.USERS.get(target_req.applicant.id)
    if not companion_full or companion_full.is_banned or companion_full.is_suspended:
        raise HTTPException(status_code=409, detail="The applicant account is no longer available.")

    updated_requests = []
    for join_request in requests:
        if join_request.id == target_req.id:
            updated_requests.append(join_request.model_copy(update={"status": RequestStatus.ACCEPTED}))
        elif join_request.status == RequestStatus.PENDING:
            updated_requests.append(join_request.model_copy(update={"status": RequestStatus.DECLINED}))
        else:
            updated_requests.append(join_request)
    matched_ping = ping.model_copy(update={"status": PingStatus.MATCHED})

    # Spawn an active Trip with a cryptographically random 4-digit PIN
    trip_id = f"trip_{uuid.uuid4().hex[:8]}"
    random_pin = f"{secrets.randbelow(9000) + 1000}"
    
    # Retrieve host and companion full records for mutual participant DTO
    host_full = current_user

    no_expected_spend = ping.category in {
        ActivityCategory.STUDY,
        ActivityCategory.WALK,
        ActivityCategory.SOCIAL,
    }
    plan = PlanDetailsSchema(
        what=f"Wspólne wyjście: {ping.destination_name}",
        when="To be agreed in chat",
        estimated_duration_minutes=45,
        cost_policy="no_expected_spend" if no_expected_spend else "buyer_pays_own",
        estimated_cost_pln=0.0,
    )

    new_trip = TripSchema(
        id=trip_id,
        ping_id=ping.id,
        chat_room_id=f"room_{trip_id}",
        host=to_trip_participant(host_full),
        companion=to_trip_participant(companion_full),
        destination_name=ping.destination_name,
        rendezvous_spot=f"Publiczny punkt przy {ping.destination_name} — ustalcie dokładne miejsce w planie",
        status=TripStatus.SCHEDULED,
        host_checked_in=False,
        companion_checked_in=False,
        rendezvous_pin=random_pin,
        rendezvous_verified=False,
        pin_attempts_left=5,
        created_at=datetime.now(timezone.utc).isoformat(),
        sos_triggered=False,
        plan_details=plan,
        host_accepted=False,
        companion_accepted=False,
    )
    chat_room_id = f"room_{trip_id}"
    chat_now = datetime.now(timezone.utc).isoformat()
    chat_room = ChatRoomSchema(
        id=chat_room_id,
        scope="trip",
        target_id=trip_id,
        participant_ids=[host_full.id, companion_full.id],
        messages=[ChatMessageSchema(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            chat_room_id=chat_room_id,
            sender_id="system",
            sender_name="CartMate",
            sender_avatar="",
            text="Trip chat opened. Agree on the exact time and cost plan here before either person accepts.",
            created_at=chat_now,
            sequence=1,
        )],
        created_at=chat_now,
    )
    try:
        database.storage.persist_join_acceptance(
            matched_ping.model_dump(),
            [join_request.model_dump() for join_request in updated_requests],
            new_trip.model_dump(),
            chat_room.model_dump(),
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    database.PINGS[ping_id] = matched_ping
    database.JOIN_REQUESTS[ping_id] = updated_requests
    database.TRIPS[trip_id] = new_trip
    database.CHAT_ROOMS[chat_room_id] = chat_room
    trip_response = build_trip_response(new_trip, current_user.id)
    companion_response = build_trip_response(new_trip)
    await ws_manager.send_to_user(new_trip.companion.id, "trip.created", companion_response.model_dump())
    return trip_response


# --- Active Trip & Safety HUD Endpoints ---

@app.get("/api/trips/{trip_id}", response_model=TripResponseSchema)
def get_trip(
    trip_id: str,
    current_user: UserPrivateSchema = Depends(require_user),
):
    if trip_id not in database.TRIPS:
        raise HTTPException(status_code=404, detail="Trip not found")
    trip = database.TRIPS[trip_id]
    if current_user.id not in [trip.host.id, trip.companion.id]:
        raise HTTPException(status_code=403, detail="Brak uprawnień do przeglądania tego wyjścia.")
    return build_trip_response(trip, current_user.id)


@app.get("/api/trips/{trip_id}/pin")
def get_trip_host_pin(
    trip_id: str,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    Host-only endpoint: returns the mutual rendezvous PIN so the host
    can verbally share it with the companion in person.
    """
    if trip_id not in database.TRIPS:
        raise HTTPException(status_code=404, detail="Trip not found")
    trip = database.TRIPS[trip_id]
    if current_user.id != trip.host.id:
        raise HTTPException(
            status_code=403,
            detail="Tylko organizator wyjścia może wyświetlić kod weryfikacyjny PIN."
        )
    if trip.status not in {TripStatus.SCHEDULED, TripStatus.IN_PROGRESS}:
        raise HTTPException(status_code=409, detail="The rendezvous PIN is unavailable for this trip state.")
    return {"trip_id": trip.id, "pin": trip.rendezvous_pin}


@app.put("/api/trips/{trip_id}/plan", response_model=TripResponseSchema)
async def update_trip_plan(
    trip_id: str,
    payload: PlanDetailsSchema,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """The host proposes concrete plan terms; every edit invalidates earlier consents."""
    if trip_id not in database.TRIPS:
        raise HTTPException(status_code=404, detail="Trip not found")
    trip = database.TRIPS[trip_id]
    if trip.host.id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the host can propose plan terms.")
    if trip.status != TripStatus.SCHEDULED or trip.host_checked_in or trip.companion_checked_in or trip.rendezvous_verified:
        raise HTTPException(status_code=400, detail="Plan terms cannot be changed after check-in or once the outing has started or ended.")
    when_value = payload.when.strip().lower()
    if when_value in {"to be agreed in chat", "do uzgodnienia", "tbd", "to be decided"}:
        raise HTTPException(status_code=400, detail="Set a specific meeting time before asking either person to accept.")
    if payload.cost_policy not in {
        "split_strictly_50_50",
        "buyer_pays_own",
        "host_treats",
        "companion_treats",
        "no_purchase_browse_only",
        "no_expected_spend",
    }:
        raise HTTPException(status_code=422, detail="Choose a supported cost policy.")
    if payload.cost_policy in {"no_expected_spend", "no_purchase_browse_only"} and payload.estimated_cost_pln != 0:
        raise HTTPException(status_code=422, detail="No-spend plans must have a zero estimated cost.")

    meeting_point = (payload.meeting_point or "").strip()
    ping = database.PINGS.get(trip.ping_id)
    if ping and ping.category in {
        ActivityCategory.STUDY, ActivityCategory.FITNESS, ActivityCategory.WALK,
        ActivityCategory.FOOD, ActivityCategory.SOCIAL,
    } and (len(meeting_point) < 8 or meeting_point.startswith("Publiczny punkt przy ")):
        raise HTTPException(status_code=422, detail="Set a specific public meeting point in the plan.")

    trip.plan_details = payload.model_copy(update={
        "what": payload.what.strip(),
        "when": payload.when.strip(),
        "meeting_point": meeting_point or None,
        "cost_policy": payload.cost_policy.strip(),
    })
    if meeting_point:
        trip.rendezvous_spot = meeting_point
    trip.plan_version += 1
    trip.host_accepted = False
    trip.companion_accepted = False
    trip.plan_accepted_at = None
    database.save_trip(trip)
    await ws_manager.broadcast(
        f"trip:{trip.id}",
        "trip.plan_updated",
        build_trip_response(trip).model_dump(),
    )
    return build_trip_response(trip, current_user.id)


@app.post("/api/trips/{trip_id}/accept-plan", response_model=TripResponseSchema)
async def accept_trip_plan(
    trip_id: str,
    payload: PlanAcceptanceRequest,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    Mutual acceptance of specific plan terms (what, when, how long, what it costs).
    Both companions must explicitly accept the terms before rendezvous check-in or PIN handshake.
    """
    if trip_id not in database.TRIPS:
        raise HTTPException(status_code=404, detail="Trip not found")
    trip = database.TRIPS[trip_id]

    if current_user.id not in [trip.host.id, trip.companion.id]:
        raise HTTPException(status_code=403, detail="Nie jesteś uczestnikiem tego wyjścia.")

    if trip.status != TripStatus.SCHEDULED or trip.host_checked_in or trip.companion_checked_in or trip.rendezvous_verified:
        raise HTTPException(status_code=400, detail="Plan acceptance is unavailable after check-in or once the outing has started or ended.")

    if payload.plan_version != trip.plan_version:
        raise HTTPException(status_code=409, detail="The plan changed. Review the latest version before accepting.")
    if not trip.plan_details or trip.plan_details.when.strip().lower() in {
        "to be agreed in chat", "do uzgodnienia", "tbd", "to be decided"
    }:
        raise HTTPException(status_code=400, detail="The host must set a specific plan before it can be accepted.")

    if payload.accept:
        if current_user.id == trip.companion.id:
            trip.companion_accepted = True
        elif current_user.id == trip.host.id:
            trip.host_accepted = True

        if trip.host_accepted and trip.companion_accepted and not trip.plan_accepted_at:
            trip.plan_accepted_at = datetime.now(timezone.utc).isoformat()
    else:
        if current_user.id == trip.companion.id:
            trip.companion_accepted = False
        elif current_user.id == trip.host.id:
            trip.host_accepted = False
        trip.plan_accepted_at = None

    database.save_trip(trip)
    await ws_manager.broadcast(
        f"trip:{trip.id}",
        "trip.plan_accepted",
        build_trip_response(trip).model_dump(),
    )
    return build_trip_response(trip, current_user.id)


@app.post("/api/trips/{trip_id}/cancel", response_model=TripResponseSchema)
async def cancel_trip(
    trip_id: str,
    payload: TripCancelRequest,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    Easy, low-guilt cancellation with clear reason tags and zero manner-temperature penalties.
    """
    if trip_id not in database.TRIPS:
        raise HTTPException(status_code=404, detail="Trip not found")
    trip = database.TRIPS[trip_id]

    if current_user.id not in [trip.host.id, trip.companion.id]:
        raise HTTPException(status_code=403, detail="Nie jesteś uczestnikiem tego wyjścia.")

    if trip.status == TripStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Nie można anulować wyjścia, które zostało już ukończone.")

    now_iso = datetime.now(timezone.utc).isoformat()
    if trip.status == TripStatus.CANCELLED:
        return build_trip_response(trip, current_user.id)
    if trip.status == TripStatus.EMERGENCY_SOS:
        raise HTTPException(status_code=409, detail="An active SOS trip cannot be cancelled from CartMate.")

    trip.status = TripStatus.CANCELLED
    trip.cancelled_by_id = current_user.id
    trip.cancellation_reason = payload.reason
    trip.cancellation_note = payload.note or ""
    trip.cancelled_at = now_iso

    database.save_trip(trip)
    await ws_manager.broadcast(f"trip:{trip.id}", "trip.cancelled", {
        "trip_id": trip.id,
        "cancelled_by": current_user.name,
        "reason": payload.reason,
        "note": payload.note,
        "cancelled_at": now_iso,
    })
    return build_trip_response(trip, current_user.id)


@app.post("/api/trips/{trip_id}/follow-up", response_model=TripFollowUpResponse)
def submit_trip_follow_up(
    trip_id: str,
    payload: TripFollowUpRequest,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    Simple follow-up to meet again.
    If both companions select 'would_meet_again: True', they become mutual connections.
    """
    if trip_id not in database.TRIPS:
        raise HTTPException(status_code=404, detail="Trip not found")
    trip = database.TRIPS[trip_id]

    if current_user.id not in [trip.host.id, trip.companion.id]:
        raise HTTPException(status_code=403, detail="Nie jesteś uczestnikiem tego wyjścia.")

    now_iso = datetime.now(timezone.utc).isoformat()
    if trip.status != TripStatus.COMPLETED or not trip.rendezvous_verified:
        raise HTTPException(status_code=400, detail="Follow-up is available after a completed, PIN-verified outing.")
    if trip.is_mutual_buddy:
        previous = trip.follow_ups.get(current_user.id, {})
        return TripFollowUpResponse(
            trip_id=trip.id,
            user_id=current_user.id,
            would_meet_again=bool(previous.get("would_meet_again")),
            is_mutual_buddy=True,
            message="You have already both opted in to meet again.",
        )
    trip.follow_ups[current_user.id] = {
        "would_meet_again": payload.would_meet_again,
        "positive_tags": payload.positive_tags,
        "feedback": payload.feedback or "",
        "submitted_at": now_iso,
    }

    other_user_id = trip.companion.id if current_user.id == trip.host.id else trip.host.id
    other_vote = trip.follow_ups.get(other_user_id)
    is_mutual = bool(payload.would_meet_again and other_vote and other_vote.get("would_meet_again"))

    if is_mutual and not trip.is_mutual_buddy:
        trip.is_mutual_buddy = True
        database.save_shopping_buddy(current_user.id, other_user_id)

    database.save_trip(trip)

    msg = (
        "Świetnie! Oboje wyraziliście chęć kolejnego wspólnego wyjścia – jesteście teraz zaufaną ekipą zakupową!"
        if is_mutual
        else "Dziękujemy za opinię! Twoja odpowiedź pomoże w bezpiecznym dobieraniu kolejnych towarzyszy."
    )
    return TripFollowUpResponse(
        trip_id=trip.id,
        user_id=current_user.id,
        would_meet_again=payload.would_meet_again,
        is_mutual_buddy=is_mutual,
        message=msg,
    )


@app.get("/api/users/me/buddies", response_model=List[ShoppingBuddySchema])
def get_my_shopping_buddies(current_user: UserPrivateSchema = Depends(require_user)):
    """
    Returns mutual shopping companions who both confirmed interest to meet again.
    """
    buddies_data = database.get_user_shopping_buddies(current_user.id)
    result = []
    for b in buddies_data:
        other_id = b["user_id_2"] if b["user_id_1"] == current_user.id else b["user_id_1"]
        other_user = database.USERS.get(other_id)
        if other_user and not database.is_user_blocked(current_user.id, other_id):
            result.append(
                ShoppingBuddySchema(
                    buddy_user=to_public_user(other_user),
                    established_at=b["established_at"],
                    shared_trips_count=b.get("shared_trips_count", 1),
                )
            )
    return result


@app.get("/api/trips/active/current", response_model=Optional[TripResponseSchema])
def get_current_active_trip(
    current_user: UserPrivateSchema = Depends(require_user),
):
    for trip in database.TRIPS.values():
        if (trip.host.id == current_user.id or trip.companion.id == current_user.id) and trip.status in [
            TripStatus.SCHEDULED,
            TripStatus.IN_PROGRESS,
            TripStatus.EMERGENCY_SOS,
        ]:
            return build_trip_response(trip, current_user.id)
    return None


@app.post("/api/trips/{trip_id}/checkin", response_model=TripResponseSchema)
async def trip_checkin(
    trip_id: str,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    Records a self-reported check-in. This endpoint does not request or verify GPS location.
    """
    if trip_id not in database.TRIPS:
        raise HTTPException(status_code=404, detail="Trip not found")
    trip = database.TRIPS[trip_id]

    if current_user.id not in [trip.host.id, trip.companion.id]:
        raise HTTPException(status_code=403, detail="Nie jesteś uczestnikiem tego wyjścia.")

    if trip.status not in {TripStatus.SCHEDULED, TripStatus.IN_PROGRESS}:
        raise HTTPException(status_code=409, detail="Check-in is unavailable for this trip state.")

    if not (trip.host_accepted and trip.companion_accepted):
        raise HTTPException(
            status_code=400,
            detail="Plan wyjścia musi zostać zaakceptowany przez obu uczestników przed zameldowaniem na miejscu spotkania.",
        )

    if trip.host.id == current_user.id:
        trip.host_checked_in = True
    else:
        trip.companion_checked_in = True
    
    if trip.host_checked_in and trip.companion_checked_in:
        trip.status = TripStatus.IN_PROGRESS

    database.save_trip(trip)
    await ws_manager.broadcast(f"trip:{trip.id}", "trip.status_updated", build_trip_response(trip).model_dump())
    return build_trip_response(trip, current_user.id)


@app.post("/api/trips/{trip_id}/sos", response_model=TripResponseSchema)
async def trigger_trip_sos(
    trip_id: str,
    payload: SosTriggerRequest,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    1-Tap Emergency SOS Alert with explicit user consent, verified carrier dispatch, and 112 fallback.
    """
    if trip_id not in database.TRIPS:
        raise HTTPException(status_code=404, detail="Trip not found")
    trip = database.TRIPS[trip_id]

    if current_user.id not in [trip.host.id, trip.companion.id]:
        raise HTTPException(status_code=403, detail="Nie jesteś uczestnikiem tego wyjścia.")

    if not payload.user_confirmed:
        raise HTTPException(status_code=400, detail="Wymagane jest jawne potwierdzenie uruchomienia alertu SOS (user_confirmed: true).")
    if trip.status == TripStatus.EMERGENCY_SOS or trip.sos_triggered:
        return build_trip_response(trip, current_user.id)
    if trip.status not in {TripStatus.SCHEDULED, TripStatus.IN_PROGRESS}:
        raise HTTPException(status_code=409, detail="SOS is unavailable for a completed or cancelled trip.")

    rate_limiter.assert_allowed(
        f"sos:{trip.id}",
        OPERATIONAL_THRESHOLDS.rate_limit_sos_per_10m,
        600,
        "uruchomienia alertu SOS",
    )

    if not payload or not payload.user_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Wymagane jest jawne potwierdzenie uruchomienia alertu SOS (user_confirmed: true).",
        )

    alert_result = await sos_manager.trigger_sos(
        trip_id=trip.id,
        user_id=current_user.id,
        user_name=current_user.name,
        destination_name=trip.destination_name,
        emergency_contact=current_user.emergency_contact,
        emergency_contact_verified=current_user.emergency_contact_verified,
        consent_confirmed=True,
    )
    if not alert_result.get("id"):
        raise HTTPException(
            status_code=400,
            detail=alert_result.get("error", "Błąd uruchomienia alertu."),
        )

    trip.status = TripStatus.EMERGENCY_SOS
    trip.sos_triggered = True
    database.save_trip(trip)

    # Trip listeners consume a TripResponseSchema, not the carrier alert object.
    # Keep the same PIN-shielded DTO shape for both REST and live participants.
    await ws_manager.broadcast(
        f"trip:{trip.id}",
        "trip.sos_triggered",
        build_trip_response(trip).model_dump(),
    )

    return build_trip_response(trip, current_user.id)


@app.post("/api/sos/delivery-receipt")
async def handle_sos_delivery_receipt(
    request: Request,
    x_twilio_signature: Optional[str] = Header(None),
    x_webhook_secret: Optional[str] = Header(None),
):
    """
    Authenticated carrier webhook endpoint for delivery status receipts (Twilio / SMSAPI.pl DLR).
    Only updates alert status to delivered when confirmed by carrier network.
    Strictly requires either valid X-Twilio-Signature or valid X-Webhook-Secret header.
    Query-string secrets are strictly forbidden to prevent credential leakage in access logs.
    """
    if SOS_PROVIDER == "disabled":
        raise HTTPException(status_code=404, detail="SMS SOS delivery receipts are disabled.")
    # 1. Parse payload based on content-type
    content_type = request.headers.get("content-type", "")
    params: dict = {}
    if "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        params = {k: str(v) for k, v in form.items()}
    else:
        try:
            body_json = await request.json()
            if isinstance(body_json, dict):
                params = {k: str(v) for k, v in body_json.items()}
        except Exception:
            params = {}

    # 2. Authenticate webhook caller via Header credentials only
    is_secret_valid = verify_webhook_secret(x_webhook_secret)
    is_twilio_valid = False
    if x_twilio_signature:
        target_url = TWILIO_STATUS_CALLBACK_URL or str(request.url)
        is_twilio_valid = verify_twilio_signature(
            target_url,
            params,
            x_twilio_signature,
            TWILIO_AUTH_TOKEN,
        )
        if not is_twilio_valid and TWILIO_STATUS_CALLBACK_URL:
            # Fallback for test client requests hitting mock/test URL
            is_twilio_valid = verify_twilio_signature(
                str(request.url),
                params,
                x_twilio_signature,
                TWILIO_AUTH_TOKEN,
            )

    if not is_secret_valid and not is_twilio_valid:
        raise HTTPException(
            status_code=401,
            detail="Brak autoryzacji webhooka: wymagana jest ważna sygnatura X-Twilio-Signature lub nagłówek X-Webhook-Secret.",
        )

    # 3. Extract and strictly validate required fields (never default missing status to DELIVERED)
    carrier_status = params.get("status") or params.get("MessageStatus") or params.get("carrier_status")
    if not carrier_status or not str(carrier_status).strip():
        raise HTTPException(
            status_code=400,
            detail="Wymagany jest jawny status doręczenia operatora (brak pola 'status' lub 'MessageStatus').",
        )

    message_id = params.get("message_id") or params.get("MessageSid") or params.get("id")
    if not message_id or not str(message_id).strip():
        raise HTTPException(
            status_code=400,
            detail="Wymagany jest identyfikator wiadomości ('message_id' lub 'MessageSid').",
        )

    updated = await sos_manager.process_delivery_receipt(str(message_id).strip(), str(carrier_status).strip())
    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Nie znaleziono alertu dla podanego identyfikatora wiadomości lub alert został zamknięty.",
        )

    trip_id = updated.get("trip_id")
    if trip_id:
        await ws_manager.broadcast(f"trip:{trip_id}", "trip.sos_updated", updated)

    return {"status": "ok", "alert": updated}


@app.get("/api/trips/{trip_id}/sos/status", response_model=SosAlertSchema)
def get_trip_sos_status(
    trip_id: str,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    Returns live carrier dispatch status and fallback URLs for active SOS alert.
    """
    if trip_id not in database.TRIPS:
        raise HTTPException(status_code=404, detail="Trip not found")
    trip = database.TRIPS[trip_id]
    if current_user.id not in [trip.host.id, trip.companion.id]:
        raise HTTPException(status_code=403, detail="Nie jesteś uczestnikiem tego wyjścia.")

    alert = sos_manager.get_alert_by_trip(trip.id)
    if not alert:
        raise HTTPException(status_code=404, detail="Brak aktywnego alertu SOS dla tego wyjścia.")
    return SosAlertSchema(**alert)


@app.post("/api/trips/{trip_id}/verify-pin", response_model=TripResponseSchema)
async def verify_trip_pin(
    trip_id: str,
    request: TripHandshakeVerifyRequest,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    Dual-Handshake verification via 4-digit mutual rendezvous PIN.
    Enforces maximum 5 attempts to protect against brute-force attacks.
    """
    if trip_id not in database.TRIPS:
        raise HTTPException(status_code=404, detail="Trip not found")
    trip = database.TRIPS[trip_id]
    
    if current_user.id not in [trip.host.id, trip.companion.id]:
        raise HTTPException(status_code=403, detail="Nie jesteś uczestnikiem tego wyjścia.")

    if not (trip.host_accepted and trip.companion_accepted):
        raise HTTPException(
            status_code=400,
            detail="Plan wyjścia musi zostać zaakceptowany przez obu uczestników przed weryfikacją kodu PIN.",
        )

    if trip.status not in {TripStatus.SCHEDULED, TripStatus.IN_PROGRESS}:
        raise HTTPException(status_code=409, detail="PIN verification is unavailable for this trip state.")
    if current_user.id != trip.companion.id:
        raise HTTPException(status_code=403, detail="Only the companion can verify the PIN shared by the host.")
    if not trip.host_checked_in:
        raise HTTPException(status_code=400, detail="The host must check in before the companion can verify the shared PIN.")
    if trip.rendezvous_verified:
        return build_trip_response(trip, current_user.id)

    if trip.pin_attempts_left <= 0:
        raise HTTPException(
            status_code=429,
            detail="Przekroczono limit prób weryfikacji PIN (blokada bezpieczeństwa). Skontaktuj się ze wsparciem."
        )

    if request.pin.strip() != trip.rendezvous_pin:
        trip.pin_attempts_left -= 1
        database.save_trip(trip)
        raise HTTPException(
            status_code=400,
            detail=f"Nieprawidłowy kod PIN. Incorrect PIN. Attempts remaining: {trip.pin_attempts_left}.",
        )
    
    trip.rendezvous_verified = True
    trip.host_checked_in = True
    trip.companion_checked_in = True
    trip.status = TripStatus.IN_PROGRESS
    database.save_trip(trip)
    await ws_manager.broadcast(f"trip:{trip.id}", "trip.handshake_verified", build_trip_response(trip).model_dump())
    return build_trip_response(trip, current_user.id)


@app.post("/api/trips/{trip_id}/split-items", response_model=TripResponseSchema)
async def add_split_item(
    trip_id: str,
    request: TripItemSplitRequest,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    Wholesale & Grocery Item Splitter (inspired by Spliit / Karrot foodsharing).
    Records user-declared purchases and calculates a 50/50 balance; no payment is initiated.
    """
    if trip_id not in database.TRIPS:
        raise HTTPException(status_code=404, detail="Trip not found")
    trip = database.TRIPS[trip_id]
    
    if current_user.id not in [trip.host.id, trip.companion.id]:
        raise HTTPException(status_code=403, detail="Nie jesteś uczestnikiem tego wyjścia.")

    if database.is_user_blocked(trip.host.id, trip.companion.id):
        raise HTTPException(status_code=403, detail="Podział kosztów jest zablokowany po zablokowaniu uczestnika.")
    if not (trip.host_accepted and trip.companion_accepted and trip.plan_details):
        raise HTTPException(status_code=400, detail="Obie osoby muszą zaakceptować szczegółowy plan przed podziałem kosztów.")
    if trip.plan_details.cost_policy != "split_strictly_50_50":
        raise HTTPException(status_code=400, detail="Podział 50/50 nie jest częścią zaakceptowanego planu.")
    if trip.status != TripStatus.IN_PROGRESS or not trip.rendezvous_verified:
        raise HTTPException(status_code=400, detail="Dodawanie pozycji jest dostępne dopiero po rozpoczęciu wyjścia.")
    if request.payer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Możesz zapisać wyłącznie pozycję opłaconą przez siebie.")
    budget_limit = trip.plan_details.estimated_cost_pln
    if budget_limit > 0 and trip.total_split_pln + request.total_price_pln > budget_limit:
        raise HTTPException(status_code=400, detail="Ta pozycja przekroczyłaby zaakceptowany szacunkowy budżet wyjścia.")

    payer_id = current_user.id
    # Work in whole grosz so odd-cent items are deterministic: the payer bears
    # the extra grosz and the other participant reimburses floor(price / 2).
    price_cents = round(request.total_price_pln * 100)
    half_price = (price_cents // 2) / 100
    
    if payer_id == trip.host.id:
        host_owes = 0.0
        companion_owes = half_price
    else:
        host_owes = half_price
        companion_owes = 0.0
        
    split_entry = TripItemSplit(
        id=f"split_{uuid.uuid4().hex[:6]}",
        item_name=request.item_name.strip(),
        total_price_pln=request.total_price_pln,
        payer_id=payer_id,
        host_owes_pln=host_owes,
        companion_owes_pln=companion_owes,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    
    trip.items_split.append(split_entry)
    trip.total_split_pln = round(sum(s.total_price_pln for s in trip.items_split), 2)
    database.save_trip(trip)
    await ws_manager.broadcast(f"trip:{trip.id}", "trip.status_updated", build_trip_response(trip).model_dump())
    return build_trip_response(trip, current_user.id)


@app.post("/api/trips/{trip_id}/review", response_model=TripResponseSchema)
def review_trip(
    trip_id: str,
    request: TripReviewRequest,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    Post-trip Manner Temperature adjustment & contextual badge award (inspired by Daangn Market).
    Increases manner temperature for positive interactions instead of toxic 5-star metric.
    """
    if trip_id not in database.TRIPS:
        raise HTTPException(status_code=404, detail="Trip not found")
    trip = database.TRIPS[trip_id]
    
    if current_user.id not in [trip.host.id, trip.companion.id]:
        raise HTTPException(status_code=403, detail="Nie jesteś uczestnikiem tego wyjścia.")

    if not trip.rendezvous_verified or trip.status not in {TripStatus.IN_PROGRESS, TripStatus.COMPLETED}:
        raise HTTPException(status_code=400, detail="Opinię można dodać dopiero po PIN-ie spotkania i rozpoczęciu wyjścia.")
    if current_user.id in trip.reviews:
        raise HTTPException(status_code=409, detail="Opinia z tego konta została już zapisana.")

    # Target is the other person in the trip
    target_id = trip.companion.id if current_user.id == trip.host.id else trip.host.id
    target_user = database.USERS.get(target_id)

    trip.reviews[current_user.id] = {
        "target_user_id": target_id,
        "rating": request.rating,
        "manner_badges": request.manner_badges,
        "feedback": request.feedback or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    if target_user:
        badge_bonus = len(request.manner_badges) * 0.2
        rating_bonus = 0.4 if request.rating >= 4.5 else 0.1 if request.rating >= 3.5 else -0.5
        new_temp = round(target_user.manner_temperature + rating_bonus + badge_bonus, 1)
        target_user.manner_temperature = max(10.0, min(99.0, new_temp))
        
        total_prev_score = target_user.rating * target_user.reviews_count
        target_user.reviews_count += 1
        target_user.rating = round((total_prev_score + request.rating) / target_user.reviews_count, 2)
        storage.persist_user(target_user.model_dump())
        
    _mark_trip_completed(trip)
    return build_trip_response(trip, current_user.id)


def _mark_trip_completed(trip: TripSchema) -> None:
    """Persist completion and count it exactly once, including review-first flows."""
    trip.status = TripStatus.COMPLETED
    if not trip.completion_counted:
        if trip.host.id in database.USERS:
            database.USERS[trip.host.id].trips_completed += 1
            storage.persist_user(database.USERS[trip.host.id].model_dump())
        if trip.companion.id in database.USERS:
            database.USERS[trip.companion.id].trips_completed += 1
            storage.persist_user(database.USERS[trip.companion.id].model_dump())
        trip.completion_counted = True
    database.save_trip(trip)


@app.post("/api/trips/{trip_id}/complete", response_model=TripResponseSchema)
def complete_trip(
    trip_id: str,
    current_user: UserPrivateSchema = Depends(require_user),
):
    if trip_id not in database.TRIPS:
        raise HTTPException(status_code=404, detail="Trip not found")
    trip = database.TRIPS[trip_id]

    if current_user.id not in [trip.host.id, trip.companion.id]:
        raise HTTPException(status_code=403, detail="Nie jesteś uczestnikiem tego wyjścia.")

    if not (trip.host_accepted and trip.companion_accepted and trip.plan_details and trip.rendezvous_verified):
        raise HTTPException(status_code=400, detail="Wyjście można zakończyć dopiero po akceptacji planu i PIN-ie spotkania.")
    if trip.status not in {TripStatus.IN_PROGRESS, TripStatus.COMPLETED}:
        raise HTTPException(status_code=400, detail="Tylko rozpoczęte wyjście można zakończyć.")

    _mark_trip_completed(trip)
    return build_trip_response(trip, current_user.id)


# --- Community & Impact Stats ---

@app.get("/api/stats")
def get_community_stats():
    return {
        "completed_outings_total": sum(
            trip.status == TripStatus.COMPLETED
            for trip in database.TRIPS.values()
        ),
    }


# --- Phase 2 & 3: Hotspots, Outings & Group Formations ---

@app.get("/api/hotspots", response_model=List[HotspotPublicSchema])
def list_hotspots(
    city: str = Query("Katowice"),
    current_user: Optional[UserPrivateSchema] = Depends(optional_user),
):
    assert_discovery_authenticated(current_user)
    return [
        build_hotspot_response(spot, current_user)
        for spot in database.HOTSPOTS.values()
        if spot.city.lower() == city.lower() and hotspot_in_live_region(spot)
    ]


@app.post("/api/hotspots", response_model=HotspotPublicSchema)
async def create_hotspot(
    payload: HotspotCreateRequest,
    current_user: UserPrivateSchema = Depends(require_user),
):
    if not is_city_in_launch_boundary(payload.city):
        raise HTTPException(status_code=422, detail="Spot is outside the active pilot region.")
    rate_limiter.assert_allowed(f"hotspot-create:{current_user.id}", 4, 3600, "tworzenia miejsc")
    await assert_public_content_safe(" ".join(
        [payload.name, payload.address, payload.description, payload.cost_policy]
    ))
    spot_id = f"spot_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    new_spot = HotspotSpotSchema(
        id=spot_id,
        city=payload.city,
        name=payload.name,
        category=payload.category,
        emoji=payload.emoji,
        address=payload.address,
        target_time=payload.target_time,
        description=payload.description,
        cost_policy=payload.cost_policy,
        votes_count=1,
        voter_ids=[current_user.id],
        voter_avatars=[current_user.avatar],
        threshold=3,
        group_formed=False,
        created_at=now.isoformat(),
    )
    database.save_hotspot(new_spot)
    database.record_hotspot_vote(new_spot.id, current_user.id)
    return build_hotspot_response(new_spot, current_user)


@app.put("/api/hotspots/{spot_id}/vote", response_model=HotspotPublicSchema)
async def vote_for_hotspot(
    spot_id: str,
    current_user: UserPrivateSchema = Depends(require_user),
):
    if spot_id not in database.HOTSPOTS:
        raise HTTPException(status_code=404, detail="Hotspot not found")
    spot = database.HOTSPOTS[spot_id]
    require_live_record(hotspot_in_live_region(spot))
    
    # If this user is blocked by any existing voter, or any existing voter is blocked
    # by the current user, block the vote to prevent group formation between blocked pairs.
    existing_voters = [uid for uid in spot.voter_ids if uid != current_user.id]
    for vid in existing_voters:
        if database.is_user_blocked(current_user.id, vid) or database.is_user_blocked(vid, current_user.id):
            raise HTTPException(
                status_code=403,
                detail="Nie możesz dołączyć do grupy tym hotspotem: znajduje się na Twojej liście blokady.",
            )
    
    # A vote is interest, not consent to join a roster or read its chat.
    # Publish this candidate in memory only after the SQLite commit succeeds.
    updated_spot = spot.model_copy(deep=True)
    if current_user.id not in updated_spot.voter_ids:
        updated_spot.voter_ids.append(current_user.id)
        updated_spot.voter_avatars.append(current_user.avatar)
    updated_spot.votes_count = len(updated_spot.voter_ids)

    threshold_reached = False
    new_outing = None
    chat_room = None
    if updated_spot.votes_count >= updated_spot.threshold and not updated_spot.group_formed:
        # Form an invitation shell only. Every participant joins explicitly,
        # and block checks run again at that transition.
        updated_spot.group_formed = True
        threshold_reached = True
        outing_id = f"out_{uuid.uuid4().hex[:8]}"
        chat_id = f"room_{outing_id}"
        if threshold_reached:
            now = datetime.now(timezone.utc)
            outing = OutingSchema(
                id=outing_id,
                hotspot_id=updated_spot.id,
                hotspot_name=updated_spot.name,
                category=updated_spot.category,
                emoji=updated_spot.emoji,
                city=updated_spot.city,
                address=updated_spot.address,
                participant_ids=[],
                participant_avatars=[],
                chat_room_id=chat_id,
                created_at=now.isoformat(),
            )
            new_outing = outing

            chat_room = ChatRoomSchema(
                id=chat_id,
                scope="outing",
                target_id=outing_id,
                participant_ids=[],
                messages=[
                    ChatMessageSchema(
                        id=f"msg_{uuid.uuid4().hex[:6]}",
                        chat_room_id=chat_id,
                        sender_id="system",
                        sender_name="CartMate Ekipa",
                        sender_avatar="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
                        text=f"🔥 Ekipa do {spot.name} zebrała wymaganą liczbę chętnych! Możecie wspólnie ustalić szczegóły wyjścia na czacie.",
                        created_at=now.isoformat(),
                        sequence=1,
                    )
                ],
                created_at=now.isoformat(),
            )
            updated_spot.outing_id = outing_id

    storage.persist_hotspot_vote_and_group(
        updated_spot.model_dump(), current_user.id,
        new_outing.model_dump() if new_outing else None,
        chat_room.model_dump() if chat_room else None,
    )
    database.HOTSPOTS[updated_spot.id] = updated_spot
    if new_outing and chat_room:
        database.OUTINGS[new_outing.id] = new_outing
        database.CHAT_ROOMS[chat_room.id] = chat_room

    # City channels carry invalidation hints, not voter identities or room membership.
    await ws_manager.broadcast(
        f"city:{updated_spot.city.lower()}", "hotspot.voted", {"spot_id": updated_spot.id, "city": updated_spot.city}
    )
    if threshold_reached and new_outing:
        await ws_manager.broadcast(
            f"city:{updated_spot.city.lower()}",
            "outing.created",
            {"spot_id": updated_spot.id, "city": updated_spot.city},
        )

    return build_hotspot_response(updated_spot, current_user)


@app.delete("/api/hotspots/{spot_id}/vote", response_model=HotspotPublicSchema)
async def unvote_hotspot(
    spot_id: str,
    current_user: UserPrivateSchema = Depends(require_user),
):
    if spot_id not in database.HOTSPOTS:
        raise HTTPException(status_code=404, detail="Hotspot not found")
    spot = database.HOTSPOTS[spot_id]
    require_live_record(hotspot_in_live_region(spot))

    if current_user.id in spot.voter_ids:
        updated_spot = spot.model_copy(deep=True)
        idx = updated_spot.voter_ids.index(current_user.id)
        updated_spot.voter_ids.pop(idx)
        if idx < len(updated_spot.voter_avatars):
            updated_spot.voter_avatars.pop(idx)
        updated_spot.votes_count = len(updated_spot.voter_ids)
        storage.persist_hotspot_unvote(updated_spot.model_dump(), current_user.id)
        database.HOTSPOTS[spot.id] = updated_spot
        spot = updated_spot

    await ws_manager.broadcast(
        f"city:{spot.city.lower()}", "hotspot.voted", {"spot_id": spot.id, "city": spot.city}
    )
    return build_hotspot_response(spot, current_user)


@app.get("/api/outings/{outing_id}", response_model=OutingSchema)
def get_outing(
    outing_id: str,
    current_user: UserPrivateSchema = Depends(require_user),
):
    if outing_id not in database.OUTINGS:
        raise HTTPException(status_code=404, detail="Outing not found")
    outing = database.OUTINGS[outing_id]
    require_live_record(outing_in_live_region(outing))
    if current_user.id not in outing.participant_ids:
        raise HTTPException(status_code=403, detail="Only confirmed outing participants can view this outing.")
    if any(database.is_user_blocked(current_user.id, member_id)
           for member_id in outing.participant_ids if member_id != current_user.id):
        raise HTTPException(status_code=403, detail="This outing is unavailable after a participant block.")
    return outing


@app.post("/api/outings/{outing_id}/join", response_model=OutingSchema)
async def join_outing(
    outing_id: str,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """Add an authenticated, unblocked local member to a formed group and its chat."""
    if outing_id not in database.OUTINGS:
        raise HTTPException(status_code=404, detail="Outing not found")
    outing = database.OUTINGS[outing_id]
    require_live_record(outing_in_live_region(outing))
    if not is_city_in_launch_boundary(current_user.city):
        raise HTTPException(status_code=403, detail="Your profile is outside the active pilot area.")
    if any(database.is_user_blocked(current_user.id, participant_id) for participant_id in outing.participant_ids):
        raise HTTPException(status_code=403, detail="You cannot join an outing with a blocked participant.")
    room = database.CHAT_ROOMS.get(outing.chat_room_id)
    if not room:
        raise HTTPException(status_code=503, detail="The outing chat is unavailable.")
    if current_user.id in outing.participant_ids:
        return outing
    if len(outing.participant_ids) >= 6:
        raise HTTPException(status_code=409, detail="This group is full (maximum six people).")
    updated_outing = outing.model_copy(deep=True)
    updated_room = room.model_copy(deep=True)
    updated_outing.participant_ids.append(current_user.id)
    updated_outing.participant_avatars.append(current_user.avatar)
    updated_room.participant_ids.append(current_user.id)
    storage.persist_outing_membership(updated_outing.model_dump(), updated_room.model_dump())
    database.OUTINGS[outing.id] = updated_outing
    database.CHAT_ROOMS[room.id] = updated_room
    await ws_manager.broadcast(f"outing:{outing.id}", "outing.participant_joined", {
        "outing_id": outing.id,
        "user": to_public_user(current_user).model_dump(),
    })
    await ws_manager.broadcast(f"city:{outing.city.lower()}", "hotspot.voted", {
        "spot_id": outing.hotspot_id, "city": outing.city,
    })
    return updated_outing


@app.post("/api/outings/{outing_id}/leave")
async def leave_outing(
    outing_id: str,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """Leave without a penalty; immediately remove access to roster and chat."""
    outing = database.OUTINGS.get(outing_id)
    if not outing:
        raise HTTPException(status_code=404, detail="Outing not found")
    require_live_record(outing_in_live_region(outing))
    if current_user.id not in outing.participant_ids:
        raise HTTPException(status_code=403, detail="You are not a member of this outing.")
    room = database.CHAT_ROOMS.get(outing.chat_room_id)
    if not room:
        raise HTTPException(status_code=503, detail="The outing chat is unavailable.")
    updated_outing = outing.model_copy(deep=True)
    updated_room = room.model_copy(deep=True)
    idx = updated_outing.participant_ids.index(current_user.id)
    updated_outing.participant_ids.pop(idx)
    if current_user.id not in updated_outing.former_participant_ids:
        updated_outing.former_participant_ids.append(current_user.id)
    if idx < len(updated_outing.participant_avatars):
        updated_outing.participant_avatars.pop(idx)
    updated_room.participant_ids = [uid for uid in updated_room.participant_ids if uid != current_user.id]
    storage.persist_outing_membership(updated_outing.model_dump(), updated_room.model_dump())
    database.OUTINGS[outing.id] = updated_outing
    database.CHAT_ROOMS[room.id] = updated_room
    await ws_manager.revoke_user_scopes(current_user.id, [f"outing:{outing.id}", f"chat:{room.id}"])
    await ws_manager.broadcast(f"outing:{outing.id}", "outing.participant_left", {
        "outing_id": outing.id, "user_id": current_user.id,
    })
    await ws_manager.broadcast(f"city:{outing.city.lower()}", "hotspot.voted", {
        "spot_id": outing.hotspot_id, "city": outing.city,
    })
    return {"left": True, "outing_id": outing.id}


@app.get("/api/chat/rooms/{room_id}", response_model=ChatRoomSchema)
def get_chat_room(
    room_id: str,
    current_user: UserPrivateSchema = Depends(require_user),
):
    if room_id not in database.CHAT_ROOMS:
        raise HTTPException(status_code=404, detail="Chat room not found")
    room = database.CHAT_ROOMS[room_id]
    if not chat_room_in_live_region(room):
        raise HTTPException(status_code=404, detail="Chat room not found")
    if current_user.id not in room.participant_ids:
        raise HTTPException(status_code=403, detail="Brak uprawnień: nie jesteś uczestnikiem tego czatu.")
    if any(database.is_user_blocked(current_user.id, member_id)
           for member_id in room.participant_ids if member_id != current_user.id):
        raise HTTPException(status_code=403, detail="This chat is unavailable after a participant block.")
    return room


class SendMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@app.post("/api/chat/rooms/{room_id}/messages", response_model=ChatMessageSchema)
async def send_chat_message(
    room_id: str,
    payload: SendMessageRequest,
    current_user: UserPrivateSchema = Depends(require_user),
):
    if room_id not in database.CHAT_ROOMS:
        raise HTTPException(status_code=404, detail="Chat room not found")
    room = database.CHAT_ROOMS[room_id]

    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    if not chat_room_in_live_region(room):
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    if current_user.id not in room.participant_ids:
        raise HTTPException(status_code=403, detail="Brak uprawnień: nie jesteś uczestnikiem tego pokoju rozmów.")

    rate_limiter.assert_allowed(
        f"chat:{current_user.id}",
        OPERATIONAL_THRESHOLDS.rate_limit_chat_messages_per_minute,
        60,
        "wysyłania wiadomości czatu",
    )

    for pid in room.participant_ids:
        if pid != current_user.id and database.is_user_blocked(current_user.id, pid):
            raise HTTPException(
                status_code=403,
                detail="Wiadomość zablokowana: użytkownik znajduje się na liście zablokowanych.",
            )

    seq = len(room.messages) + 1
    new_msg = ChatMessageSchema(
        id=f"msg_{uuid.uuid4().hex[:8]}",
        chat_room_id=room_id,
        sender_id=current_user.id,
        sender_name=current_user.name,
        sender_avatar=current_user.avatar,
        text=payload.text.strip(),
        created_at=datetime.now(timezone.utc).isoformat(),
        sequence=seq,
    )
    room.messages.append(new_msg)
    database.save_chat_message(room_id, new_msg)

    # Real-time WebSocket event broadcast to room and outing scopes
    await ws_manager.broadcast(f"chat:{room_id}", "chat.message", new_msg.model_dump())
    if room.scope == "outing":
        await ws_manager.broadcast(f"outing:{room.target_id}", "chat.message", new_msg.model_dump())

    return new_msg


# --- Phase 3: Authenticated Real-Time WebSocket Endpoint ---

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    ticket: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
):
    """
    Authenticated Real-Time WebSocket endpoint.
    Clients exchange their session for a single-use '?ticket=<ticket>'. Legacy
    token URLs are accepted only for local development test fixtures.
    Enforces automatic heartbeat, scope subscriptions, and structured event streaming.
    """
    if is_production():
        origin = websocket.headers.get("origin")
        host = websocket.headers.get("host", "").lower()
        parsed_origin = urlsplit(origin) if origin else None
        same_origin = bool(
            parsed_origin and (
                parsed_origin.scheme == "https"
                or (CARTMATE_ENV == "staging" and parsed_origin.hostname in {"127.0.0.1", "localhost"})
            )
            and parsed_origin.netloc.lower() == host
            and parsed_origin.path == ""
        )
        if not same_origin and origin not in ALLOWED_ORIGINS:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Untrusted WebSocket origin")
            return
    if ticket:
        ticket_record = WS_TICKETS.pop(ticket, None)
        token = ticket_record[0] if ticket_record and ticket_record[1] > datetime.now(timezone.utc) and not token else None
    elif is_production():
        token = None
    if not token or token in REVOKED_TOKENS or token not in ACTIVE_SESSIONS or session_is_expired(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized or revoked session token")
        return

    user_id = ACTIVE_SESSIONS[token]
    user = database.USERS.get(user_id)
    if not user or user.is_banned or user.is_suspended:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User profile not active or suspended")
        return
    if is_production() and not is_adult_verified(user):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Approved 18+ verification required")
        return

    city_scope = f"city:{user.city.lower()}"
    user_scope = f"user:{user.id}"
    await ws_manager.connect(websocket, user_id=user.id, session_token=token, initial_scopes=[city_scope, user_scope])
    voice_call_manager.cancel_disconnect_grace(user.id)

    try:
        while True:
            try:
                text = await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                text = None
            if token in REVOKED_TOKENS or token not in ACTIVE_SESSIONS or session_is_expired(token) or user.is_banned or user.is_suspended or (is_production() and not is_adult_verified(user)):
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Session no longer active")
                break
            if text is None:
                continue
            if len(text.encode("utf-8")) > 8192:
                await websocket.close(code=status.WS_1009_MESSAGE_TOO_BIG, reason="WebSocket message too large")
                break
            try:
                msg = json.loads(text)
            except Exception:
                continue

            action = msg.get("action")
            if action == "ping":
                await ws_manager.send_personal_message(
                    websocket,
                    {"type": "pong", "time": datetime.now(timezone.utc).isoformat()}
                )
            elif action == "subscribe":
                scope = msg.get("scope")
                if scope:
                    if not is_scope_authorized_for_user(scope, user.id):
                        await ws_manager.send_personal_message(
                            websocket,
                            {"type": "error", "message": f"Brak uprawnień do subskrypcji kanału '{scope}'."}
                        )
                        continue
                    await ws_manager.subscribe(websocket, scope)
                    await ws_manager.send_personal_message(
                        websocket,
                        {"type": "subscription.confirmed", "scope": scope}
                    )
            elif action == "unsubscribe":
                scope = msg.get("scope")
                if scope:
                    await ws_manager.unsubscribe(websocket, scope)
                    await ws_manager.send_personal_message(
                        websocket,
                        {"type": "unsubscription.confirmed", "scope": scope}
                    )
            elif action == "chat_message":
                room_id = msg.get("room_id")
                content = (msg.get("text") or "").strip()
                if room_id and content:
                    if len(content) > 2000:
                        await ws_manager.send_personal_message(
                            websocket,
                            {"type": "error", "message": "Messages are limited to 2000 characters."},
                        )
                        continue
                    try:
                        rate_limiter.assert_allowed(
                            f"chat:{user.id}",
                            OPERATIONAL_THRESHOLDS.rate_limit_chat_messages_per_minute,
                            60,
                            "wysyłania wiadomości czatu",
                        )
                    except HTTPException as limit_error:
                        await ws_manager.send_personal_message(
                            websocket,
                            {"type": "error", "message": limit_error.detail},
                        )
                        continue
                    if room_id not in database.CHAT_ROOMS:
                        await ws_manager.send_personal_message(
                            websocket,
                            {"type": "error", "message": f"Pokój rozmów '{room_id}' nie istnieje."}
                        )
                        continue
                    room = database.CHAT_ROOMS[room_id]
                    if not chat_room_in_live_region(room):
                        await ws_manager.send_personal_message(
                            websocket,
                            {"type": "error", "message": f"Pokój rozmów '{room_id}' nie istnieje."}
                        )
                        continue
                    if user.id not in room.participant_ids:
                        await ws_manager.send_personal_message(
                            websocket,
                            {"type": "error", "message": "Brak uprawnień do wysyłania wiadomości w tym pokoju."}
                        )
                        continue
                    if any(database.is_user_blocked(user.id, pid) for pid in room.participant_ids if pid != user.id):
                        await ws_manager.send_personal_message(
                            websocket,
                            {"type": "error", "message": "Wiadomość zablokowana przez filtr bezpieczeństwa."}
                        )
                        continue
                    seq = len(room.messages) + 1
                    new_msg = ChatMessageSchema(
                        id=f"msg_{uuid.uuid4().hex[:8]}",
                        chat_room_id=room_id,
                        sender_id=user.id,
                        sender_name=user.name,
                        sender_avatar=user.avatar,
                        text=content,
                        created_at=datetime.now(timezone.utc).isoformat(),
                        sequence=seq,
                    )
                    room.messages.append(new_msg)
                    database.save_chat_message(room_id, new_msg)
                    await ws_manager.broadcast(f"chat:{room_id}", "chat.message", new_msg.model_dump())
                    if room.scope == "outing":
                        await ws_manager.broadcast(f"outing:{room.target_id}", "chat.message", new_msg.model_dump())
            elif action == "pod_chat_message":
                if is_production() and not is_adult_verified(user):
                    await ws_manager.send_personal_message(
                        websocket,
                        {"type": "error", "message": "Wymagane zatwierdzone potwierdzenie pełnoletności (18+)."}
                    )
                    continue
                pod_id_raw = msg.get("pod_id")
                content = (msg.get("text") or "").strip()
                if pod_id_raw and content:
                    try:
                        pod_id = int(pod_id_raw)
                        rate_limiter.assert_allowed(f"pod-chat:{user.id}", 30, 60, "wysyłania wiadomości")
                        await assert_public_content_safe(content)
                        sent_msg = storage.send_pod_message(pod_id, user.id, content)
                        await ws_manager.broadcast(
                            f"pod:{pod_id}",
                            "pod_chat_message",
                            {"pod_id": pod_id, "message": sent_msg}
                        )
                    except ValueError as ve:
                        await ws_manager.send_personal_message(
                            websocket,
                            {"type": "error", "message": str(ve)}
                        )
                    except HTTPException as he:
                        await ws_manager.send_personal_message(
                            websocket,
                            {"type": "error", "message": he.detail}
                        )
                    except Exception as exc:
                        logger.error(f"Error in pod_chat_message: {exc}")
                        await ws_manager.send_personal_message(
                            websocket,
                            {"type": "error", "message": "Nie udało się wysłać wiadomości."}
                        )
            elif action == "voice.join_queue":
                if is_production() and not is_adult_verified(user):
                    await ws_manager.send_personal_message(
                        websocket,
                        {"type": "error", "message": "Wymagane zatwierdzone potwierdzenie pełnoletności (18+)."}
                    )
                    continue
                topic = (msg.get("topic") or "Spokojna rozmowa o dniu").strip()[:120]
                try:
                    rate_limiter.assert_allowed(f"voice-queue:{user.id}", 6, 60, "kolejki głosowej")
                    await assert_public_content_safe(topic)
                except HTTPException as he:
                    await ws_manager.send_personal_message(
                        websocket,
                        {"type": "error", "message": he.detail}
                    )
                    continue
                status_res, call_data = await voice_call_manager.enqueue_caller(user.id, topic, websocket)
                if status_res == "WINDOW_CLOSED":
                    await ws_manager.send_personal_message(
                        websocket,
                        {"type": "error", "message": "Rozmowy głosowe są dostępne codziennie w godzinach 18:00 - 23:00."}
                    )
                elif status_res == "ALREADY_IN_CALL":
                    await ws_manager.send_personal_message(
                        websocket,
                        {"type": "error", "message": "Jesteś już w trakcie aktywnego połączenia."}
                    )
                elif status_res == "DAILY_LIMIT_REACHED":
                    await ws_manager.send_personal_message(
                        websocket,
                        {"type": "error", "message": "Osiągnięto dzienny limit połączeń (3 na dobę). Spróbuj jutro."}
                    )
                elif status_res.startswith("COOLDOWN_ACTIVE_"):
                    sec_rem = status_res.split("_")[-1].replace("S", "")
                    await ws_manager.send_personal_message(
                        websocket,
                        {"type": "error", "message": f"Przerwa między rozmowami. Pozostało {sec_rem}s do kolejnego połączenia."}
                    )
                elif status_res == "QUEUED":
                    await ws_manager.send_personal_message(
                        websocket,
                        {"type": "voice.queued", "topic": topic, "message": "Szukamy rozmówcy..."}
                    )
            elif action == "voice.leave_queue":
                await voice_call_manager.dequeue_caller(user.id)
                await ws_manager.send_personal_message(
                    websocket,
                    {"type": "voice.left_queue"}
                )
            elif action == "voice.call_offer":
                call_id = msg.get("call_id")
                sdp = msg.get("sdp")
                if call_id and sdp:
                    await voice_call_manager.forward_signaling(call_id, user.id, "voice.call_offer", {"sdp": sdp})
            elif action == "voice.call_answer":
                call_id = msg.get("call_id")
                sdp = msg.get("sdp")
                if call_id and sdp:
                    await voice_call_manager.forward_signaling(call_id, user.id, "voice.call_answer", {"sdp": sdp})
            elif action == "voice.call_ice_candidate":
                call_id = msg.get("call_id")
                candidate = msg.get("candidate")
                if call_id and candidate:
                    await voice_call_manager.forward_signaling(call_id, user.id, "voice.call_ice_candidate", {"candidate": candidate})
            elif action == "voice.call_connected":
                call_id = msg.get("call_id")
                if call_id:
                    await voice_call_manager.handle_call_connected(call_id, user.id)
            elif action == "voice.call_hangup":
                call_id = msg.get("call_id")
                reason = msg.get("reason", "user_hangup")
                block_peer = bool(msg.get("block_peer", False))
                if call_id:
                    await voice_call_manager.terminate_call(call_id, initiator_user_id=user.id, reason=reason, block_peer=block_peer)
                    if block_peer:
                        await ws_manager.close_user(user.id)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
        await voice_call_manager.dequeue_caller(user.id)
        if user.id in voice_call_manager.user_to_call:
            await voice_call_manager.handle_socket_disconnect(user.id)
    except Exception:
        await ws_manager.disconnect(websocket)
        await voice_call_manager.dequeue_caller(user.id)
        if user.id in voice_call_manager.user_to_call:
            await voice_call_manager.handle_socket_disconnect(user.id)


# --- Phase 4: TypeSafe AI Jev Governance & Decision Endpoints ---

@app.post("/api/ai/classify-intent", response_model=IntentClassificationResult)
async def classify_intent(
    request: ClassifyIntentRequest,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    TypeSafe AI Jev Bounded Classification:
    Analyzes Polish activity intent and classifies into standard tags, duration,
    and social outing context with deterministic safety fallbacks.
    """
    return await jev_service.classify_ping_intent(request.text, request.category_hint)


@app.post("/api/ai/screen-content", response_model=ContentSafetyResult)
async def screen_content(
    request: ScreenContentRequest,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    TypeSafe AI Jev Content Safety Barometer:
    Screens free-text inputs for harassment, predatory phrasing, and commercial spam.
    """
    return await jev_service.screen_content_safety(request.text)


@app.post("/api/ai/suggest-rendezvous", response_model=List[RendezvousSuggestion])
def suggest_rendezvous(
    request: SuggestRendezvousRequest,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    Suggests safe, highly-monitored, well-lit public meeting points near destination.
    """
    return jev_service.suggest_rendezvous(request.destination_name, request.category)


@app.get("/api/ai/shadow-audit")
def get_shadow_audit(
    current_user: UserPrivateSchema = Depends(require_moderator),
):
    """
    Operator-only observability endpoint for Jev AI shadow mode evaluation
    metrics: baseline agreement rate, shadow evaluation count, and latency.
    Restricted to the server-configured moderator allowlist because audit
    entries describe other users' submissions. Ordinary members receive 403.
    Entries themselves carry only redacted inputs and non-content status
    fields; no raw text, summaries, or provider blobs are retained.
    """
    return jev_service.get_shadow_audit_stats()


# --- Micro-Pods & Third Places (Migration 11 API) ---

class PodCreateRequest(BaseModel):
    template_code: str
    third_place_id: int
    starts_at: str
    ends_at: str
    quorum_deadline_at: str
    title: Optional[str] = Field(default=None, max_length=120)
    language_code: str = "pl"
    exchange_language_code: Optional[str] = None
    template_params: Optional[str] = None
    min_participants: int = 3
    max_participants: int = 5
    spend_expectation: str = "no_expected_spend"
    spend_max_minor: Optional[int] = None
    spend_currency: str = "PLN"
    cohort_id: Optional[int] = None

class PodMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)

class ThirdPlaceCreateRequest(BaseModel):
    slug: str = Field(min_length=2, max_length=60)
    name: str = Field(min_length=2, max_length=120)
    kind: str = Field(min_length=2, max_length=60)
    city: str
    meeting_point: str = Field(min_length=3, max_length=200)
    latitude: float
    longitude: float
    is_indoor: int = 1
    address: Optional[str] = None
    district: Optional[str] = None
    template_codes: Optional[List[str]] = None


@app.get("/api/pods/templates")
def list_activity_templates(
    current_user: Optional[UserPrivateSchema] = Depends(optional_user),
):
    """Returns all active structured activity templates (study sprint, park walk, etc)."""
    assert_discovery_authenticated(current_user)
    return storage.get_activity_templates()


@app.get("/api/pods/places")
def list_third_places(
    city: Optional[str] = None,
    current_user: Optional[UserPrivateSchema] = Depends(optional_user),
):
    """Returns verified public Third Places, optionally filtered by city."""
    assert_discovery_authenticated(current_user)
    return storage.get_third_places(city=city)


@app.post("/api/pods/places")
def create_third_place_endpoint(
    req: ThirdPlaceCreateRequest,
    current_user: UserPrivateSchema = Depends(require_moderator),
):
    """Adds a verified Third Place anchor with its exact meeting point (moderator-only)."""
    if not is_city_in_launch_boundary(req.city):
        raise HTTPException(status_code=422, detail="Spot is outside the active pilot region.")
    try:
        place_id = storage.create_third_place(
            slug=req.slug,
            name=req.name,
            kind=req.kind,
            city=req.city,
            meeting_point=req.meeting_point,
            latitude=req.latitude,
            longitude=req.longitude,
            is_indoor=req.is_indoor,
            address=req.address,
            district=req.district,
            template_codes=req.template_codes,
        )
        return {"id": place_id, "name": req.name, "slug": req.slug}
    except Exception as exc:
        logger.error(f"Error creating third place: {exc}")
        raise HTTPException(status_code=400, detail="Nie udało się utworzyć miejsca.")


@app.get("/api/pods/feed")
def get_pods_feed(
    city: Optional[str] = None,
    language_code: Optional[str] = None,
    current_user: Optional[UserPrivateSchema] = Depends(optional_user),
):
    """
    Near Me Today Feed: Returns available micro-pods (forming or at quorum).
    Hides pods containing mutually blocked users.
    """
    assert_discovery_authenticated(current_user)
    viewer_id = current_user.id if current_user else None
    return storage.list_pods(city=city, language_code=language_code, viewer_user_id=viewer_id)


@app.post("/api/pods")
async def create_micro_pod(
    req: PodCreateRequest,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """Creates a new scheduled micro-pod. The host is automatically added as first confirmed member."""
    rate_limiter.assert_allowed(f"pod-create:{current_user.id}", 5, 3600, "tworzenia podów")
    if req.title:
        await assert_public_content_safe(req.title)
    try:
        pod_id = storage.create_pod(
            template_code=req.template_code,
            third_place_id=req.third_place_id,
            starts_at=req.starts_at,
            ends_at=req.ends_at,
            quorum_deadline_at=req.quorum_deadline_at,
            created_by_user_id=current_user.id,
            cohort_id=req.cohort_id,
            title=req.title,
            language_code=req.language_code,
            exchange_language_code=req.exchange_language_code,
            template_params=req.template_params,
            min_participants=req.min_participants,
            max_participants=req.max_participants,
            spend_expectation=req.spend_expectation,
            spend_max_minor=req.spend_max_minor,
            spend_currency=req.spend_currency,
        )
        pod = storage.get_pod(pod_id)
        return pod
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Nieprawidłowe dane lub ograniczenie integralności danych.")
    except Exception as exc:
        logger.error(f"Error creating pod: {exc}")
        raise HTTPException(status_code=400, detail="Nie udało się utworzyć poda.")


@app.get("/api/pods/{pod_id}")
def get_pod_details(
    pod_id: int,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """Returns details of a specific micro-pod, including venue and confirmed members."""
    pod = storage.get_pod(pod_id)
    if not pod:
        raise HTTPException(status_code=404, detail="Pod nie został znaleziony.")
    if any(database.is_user_blocked(current_user.id, m["user_id"]) for m in pod.get("members", []) if m["user_id"] != current_user.id):
        raise HTTPException(status_code=403, detail="Ten pod jest niedostępny ze względu na blokadę użytkownika.")
    return pod


@app.post("/api/pods/{pod_id}/join")
async def join_pod_endpoint(
    pod_id: int,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """Joins a micro-pod. Enforces mutual blocks, seat limits, and updates quorum automatically."""
    rate_limiter.assert_allowed(f"pod-join:{current_user.id}", 15, 60, "dołączania do podów")
    try:
        pod = storage.join_pod(pod_id, current_user.id)
        await ws_manager.broadcast(
            f"pod:{pod_id}",
            "pod.member_joined",
            {
                "pod_id": pod_id,
                "user_id": current_user.id,
                "user_name": current_user.name,
                "status": pod["status"],
                "confirmed_count": pod["confirmed_count"],
            },
        )
        return pod
    except ValueError as ve:
        raise HTTPException(status_code=409, detail=str(ve))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Nie można dołączyć do poda.")
    except Exception as exc:
        logger.error(f"Error joining pod: {exc}")
        raise HTTPException(status_code=400, detail="Błąd dołączania do poda.")


@app.post("/api/pods/{pod_id}/leave")
async def leave_pod_endpoint(
    pod_id: int,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """Leaves a micro-pod. Drops confirmed count and demotes to 'forming' if below quorum."""
    try:
        pod = storage.leave_pod(pod_id, current_user.id)
        await ws_manager.broadcast(
            f"pod:{pod_id}",
            "pod.member_left",
            {
                "pod_id": pod_id,
                "user_id": current_user.id,
                "status": pod["status"],
                "confirmed_count": pod["confirmed_count"],
            },
        )
        return pod
    except ValueError as ve:
        raise HTTPException(status_code=409, detail=str(ve))
    except Exception as exc:
        logger.error(f"Error leaving pod: {exc}")
        raise HTTPException(status_code=400, detail="Błąd opuszczania poda.")


@app.get("/api/pods/{pod_id}/messages")
def get_pod_messages_endpoint(
    pod_id: int,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """Returns pod messages. Locked until quorum (at least 3 people) is confirmed."""
    try:
        return storage.get_pod_messages(pod_id, current_user.id)
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))


@app.post("/api/pods/{pod_id}/messages")
async def send_pod_message_endpoint(
    pod_id: int,
    req: PodMessageRequest,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """Sends a chat message to the micro-pod. Enforced by database trigger to require quorum."""
    rate_limiter.assert_allowed(f"pod-chat:{current_user.id}", 30, 60, "wysyłania wiadomości")
    await assert_public_content_safe(req.text)
    try:
        msg = storage.send_pod_message(pod_id, current_user.id, req.text)
        await ws_manager.broadcast(
            f"pod:{pod_id}",
            "pod_chat_message",
            {"pod_id": pod_id, "message": msg},
        )
        return msg
    except (ValueError, sqlite3.IntegrityError) as ve:
        status_code = 403 if "quorum" in str(ve).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(ve))
    except Exception as exc:
        logger.error(f"Error sending pod message: {exc}")
        raise HTTPException(status_code=400, detail="Nie udało się wysłać wiadomości.")


@app.post("/api/pods/sweep")
def sweep_unconfirmed_pods(
    current_user: UserPrivateSchema = Depends(require_moderator),
):
    """Cancels pods that failed to reach quorum before their deadline (moderator-only)."""
    cancelled = storage.cancel_unconfirmed_pods()
    return {"cancelled_count": cancelled}


# --- Track 2: 10-Minute Remote Voice Calls Endpoints ---

class VoiceRatingCreate(BaseModel):
    rating: Literal["respectful", "neutral", "inappropriate"]
    report_tag: Optional[str] = None
    details: Optional[str] = None
    block_peer: bool = False


class VoiceHangupRequest(BaseModel):
    reason: str = "user_hangup"
    block_peer: bool = False


@app.get("/api/voice/status")
def get_voice_status(
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    Returns daily voice call status, cooldown state, and evening schedule for current user.
    """
    daily_count = storage.get_daily_voice_call_count(current_user.id)
    sec_since_last = storage.get_seconds_since_last_voice_call(current_user.id)
    cooldown_remaining = max(0, int(600 - sec_since_last)) if (sec_since_last is not None and sec_since_last < 600) else 0

    active_call_id = voice_call_manager.user_to_call.get(current_user.id)
    active_call = None
    if active_call_id and active_call_id in voice_call_manager.active_calls:
        c = voice_call_manager.active_calls[active_call_id]
        active_call = {
            "id": c["id"],
            "topic": c.get("topic", "Spokojna rozmowa"),
            "status": c.get("status", "connecting"),
            "created_at": c.get("created_at"),
            "started_at": c.get("started_at"),
        }

    is_in_queue = current_user.id in voice_call_manager.queue
    queue_topic = voice_call_manager.queue[current_user.id].topic if is_in_queue else None

    # Scheduled window: 18:00 - 23:00 Polish Time
    from voice_manager import is_voice_window_open
    window_open = is_voice_window_open()

    icebreakers = [
        "Jak minął Ci dzisiejszy dzień?",
        "Jaki jest Twój ulubiony sprawdzony przepis na obiad?",
        "Ciekawy film, serial lub książka warta polecenia?",
        "Ulubione miejsce na spacer lub kawę w Twoim mieście?",
        "Najbardziej niezwykłe miejsce w Polsce, które odwiedziłeś?",
    ]

    return {
        "user_id": current_user.id,
        "daily_calls_used": daily_count,
        "daily_limit": 3,
        "cooldown_remaining_seconds": cooldown_remaining,
        "is_in_queue": is_in_queue,
        "queue_topic": queue_topic,
        "active_call": active_call,
        "window_open": window_open,
        "window_schedule": "Codziennie 18:00 - 23:00",
        "icebreakers": icebreakers,
        "ice_servers": voice_call_manager.get_ice_servers(current_user.id),
    }


@app.post("/api/voice/calls/{call_id}/rate")
async def rate_voice_call(
    call_id: str,
    request: VoiceRatingCreate,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    Submits a post-call rating (respectful / neutral / inappropriate) and optionally blocks peer.
    """
    session = storage.get_voice_session(call_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesja połączenia nie została znaleziona.")

    if current_user.id not in (session["user_a_id"], session["user_b_id"]):
        raise HTTPException(status_code=403, detail="Brak uprawnień do oceny tego połączenia.")

    target_id = session["user_b_id"] if current_user.id == session["user_a_id"] else session["user_a_id"]

    rating_id = storage.record_voice_rating(
        session_id=call_id,
        reporter_id=current_user.id,
        target_id=target_id,
        rating=request.rating,
        report_tag=request.report_tag,
        details=request.details,
    )

    if request.block_peer:
        try:
            database.block_user(current_user.id, target_id)
            separated_pids = storage.separate_blocked_user_from_pods(current_user.id, target_id)
            for pid in separated_pids:
                updated_pod = storage.get_pod(pid)
                if updated_pod:
                    await ws_manager.broadcast(
                        f"pod:{pid}",
                        "pod.member_left",
                        {
                            "pod_id": pid,
                            "user_id": current_user.id,
                            "confirmed_count": updated_pod["confirmed_count"],
                            "status": updated_pod["status"],
                        },
                    )
            await ws_manager.close_user(current_user.id)
            await ws_manager.close_user(target_id)
        except Exception as exc:
            logger.error(f"Error persisting block during rate_voice_call: {exc}")

    if request.rating == "inappropriate":
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            report = ReportSchema(
                id=f"rep_v_{secrets.token_hex(6)}",
                reporter_id=current_user.id,
                reported_user_id=target_id,
                category=request.report_tag or "harassment",
                details=f"Zgłoszenie z rozmowy głosowej ({call_id}): {request.details or 'Brak opisu'}",
                status="pending",
                created_at=now_iso,
                updated_at=now_iso,
            )
            database.save_report(report)
        except Exception as exc:
            logger.error(f"Error creating report from voice call: {exc}")

    return {"success": True, "rating_id": rating_id, "call_id": call_id}


@app.post("/api/voice/calls/{call_id}/hangup")
async def hangup_voice_call(
    call_id: str,
    request: VoiceHangupRequest,
    current_user: UserPrivateSchema = Depends(require_user),
):
    """
    Terminates an active voice call via REST and optionally blocks the peer.
    """
    session = storage.get_voice_session(call_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesja połączenia nie została znaleziona.")

    if current_user.id not in (session["user_a_id"], session["user_b_id"]):
        raise HTTPException(status_code=403, detail="Brak uprawnień do zakończenia tego połączenia.")

    target_id = session["user_b_id"] if current_user.id == session["user_a_id"] else session["user_a_id"]
    res = await voice_call_manager.terminate_call(
        call_id=call_id,
        initiator_user_id=current_user.id,
        reason=request.reason,
        block_peer=request.block_peer,
    )
    if request.block_peer:
        await ws_manager.close_user(current_user.id)
        await ws_manager.close_user(target_id)

    return {"success": True, "result": res}


# Serve React frontend and the API from one HTTPS origin. Keep this
# catch-all mount last so /api and /ws retain their dedicated handlers.
frontend_dist = os.getenv("CARTMATE_FRONTEND_DIST")
if not frontend_dist:
    default_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
    if os.path.isdir(default_dist):
        frontend_dist = default_dist
if frontend_dist and os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
