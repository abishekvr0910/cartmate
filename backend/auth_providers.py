import logging
import secrets
from typing import Optional, Protocol
import httpx
from storage import DurableStorage, storage
from config import (
    CARTMATE_ENV,
    OTP_PROVIDER,
    SMSAPI_API_TOKEN,
    SMSAPI_SENDER,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_FROM_NUMBER,
    is_production,
)

logger = logging.getLogger("cartmate.auth.otp")


class OtpProvider(Protocol):
    """
    Interface for replaceable SMS / Email OTP providers.
    """
    async def send_otp(self, identifier: str, code: str) -> bool:
        ...


class DevConsoleOtpProvider:
    """
    Development & Testing provider.
    Development returns the code only in the explicit API dev_code field.
    Strictly forbidden in production mode.
    """
    async def send_otp(self, identifier: str, code: str) -> bool:
        if is_production():
            raise RuntimeError("Console OTP provider is forbidden in production.")
        logger.info("[OTP DISPATCH (DEV)] TTL=5m Mode=%s", CARTMATE_ENV)
        return True


class SmsApiPlOtpProvider:
    """
    Polish SMS provider (SMSAPI.pl) integration using real HTTP REST API.
    Designed for production deployment in Poland.
    Fails closed when credentials are missing or gateway rejects the dispatch.
    """
    def __init__(self):
        self.api_token = SMSAPI_API_TOKEN
        self.sender_name = SMSAPI_SENDER

    async def send_otp(self, identifier: str, code: str) -> bool:
        if not self.api_token:
            if is_production():
                logger.error("[SMSAPI.pl FAIL-CLOSED] No API token configured in production.")
                raise RuntimeError("SMSAPI_API_TOKEN is not configured in production mode. Gateway dispatch failed.")
            logger.warning("[SMSAPI.pl DEV] No API token configured. Simulating console dispatch.")
            logger.info("[SMSAPI.pl SIMULATED] OTP dispatch skipped without credentials")
            return True

        clean_phone = identifier.replace("+", "").replace(" ", "").replace("-", "")
        payload = {
            "to": clean_phone,
            "message": f"Twój jednorazowy kod weryfikacyjny CartMate: {code}",
            "from": self.sender_name,
            "format": "json",
        }
        headers = {"Authorization": f"Bearer {self.api_token}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post("https://api.smsapi.pl/sms.do", data=payload, headers=headers)
                if resp.status_code != 200:
                    logger.error("[SMSAPI.pl ERROR] Status=%s", resp.status_code)
                    return False
                data = resp.json()
                if "error" in data:
                    logger.error("[SMSAPI.pl ERROR] Gateway returned an error")
                    return False
                logger.info("[SMSAPI.pl SUCCESS] OTP accepted by gateway")
                return True
        except Exception as e:
            logger.error("[SMSAPI.pl EXCEPTION] %s", type(e).__name__)
            if is_production():
                raise
            return False


class TwilioOtpProvider:
    """
    Twilio SMS provider integration using real HTTP REST API.
    Fails closed when credentials are missing or gateway rejects the dispatch.
    """
    def __init__(self):
        self.account_sid = TWILIO_ACCOUNT_SID
        self.auth_token = TWILIO_AUTH_TOKEN
        self.from_number = TWILIO_FROM_NUMBER

    async def send_otp(self, identifier: str, code: str) -> bool:
        if not self.account_sid or not self.auth_token:
            if is_production():
                logger.error("[Twilio FAIL-CLOSED] Credentials not configured in production.")
                raise RuntimeError("Twilio credentials not configured in production mode.")
            logger.warning("[Twilio DEV] No credentials configured. Simulating console dispatch.")
            logger.info("[Twilio SIMULATED] OTP dispatch skipped without credentials")
            return True

        if not self.from_number:
            logger.error("[Twilio FAIL-CLOSED] TWILIO_FROM_NUMBER is not configured.")
            if is_production():
                raise RuntimeError("TWILIO_FROM_NUMBER is not configured.")
            return False

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = {
            "To": identifier,
            "From": self.from_number,
            "Body": f"Twój kod weryfikacyjny CartMate: {code}",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, data=data, auth=(self.account_sid, self.auth_token))
                if resp.status_code not in [200, 201]:
                    logger.error("[Twilio ERROR] Status=%s", resp.status_code)
                    return False
                logger.info("[Twilio SUCCESS] OTP accepted by gateway")
                return True
        except Exception as e:
            logger.error("[Twilio EXCEPTION] %s", type(e).__name__)
            if is_production():
                raise
            return False


def get_otp_provider() -> OtpProvider:
    provider_name = OTP_PROVIDER.lower().strip()
    if provider_name == "smsapi":
        return SmsApiPlOtpProvider()
    elif provider_name == "twilio":
        return TwilioOtpProvider()
    elif provider_name == "console":
        if is_production():
            raise RuntimeError("Console OTP provider is forbidden in production mode. Configure 'smsapi' or 'twilio'.")
        return DevConsoleOtpProvider()
    raise ValueError(f"Unknown OTP provider: '{provider_name}'")


class OtpManager:
    """Durable, single-use SMS codes with restart-safe abuse limits."""

    def __init__(self, otp_storage: Optional[DurableStorage] = None):
        self._storage = otp_storage or storage

    async def request_otp(self, raw_identifier: str) -> dict:
        identifier = raw_identifier.strip().lower()
        code = f"{secrets.randbelow(900_000) + 100_000}"
        reserved = self._storage.reserve_otp_challenge(identifier, code)
        if reserved["status"] == "rate_limited":
            retry_after = reserved["retry_after"]
            return {
                "status": "rate_limited",
                "error": f"Odczekaj {retry_after}s przed ponownym wysłaniem kodu.",
                "resend_cooldown_seconds": retry_after,
            }

        try:
            sent = await get_otp_provider().send_otp(identifier, code)
        except Exception as error:
            # Gateway exception text and response bodies may contain phone
            # numbers, message content, or provider credentials.
            logger.error("OTP dispatch failed: %s", type(error).__name__)
            sent = False
        if not sent:
            self._storage.discard_otp_challenge(identifier, code)
            return {
                "status": "failed",
                "error": "Błąd wysyłania wiadomości SMS przez bramkę operatora.",
            }

        return {
            "status": "sent",
            "resend_cooldown_seconds": 60,
            "expires_in_seconds": 300,
            "identifier": identifier,
            "dev_code": code if (CARTMATE_ENV == "development" and OTP_PROVIDER == "console") else None,
        }

    async def verify_otp(self, raw_identifier: str, raw_code: str) -> dict:
        identifier = raw_identifier.strip().lower()
        code = raw_code.strip()

        # Existing local-only fixture bypass; never available in deployment.
        if CARTMATE_ENV == "development" and OTP_PROVIDER == "console" and code == "1234":
            self._storage.invalidate_otp_challenge(identifier)
            return {"valid": True, "reason": "dev_console_bypass"}

        result = self._storage.consume_otp_challenge(identifier, code)
        outcome = result["status"]
        if outcome == "verified":
            return {"valid": True, "reason": "verified"}
        if outcome == "locked":
            return {
                "valid": False,
                "error": "Przekroczono limit prób weryfikacji. Spróbuj ponownie później.",
                "retry_after": result["retry_after"],
            }
        if outcome == "expired":
            return {
                "valid": False,
                "error": "Kod weryfikacyjny wygasł (ważność 5 minut). Wyślij nowy kod.",
            }
        if outcome == "missing":
            return {
                "valid": False,
                "error": "Brak aktywnego kodu weryfikacyjnego. Kliknij 'Wyślij kod SMS'.",
            }
        return {
            "valid": False,
            "error": f"Nieprawidłowy kod weryfikacyjny. Pozostało prób: {result['attempts_left']}.",
            "attempts_left": result["attempts_left"],
        }


# Global singleton instance
otp_manager = OtpManager()
