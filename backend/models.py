from __future__ import annotations
import enum
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field, field_validator


class TrustTier(str, enum.Enum):
    BRONZE = "Bronze"       # Phone/Email verified
    SILVER = "Silver"       # Genuine external identity verification required; provider not yet integrated
    GOLD = "Gold"           # Intended future higher-trust tier; background checks are not currently integrated


class ActivityCategory(str, enum.Enum):
    STUDY = "study"         # Library or other public study space
    FITNESS = "fitness"     # Gym or class; access terms must be agreed
    WALK = "walk"           # Walk starting at a named public meeting point
    FOOD = "food"           # Meal, not limited to late-night venues
    SOCIAL = "social"       # Conversation or low-pressure public outing
    GROCERY = "grocery"       # Biedronka, Lidl, supermarkets
    WHOLESALE = "wholesale"   # Makro Cash & Carry, Selgros
    FASHION = "fashion"       # Złote Tarasy, Arkadia, mall styling
    HOME = "home"             # IKEA, Castorama, furniture
    QUICK = "quick"           # Existing general errands / quick tasks category
    LATE_NIGHT = "late_night" # Burger King 24h, Kebab, McDonald's night runs
    CAFE = "cafe"             # Coffee, co-working, Green Caffè Nero
    ENTERTAINMENT = "entertainment" # Cinema, city walks, Powiśle hangouts


class PingStatus(str, enum.Enum):
    ACTIVE = "active"
    MATCHED = "matched"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class TripStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EMERGENCY_SOS = "emergency_sos"
    CANCELLED = "cancelled"


# --- Pydantic Schema Definitions ---

# 1. Public user profile exposed in feeds, radar, search, and join requests.
# STRICTOR PRIVACY: Zero sensitive PII (email, phone, emergency contact are completely stripped).
class UserPublicSchema(BaseModel):
    id: str
    name: str
    avatar: str
    bio: str
    trust_tier: TrustTier
    gender: str
    city: str = "Katowice"
    safe_haven_enabled: bool = False
    is_id_verified: bool = False
    campus_badge: Optional[str] = None
    rating: float = 5.0
    manner_temperature: float = 36.5  # Daangn/Karrot 36.5°C thermal reputation barometer
    reviews_count: int = 0
    trips_completed: int = 0
    instagram_handle: Optional[str] = None
    instagram_verified: bool = False
    linkedin_handle: Optional[str] = None
    linkedin_verified: bool = False
    tiktok_handle: Optional[str] = None
    tiktok_verified: bool = False
    facebook_handle: Optional[str] = None
    facebook_verified: bool = False


# 2. Trip participant profile: revealed ONLY between confirmed companions after mutual handshake.
class TripParticipantUserSchema(UserPublicSchema):
    phone: Optional[str] = None  # Phone revealed only for mutual coordination once trip is scheduled


# 3. Private user profile: returned exclusively to the authenticated user on /api/users/me.
class UserPrivateSchema(UserPublicSchema):
    email: str
    phone: str
    # SMS OTP proves control of this number, not the person's identity.
    phone_verified_at: Optional[str] = None
    # Reserved for a future independently approved age-assurance integration.
    # No public request can write these fields and no provider is trusted yet.
    adult_verified_at: Optional[str] = None
    adult_verification_expires_at: Optional[str] = None
    age_assurance_provider: Optional[str] = None
    is_selfie_verified: bool = False
    is_background_checked: bool = False
    emergency_contact: Optional[str] = None
    emergency_contact_verified: bool = False
    is_suspended: bool = False
    is_banned: bool = False
    suspension_reason: Optional[str] = None
    # Operator admission marker for staging-only, zero-cost private pilot.
    # Explicitly separate from phone_verified_at (never implies SMS control).
    assurance_marker: Optional[str] = None
    operator_admitted_at: Optional[str] = None


# Backward-compatible internal alias for the full database record
UserSchema = UserPrivateSchema


class RedeemOperatorActivationRequest(BaseModel):
    activation_token: str = Field(..., min_length=16, max_length=64)
    name: str = Field(..., min_length=2, max_length=50)
    city: str = Field(default="Katowice", max_length=50)
    bio: Optional[str] = Field(default="Nowy użytkownik CartMate.", max_length=300)
    gender: Optional[str] = Field(default="unspecified", max_length=20)


class RedeemOperatorRecoveryRequest(BaseModel):
    recovery_token: str = Field(..., min_length=16, max_length=64)


class ConnectSocialRequest(BaseModel):
    provider: str  # instagram, linkedin, tiktok, facebook
    handle: str
    code: Optional[str] = "oauth_token_simulated"


class AuthLoginRequest(BaseModel):
    identifier: str  # Phone or email
    code: Optional[str] = None  # Provider-backed OTP code


class AuthRegisterRequest(BaseModel):
    name: str
    phone: str
    email: str
    gender: str
    city: str = "Katowice"
    bio: Optional[str] = "Nowa osoba w CartMate. Chętnie wyjdę z kimś na miasto!"
    campus_badge: Optional[str] = None
    otp_code: str  # Verified OTP code required for account creation
    invite_code: Optional[str] = Field(default=None, max_length=64)


class SosDeliveryReceiptWebhook(BaseModel):
    message_id: str
    status: str  # e.g., "delivered", "failed", "undelivered"
    carrier_status: Optional[str] = None


class JoinRequestSchema(BaseModel):
    id: str
    ping_id: str
    applicant: UserPublicSchema
    message: str
    status: RequestStatus
    created_at: str


class LivePingCreate(BaseModel):
    category: ActivityCategory
    destination_name: str = Field(min_length=3, max_length=140)
    destination_lat: float = Field(ge=-90, le=90)
    destination_lng: float = Field(ge=-180, le=180)
    address: str = Field(min_length=3, max_length=200)
    intent_tags: List[str] = Field(default_factory=list, max_length=8)
    ttl_minutes: int = Field(default=45, ge=15, le=240)
    notes: Optional[str] = Field(default="", max_length=500)
    women_only: bool = False


class LivePingSchema(BaseModel):
    id: str
    host: UserPublicSchema
    category: ActivityCategory
    destination_name: str
    destination_lat: float
    destination_lng: float
    address: str
    intent_tags: List[str]
    notes: str
    women_only: bool
    status: PingStatus
    distance_miles: Optional[float] = None
    distance_km: Optional[float] = None
    created_at: str
    expires_at: str
    remaining_seconds: int
    join_requests_count: int = 0


class TripItemSplit(BaseModel):
    id: str
    item_name: str
    total_price_pln: float
    payer_id: str
    host_owes_pln: float
    companion_owes_pln: float
    created_at: str


class TripSettlementSchema(BaseModel):
    debtor_id: Optional[str] = None
    creditor_id: Optional[str] = None
    amount_pln: float = 0.0


class TripItemSplitRequest(BaseModel):
    item_name: str = Field(min_length=1, max_length=140)
    total_price_pln: float = Field(gt=0, le=5000)
    payer_id: str = Field(min_length=1, max_length=80)
    split_type: Literal["50_50"] = "50_50"

    @field_validator("total_price_pln")
    @classmethod
    def require_whole_grosz(cls, value: float) -> float:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount != amount.quantize(Decimal("0.01")):
            raise ValueError("Amount must be a finite PLN value with at most two decimal places")
        return value


class TripHandshakeVerifyRequest(BaseModel):
    pin: str


class TripReviewRequest(BaseModel):
    rating: float = Field(ge=1.0, le=5.0)
    manner_badges: List[str] = Field(default_factory=list, max_length=4)
    feedback: Optional[str] = ""


class PlanDetailsSchema(BaseModel):
    what: str = Field(min_length=3, max_length=140)
    when: str = Field(min_length=3, max_length=120)
    meeting_point: Optional[str] = Field(default=None, max_length=200)
    estimated_duration_minutes: int = Field(default=45, ge=15, le=240)
    cost_policy: str = "buyer_pays_own"
    estimated_cost_pln: float = Field(default=0.0, ge=0, le=5000)


class PlanAcceptanceRequest(BaseModel):
    accept: bool
    plan_version: int = Field(ge=1)


class TripCancelRequest(BaseModel):
    reason: str = "running_late"  # running_late, sudden_conflict, unwell, changed_mind, safety_concern, other
    note: Optional[str] = ""


class TripFollowUpRequest(BaseModel):
    would_meet_again: bool
    positive_tags: List[str] = []
    feedback: Optional[str] = ""


class TripFollowUpResponse(BaseModel):
    trip_id: str
    user_id: str
    would_meet_again: bool
    is_mutual_buddy: bool
    message: str


class ShoppingBuddySchema(BaseModel):
    buddy_user: UserPublicSchema
    established_at: str
    shared_trips_count: int = 1


class BlockUserRequest(BaseModel):
    reason: Optional[str] = ""


class BlockedUserSchema(BaseModel):
    user: UserPublicSchema
    blocked_at: str


class ReportCategory(str, enum.Enum):
    HARASSMENT = "harassment"
    UNSAFE_BEHAVIOR = "unsafe_behavior"
    FAKE_PROFILE = "fake_profile"
    NO_SHOW = "no_show"
    SPAM = "spam"
    FINANCIAL_FRAUD = "financial_fraud"
    SAFETY_RISK = "safety_risk"
    OTHER = "other"


class CreateReportRequest(BaseModel):
    reported_user_id: str
    category: ReportCategory
    details: str = Field(min_length=3, max_length=2000)
    evidence_chat_message_id: Optional[str] = None
    trip_id: Optional[str] = None
    outing_id: Optional[str] = None


class ReportSchema(BaseModel):
    id: str
    reporter_id: str
    reported_user_id: str
    category: str
    details: str
    evidence_chat_message_id: Optional[str] = None
    trip_id: Optional[str] = None
    outing_id: Optional[str] = None
    status: str = "pending"  # pending, dismiss, warn, suspend, ban
    resolution_note: Optional[str] = None
    moderator_id: Optional[str] = None
    created_at: str
    updated_at: str


class ModerationActionRequest(BaseModel):
    action: str  # dismiss, warn, suspend, ban
    resolution_note: str


class ModerationQueueItem(BaseModel):
    id: str
    type: str  # user_report, jev_flag
    item: dict
    created_at: str


class SessionInfoSchema(BaseModel):
    token_masked: str
    user_id: str
    created_at: str
    expires_at: Optional[str] = None
    is_revoked: bool = False


class TripSchema(BaseModel):
    id: str
    ping_id: str
    chat_room_id: Optional[str] = None
    plan_version: int = 1
    host: TripParticipantUserSchema
    companion: TripParticipantUserSchema
    destination_name: str
    rendezvous_spot: str
    status: TripStatus
    host_checked_in: bool = False
    companion_checked_in: bool = False
    rendezvous_pin: str  # Generated for each trip; never reuse a schema-level fallback PIN.
    rendezvous_verified: bool = False
    pin_attempts_left: int = 5
    safety_deadline_minutes: int = 45
    items_split: List[TripItemSplit] = []
    total_split_pln: float = 0.0
    created_at: str
    sos_triggered: bool = False
    # Plan specifics (what, when, how long, what it costs) & mutual acceptance
    plan_details: Optional[PlanDetailsSchema] = None
    host_accepted: bool = False
    companion_accepted: bool = False
    plan_accepted_at: Optional[str] = None
    # Easy, low-guilt cancellation
    cancelled_by_id: Optional[str] = None
    cancellation_reason: Optional[str] = None
    cancellation_note: Optional[str] = None
    cancelled_at: Optional[str] = None
    # Post-trip follow-up & mutual buddy connection
    follow_ups: Dict[str, dict] = {}
    is_mutual_buddy: bool = False
    reviews: Dict[str, dict] = Field(default_factory=dict)
    completion_counted: bool = False


def calculate_trip_settlement(trip: TripSchema) -> TripSettlementSchema:
    """Net the two participants' declared 50/50 purchases in whole grosz.

    The payer absorbs an odd grosz on each item. Recompute from payer and price
    rather than trusting stored owe fields from earlier versions of the app.
    """
    companion_owes_host_cents = 0
    for item in trip.items_split:
        price_cents = int(
            (Decimal(str(item.total_price_pln)) * 100).to_integral_value(rounding=ROUND_HALF_UP)
        )
        other_person_share_cents = price_cents // 2
        if item.payer_id == trip.host.id:
            companion_owes_host_cents += other_person_share_cents
        elif item.payer_id == trip.companion.id:
            companion_owes_host_cents -= other_person_share_cents

    if companion_owes_host_cents > 0:
        return TripSettlementSchema(
            debtor_id=trip.companion.id,
            creditor_id=trip.host.id,
            amount_pln=companion_owes_host_cents / 100,
        )
    if companion_owes_host_cents < 0:
        return TripSettlementSchema(
            debtor_id=trip.host.id,
            creditor_id=trip.companion.id,
            amount_pln=-companion_owes_host_cents / 100,
        )
    return TripSettlementSchema()


# Public trip response schema: shields rendezvous_pin from unauthorized/ordinary exposure
class TripResponseSchema(BaseModel):
    id: str
    ping_id: str
    chat_room_id: Optional[str] = None
    plan_version: int = 1
    host: TripParticipantUserSchema
    companion: TripParticipantUserSchema
    destination_name: str
    rendezvous_spot: str
    status: TripStatus
    host_checked_in: bool = False
    companion_checked_in: bool = False
    rendezvous_verified: bool = False
    pin_attempts_left: int = 5
    safety_deadline_minutes: int = 45
    items_split: List[TripItemSplit] = []
    total_split_pln: float = 0.0
    settlement: Optional[TripSettlementSchema] = None
    created_at: str
    sos_triggered: bool = False
    host_pin: Optional[str] = None
    sos_alert: Optional[SosAlertSchema] = None
    # Plan specifics & mutual acceptance
    plan_details: Optional[PlanDetailsSchema] = None
    host_accepted: bool = False
    companion_accepted: bool = False
    plan_accepted_at: Optional[str] = None
    cancelled_by_id: Optional[str] = None
    cancellation_reason: Optional[str] = None
    cancellation_note: Optional[str] = None
    cancelled_at: Optional[str] = None
    follow_ups: Dict[str, dict] = {}
    is_mutual_buddy: bool = False


def to_public_user(user: UserPrivateSchema) -> UserPublicSchema:
    return UserPublicSchema.model_validate(user.model_dump())


def to_trip_participant(user: UserPrivateSchema) -> TripParticipantUserSchema:
    return TripParticipantUserSchema.model_validate(user.model_dump())


def to_trip_response(trip: TripSchema, current_user_id: Optional[str] = None) -> TripResponseSchema:
    data = trip.model_dump()
    data.pop("rendezvous_pin", None)
    if not (
        current_user_id in {trip.host.id, trip.companion.id}
        and trip.host_accepted
        and trip.companion_accepted
    ):
        # Shared/broadcast responses must never include contact details. A
        # participant-specific response may reveal them only after acceptance.
        for participant_key in ("host", "companion"):
            participant = data.get(participant_key)
            if participant:
                participant["phone"] = None
    # Filter follow_ups: only the current user's own entry is visible in shared responses.
    # The other user's unilateral choice, tags, or feedback must not be exposed.
    # Broadcasts (current_user_id=None) must carry no follow-up entries at all;
    # each participant fetches their own authorized view via REST.
    if "follow_ups" in data:
        if current_user_id and current_user_id in {trip.host.id, trip.companion.id}:
            data["follow_ups"] = {
                k: v for k, v in data["follow_ups"].items() if k == current_user_id
            }
        else:
            data["follow_ups"] = {}
    host_pin = trip.rendezvous_pin if (current_user_id and current_user_id == trip.host.id) else None
    settlement = None
    if (
        trip.plan_details
        and trip.plan_details.cost_policy == "split_strictly_50_50"
        and trip.host_accepted
        and trip.companion_accepted
        and trip.items_split
    ):
        settlement = calculate_trip_settlement(trip)
    return TripResponseSchema(**data, host_pin=host_pin, settlement=settlement)


# --- Phase 2: Hotspot & Outing Models ---

class HotspotCreateRequest(BaseModel):
    city: str = Field(default="Katowice", min_length=2, max_length=100)
    name: str = Field(min_length=3, max_length=140)
    category: ActivityCategory = ActivityCategory.LATE_NIGHT
    emoji: str = Field(default="🍔", max_length=16)
    address: str = Field(min_length=3, max_length=200)
    target_time: str = Field(default="23:30 (Dzisiaj)", max_length=80)
    description: str = Field(min_length=3, max_length=500)
    cost_policy: str = Field(default="Każdy płaci za siebie", max_length=100)


class HotspotSpotSchema(BaseModel):
    id: str
    city: str = "Katowice"
    name: str
    category: ActivityCategory
    emoji: str
    address: str
    target_time: str
    description: str
    cost_policy: str
    votes_count: int = 0
    voter_ids: List[str] = []
    voter_avatars: List[str] = []
    threshold: int = 3
    group_formed: bool = False
    outing_id: Optional[str] = None
    created_at: str


class HotspotPublicSchema(BaseModel):
    id: str
    city: str
    name: str
    category: ActivityCategory
    emoji: str
    address: str
    target_time: str
    description: str
    cost_policy: str
    votes_count: int
    voter_avatars: List[str]
    user_voted: bool = False
    user_joined: bool = False
    threshold: int
    group_formed: bool
    outing_id: Optional[str] = None
    created_at: str


class ChatMessageSchema(BaseModel):
    id: str
    chat_room_id: str
    sender_id: str
    sender_name: str
    sender_avatar: str
    text: str
    created_at: str
    sequence: int = 1


class ChatRoomSchema(BaseModel):
    id: str
    scope: str  # "outing" or "trip"
    target_id: str
    participant_ids: List[str] = []
    messages: List[ChatMessageSchema] = []
    created_at: str


class OutingSchema(BaseModel):
    id: str
    hotspot_id: str
    hotspot_name: str
    category: ActivityCategory
    emoji: str
    city: str
    address: str
    participant_ids: List[str] = []
    former_participant_ids: List[str] = []
    participant_avatars: List[str] = []
    chat_room_id: str
    created_at: str


# --- Phase 3 & 4: WebSocket & Jev AI Schemas ---

class WsEventEnvelope(BaseModel):
    version: int = 1
    id: str
    sequence: int
    type: str
    occurred_at: str
    scope: str
    payload: dict


class WaveResponseSchema(BaseModel):
    ping_id: str
    from_user_id: str
    from_user_name: str
    from_user_avatar: str
    message: str
    timestamp: str


class IntentClassificationResult(BaseModel):
    category: ActivityCategory
    intent_tags: List[str]
    confidence_score: float
    suggested_duration_minutes: int
    recommended_group_size: int
    social_context_summary: str
    is_safe: bool = True


class ContentSafetyResult(BaseModel):
    is_safe: bool
    safety_score: float
    flagged_reasons: List[str] = []
    action_recommended: str = "allow"


class RendezvousSuggestion(BaseModel):
    title: str
    description: str
    safety_rating: str
    tip: str


class ClassifyIntentRequest(BaseModel):
    text: str
    category_hint: Optional[ActivityCategory] = None


class ScreenContentRequest(BaseModel):
    text: str


class SuggestRendezvousRequest(BaseModel):
    destination_name: str
    category: ActivityCategory = ActivityCategory.GROCERY


# --- OTP Provider Schemas ---

class OtpRequestSchema(BaseModel):
    identifier: str  # Phone number or email
    invite_code: Optional[str] = Field(default=None, max_length=64)


class OtpRequestResponse(BaseModel):
    status: str
    resend_cooldown_seconds: int = 60
    expires_in_seconds: int = 300
    identifier: str
    dev_code: Optional[str] = None
    error: Optional[str] = None


class OtpVerifySchema(BaseModel):
    identifier: str
    code: str


class SosTriggerRequest(BaseModel):
    user_confirmed: bool  # Strictly required, no default. Explicit true confirmation required.


class SosAlertSchema(BaseModel):
    id: str
    trip_id: str
    triggered_by_id: str
    triggered_by_name: str
    status: str  # "pending", "dispatched", "delivered", "fallback_triggered", "failed"
    delivery_confirmed: bool = False
    dispatched_at: str
    confirmed_at: Optional[str] = None
    emergency_contact: Optional[str] = None
    fallback_112_url: str = "tel:112"
    direct_contact_url: Optional[str] = None
    failure_reason: Optional[str] = None


TripResponseSchema.model_rebuild()
