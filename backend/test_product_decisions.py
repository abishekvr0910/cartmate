import base64
import hashlib
import hmac
import uuid
import pytest
from fastapi.testclient import TestClient
from main import app, ACTIVE_SESSIONS, DEMO_SESSIONS, SESSION_EXPIRIES, REVOKED_TOKENS
import main
import database
from config import (
    SILESIA_REGION,
    is_city_in_launch_boundary,
    SOS_WEBHOOK_SECRET,
    TWILIO_AUTH_TOKEN,
    TWILIO_STATUS_CALLBACK_URL,
    assert_deployment_environment,
)
from auth_providers import otp_manager
from sos_providers import sos_manager, verify_twilio_signature
from jev_service import jev_service, JevEvaluationService
from storage import storage

client = TestClient(app)

ZUZANNA_TOKEN = "token_zuzanna"
JAKUB_TOKEN = "token_jakub"
ANIA_TOKEN = "token_ania"
AUTH_HEADER_ZUZANNA = {"Authorization": f"Bearer {ZUZANNA_TOKEN}"}
AUTH_HEADER_JAKUB = {"Authorization": f"Bearer {JAKUB_TOKEN}"}
AUTH_HEADER_ANIA = {"Authorization": f"Bearer {ANIA_TOKEN}"}


# --- 1. Regional Launch Boundary: Silesia (Katowice Hub) ---

def test_silesian_launch_market_config():
    res = client.get("/api/config/regions")
    assert res.status_code == 200
    data = res.json()
    assert data["default_region"] == "silesia"
    assert data["active_region"]["id"] == "silesia"
    assert any(c["name"] == "Katowice" and c["is_launch_hub"] for c in data["active_region"]["cities"])
    
    # Check that Silesian cities are within boundary
    city_names = [c["name"].lower() for c in data["active_region"]["cities"]]
    assert "katowice" in city_names
    assert "gliwice" in city_names
    assert "sosnowiec" in city_names
    assert "zabrze" in city_names

    assert is_city_in_launch_boundary("Katowice") is True
    assert is_city_in_launch_boundary("Gliwice") is True
    assert is_city_in_launch_boundary("Nowy Jork") is False


def test_silesian_pilot_rejects_out_of_region_destinations_and_registration():
    payload = {
        "category": "grocery",
        "destination_name": "Outside pilot",
        "destination_lat": 52.2300,
        "destination_lng": 21.0100,
        "address": "Warszawa",
        "intent_tags": [],
        "ttl_minutes": 45,
        "notes": "",
        "women_only": False,
    }
    out_of_region = client.post("/api/pings", headers=AUTH_HEADER_JAKUB, json=payload)
    assert out_of_region.status_code == 422
    assert "region" in out_of_region.json()["detail"]

    invalid_coordinate = client.post(
        "/api/pings",
        headers=AUTH_HEADER_JAKUB,
        json={**payload, "destination_lat": 100},
    )
    assert invalid_coordinate.status_code == 422

    registration = client.post(
        "/api/auth/register",
        json={
            "name": "Pilot outside region",
            "phone": "+48500999888",
            "email": "outside-pilot@example.test",
            "gender": "other",
            "city": "Warszawa",
            "otp_code": "0000",
        },
    )
    assert registration.status_code == 400
    assert "regionie" in registration.json()["detail"]


def test_health_check_silesia_and_providers():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "Silesia" in data["launch_market"]
    assert data["default_city"] == "Katowice"
    assert "providers" in data
    assert "otp" in data["providers"]
    assert "sos" in data["providers"]
    assert "jev_mode" in data["providers"]


def test_launch_readiness_fails_closed_on_missing_real_integrations():
    res = client.get("/api/ready")
    assert res.status_code == 503
    readiness = res.json()
    assert readiness["status"] == "blocked"
    assert readiness["scope"] == "closed_silesia_pilot"
    assert readiness["ordinary_outings_require"] == "sms_verified_phone_and_approved_18_plus_proof"
    assert readiness["age_assurance_available"] is False
    assert readiness["identity_verification_available"] is False
    assert readiness["women_only_outings_available"] is False
    assert readiness["release_approval_required"] is True
    assert any("SMS OTP" in item or "SMSAPI" in item for item in readiness["blockers"])


def test_closed_silesia_operational_readiness_requires_age_assurance_not_id_provider(monkeypatch):
    monkeypatch.setattr(main, "CARTMATE_ENV", "staging")
    monkeypatch.setattr(main, "is_production", lambda: True)
    monkeypatch.setattr(main, "OTP_PROVIDER", "smsapi")
    monkeypatch.setattr(main, "SMSAPI_API_TOKEN", "configured-for-contract-test")
    monkeypatch.setattr(main, "SOS_PROVIDER", "disabled")
    monkeypatch.setattr(main, "SOS_WEBHOOK_SECRET", "configured-for-contract-test")
    monkeypatch.setattr(main, "MODERATOR_USER_IDS", {"usr_zuzanna"})
    monkeypatch.setattr(main, "CARTMATE_DEFAULT_REGION", "silesia")
    monkeypatch.setenv("CARTMATE_DATABASE_PATH", "isolated-contract-test.db")

    ready = client.get("/api/ready")
    assert ready.status_code == 503
    assert ready.json()["status"] == "blocked"
    assert ready.json()["environment"] == "staging"
    assert ready.json()["scope"] == "closed_silesia_pilot"
    assert any("18+" in blocker for blocker in ready.json()["blockers"])
    assert ready.json()["age_assurance_available"] is False
    assert ready.json()["identity_verification_available"] is False
    assert ready.json()["women_only_outings_available"] is False
    assert ready.json()["release_approval_required"] is True


# --- 2. Provider-Backed OTP Authentication Flow ---

def test_otp_request_and_verification_flow():
    test_phone = f"+48500{uuid.uuid4().int % 1_000_000:06d}"

    # Step 1: Request OTP code
    req_res = client.post(
        "/api/auth/otp/request",
        json={"identifier": test_phone},
    )
    assert req_res.status_code == 200
    req_data = req_res.json()
    assert req_data["status"] == "sent"
    assert req_data["resend_cooldown_seconds"] == 60
    assert req_data["expires_in_seconds"] == 300
    assert req_data["identifier"] == test_phone
    dev_code = req_data.get("dev_code")
    assert dev_code is not None
    assert len(dev_code) == 6

    # Step 2: Rate limit / cooldown on immediate re-request
    cooldown_res = client.post(
        "/api/auth/otp/request",
        json={"identifier": test_phone},
    )
    assert cooldown_res.status_code == 429
    assert "Odczekaj" in cooldown_res.json()["detail"]

    # Step 3: Bad code verification fails
    bad_verify = client.post(
        "/api/auth/otp/verify",
        json={"identifier": test_phone, "code": "0000"},
    )
    assert bad_verify.status_code == 400
    assert "Nieprawidłowy" in bad_verify.json()["detail"]

    # Step 4: Correct code verification succeeds and provisions user
    good_verify = client.post(
        "/api/auth/otp/verify",
        json={"identifier": test_phone, "code": dev_code},
    )
    assert good_verify.status_code == 200
    auth_data = good_verify.json()
    assert auth_data["token"].startswith("cmt_")
    assert auth_data["user"]["phone"] == test_phone
    assert auth_data["user"]["city"] == "Katowice"

    # Step 5: Replay protection: cannot reuse the same OTP code
    replay_verify = client.post(
        "/api/auth/otp/verify",
        json={"identifier": test_phone, "code": dev_code},
    )
    assert replay_verify.status_code == 400


# --- 3. Truthful SOS Dispatch & Fallbacks ---

def test_truthful_sos_trigger_and_status():
    trip_id = "trip_makro_01"
    trip = database.TRIPS[trip_id]
    trip.status = database.TripStatus.SCHEDULED
    trip.sos_triggered = False

    # A phone value without recipient consent must not be messaged or exposed.
    database.USERS["usr_zuzanna"].emergency_contact_verified = False
    # Participant (Zuzanna) triggers SOS with explicit consent
    sos_res = client.post(
        f"/api/trips/{trip_id}/sos",
        headers=AUTH_HEADER_ZUZANNA,
        json={"user_confirmed": True},
    )
    assert sos_res.status_code == 200
    trip_data = sos_res.json()
    assert trip_data["status"] == "emergency_sos"
    assert trip_data["sos_triggered"] is True
    assert trip_data["sos_alert"] is not None

    alert = trip_data["sos_alert"]
    assert alert["trip_id"] == trip_id
    assert alert["triggered_by_id"] == "usr_zuzanna"
    # Carrier truthfulness
    assert alert["status"] == "fallback_required"
    assert alert["delivery_confirmed"] is False
    assert alert["emergency_contact"] is None
    assert alert["direct_contact_url"] is None
    assert alert["fallback_112_url"] == "tel:112"
    assert alert["dispatched_at"] is not None

    repeated_sos = client.post(
        f"/api/trips/{trip_id}/sos",
        headers=AUTH_HEADER_ZUZANNA,
        json={"user_confirmed": True},
    )
    assert repeated_sos.status_code == 200
    assert repeated_sos.json()["sos_alert"]["id"] == alert["id"]

    # Step 2: Query SOS status via dedicated status endpoint
    status_res = client.get(
        f"/api/trips/{trip_id}/sos/status",
        headers=AUTH_HEADER_ZUZANNA,
    )
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["id"] == alert["id"]
    assert status_data["fallback_112_url"] == "tel:112"

    # Non-participant (Ania) is forbidden from viewing SOS status
    forbidden_res = client.get(
        f"/api/trips/{trip_id}/sos/status",
        headers=AUTH_HEADER_ANIA,
    )
    assert forbidden_res.status_code == 403


def test_stats_only_report_real_completed_outings(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr("main.database.TRIPS", {
        "completed": SimpleNamespace(status=database.TripStatus.COMPLETED),
        "scheduled": SimpleNamespace(status=database.TripStatus.SCHEDULED),
    })
    response = client.get("/api/stats")
    assert response.status_code == 200
    assert response.json() == {"completed_outings_total": 1}


def test_hotspots_do_not_fall_back_to_another_city():
    response = client.get("/api/hotspots?city=Gdansk")
    assert response.status_code == 200
    assert response.json() == []


def test_emergency_contact_phone_parsing_keeps_full_number():
    from sos_providers import extract_e164_phone

    assert extract_e164_phone("+48 609 888 111 (Siostra Marta)") == "+48609888111"
    assert extract_e164_phone("no phone here") is None


def test_sos_unconfirmed_and_empty_payload_refused():
    trip_id = "trip_makro_01"
    trip = database.TRIPS[trip_id]

    trip.status = database.TripStatus.CANCELLED
    closed_trip_attempt = client.post(
        f"/api/trips/{trip_id}/sos",
        headers=AUTH_HEADER_ZUZANNA,
        json={"user_confirmed": True},
    )
    assert closed_trip_attempt.status_code == 409
    trip.status = database.TripStatus.SCHEDULED

    # 1. Missing request body -> 422 Unprocessable Entity
    res_missing = client.post(
        f"/api/trips/{trip_id}/sos",
        headers=AUTH_HEADER_ZUZANNA,
    )
    assert res_missing.status_code == 422

    # 2. Empty JSON object {} -> 422 Unprocessable Entity (user_confirmed is strictly required)
    res_empty = client.post(
        f"/api/trips/{trip_id}/sos",
        headers=AUTH_HEADER_ZUZANNA,
        json={},
    )
    assert res_empty.status_code == 422

    # 3. Explicit False -> 400 Bad Request
    res_false = client.post(
        f"/api/trips/{trip_id}/sos",
        headers=AUTH_HEADER_ZUZANNA,
        json={"user_confirmed": False},
    )
    assert res_false.status_code == 400
    assert "potwierdzenie" in res_false.json()["detail"].lower()


def test_forged_dlr_rejected_and_authenticated_receipt_updates_status():
    trip_id = "trip_makro_01"
    trip = database.TRIPS[trip_id]
    trip.status = database.TripStatus.SCHEDULED
    trip.sos_triggered = False
    database.USERS["usr_zuzanna"].emergency_contact_verified = True

    # Zuzanna triggers SOS
    sos_res = client.post(
        f"/api/trips/{trip_id}/sos",
        headers=AUTH_HEADER_ZUZANNA,
        json={"user_confirmed": True},
    )
    assert sos_res.status_code == 200
    alert_data = sos_res.json()["sos_alert"]
    assert alert_data["delivery_confirmed"] is False
    assert alert_data["status"] == "dispatched"
    msg_id = alert_data.get("message_id") or alert_data["id"]

    # 1. Forged DLR without secret/signature -> 401 Unauthorized
    forged_res = client.post(
        "/api/sos/delivery-receipt",
        json={"message_id": msg_id, "status": "DELIVERED"},
    )
    assert forged_res.status_code == 401
    assert "Brak autoryzacji webhooka" in forged_res.json()["detail"]

    # 2. Forged DLR with bad secret -> 401 Unauthorized
    bad_sec_res = client.post(
        "/api/sos/delivery-receipt",
        headers={"X-Webhook-Secret": "fraudulent_secret_token"},
        json={"message_id": msg_id, "status": "DELIVERED"},
    )
    assert bad_sec_res.status_code == 401

    # 3. Missing status (never defaults to DELIVERED) -> 400 Bad Request
    no_status_res = client.post(
        "/api/sos/delivery-receipt",
        headers={"X-Webhook-Secret": SOS_WEBHOOK_SECRET},
        json={"message_id": msg_id},
    )
    assert no_status_res.status_code == 400
    assert "status" in no_status_res.json()["detail"]

    # 4. Valid secret webhook receipt -> 200 OK
    valid_res = client.post(
        "/api/sos/delivery-receipt",
        headers={"X-Webhook-Secret": SOS_WEBHOOK_SECRET},
        json={"message_id": msg_id, "status": "DELIVERED"},
    )
    assert valid_res.status_code == 200
    updated_alert = valid_res.json()["alert"]
    assert updated_alert["status"] == "delivered"
    assert updated_alert["delivery_confirmed"] is True
    assert updated_alert["confirmed_at"] is not None

    # 5. Twilio signature verification validation
    webhook_url = "http://testserver/api/sos/delivery-receipt"
    form_params = {"MessageSid": msg_id, "MessageStatus": "delivered"}
    data_str = webhook_url
    for k in sorted(form_params.keys()):
        data_str += f"{k}{form_params[k]}"
    test_auth_token = TWILIO_AUTH_TOKEN or "test_twilio_auth_token"
    mac = hmac.new(test_auth_token.encode("utf-8"), data_str.encode("utf-8"), hashlib.sha1).digest()
    valid_sig = base64.b64encode(mac).decode("utf-8")
    assert verify_twilio_signature(webhook_url, form_params, valid_sig, test_auth_token) is True
    assert verify_twilio_signature(webhook_url, form_params, "fake_signature", test_auth_token) is False


def test_production_mode_rejects_demo_tokens(monkeypatch):
    # Simulate production mode
    monkeypatch.setattr("main.is_production", lambda: True)

    # Demo tokens are strictly rejected in production
    res = client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer token_zuzanna"},
    )
    assert res.status_code == 401

    # Switch user is also blocked in production
    switch_res = client.post("/api/auth/switch-user?user_id=usr_jakub")
    assert switch_res.status_code == 403


def test_production_rejects_email_otp_without_email_provider(monkeypatch):
    monkeypatch.setattr("main.is_production", lambda: True)
    response = client.post("/api/auth/otp/request", json={"identifier": "person@example.pl"})
    assert response.status_code == 400
    assert "numeru telefonu" in response.json()["detail"].lower()


def test_production_verification_endpoints_fail_closed(monkeypatch):
    user_id = "usr_unverified_release_test"
    token = "cmt_unverified_release_test"
    user = database.USERS["usr_ania"].model_copy(update={
        "id": user_id,
        "is_id_verified": False,
        "is_selfie_verified": False,
        "trust_tier": database.TrustTier.BRONZE,
        "instagram_handle": None,
        "instagram_verified": False,
    })
    database.USERS[user_id] = user
    ACTIVE_SESSIONS[token] = user_id
    SESSION_EXPIRIES[token] = "2099-01-01T00:00:00+00:00"
    monkeypatch.setattr(main, "is_production", lambda: True)
    headers = {"Authorization": f"Bearer {token}"}

    try:
        id_result = client.post("/api/users/verify-id", headers=headers)
        social_result = client.post(
            "/api/users/connect-social",
            headers=headers,
            json={"provider": "instagram", "handle": "made-up-profile"},
        )
        assert id_result.status_code == 503
        assert social_result.status_code == 503
        assert user.is_id_verified is False
        assert user.instagram_verified is False
    finally:
        database.USERS.pop(user_id, None)
        ACTIVE_SESSIONS.pop(token, None)
        SESSION_EXPIRIES.pop(token, None)


def test_women_only_pings_require_verified_eligibility(monkeypatch):
    from unittest.mock import AsyncMock

    monkeypatch.setattr(main.ws_manager, "broadcast", AsyncMock())
    payload = {
        "category": "quick",
        "destination_name": "Safe women-only test outing",
        "destination_lat": 50.2649,
        "destination_lng": 19.0238,
        "address": "Public meeting point",
        "ttl_minutes": 30,
        "women_only": True,
    }

    male_host = client.post("/api/pings", headers=AUTH_HEADER_JAKUB, json=payload)
    assert male_host.status_code == 403

    women_ping = client.post("/api/pings", headers=AUTH_HEADER_ZUZANNA, json=payload)
    assert women_ping.status_code == 200
    ping_id = women_ping.json()["id"]
    assert not any(call.args[1] == "ping.created" for call in main.ws_manager.broadcast.await_args_list)

    male_feed = client.get("/api/pings", headers=AUTH_HEADER_JAKUB).json()
    unverified_woman_feed = client.get("/api/pings", headers=AUTH_HEADER_ANIA).json()
    assert not any(item["id"] == ping_id for item in male_feed)
    assert not any(item["id"] == ping_id for item in unverified_woman_feed)
    monkeypatch.setattr(database.USERS["usr_ania"], "is_id_verified", True)
    verified_woman_feed = client.get("/api/pings", headers=AUTH_HEADER_ANIA).json()
    assert any(item["id"] == ping_id for item in verified_woman_feed)
    assert client.post(f"/api/pings/{ping_id}/wave", headers=AUTH_HEADER_JAKUB).status_code == 403
    assert client.post(f"/api/pings/{ping_id}/join", headers=AUTH_HEADER_JAKUB).status_code == 403
    database.PINGS.pop(ping_id, None)
    database.JOIN_REQUESTS.pop(ping_id, None)


def test_expired_sessions_are_rejected(monkeypatch):
    token = "cmt_expired_release_test"
    ACTIVE_SESSIONS[token] = "usr_ania"
    SESSION_EXPIRIES[token] = "2000-01-01T00:00:00+00:00"
    monkeypatch.setattr(main.storage, "revoke_session", lambda _token, _user_id: None)
    try:
        result = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
        assert result.status_code == 401
        assert token not in ACTIVE_SESSIONS
        assert token in REVOKED_TOKENS
    finally:
        ACTIVE_SESSIONS.pop(token, None)
        SESSION_EXPIRIES.pop(token, None)
        REVOKED_TOKENS.discard(token)


def test_phone_login_lookup_is_exact_not_substring():
    user = database.USERS["usr_zuzanna"]
    assert database.find_user_by_identifier(user.phone) is user
    assert database.find_user_by_identifier("601234567") is user
    assert database.find_user_by_identifier(user.phone[-4:]) is None
    assert database.find_user_by_identifier("Zuzanna") is None


def test_registration_requires_verified_otp():
    import uuid
    rand_suffix = uuid.uuid4().hex[:6]
    new_phone = f"+48500{uuid.uuid4().hex[:6]}"[:12]
    new_email = f"nowy.{rand_suffix}@katowice.pl"

    # Step 1: Request OTP code for registration phone
    otp_res = client.post("/api/auth/otp/request", json={"identifier": new_phone})
    assert otp_res.status_code == 200
    dev_code = otp_res.json()["dev_code"]

    # Step 2: Attempt registration with incorrect OTP code -> 401
    bad_reg = client.post(
        "/api/auth/register",
        json={
            "name": "Kamil Katowicki",
            "phone": new_phone,
            "email": new_email,
            "gender": "male",
            "city": "Katowice",
            "otp_code": "0000",
        },
    )
    assert bad_reg.status_code == 401

    # Step 3: Registration with valid OTP code succeeds
    good_reg = client.post(
        "/api/auth/register",
        json={
            "name": "Kamil Katowicki",
            "phone": new_phone,
            "email": new_email,
            "gender": "male",
            "city": "Katowice",
            "otp_code": dev_code,
        },
    )
    assert good_reg.status_code == 200
    reg_data = good_reg.json()
    assert reg_data["user"]["name"] == "Kamil Katowicki"
    assert reg_data["token"].startswith("cmt_")


# --- 4. TypeSafe AI Jev Governance & System One Contract ---

def test_typesafe_jev_systemone_contract_and_presend_sanitization():
    # 1. Pre-send PII scrubbing test:
    raw_sensitive_text = (
        "Cześć, zadzwoń pod +48 601 234 567 lub piotr.nowak@example.pl. "
        "Mieszkam przy ul. Mariackiej 14/2, kod 40-014 Katowice, PESEL 90010112345. "
        "Szukam kogoś na zakupy w Biedronce."
    )
    sanitized = JevEvaluationService.sanitize_for_external_jev(raw_sensitive_text)

    # All sensitive PII stripped BEFORE external transmission
    assert "601 234 567" not in sanitized
    assert "+48" not in sanitized
    assert "piotr.nowak@example.pl" not in sanitized
    assert "90010112345" not in sanitized
    assert "40-014" not in sanitized
    assert "ul. Mariackiej 14/2" not in sanitized

    # Redaction placeholders inserted
    assert "[NUMER_TEL]" in sanitized
    assert "[EMAIL]" in sanitized
    assert "[ID]" in sanitized
    assert "[KOD_POCZTOWY]" in sanitized
    assert "[ADRES]" in sanitized
    assert "Biedronce" in sanitized

    # 2. TypeSafe System One contract audit verification:
    audit_stats = jev_service.get_shadow_audit_stats()
    assert audit_stats["target_model"] == "jev-latest"
    assert audit_stats["endpoint"] == "POST https://api.typesafe.ai/v1/systemone"


def test_jev_shadow_mode_intent_classification():
    # Test intent classification in shadow mode. The audit endpoint is
    # moderator-allowlisted (F02); pin the allowlist for this test so it does
    # not depend on the ambient CARTMATE_MODERATOR_USER_IDS configuration.
    import os

    import main as main_module
    from config import MODERATOR_USER_IDS as _ambient_moderators

    was_set = "CARTMATE_MODERATOR_USER_IDS" in os.environ
    previous = os.environ.get("CARTMATE_MODERATOR_USER_IDS")
    try:
        os.environ["CARTMATE_MODERATOR_USER_IDS"] = "usr_zuzanna"
        main_module.MODERATOR_USER_IDS = frozenset({"usr_zuzanna"})
        _ = _ambient_moderators  # referenced for clarity; allowlist re-pinned below

        res = client.post(
            "/api/ai/classify-intent",
            headers=AUTH_HEADER_ZUZANNA,
            json={"text": "Szukam kogoś do Makro Katowice na zgrzewki wody i sery"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["category"] in ["wholesale", "grocery"]
        assert len(data["intent_tags"]) > 0

        # 1. Unauthenticated shadow audit query fails with 401 Unauthorized
        unauth_audit = client.get("/api/ai/shadow-audit")
        assert unauth_audit.status_code == 401

        # 2. Moderator-allowlisted query succeeds; ordinary members get 403.
        audit_res = client.get("/api/ai/shadow-audit", headers=AUTH_HEADER_JAKUB)
        assert audit_res.status_code == 403, "ordinary members must not read audit entries"
        audit_res = client.get("/api/ai/shadow-audit", headers=AUTH_HEADER_ZUZANNA)
        assert audit_res.status_code == 200
        audit_data = audit_res.json()
        assert audit_data["mode"] == "shadow"
        assert audit_data["total_evaluations"] >= 1
        assert "agreement_rate" in audit_data
        assert "average_latency_ms" in audit_data

        # 3. Privacy check: snippets in audit logs are strictly redacted, and no
        # model decision blobs or free-text summaries are retained (F02).
        for entry in audit_data.get("recent_entries", []):
            assert "[REDACTED_INPUT" in entry["input_snippet"]
            assert "Makro Katowice" not in entry["input_snippet"]
            assert "baseline_decision" not in entry
            assert "jev_decision" not in entry
            assert "baseline_is_safe" in entry
            assert "jev_agreement_status" in entry
    finally:
        if was_set:
            os.environ["CARTMATE_MODERATOR_USER_IDS"] = previous
        else:
            os.environ.pop("CARTMATE_MODERATOR_USER_IDS", None)
        main_module.MODERATOR_USER_IDS = frozenset(
            value
            for value in os.environ.get("CARTMATE_MODERATOR_USER_IDS", "").split(",")
            if value.strip()
        )


def test_jev_content_safety_screening():
    # Safe text
    safe_res = client.post(
        "/api/ai/screen-content",
        headers=AUTH_HEADER_ZUZANNA,
        json={"text": "Cześć, chętnie zrobię z Tobą zakupy w Biedronce przy Mariackiej!"},
    )
    assert safe_res.status_code == 200
    assert safe_res.json()["is_safe"] is True

    # Unsafe text (harassment / inappropriate)
    unsafe_res = client.post(
        "/api/ai/screen-content",
        headers=AUTH_HEADER_ZUZANNA,
        json={"text": "Szukam sponsora na randkę w ciemno płacę kasę"},
    )
    assert unsafe_res.status_code == 200
    assert unsafe_res.json()["is_safe"] is False
    assert len(unsafe_res.json()["flagged_reasons"]) > 0


def test_typesafe_systemone_contract_request_shapes_and_fail_closed_parsing():
    # Choice criteria are a map of option -> description.
    classify_q = JevEvaluationService.build_classify_questions()
    assert "criteria" in classify_q["category"]
    assert "options" not in classify_q["category"]
    assert isinstance(classify_q["category"]["criteria"], dict)
    assert "grocery" in classify_q["category"]["criteria"]

    # Noul criteria are optional, but when present use true/false rubric keys.
    assert classify_q["is_safe"]["type"] == "noul"
    assert set(classify_q["is_safe"]["criteria"]) == {"true", "false"}

    # Score criteria are ordered text descriptions; TypeSafe returns a weighted index.
    assert "criteria" in classify_q["confidence"]
    assert "levels" not in classify_q["confidence"]
    assert len(classify_q["confidence"]["criteria"]) == 5
    assert all(isinstance(level, str) for level in classify_q["confidence"]["criteria"])

    screen_q = JevEvaluationService.build_screen_questions()
    assert screen_q["is_safe"]["type"] == "noul"
    assert set(screen_q["is_safe"]["criteria"]) == {"true", "false"}
    assert "levels" not in screen_q["risk_level"]
    assert len(screen_q["risk_level"]["criteria"]) == 4
    assert all(isinstance(level, str) for level in screen_q["risk_level"]["criteria"])

    # Official response keys and value types: Noul is a numeric probability;
    # Score is a probability-weighted zero-based rubric index.
    valid_official_response = {
        "model": "jev-latest",
        "answers": {
            "category": {"type": "choice", "choice": "grocery", "confidence": 0.98},
            "is_safe": {"type": "noul", "noul": 0.95},
            "confidence": {"type": "score", "score": 4.0},
        },
    }
    parsed = JevEvaluationService.parse_systemone_classify_response(valid_official_response)
    assert parsed["category"] == "grocery"
    assert parsed["is_safe"] is True
    assert parsed["confidence"] == 1.0

    mid_scale_response = {
        "model": "jev-latest",
        "answers": {
            "category": {"choice": "wholesale"},
            "is_safe": {"noul": 0.75},
            "confidence": {"score": 2.0},
        },
    }
    parsed_mid = JevEvaluationService.parse_systemone_classify_response(mid_scale_response)
    assert parsed_mid["confidence"] == 0.5

    # A legitimate zero score must remain zero, not trigger a fallback confidence.
    zero_score_response = {
        "answers": {
            "category": {"choice": "grocery"},
            "is_safe": {"noul": 0.0},
            "confidence": {"score": 0.0},
        },
    }
    parsed_zero = JevEvaluationService.parse_systemone_classify_response(zero_score_response)
    assert parsed_zero["confidence"] == 0.0
    assert parsed_zero["is_safe"] is False

    valid_screen_response = {
        "model": "jev-latest",
        "answers": {
            "is_safe": {"type": "noul", "noul": 0.95},
            "risk_level": {"type": "score", "score": 0.0},
        },
    }
    parsed_screen = JevEvaluationService.parse_systemone_screen_response(valid_screen_response)
    assert parsed_screen["is_safe"] is True
    assert parsed_screen["safety_score"] == 1.0

    high_risk_response = {
        "answers": {
            "is_safe": {"noul": 0.95},
            "risk_level": {"score": 3.0},
        },
    }
    parsed_high_risk = JevEvaluationService.parse_systemone_screen_response(high_risk_response)
    assert parsed_high_risk["is_safe"] is False
    assert parsed_high_risk["safety_score"] == 0.0

    # Malformed contract values, booleans, strings, and out-of-range probabilities fail closed.
    corrupted_cases = [
        {"answers": {}},
        {"answers": {"is_safe": {}}},
        {"answers": {"is_safe": {"noul": None}}},
        {"answers": {"is_safe": {"noul": False}}},
        {"answers": {"is_safe": {"noul": True}}},
        {"answers": {"is_safe": {"noul": 0}}},
        {"answers": {"is_safe": {"noul": 0.4}}},
        {"answers": {"is_safe": {"noul": 1.1}}},
        {"answers": {"is_safe": {"noul": -0.1}}},
        {"answers": {"is_safe": {"noul": "0.95"}}},
        {"answers": {"is_safe": {"result": True}}},  # Old unaligned key must NOT be accepted as safe!
        {"decisions": {"is_safe": {"noul": True}}},   # Response outside 'answers' must fail closed!
        {},
        None,
    ]
    for bad_response in corrupted_cases:
        res_parsed = JevEvaluationService.parse_systemone_classify_response(bad_response)
        assert res_parsed["is_safe"] is False, f"Failed closed check for {bad_response}"

        screen_parsed = JevEvaluationService.parse_systemone_screen_response(bad_response)
        assert screen_parsed["is_safe"] is False, f"Screen failed closed check for {bad_response}"

    invalid_score_response = {
        "answers": {
            "category": {"choice": "grocery"},
            "is_safe": {"noul": 0.95},
            "confidence": {"score": 5.0},  # outside the 0..4 rubric index
        },
    }
    assert JevEvaluationService.parse_systemone_classify_response(invalid_score_response)["confidence"] == 0.0

    invalid_risk_response = {
        "answers": {
            "is_safe": {"noul": 0.95},
            "risk_level": {"score": 4.0},  # outside the 0..3 rubric index
        },
    }
    assert JevEvaluationService.parse_systemone_screen_response(invalid_risk_response)["is_safe"] is False


def test_sos_webhook_secret_header_only_and_query_string_rejected():
    trip_id = "trip_makro_01"
    trip = database.TRIPS[trip_id]
    trip.status = database.TripStatus.SCHEDULED
    trip.sos_triggered = False

    sos_res = client.post(
        f"/api/trips/{trip_id}/sos",
        headers=AUTH_HEADER_ZUZANNA,
        json={"user_confirmed": True},
    )
    assert sos_res.status_code == 200
    alert_info = sos_res.json()["sos_alert"]
    msg_id = alert_info.get("message_id") or alert_info["id"]

    # 1. Query parameter secret is strictly ignored / rejected -> 401 Unauthorized
    query_secret_res = client.post(
        f"/api/sos/delivery-receipt?secret={SOS_WEBHOOK_SECRET}",
        json={"message_id": msg_id, "status": "DELIVERED"},
    )
    assert query_secret_res.status_code == 401
    assert "Brak autoryzacji webhooka" in query_secret_res.json()["detail"]

    # 2. Header X-Webhook-Secret is accepted -> 200 OK
    header_secret_res = client.post(
        "/api/sos/delivery-receipt",
        headers={"X-Webhook-Secret": SOS_WEBHOOK_SECRET},
        json={"message_id": msg_id, "status": "DELIVERED"},
    )
    assert header_secret_res.status_code == 200
    assert header_secret_res.json()["alert"]["delivery_confirmed"] is True


def test_cartmate_env_and_deployment_assertions():
    # 1. Calling assert_deployment_environment with 'development' raises RuntimeError
    with pytest.raises(RuntimeError) as exc_dev:
        assert_deployment_environment("development")
    assert "Implicit fallback to development mode is strictly prohibited" in str(exc_dev.value)

    # 2. Calling with None or invalid raises RuntimeError
    with pytest.raises(RuntimeError):
        assert_deployment_environment("")

    # 3. Explicit 'staging' or 'production' without unique secret raises RuntimeError
    with pytest.raises(RuntimeError) as exc_sec:
        assert_deployment_environment("staging", webhook_secret_override="cartmate_sos_webhook_secret_dev")
    assert "SOS_WEBHOOK_SECRET must be explicitly set to a unique" in str(exc_sec.value)

    # 4. Explicit 'staging' or 'production' with valid unique secret succeeds
    valid_sec = "whsec_live_prod_super_secret_unique_99"
    assert assert_deployment_environment("staging", webhook_secret_override=valid_sec) == "staging"
    assert assert_deployment_environment("production", webhook_secret_override=valid_sec) == "production"

    # 5. Verify /api/config/environment introspection endpoint
    res = client.get("/api/config/environment")
    assert res.status_code == 200
    data = res.json()
    assert "environment" in data
    assert "is_production" in data
    assert "is_explicitly_set" in data
    assert "production" in data["valid_environments"]


def test_durable_storage_and_restart_hydration():
    # 1. Migrations verification
    migrations = storage.get_applied_migrations()
    assert len(migrations) >= 1
    assert migrations[0]["name"] == "initial_core_schema"

    # 2. Persist a new test session directly into storage
    test_token = "cmt_durable_test_token_123"
    test_user_id = "usr_zuzanna"
    storage.persist_session(test_token, test_user_id)

    persisted_sessions = storage.load_sessions()
    assert test_token in persisted_sessions
    assert persisted_sessions[test_token] == test_user_id

    # 3. Simulate process restart hydration
    ACTIVE_SESSIONS.clear()
    assert test_token not in ACTIVE_SESSIONS

    # Hydrate from durable storage and restore DEMO_SESSIONS
    ACTIVE_SESSIONS.update(dict(DEMO_SESSIONS))
    ACTIVE_SESSIONS.update(storage.load_sessions())
    assert test_token in ACTIVE_SESSIONS

    # Clean up test session
    storage.remove_session(test_token)
    assert test_token not in storage.load_sessions()
