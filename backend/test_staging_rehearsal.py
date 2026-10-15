"""Cold-process staging contract checks against a clean, isolated SQLite file.

No network SMS is sent: one probe verifies missing credentials fail closed, while
the other injects a capture-only OTP adapter to exercise authentication semantics.
"""

import os
import secrets
import subprocess
import sys
import importlib.util
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parent


def test_operator_otp_runner_requires_https_and_explicit_sms_opt_in(monkeypatch):
    runner_path = BACKEND_DIR.parent / "staging" / "otp_rehearsal.py"
    spec = importlib.util.spec_from_file_location("cartmate_staging_otp_rehearsal", runner_path)
    assert spec and spec.loader
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)

    with pytest.raises(ValueError, match="HTTPS staging origin"):
        runner.validate_target("http://staging.example.invalid", "+48600111002")
    with pytest.raises(ValueError, match="approved Polish test number"):
        runner.validate_target("https://staging.example.invalid", "1234")
    assert runner.validate_target("https://staging.example.invalid/", "+48600111002") == "https://staging.example.invalid"
    assert runner.validate_otp_code("123456") == "123456"
    assert runner.validate_otp_code(runner.IMPOSSIBLE_OTP_CODE) == "000000"
    with pytest.raises(ValueError, match="six-digit code"):
        runner.validate_otp_code("1234")

    monkeypatch.setattr(runner, "call_api", lambda *args, **kwargs: pytest.fail("Network must not be used without opt-in"))
    monkeypatch.setattr(sys, "argv", [
        "otp_rehearsal.py", "--base-url", "https://staging.example.invalid",
        "--test-phone", "+48600111002",
    ])
    assert runner.main() == 1


def test_read_only_staging_preflight_checks_auth_and_launch_gate(monkeypatch):
    preflight_path = BACKEND_DIR.parent / "staging" / "preflight.py"
    spec = importlib.util.spec_from_file_location("cartmate_staging_preflight", preflight_path)
    assert spec and spec.loader
    preflight = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preflight)

    with pytest.raises(ValueError, match="HTTPS staging origin"):
        preflight.validate_origin("http://staging.example.invalid")
    assert preflight.validate_origin("https://staging.example.invalid/") == "https://staging.example.invalid"

    calls = []
    provider = "smsapi"

    def fake_get_json(origin, path, token=None):
        calls.append((origin, path, token))
        if path == "/api/health":
            return 200, {"environment": "staging", "providers": {"otp": provider, "sos": "disabled"}}
        if path == "/api/config/regions":
            return 200, {"active_region": {"id": "silesia"}}
        if path == "/api/ready":
            return 503, {"status": "blocked", "blockers": ["Human moderator missing"]}
        return 401, {}

    monkeypatch.setattr(preflight, "get_json", fake_get_json)
    assert preflight.run_checks("https://staging.example.invalid") == ["Human moderator missing"]
    assert ("https://staging.example.invalid", "/api/users/me", "token_jakub") in calls

    provider = "twilio"
    assert preflight.run_checks("https://staging.example.invalid") == ["Human moderator missing"]
    provider = "console"
    with pytest.raises(RuntimeError, match="carrier-backed OTP"):
        preflight.run_checks("https://staging.example.invalid")
    provider = "smsapi"

    def insecure_get_json(origin, path, token=None):
        if path == "/api/pings":
            return 200, {}
        return fake_get_json(origin, path, token)

    monkeypatch.setattr(preflight, "get_json", insecure_get_json)
    with pytest.raises(RuntimeError, match="Protected path"):
        preflight.run_checks("https://staging.example.invalid")


def run_staging_probe(
    tmp_path: Path,
    script: str,
    sos_provider: str | None = "disabled",
    extra_env: dict[str, str] | None = None,
) -> None:
    env = os.environ.copy()
    env.update({
        "CARTMATE_ENV": "staging",
        "CARTMATE_DEPLOYMENT": "1",
        "CARTMATE_DATABASE_PATH": str(tmp_path / "clean_staging.db"),
        "CARTMATE_CORS_ALLOWED_ORIGINS": "https://staging.cartmate.example",
        "CARTMATE_MODERATOR_USER_IDS": "",
        "CARTMATE_STAGING_ALLOWED_PHONES": "+48600111001,+48600111002",
        "OTP_PROVIDER": "smsapi",
        "SMSAPI_API_TOKEN": "",
        "TWILIO_ACCOUNT_SID": "",
        "TWILIO_AUTH_TOKEN": "",
        "TWILIO_FROM_NUMBER": "",
        "SOS_WEBHOOK_SECRET": secrets.token_urlsafe(24),
        "CARTMATE_DEFAULT_REGION": "silesia",
    })
    if extra_env:
        env.update(extra_env)
    if sos_provider is None:
        env.pop("SOS_PROVIDER", None)
    else:
        env["SOS_PROVIDER"] = sos_provider
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, f"Cold staging probe failed:\n{result.stdout}\n{result.stderr}"


@pytest.mark.parametrize("sos_provider", [None, "disabled", "twilio"])
def test_staging_missing_gateway_and_sos_policy_fail_closed(tmp_path, sos_provider):
    run_staging_probe(tmp_path, """
import asyncio
from fastapi.testclient import TestClient
import database
import main
from sos_providers import sos_manager

client = TestClient(main.app)
health = client.get('/api/health')
assert health.status_code == 200
assert health.json()['environment'] == 'staging'
assert health.json()['stats']['users'] == 0
assert database.USERS == {}

ready = client.get('/api/ready')
assert ready.status_code == 503
blockers = ready.json()['blockers']
assert ready.json()['scope'] == 'closed_silesia_pilot'
assert ready.json()['identity_verification_available'] is False
assert ready.json()['women_only_outings_available'] is False
assert any('SMS OTP' in item or 'SMSAPI' in item for item in blockers)
if health.json()['providers']['sos'] == 'disabled':
    assert not any('SMS SOS dispatch' in item for item in blockers)
else:
    assert any('SMS SOS dispatch' in item for item in blockers)

assert client.get('/api/users/me', headers={'Authorization': 'Bearer token_jakub'}).status_code == 401
assert client.get('/api/users/all').status_code == 401
assert client.get('/api/pings').status_code == 401
assert client.get('/api/hotspots?city=Katowice').status_code == 401
otp = client.post('/api/auth/otp/request', json={'identifier': '+48600111001'})
assert otp.status_code == 503
assert 'dev_code' not in otp.json()
assert client.post('/api/auth/otp/request', json={'identifier': '+48600999999'}).status_code == 403
assert client.post('/api/auth/otp/verify', json={'identifier': '+48600999999', 'code': '1234'}).status_code == 403
assert client.post('/api/auth/login', json={'identifier': '+48600999999', 'code': '1234'}).status_code == 403
assert client.post('/api/auth/register', json={
    'name': 'Unapproved', 'phone': '+48600999999', 'email': 'blocked@example.invalid',
    'gender': 'unspecified', 'city': 'Katowice', 'otp_code': '1234'
}).status_code == 403
assert database.USERS == {}

alert = asyncio.run(sos_manager.trigger_sos(
    trip_id='staging_contract_trip', user_id='staging_user', user_name='Test',
    destination_name='Katowice', emergency_contact='+48600111222',
    emergency_contact_verified=True, consent_confirmed=True,
))
assert alert['status'] == 'fallback_required'
assert alert['delivery_confirmed'] is False
assert alert['emergency_contact'] is None
assert alert['direct_contact_url'] is None
assert alert['fallback_112_url'] == 'tel:112'
if health.json()['providers']['sos'] == 'disabled':
    assert client.post('/api/sos/delivery-receipt', json={}).status_code == 404

allowed = client.options('/api/users/me', headers={
    'Origin': 'https://staging.cartmate.example',
    'Access-Control-Request-Method': 'GET',
})
assert allowed.headers.get('access-control-allow-origin') == 'https://staging.cartmate.example'
denied = client.options('/api/users/me', headers={
    'Origin': 'https://untrusted.example',
    'Access-Control-Request-Method': 'GET',
})
assert denied.headers.get('access-control-allow-origin') is None
""", sos_provider=sos_provider)


def test_staging_captured_otp_session_and_authorization_contract(tmp_path):
    run_staging_probe(tmp_path, """
from fastapi.testclient import TestClient
import auth_providers

captured = {}
class CaptureOnlyOtpProvider:
    async def send_otp(self, identifier, code):
        captured[identifier] = code
        return True
auth_providers.get_otp_provider = lambda: CaptureOnlyOtpProvider()

import main
import database
from storage import storage
client = TestClient(main.app)
phone = '+48600111002'
assert client.post('/api/auth/otp/request', json={'identifier': '+48600999999'}).status_code == 403
assert captured == {}
requested = client.post('/api/auth/otp/request', json={'identifier': phone})
assert requested.status_code == 200
assert requested.json()['status'] == 'sent'
assert requested.json()['dev_code'] is None
assert phone in captured

wrong = client.post('/api/auth/otp/verify', json={'identifier': phone, 'code': '0000'})
assert wrong.status_code == 400
verified = client.post('/api/auth/otp/verify', json={'identifier': phone, 'code': captured[phone]})
assert verified.status_code == 200
token = verified.json()['token']
assert token.startswith('cmt_')
assert verified.json()['user']['phone'] == phone
assert verified.json()['user']['phone_verified_at']
assert verified.json()['user']['email'].endswith('@cartmate.invalid')
assert phone[-6:] not in verified.json()['user']['email']
headers = {'Authorization': f'Bearer {token}'}
assert client.get('/api/users/me', headers=headers).status_code == 200
assert client.get('/api/pings', headers=headers).status_code == 403
assert client.post('/api/auth/ws-ticket', headers=headers).status_code == 403
main.AGE_ASSURANCE_TRUSTED_PROVIDERS = frozenset({'qa-contract'})
member = database.find_user_by_identifier(phone)
member.age_assurance_provider = 'qa-contract'
member.adult_verified_at = '2026-01-01T00:00:00+00:00'
member.adult_verification_expires_at = '2099-01-01T00:00:00+00:00'
storage.persist_user(member.model_dump())
public_users = client.get('/api/users/all', headers=headers)
assert public_users.status_code == 200
assert all('phone_verified_at' not in user for user in public_users.json())
assert client.get('/api/pings', headers=headers).status_code == 200
assert client.get('/api/hotspots?city=Katowice', headers=headers).status_code == 200
assert client.get('/api/moderation/queue', headers=headers).status_code == 403
assert client.post('/api/users/verify-id', headers=headers).status_code == 503
assert client.post('/api/auth/switch-user?user_id=usr_jakub', headers=headers).status_code == 403

original_verify = main.otp_manager.verify_otp
verified_identifiers = []
async def email_only_code(identifier, code):
    verified_identifiers.append(identifier)
    return {'valid': identifier == 'email-only@example.invalid'}
main.otp_manager.verify_otp = email_only_code
email_only_registration = client.post('/api/auth/register', json={
    'name': 'Email-only account', 'phone': '+48600111001',
    'email': 'email-only@example.invalid', 'gender': 'unspecified',
    'city': 'Katowice', 'otp_code': 'email-only-code',
})
main.otp_manager.verify_otp = original_verify
assert email_only_registration.status_code == 401
assert verified_identifiers == ['+48600111001']

ping = {
    'category': 'grocery', 'destination_name': 'Biedronka Katowice',
    'destination_lat': 50.2649, 'destination_lng': 19.0238,
    'address': 'Centrum Katowic', 'intent_tags': ['#SpokojneZakupy'],
    'ttl_minutes': 45, 'notes': 'Spotkajmy się przy wejściu.', 'women_only': False,
}
created = client.post('/api/pings', headers=headers, json=ping)
assert created.status_code == 200, created.text
assert created.json()['host']['trust_tier'] == 'Bronze'
assert 'phone_verified_at' not in created.json()['host']
assert client.post('/api/pings', headers=headers, json={**ping, 'women_only': True}).status_code == 403

user = database.find_user_by_identifier(phone)
assert user and storage.load_users()[user.id]['phone_verified_at']
user.phone_verified_at = None
storage.persist_user(user.model_dump())
assert client.post('/api/pings', headers=headers, json=ping).status_code == 403
assert client.post('/api/pings', json=ping).status_code == 401

replay = client.post('/api/auth/otp/verify', json={'identifier': phone, 'code': captured[phone]})
assert replay.status_code == 400
assert client.post('/api/auth/logout', headers=headers).status_code == 200
assert client.get('/api/users/me', headers=headers).status_code == 401
""")


@pytest.mark.parametrize("allowed_phones", ["", "1234", "+48600111002,not-a-phone"])
def test_deployed_staging_requires_approved_phone_allowlist(tmp_path, allowed_phones):
    env = os.environ.copy()
    env.update({
        "CARTMATE_ENV": "staging",
        "CARTMATE_DEPLOYMENT": "1",
        "CARTMATE_DATABASE_PATH": str(tmp_path / "unused.db"),
        "SOS_WEBHOOK_SECRET": secrets.token_urlsafe(24),
        "CARTMATE_STAGING_ALLOWED_PHONES": allowed_phones,
    })
    result = subprocess.run(
        [sys.executable, "-c", "import config"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode != 0
    assert "CARTMATE_STAGING_ALLOWED_PHONES" in result.stderr


def test_render_same_origin_frontend_and_api(tmp_path):
    frontend_dir = tmp_path / "frontend-dist"
    frontend_dir.mkdir()
    (frontend_dir / "index.html").write_text("<!doctype html><title>CartMate staging</title>", encoding="utf-8")
    run_staging_probe(tmp_path, """
from fastapi.testclient import TestClient
import main
client = TestClient(main.app)
home = client.get('/')
assert home.status_code == 200
assert 'CartMate staging' in home.text
assert client.get('/api/health').json()['environment'] == 'staging'
assert client.get('/api/users/me').status_code == 401
assert client.get('/api/pings').status_code == 401
assert client.post('/api/auth/otp/request', json={'identifier': '+48600999999'}).status_code == 403
""", extra_env={"CARTMATE_FRONTEND_DIST": str(frontend_dir)})
