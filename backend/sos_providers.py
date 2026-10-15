import asyncio
import base64
import hashlib
import hmac
import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Protocol
import httpx
from config import (
    CARTMATE_ENV,
    SOS_PROVIDER,
    SMSAPI_API_TOKEN,
    SMSAPI_SENDER,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_FROM_NUMBER,
    TWILIO_STATUS_CALLBACK_URL,
    SOS_WEBHOOK_SECRET,
    DEV_SOS_WEBHOOK_SECRET,
    is_production,
)
from storage import storage

logger = logging.getLogger("cartmate.safety.sos")


def extract_e164_phone(value: Optional[str]) -> Optional[str]:
    """Extract a plausible international phone number from a private contact label."""
    if not value:
        return None
    match = re.search(r"(?<!\w)\+?\d[\d\s().-]{6,}\d(?!\w)", value)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(0))
    if not 8 <= len(digits) <= 15:
        return None
    return f"+{digits}"


def verify_twilio_signature(
    webhook_url: str,
    params: dict,
    expected_signature: Optional[str],
    auth_token: Optional[str] = TWILIO_AUTH_TOKEN,
) -> bool:
    """
    Validates Twilio X-Twilio-Signature per Twilio Webhook Security specification:
    1. Take the full request URL as received by the server.
    2. Sort POST parameter keys alphabetically in ASCII order.
    3. Append each key and its value without delimiters onto the end of the URL.
    4. Compute HMAC-SHA1 using TWILIO_AUTH_TOKEN.
    5. Compare base64-encoded digest with X-Twilio-Signature header using constant-time comparison.
    """
    if not expected_signature or not auth_token:
        return False
    data_str = webhook_url
    for key in sorted(params.keys()):
        data_str += f"{key}{params[key]}"
    mac = hmac.new(auth_token.encode("utf-8"), data_str.encode("utf-8"), hashlib.sha1).digest()
    computed_signature = base64.b64encode(mac).decode("utf-8")
    return secrets.compare_digest(computed_signature.strip(), expected_signature.strip())


def verify_webhook_secret(secret_received: Optional[str]) -> bool:
    """
    Validates secret token for internal or SMSAPI webhook callbacks.
    In staging/production, the development fallback secret is strictly prohibited.
    """
    if not secret_received or not SOS_WEBHOOK_SECRET:
        return False
    if is_production() and SOS_WEBHOOK_SECRET == DEV_SOS_WEBHOOK_SECRET:
        logger.error("Security violation: Rejecting webhook callback using default development secret in production/staging.")
        return False
    return secrets.compare_digest(secret_received.strip(), SOS_WEBHOOK_SECRET.strip())


class SosDispatchProvider(Protocol):
    """
    Interface for emergency SOS alert dispatch gateways.
    """
    async def dispatch_alert(self, alert_id: str, recipient_phone: str, text: str) -> dict:
        ...


class DevConsoleSosProvider:
    """
    Deterministic testing and development provider.
    Outputs the urgent alert to structured security logs.
    Never pretends the alert is delivered until an explicit delivery receipt callback is processed.
    """
    async def dispatch_alert(self, alert_id: str, recipient_phone: str, text: str) -> dict:
        if is_production():
            raise RuntimeError("DevConsoleSosProvider is prohibited in production.")
        logger.warning(
            f"[SOS ALERT DISPATCH (DEV)] AlertID={alert_id} Recipient={recipient_phone} Message='{text}'"
        )
        return {
            "dispatched": True,
            "delivered": False,
            "carrier_status": "dispatched_awaiting_receipt",
            "message_id": f"msg_sos_{uuid.uuid4().hex[:8]}",
        }


class SmsApiPlSosProvider:
    """
    Polish SMS gateway (SMSAPI.pl) integration with real HTTP delivery dispatch.
    Fails closed when credentials are missing in production.
    """
    def __init__(self):
        self.api_token = SMSAPI_API_TOKEN
        self.sender_name = SMSAPI_SENDER

    async def dispatch_alert(self, alert_id: str, recipient_phone: str, text: str) -> dict:
        if not self.api_token:
            if is_production():
                raise RuntimeError("SMSAPI_API_TOKEN is not configured for emergency SOS dispatch in production.")
            logger.warning("[SMSAPI.pl SOS DEV] No token. Simulating carrier queue dispatch.")
            return {
                "dispatched": True,
                "delivered": False,
                "carrier_status": "dev_queued_awaiting_receipt",
                "message_id": f"smsapi_{alert_id}",
            }

        clean_phone = recipient_phone.replace("+", "").replace(" ", "").replace("-", "")
        payload = {
            "to": clean_phone,
            "message": text,
            "from": self.sender_name,
            "format": "json",
        }
        headers = {"Authorization": f"Bearer {self.api_token}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post("https://api.smsapi.pl/sms.do", data=payload, headers=headers)
                if resp.status_code != 200:
                    return {
                        "dispatched": False,
                        "delivered": False,
                        "carrier_status": f"http_{resp.status_code}",
                        "error": resp.text,
                    }
                data = resp.json()
                msg_id = data.get("list", [{}])[0].get("id", f"smsapi_{alert_id}")
                return {
                    "dispatched": True,
                    "delivered": False,
                    "carrier_status": "dispatched_awaiting_receipt",
                    "message_id": str(msg_id),
                }
        except Exception as e:
            logger.error(f"[SMSAPI.pl SOS EXCEPTION] {e}")
            return {
                "dispatched": False,
                "delivered": False,
                "carrier_status": "connection_error",
                "error": str(e),
            }


class TwilioSosProvider:
    """
    Twilio Emergency SMS provider using real HTTP REST API.
    Fails closed when credentials are missing in production.
    """
    def __init__(self):
        self.account_sid = TWILIO_ACCOUNT_SID
        self.auth_token = TWILIO_AUTH_TOKEN
        self.from_number = TWILIO_FROM_NUMBER
        self.status_callback_url = TWILIO_STATUS_CALLBACK_URL

    async def dispatch_alert(self, alert_id: str, recipient_phone: str, text: str) -> dict:
        if is_production():
            if not self.account_sid or not self.auth_token:
                raise RuntimeError("Twilio credentials not configured for emergency SOS dispatch in production.")
            if not self.status_callback_url:
                raise RuntimeError("TWILIO_STATUS_CALLBACK_URL must be configured for Twilio emergency SOS dispatch in production.")

        if not self.account_sid or not self.auth_token:
            logger.warning("[Twilio SOS DEV] No credentials. Simulating carrier queue dispatch.")
            return {
                "dispatched": True,
                "delivered": False,
                "carrier_status": "dev_queued_awaiting_receipt",
                "message_id": f"twilio_{alert_id}",
            }

        if not self.from_number:
            if is_production():
                raise RuntimeError("TWILIO_FROM_NUMBER is not configured for emergency SOS dispatch.")
            return {
                "dispatched": False,
                "delivered": False,
                "carrier_status": "missing_sender_number",
                "error": "TWILIO_FROM_NUMBER is not configured.",
            }

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = {
            "To": recipient_phone,
            "From": self.from_number,
            "Body": text,
        }
        if self.status_callback_url:
            data["StatusCallback"] = self.status_callback_url
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, data=data, auth=(self.account_sid, self.auth_token))
                if resp.status_code not in [200, 201]:
                    return {
                        "dispatched": False,
                        "delivered": False,
                        "carrier_status": f"http_{resp.status_code}",
                        "error": resp.text,
                    }
                data = resp.json()
                return {
                    "dispatched": True,
                    "delivered": False,
                    "carrier_status": data.get("status", "dispatched"),
                    "message_id": data.get("sid", f"twilio_{alert_id}"),
                }
        except Exception as e:
            logger.error(f"[Twilio SOS EXCEPTION] {e}")
            return {
                "dispatched": False,
                "delivered": False,
                "carrier_status": "connection_error",
                "error": str(e),
            }


def get_sos_provider() -> SosDispatchProvider:
    p = SOS_PROVIDER.lower().strip()
    if p == "disabled":
        raise RuntimeError("SMS SOS dispatch is disabled; use direct 112 voice calling.")
    if p == "smsapi":
        return SmsApiPlSosProvider()
    elif p == "twilio":
        return TwilioSosProvider()
    elif p == "console":
        if is_production():
            raise RuntimeError("Console SOS provider is forbidden in production mode. Configure 'smsapi' or 'twilio'.")
        return DevConsoleSosProvider()
    raise ValueError(f"Unknown SOS provider: '{p}'")


class SosAlertRecord:
    def __init__(
        self,
        id: str,
        trip_id: str,
        triggered_by_id: str,
        triggered_by_name: str,
        emergency_contact: Optional[str],
        destination_name: str,
    ):
        self.id = id
        self.trip_id = trip_id
        self.triggered_by_id = triggered_by_id
        self.triggered_by_name = triggered_by_name
        self.emergency_contact = emergency_contact
        self.destination_name = destination_name
        self.status = "pending"  # pending, dispatched, delivered, fallback_required, fallback_triggered, failed
        self.delivery_confirmed = False
        self.dispatched_at = datetime.now(timezone.utc).isoformat()
        self.confirmed_at: Optional[str] = None
        self.fallback_112_url = "tel:112"
        parsed_phone = extract_e164_phone(emergency_contact)
        self.direct_contact_url = f"tel:{parsed_phone}" if parsed_phone else None
        self.failure_reason: Optional[str] = None
        self.message_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "trip_id": self.trip_id,
            "triggered_by_id": self.triggered_by_id,
            "triggered_by_name": self.triggered_by_name,
            "status": self.status,
            "delivery_confirmed": self.delivery_confirmed,
            "dispatched_at": self.dispatched_at,
            "confirmed_at": self.confirmed_at,
            "emergency_contact": self.emergency_contact,
            "fallback_112_url": self.fallback_112_url,
            "direct_contact_url": self.direct_contact_url,
            "failure_reason": self.failure_reason,
            "message_id": self.message_id,
        }


class SosManager:
    """
    Coordinates emergency alert dispatches with strict truthfulness.
    Never asserts delivery unless confirmed by provider receipt.
    Never attempts SMS to 112 (which is invalid in Polish telecommunications).
    """
    def __init__(self):
        self._alerts: Dict[str, SosAlertRecord] = {}
        self._trip_to_alert: Dict[str, str] = {}
        self._message_to_alert: Dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._load_from_storage()

    def _load_from_storage(self):
        try:
            persisted = storage.load_sos_records()
            for rec_id, rdata in persisted.items():
                record = SosAlertRecord(
                    id=rec_id,
                    trip_id=rdata.get("trip_id", ""),
                    triggered_by_id=rdata.get("triggered_by_id", ""),
                    triggered_by_name=rdata.get("triggered_by_name", ""),
                    emergency_contact=rdata.get("emergency_contact"),
                    destination_name=rdata.get("destination_name", ""),
                )
                record.status = rdata.get("status", "pending")
                record.delivery_confirmed = rdata.get("delivery_confirmed", False)
                record.dispatched_at = rdata.get("dispatched_at", record.dispatched_at)
                record.confirmed_at = rdata.get("confirmed_at")
                record.failure_reason = rdata.get("failure_reason")
                record.message_id = rdata.get("message_id")
                self._alerts[rec_id] = record
                if record.trip_id:
                    self._trip_to_alert[record.trip_id] = rec_id
                if record.message_id:
                    self._message_to_alert[record.message_id] = rec_id
        except Exception as e:
            logger.warning(f"Error hydrating SOS records from durable storage: {e}")

    async def trigger_sos(
        self,
        trip_id: str,
        user_id: str,
        user_name: str,
        destination_name: str,
        emergency_contact: Optional[str],
        emergency_contact_verified: bool,
        consent_confirmed: bool,
    ) -> dict:
        if not consent_confirmed:
            return {
                "success": False,
                "error": "Wymagane jest jawne potwierdzenie uruchomienia alertu ratunkowego (consent_confirmed=True).",
            }

        alert_id = f"sos_{uuid.uuid4().hex[:8]}"
        # A contact value alone is not evidence that its recipient consented to receive SOS alerts.
        # Until a real confirmation flow exists, do not expose or dispatch to unverified contacts.
        # Until recipient-consent verification exists, deployed environments can
        # never dispatch an SMS, even if imported data claims a contact is verified.
        sms_dispatch_disabled = is_production() or SOS_PROVIDER == "disabled"
        eligible_contact = emergency_contact if emergency_contact_verified and not sms_dispatch_disabled else None
        record = SosAlertRecord(
            id=alert_id,
            trip_id=trip_id,
            triggered_by_id=user_id,
            triggered_by_name=user_name,
            emergency_contact=eligible_contact,
            destination_name=destination_name,
        )

        async with self._lock:
            self._alerts[alert_id] = record
            self._trip_to_alert[trip_id] = alert_id

        # If no emergency contact is configured, DO NOT send SMS to 112 (112 does not receive commercial SMS)
        if not eligible_contact or not eligible_contact.strip():
            record.status = "fallback_required"
            record.failure_reason = (
                "Powiadomienia SMS SOS są wyłączone. Zadzwoń bezpośrednio pod numer alarmowy 112."
                if sms_dispatch_disabled
                else "Brak zweryfikowanej zgody kontaktu alarmowego. Zadzwoń bezpośrednio pod numer alarmowy 112."
            )
            storage.persist_sos_record(record.to_dict())
            return record.to_dict()

        recipient_phone = extract_e164_phone(eligible_contact)
        if not recipient_phone:
            record.status = "fallback_required"
            record.failure_reason = "Nie można bezpiecznie odczytać numeru kontaktu. Zadzwoń bezpośrednio pod numer alarmowy 112."
            storage.persist_sos_record(record.to_dict())
            return record.to_dict()
        sms_body = (
            f"PILNE: CartMate SOS! Użytkownik {user_name} uruchomił alert ratunkowy podczas wyjścia do: "
            f"{destination_name}. Skontaktuj się lub zadzwoń pod 112."
        )

        provider = get_sos_provider()
        try:
            result = await provider.dispatch_alert(alert_id, recipient_phone, sms_body)
            if result.get("dispatched"):
                record.status = "dispatched"
                record.message_id = result.get("message_id")
                if record.message_id:
                    async with self._lock:
                        self._message_to_alert[record.message_id] = alert_id
            else:
                record.status = "fallback_triggered"
                record.failure_reason = result.get("error", "Brak potwierdzenia wysłania przez bramkę SMS.")
        except Exception as e:
            logger.error(f"SOS dispatch failure: {e}")
            record.status = "fallback_triggered"
            record.failure_reason = str(e)

        storage.persist_sos_record(record.to_dict())
        return record.to_dict()

    async def process_delivery_receipt(self, message_id: str, carrier_status: str) -> Optional[dict]:
        """
        Processes verified carrier delivery receipts (e.g. via SMSAPI or Twilio webhook callback).
        Only updates delivery_confirmed to True when confirmed by the carrier network.
        """
        async with self._lock:
            alert_id = self._message_to_alert.get(message_id)
            if not alert_id:
                # Fallback: check if message_id matches alert_id directly
                record = self._alerts.get(message_id)
            else:
                record = self._alerts.get(alert_id)

            if not record:
                return None

            now = datetime.now(timezone.utc)
            status_norm = carrier_status.strip().upper()
            if status_norm in ["DELIVERED", "CONFIRMED", "SUCCESS"]:
                record.delivery_confirmed = True
                record.status = "delivered"
                record.confirmed_at = now.isoformat()
            elif status_norm in ["UNDELIVERED", "FAILED", "REJECTED"]:
                record.status = "failed"
                record.failure_reason = f"Raport doręczenia operatora: {carrier_status}"
            else:
                record.status = "dispatched"

            storage.persist_sos_record(record.to_dict())
            return record.to_dict()

    def get_alert_by_trip(self, trip_id: str) -> Optional[dict]:
        alert_id = self._trip_to_alert.get(trip_id)
        if not alert_id:
            return None
        record = self._alerts.get(alert_id)
        return record.to_dict() if record else None


# Global singleton instance
sos_manager = SosManager()
