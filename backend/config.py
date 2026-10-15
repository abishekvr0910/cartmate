import os
import re
from typing import Dict, List, Optional
from pydantic import BaseModel


class CityConfig(BaseModel):
    name: str
    label: str
    lat: float
    lng: float
    voivodeship: str
    is_launch_hub: bool = False


class RegionConfig(BaseModel):
    id: str
    name: str
    voivodeship: str
    center_lat: float
    center_lng: float
    default_radius_km: float
    cities: List[CityConfig]


# --- Launch Boundary: Silesian Voivodeship (Województwo Śląskie) ---
SILESIA_REGION = RegionConfig(
    id="silesia",
    name="Górnośląsko-Zagłębiowska Metropolia (Śląsk)",
    voivodeship="śląskie",
    center_lat=50.2649,
    center_lng=19.0238,
    default_radius_km=35.0,
    cities=[
        CityConfig(name="Katowice", label="Katowice 🏙️", lat=50.2649, lng=19.0238, voivodeship="śląskie", is_launch_hub=True),
        CityConfig(name="Gliwice", label="Gliwice 🏛️", lat=50.2945, lng=18.6714, voivodeship="śląskie", is_launch_hub=True),
        CityConfig(name="Sosnowiec", label="Sosnowiec 🛍️", lat=50.2789, lng=19.1306, voivodeship="śląskie", is_launch_hub=False),
        CityConfig(name="Zabrze", label="Zabrze 🏭", lat=50.3249, lng=18.7857, voivodeship="śląskie", is_launch_hub=False),
        CityConfig(name="Chorzów", label="Chorzów 🌳", lat=50.2975, lng=18.9546, voivodeship="śląskie", is_launch_hub=False),
        CityConfig(name="Tychy", label="Tychy 🌲", lat=50.1261, lng=18.9868, voivodeship="śląskie", is_launch_hub=False),
        CityConfig(name="Bytom", label="Bytom 🏺", lat=50.3480, lng=18.9328, voivodeship="śląskie", is_launch_hub=False),
        CityConfig(name="Dąbrowa Górnicza", label="Dąbrowa Górnicza 🌊", lat=50.3217, lng=19.1947, voivodeship="śląskie", is_launch_hub=False),
    ],
)

# Secondary Polish Metros (Available for expansion)
EXPANSION_REGIONS: Dict[str, RegionConfig] = {
    "mazovia": RegionConfig(
        id="mazovia",
        name="Mazowsze (Warszawa)",
        voivodeship="mazowieckie",
        center_lat=52.2297,
        center_lng=21.0122,
        default_radius_km=30.0,
        cities=[
            CityConfig(name="Warszawa", label="Warszawa 🇵🇱", lat=52.2297, lng=21.0122, voivodeship="mazowieckie", is_launch_hub=True),
        ],
    ),
    "lesser_poland": RegionConfig(
        id="lesser_poland",
        name="Małopolska (Kraków)",
        voivodeship="małopolskie",
        center_lat=50.0647,
        center_lng=19.9450,
        default_radius_km=25.0,
        cities=[
            CityConfig(name="Kraków", label="Kraków 🏰", lat=50.0647, lng=19.9450, voivodeship="małopolskie", is_launch_hub=True),
        ],
    ),
    "lower_silesia": RegionConfig(
        id="lower_silesia",
        name="Dolny Śląsk (Wrocław)",
        voivodeship="dolnośląskie",
        center_lat=51.1079,
        center_lng=17.0385,
        default_radius_km=25.0,
        cities=[
            CityConfig(name="Wrocław", label="Wrocław 🌉", lat=51.1079, lng=17.0385, voivodeship="dolnośląskie", is_launch_hub=True),
        ],
    ),
}

REGIONS_REGISTRY: Dict[str, RegionConfig] = {
    "silesia": SILESIA_REGION,
    **EXPANSION_REGIONS,
}

# --- Runtime Configuration Settings ---
VALID_ENVIRONMENTS = {"development", "staging", "production", "test"}
RAW_CARTMATE_ENV = os.getenv("CARTMATE_ENV")
IS_ENV_EXPLICITLY_SET = RAW_CARTMATE_ENV is not None and bool(RAW_CARTMATE_ENV.strip())

CARTMATE_ENV = (RAW_CARTMATE_ENV.strip().lower() if IS_ENV_EXPLICITLY_SET else "development")
if CARTMATE_ENV not in VALID_ENVIRONMENTS:
    raise ValueError(
        f"Invalid CARTMATE_ENV '{CARTMATE_ENV}'. Must be one of: {', '.join(sorted(VALID_ENVIRONMENTS))}"
    )

# Production remains a closed, invite-only pilot until a reviewed public-launch
# change explicitly removes this gate. Staging can opt in for rehearsal.
PILOT_INVITES_ENABLED = CARTMATE_ENV == "production" or (
    CARTMATE_ENV == "staging"
    and os.getenv("CARTMATE_PILOT_INVITES_ENABLED", "").strip().lower() in {"1", "true", "yes"}
)

DEV_SOS_WEBHOOK_SECRET = "cartmate_sos_webhook_secret_dev"

def assert_deployment_environment(
    env_override: Optional[str] = None,
    webhook_secret_override: Optional[str] = None,
) -> str:
    """
    Asserts that deployment has explicitly configured CARTMATE_ENV as 'staging' or 'production'.
    Prohibits deployed instances from implicitly defaulting to 'development'.
    Also enforces that SOS_WEBHOOK_SECRET is explicitly configured to a unique secret (not development fallback).
    """
    effective_env = (
        env_override.strip().lower()
        if env_override
        else (RAW_CARTMATE_ENV.strip().lower() if IS_ENV_EXPLICITLY_SET else None)
    )
    if not effective_env:
        raise RuntimeError(
            "Deployment failure: CARTMATE_ENV environment variable is not explicitly set. "
            "Deployments must explicitly set CARTMATE_ENV='staging' or CARTMATE_ENV='production'."
        )
    if effective_env not in {"staging", "production"}:
        raise RuntimeError(
            f"Deployment failure: Deployed instances must run in 'staging' or 'production', but got '{effective_env}'. "
            "Implicit fallback to development mode is strictly prohibited."
        )

    # Validate that SOS_WEBHOOK_SECRET is explicitly configured to a unique, non-fallback secret
    secret = (
        webhook_secret_override.strip()
        if webhook_secret_override is not None
        else os.getenv("SOS_WEBHOOK_SECRET", "").strip()
    )
    if not secret or secret == DEV_SOS_WEBHOOK_SECRET or len(secret) < 16:
        raise RuntimeError(
            "Deployment failure: SOS_WEBHOOK_SECRET must be explicitly set to a unique, cryptographically strong secret "
            "(min 16 chars) in staging and production. Using the default development secret is strictly prohibited."
        )

    return effective_env

# Automatic deployment enforcement when CARTMATE_DEPLOYMENT is enabled
IS_DEPLOYED_INSTANCE = os.getenv("CARTMATE_DEPLOYMENT", "").strip().lower() in {"1", "true", "yes"}
if IS_DEPLOYED_INSTANCE:
    assert_deployment_environment()

# A Render web service has a public URL. Keep the staging SMS gateway limited to
# deliberately approved Polish handsets even before an edge access gate exists.
STAGING_ALLOWED_PHONE_NUMBERS = frozenset(
    number.strip()
    for number in os.getenv("CARTMATE_STAGING_ALLOWED_PHONES", "").split(",")
    if number.strip()
)
if IS_DEPLOYED_INSTANCE and CARTMATE_ENV == "staging" and (
    not STAGING_ALLOWED_PHONE_NUMBERS
    or any(not re.fullmatch(r"\+48\d{9}", number) for number in STAGING_ALLOWED_PHONE_NUMBERS)
):
    raise RuntimeError(
        "Deployment failure: CARTMATE_STAGING_ALLOWED_PHONES must contain at least one approved +48 phone number."
    )

CARTMATE_DEFAULT_REGION = os.getenv("CARTMATE_DEFAULT_REGION", "silesia")
MODERATOR_USER_IDS = frozenset(
    value.strip()
    for value in os.getenv("CARTMATE_MODERATOR_USER_IDS", "").split(",")
    if value.strip()
)
# Operator-issued in-person admission for the closed zero-cost staging pilot.
# Strictly staging-only; production remains fail-closed.
OPERATOR_PILOT_ENABLED = (
    CARTMATE_ENV == "staging"
    and os.getenv("CARTMATE_OPERATOR_PILOT_ENABLED", "").strip().lower() in {"1", "true", "yes"}
)
# A named human may attest a live document check for a tiny staging pilot.
# This is never an automatic mObywatel integration and is always off in production.
MANUAL_AGE_PILOT_ENABLED = (
    CARTMATE_ENV == "staging"
    and (PILOT_INVITES_ENABLED or OPERATOR_PILOT_ENABLED)
    and os.getenv("CARTMATE_MANUAL_AGE_PILOT_ENABLED", "").strip().lower() in {"1", "true", "yes"}
)
OTP_PROVIDER = os.getenv("OTP_PROVIDER", "console").strip().lower()  # "console", "smsapi", "twilio"
# Deployed environments ship direct-112-only until recipient consent is implemented.
SOS_PROVIDER = os.getenv("SOS_PROVIDER", "disabled" if CARTMATE_ENV in {"staging", "production"} else "console").strip().lower()
JEV_MODE = os.getenv("JEV_MODE", "shadow").strip().lower()           # "shadow", "enforce", "disabled"

# External Gateway Credentials
SMSAPI_API_TOKEN = os.getenv("SMSAPI_API_TOKEN")
SMSAPI_SENDER = os.getenv("SMSAPI_SENDER", "CartMate")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")
TWILIO_STATUS_CALLBACK_URL = os.getenv("TWILIO_STATUS_CALLBACK_URL")

RAW_SOS_WEBHOOK_SECRET = os.getenv("SOS_WEBHOOK_SECRET")
if CARTMATE_ENV in {"production", "staging"}:
    # In production and staging, if secret is missing or is the dev fallback, fail closed to empty
    if not RAW_SOS_WEBHOOK_SECRET or RAW_SOS_WEBHOOK_SECRET.strip() == DEV_SOS_WEBHOOK_SECRET or len(RAW_SOS_WEBHOOK_SECRET.strip()) < 16:
        SOS_WEBHOOK_SECRET = ""
    else:
        SOS_WEBHOOK_SECRET = RAW_SOS_WEBHOOK_SECRET.strip()
else:
    SOS_WEBHOOK_SECRET = RAW_SOS_WEBHOOK_SECRET.strip() if RAW_SOS_WEBHOOK_SECRET else DEV_SOS_WEBHOOK_SECRET

TYPESAFE_JEV_API_KEY = os.getenv("TYPESAFE_JEV_API_KEY")


def is_production() -> bool:
    """
    Returns True if the application is running in production or staging.
    In production mode:
      - Demo switch-user and demo tokens are strictly rejected
      - Console OTP and console SOS are prohibited
      - Missing gateway credentials fail closed
      - DLR webhooks require valid signatures or secret tokens
    """
    return CARTMATE_ENV in {"production", "staging"}


def get_active_region() -> RegionConfig:
    # Expansion regions are catalog entries, not deployable live markets yet.
    if is_production():
        return SILESIA_REGION
    return REGIONS_REGISTRY.get(CARTMATE_DEFAULT_REGION, SILESIA_REGION)


def is_city_in_launch_boundary(city_name: str) -> bool:
    region = get_active_region()
    return any(c.name.lower() == city_name.strip().lower() for c in region.cities)


# --- Validated Operational Safety & Rate Limiting Thresholds ---

class OperationalThresholds(BaseModel):
    plan_min_duration_minutes: int = 15
    plan_max_duration_minutes: int = 240
    max_pin_attempts: int = 5
    rate_limit_otp_requests_per_15m: int = 5
    rate_limit_otp_verify_attempts_per_15m: int = 5
    rate_limit_chat_messages_per_minute: int = 30
    rate_limit_reports_per_hour: int = 10
    rate_limit_sos_per_10m: int = 3
    rate_limit_pings_per_hour: int = 10
    session_ttl_hours: int = 720
    coarse_location_precision_decimals: int = 2
    max_active_pings_per_user: int = 3

    def validate_plan_duration(self, minutes: int) -> bool:
        return self.plan_min_duration_minutes <= minutes <= self.plan_max_duration_minutes


OPERATIONAL_THRESHOLDS = OperationalThresholds(
    plan_min_duration_minutes=int(os.getenv("PLAN_MIN_DURATION_MINUTES", "15")),
    plan_max_duration_minutes=int(os.getenv("PLAN_MAX_DURATION_MINUTES", "240")),
    max_pin_attempts=int(os.getenv("MAX_PIN_ATTEMPTS", "5")),
    rate_limit_otp_requests_per_15m=int(os.getenv("RATE_LIMIT_OTP_REQUESTS_PER_15M", "5")),
    rate_limit_otp_verify_attempts_per_15m=int(os.getenv("RATE_LIMIT_OTP_VERIFY_ATTEMPTS_PER_15M", "5")),
    rate_limit_chat_messages_per_minute=int(os.getenv("RATE_LIMIT_CHAT_MESSAGES_PER_MINUTE", "30")),
    rate_limit_reports_per_hour=int(os.getenv("RATE_LIMIT_REPORTS_PER_HOUR", "10")),
    rate_limit_sos_per_10m=int(os.getenv("RATE_LIMIT_SOS_PER_10M", "3")),
    rate_limit_pings_per_hour=int(os.getenv("RATE_LIMIT_PINGS_PER_HOUR", "10")),
    session_ttl_hours=int(os.getenv("SESSION_TTL_HOURS", "720")),
    coarse_location_precision_decimals=int(os.getenv("COARSE_LOCATION_PRECISION_DECIMALS", "2")),
    max_active_pings_per_user=int(os.getenv("MAX_ACTIVE_PINGS_PER_USER", "3")),
)
