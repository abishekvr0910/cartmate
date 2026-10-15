import logging
import re
from typing import Tuple
from config import OPERATIONAL_THRESHOLDS

logger = logging.getLogger("cartmate.sanitizer")


def mask_phone(phone: str) -> str:
    """
    Masks phone numbers to protect PII in logs, public profile responses, and notifications.
    E.g. '+48 601 234 567' -> '+48 *** *** 567'
    """
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if len(digits) >= 9:
        last3 = digits[-3:]
        prefix = f"+{digits[:2]} " if len(digits) > 9 else ""
        return f"{prefix}*** *** {last3}"
    return "***"


def mask_email(email: str) -> str:
    """
    Masks email addresses.
    E.g. 'zuzanna.w@example.pl' -> 'z***@example.pl'
    """
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) > 1:
        return f"{local[0]}***@{domain}"
    return f"*@{domain}"


def mask_token(token: str) -> str:
    """
    Masks session tokens.
    E.g. 'cmt_1a2b3c4d5e6f...' -> 'cmt_***...e6f'
    """
    if not token:
        return "***"
    if token.startswith("cmt_") and len(token) > 10:
        return f"cmt_***{token[-4:]}"
    if len(token) > 6:
        return f"{token[:3]}***{token[-3:]}"
    return "***"


def coarse_coordinates(lat: float, lng: float, decimals: int = None) -> Tuple[float, float]:
    """
    Truncates/fuzzes coordinates to prevent micro-tracking of users' private locations.
    With decimals=2, coordinates are rounded to ~1.1 km precision.
    """
    if decimals is None:
        decimals = OPERATIONAL_THRESHOLDS.coarse_location_precision_decimals
    return round(lat, decimals), round(lng, decimals)


class SensitiveDataLogFilter(logging.Filter):
    """
    Logging filter that intercepts log records and scrubs:
      - Polish nine-digit phone numbers, including +48 notation
      - Authorization Bearer tokens & session keys
      - Webhook secret parameters
      - 4-digit / 6-digit verification codes
    """
    PHONE_REGEX = re.compile(r"(?<![A-Za-z0-9])(?:\+?48[\s-]?)?(?:\d[\s-]?){8}\d(?![A-Za-z0-9])")
    OTP_VALUE_REGEX = re.compile(
        r"\b((?:otp[_ -]?code|verification[_ -]?code|code|kod|pin)\s*[:=]\s*['\"]?)(\d{4,6})",
        re.IGNORECASE,
    )
    BEARER_REGEX = re.compile(r"Bearer\s+([a-zA-Z0-9_\-\.]+)", re.IGNORECASE)
    TOKEN_REGEX = re.compile(r"\b(cmt_[a-zA-Z0-9]{10,}|token_[a-zA-Z0-9]{4,})\b")
    WS_TICKET_REGEX = re.compile(r"([?&]ticket=)([^\s&\"']+)", re.IGNORECASE)
    PILOT_INVITE_REGEX = re.compile(r"\bCM-[A-F0-9]{24}\b", re.IGNORECASE)
    SECRET_REGEX = re.compile(r"(secret|token|api_key|password)=([^\s&]+)", re.IGNORECASE)

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            # Format logger arguments before redaction; otherwise secrets passed
            # through logger.info("... %s", secret) bypass this filter.
            msg = record.getMessage()
            msg = self.BEARER_REGEX.sub("Bearer [REDACTED_TOKEN]", msg)
            msg = self.WS_TICKET_REGEX.sub(r"\1[REDACTED_WS_TICKET]", msg)
            msg = self.TOKEN_REGEX.sub("[REDACTED_SESSION_TOKEN]", msg)
            msg = self.PILOT_INVITE_REGEX.sub("[REDACTED_PILOT_INVITE]", msg)
            msg = self.SECRET_REGEX.sub(r"\1=[REDACTED_SECRET]", msg)
            msg = self.PHONE_REGEX.sub("[REDACTED_PHONE]", msg)
            msg = self.OTP_VALUE_REGEX.sub(r"\1[REDACTED_CODE]", msg)
            record.msg = msg
            record.args = ()
        return True


def apply_sanitized_logging():
    root = logging.getLogger()
    filt = SensitiveDataLogFilter()
    for handler in root.handlers:
        if not any(isinstance(existing, SensitiveDataLogFilter) for existing in handler.filters):
            handler.addFilter(filt)
    # Uvicorn configures its own handlers, so root-only filtering misses
    # WebSocket upgrade lines containing one-use ticket query parameters.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        target = logging.getLogger(name)
        if not any(isinstance(existing, SensitiveDataLogFilter) for existing in target.filters):
            target.addFilter(filt)
