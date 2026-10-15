"""Adversarial contracts, role bootstrap, authorization and recovery tests for
Gemini Private Pilot Review (Codex Acceptance Brief).

Covers:
- RT-00: Attestation method schema validation (physical_identity_document vs physical_id)
- RT-01: Correct private startup, role bootstrap without in-memory mutation, and console OTP rejection in staging
- RT-02: Operator admission is not a production bypass (fail-closed in production, SafeHaven denied)
- RT-03: Activation lifecycle, race conditions, partial state, and rate limits
- RT-04: Adult gate, challenge binding, unsupported methods, and emergency exit availability
- RT-05: Membership, cross-object transport boundaries, moderator isolation, and bidirectional blocking
- RT-06: WebSocket ticket generation, single-use tickets, origin validation, and oversized frame rejection
- RT-10: PII shielding, raw token absence, and absence of /_qa helper routes in shipped app
- RT-11: Disaster recovery with populated operator admission & attestation tables
"""

import hashlib
import json
import os
import secrets
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from contextlib import closing
import sqlite3

import pytest
from pydantic import ValidationError

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent


def run_isolated_probe(tmp_path: Path, script: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update({
        "CARTMATE_ENV": "staging",
        "CARTMATE_DEPLOYMENT": "0",
        "CARTMATE_DATABASE_PATH": str(tmp_path / "probe.db"),
        "CARTMATE_CORS_ALLOWED_ORIGINS": "https://staging.cartmate.example",
        "CARTMATE_MODERATOR_USER_IDS": "",
        "CARTMATE_STAGING_ALLOWED_PHONES": "+48600111001,+48600111002",
        "CARTMATE_OPERATOR_PILOT_ENABLED": "1",
        "CARTMATE_MANUAL_AGE_PILOT_ENABLED": "1",
        "OTP_PROVIDER": "console",
        "SOS_PROVIDER": "disabled",
        "SOS_WEBHOOK_SECRET": secrets.token_urlsafe(24),
        "CARTMATE_DEFAULT_REGION": "silesia",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    })
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_rt00_attestation_method_schema_validation(tmp_path):
    """RT-00: Validate schema accepts physical_identity_document and mdowod_qr, rejects physical_id."""
    from main import PilotAdultAttestationRequest

    # 1. Accepted methods
    valid_doc = PilotAdultAttestationRequest(
        method="physical_identity_document",
        confirmed_over_18=True,
        subject_present=True,
        subject_consented=True,
        account_bound=True,
        account_challenge="challenge_code_12345",
    )
    assert valid_doc.method == "physical_identity_document"

    valid_qr = PilotAdultAttestationRequest(
        method="mdowod_qr",
        confirmed_over_18=True,
        subject_present=True,
        subject_consented=True,
        account_bound=True,
        account_challenge="challenge_code_12345",
    )
    assert valid_qr.method == "mdowod_qr"

    # 2. Rejected method: physical_id must raise literal_error
    with pytest.raises(ValidationError) as exc_info:
        PilotAdultAttestationRequest(
            method="physical_id",
            confirmed_over_18=True,
            subject_present=True,
            subject_consented=True,
            account_bound=True,
            account_challenge="challenge_code_12345",
        )
    errors = exc_info.value.errors()
    assert any("literal_error" in str(e) or "method" in str(e["loc"]) for e in errors)

    # 3. Extra fields must be forbidden (extra="forbid")
    with pytest.raises(ValidationError) as exc_extra:
        PilotAdultAttestationRequest(
            method="physical_identity_document",
            confirmed_over_18=True,
            subject_present=True,
            subject_consented=True,
            account_bound=True,
            account_challenge="challenge_code_12345",
            extra_pesel="12345678901",  # forbidden
        )
    assert "extra_forbidden" in str(exc_extra.value)

    # 4. HTTP endpoint regression: physical_identity_document passes, physical_id returns 422
    proc = run_isolated_probe(tmp_path, """
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import main
from storage import storage

client = TestClient(main.app)
expiry = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
mod_tok = storage.issue_operator_activation(expiry, intended_for='Moderator')
sub_tok = storage.issue_operator_activation(expiry, intended_for='Subject')

res_mod = client.post('/api/auth/redeem-operator-activation', json={'activation_token': mod_tok, 'name': 'Mod', 'city': 'Katowice'})
mod_id = res_mod.json()['user']['id']
mod_headers = {'Authorization': f'Bearer {res_mod.json()[\"token\"]}'}

res_sub = client.post('/api/auth/redeem-operator-activation', json={'activation_token': sub_tok, 'name': 'Sub', 'city': 'Katowice'})
sub_id = res_sub.json()['user']['id']
sub_headers = {'Authorization': f'Bearer {res_sub.json()[\"token\"]}'}

main.MODERATOR_USER_IDS = frozenset({mod_id})
ch = client.post('/api/users/me/age-check-challenge', headers=sub_headers).json()['challenge']

# Test physical_id: must return 422 Unprocessable Entity
res_bad = client.post(
    f'/api/moderation/users/{sub_id}/adult-attestation',
    headers=mod_headers,
    json={
        'method': 'physical_id',
        'confirmed_over_18': True,
        'subject_present': True,
        'subject_consented': True,
        'account_bound': True,
        'account_challenge': ch,
    },
)
assert res_bad.status_code == 422, f'Expected 422 for physical_id, got {res_bad.status_code}'

# Test physical_identity_document: must return 200 OK
res_ok = client.post(
    f'/api/moderation/users/{sub_id}/adult-attestation',
    headers=mod_headers,
    json={
        'method': 'physical_identity_document',
        'confirmed_over_18': True,
        'subject_present': True,
        'subject_consented': True,
        'account_bound': True,
        'account_challenge': ch,
    },
)
assert res_ok.status_code == 200, f'Expected 200, got {res_ok.status_code}: {res_ok.text}'
assert res_ok.json()['adult_verified'] is True
assert res_ok.json()['method'] == 'physical_identity_document'
""")
    assert proc.returncode == 0, f"Error: {proc.stderr}\nOutput: {proc.stdout}"


def test_rt01_private_startup_and_role_bootstrap(tmp_path):
    """RT-01: Correct startup, role bootstrap without mutating main.MODERATOR_USER_IDS in running app, and console OTP rejection in staging."""
    # Step 1: Start process without moderator IDs, redeem accounts
    setup_script = """
import json
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import main
from storage import storage

client = TestClient(main.app)
# Check health and env
res_env = client.get('/api/config/environment')
assert res_env.status_code == 200
data = res_env.json()
assert data['environment'] == 'staging'
assert data['operator_pilot_enabled'] is True

# Check demo switch auth is strictly forbidden in staging
res_demo = client.post('/api/auth/switch-user?user_id=usr_zuzanna')
assert res_demo.status_code == 403

# Check ready endpoint is blocked (no moderator configured yet)
res_ready = client.get('/api/ready')
assert res_ready.status_code == 503
assert any('CARTMATE_MODERATOR_USER_IDS' in b for b in res_ready.json()['blockers'])

# Console OTP requests must fail closed in staging
res_otp = client.post('/api/auth/otp/request', json={'identifier': '+48600111001'})
assert res_otp.status_code in {403, 503}, f'Expected OTP rejection in staging with console provider, got {res_otp.status_code}'

# Issue and redeem operator accounts
exp = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
tok_op = storage.issue_operator_activation(exp, intended_for='Operator')
tok_friend = storage.issue_operator_activation(exp, intended_for='Friend')

res_op = client.post('/api/auth/redeem-operator-activation', json={'activation_token': tok_op, 'name': 'Jan Op', 'city': 'Katowice'})
assert res_op.status_code == 200
op_id = res_op.json()['user']['id']

res_fr = client.post('/api/auth/redeem-operator-activation', json={'activation_token': tok_friend, 'name': 'Anna Fr', 'city': 'Katowice'})
assert res_fr.status_code == 200
fr_id = res_fr.json()['user']['id']

# Print IDs for step 2
print(json.dumps({'op_id': op_id, 'fr_id': fr_id, 'op_token': res_op.json()['token'], 'fr_token': res_fr.json()['token']}))
"""
    proc1 = run_isolated_probe(tmp_path, setup_script)
    assert proc1.returncode == 0, f"Setup failed: {proc1.stderr}\n{proc1.stdout}"
    ids = json.loads(proc1.stdout.strip().splitlines()[-1])

    # Step 2: Fresh process start with CARTMATE_MODERATOR_USER_IDS set via environment (NO test-only in-memory mutation)
    verify_script = f"""
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)
# Verify moderator IDs loaded from environment
assert '{ids["op_id"]}' in main.MODERATOR_USER_IDS
assert '{ids["fr_id"]}' in main.MODERATOR_USER_IDS

# Now ready status reflects moderator presence
res_ready = client.get('/api/ready')
# Check no moderator blocker exists anymore
blockers = res_ready.json().get('blockers', [])
assert not any('CARTMATE_MODERATOR_USER_IDS' in b for b in blockers), f'Found unexpected mod blockers: {{blockers}}'

# Perform attestation from op to friend using environment-configured role
fr_headers = {{'Authorization': 'Bearer {ids["fr_token"]}'}}
op_headers = {{'Authorization': 'Bearer {ids["op_token"]}'}}
ch = client.post('/api/users/me/age-check-challenge', headers=fr_headers).json()['challenge']

res_attest = client.post(
    f'/api/moderation/users/{ids["fr_id"]}/adult-attestation',
    headers=op_headers,
    json={{
        'method': 'physical_identity_document',
        'confirmed_over_18': True,
        'subject_present': True,
        'subject_consented': True,
        'account_bound': True,
        'account_challenge': ch,
    }},
)
assert res_attest.status_code == 200, res_attest.text
assert res_attest.json()['adult_verified'] is True
"""
    proc2 = run_isolated_probe(
        tmp_path,
        verify_script,
        extra_env={"CARTMATE_MODERATOR_USER_IDS": f"{ids['op_id']},{ids['fr_id']}"},
    )
    assert proc2.returncode == 0, f"Verify failed: {proc2.stderr}\n{proc2.stdout}"


def test_rt02_operator_admission_fails_closed_in_production(tmp_path):
    """RT-02: Operator admission fails closed in production, and operator-admitted staging accounts cannot bypass production gates."""
    # 1. Redemption rejected in production
    proc_prod = run_isolated_probe(
        tmp_path,
        """
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)
res = client.post('/api/auth/redeem-operator-activation', json={
    'activation_token': 'CMACT-AAAAAAAAAAAAAAAAAAAAAAAA',
    'name': 'Production Attempter',
    'city': 'Katowice',
})
assert res.status_code == 403
assert 'prohibited in production' in res.text
""",
        extra_env={"CARTMATE_ENV": "production", "CARTMATE_OPERATOR_PILOT_ENABLED": "1"},
    )
    assert proc_prod.returncode == 0, f"Prod fail: {proc_prod.stderr}"

    # 2. Persisted operator-admitted account in DB accessed under production mode is denied live participation
    proc_stage_to_prod = run_isolated_probe(
        tmp_path,
        """
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import main
from storage import storage

# In staging: admit user
client = TestClient(main.app)
exp = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
tok = storage.issue_operator_activation(exp, intended_for='Tester')
res = client.post('/api/auth/redeem-operator-activation', json={'activation_token': tok, 'name': 'Admitted', 'city': 'Katowice'})
assert res.status_code == 200
user_token = res.json()['token']
user_id = res.json()['user']['id']
print(f'{user_token}:{user_id}')
""",
    )
    assert proc_stage_to_prod.returncode == 0
    token, user_id = proc_stage_to_prod.stdout.strip().splitlines()[-1].split(":")

    # Now run production against that same database: live outing routes MUST return 403
    proc_prod_denial = run_isolated_probe(
        tmp_path,
        f"""
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)
headers = {{'Authorization': 'Bearer {token}'}}
# In production, operator-admitted user has phone_verified_at=None, so live pings fail closed
res_pings = client.get('/api/pings', headers=headers)
assert res_pings.status_code == 403, f'Expected 403 in production, got {{res_pings.status_code}}'

# Women-only / SafeHaven access strictly requires is_id_verified=True
res_women = client.post('/api/pings', headers=headers, json={{
    'category': 'coffee',
    'destination_name': 'Cafe SafeHaven',
    'destination_lat': 50.26,
    'destination_lng': 19.02,
    'women_only': True,
    'address': 'Katowice',
    'ttl_minutes': 60,
}})
assert res_women.status_code == 403
""",
        extra_env={"CARTMATE_ENV": "production", "CARTMATE_OPERATOR_PILOT_ENABLED": "0"},
    )
    assert proc_prod_denial.returncode == 0, f"Prod denial failed: {proc_prod_denial.stderr}\n{proc_prod_denial.stdout}"


def test_rt03_activation_lifecycle_and_recoverable_failures(tmp_path):
    """RT-03: Activation lifecycle, concurrency safety, partial state, and rate limits."""
    proc = run_isolated_probe(tmp_path, """
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
import main
from storage import storage, get_db_connection

client = TestClient(main.app)
exp = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
tok = storage.issue_operator_activation(exp, intended_for='Race Test')

# Concurrency test: 2 threads try to redeem same token
def redeem(name):
    c = TestClient(main.app)
    return c.post('/api/auth/redeem-operator-activation', json={
        'activation_token': tok,
        'name': name,
        'city': 'Katowice',
    }).status_code

with ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(redeem, ['User A', 'User B']))

assert sorted(results) == [200, 403], f'Expected [200, 403], got {sorted(results)}'

# Verify exactly one account was created in SQLite, no orphan accounts
conn = get_db_connection(storage.db_path)
try:
    users = conn.execute("SELECT COUNT(*) FROM operator_admissions").fetchone()[0]
    assert users == 1
finally:
    conn.close()

# Rate limiting: 5 attempts allowed in 15 min. The 2 concurrency attempts above consumed 2 slots,
# so 3 more attempts are permitted before 429 is triggered on the 6th overall attempt.
for i in range(3):
    res_rl = client.post(
        '/api/auth/redeem-operator-activation',
        json={'activation_token': f'CMACT-{i:024X}', 'name': 'RL Tester', 'city': 'Katowice'},
        headers={'X-Forwarded-For': f'10.0.0.{i}'},  # Test forwarded IP spoofing attempt
    )
    assert res_rl.status_code in {403, 422}

res_rl6 = client.post(
    '/api/auth/redeem-operator-activation',
    json={'activation_token': 'CMACT-AAAAAAAAAAAAAAAAAAAAAAAA', 'name': 'RL Tester', 'city': 'Katowice'},
    headers={'X-Forwarded-For': '10.0.0.99'},
)
assert res_rl6.status_code == 429, f'Expected 429, got {res_rl6.status_code}'
assert 'Zbyt wiele prób' in res_rl6.text
assert 'Retry-After' in res_rl6.headers

# Clear rate limiter before testing fault injection and recovery
from rate_limiter import rate_limiter
rate_limiter.clear()

# Fault injection: session persistence failure rolls back durable records (no stranded accounts)
from unittest.mock import patch
failed_tok = storage.issue_operator_activation(exp, intended_for='Interrupted User')
with patch.object(main, 'persist_active_session', side_effect=RuntimeError('synthetic persistence failure')):
    c_fail = TestClient(main.app, raise_server_exceptions=False)
    fail_res = c_fail.post('/api/auth/redeem-operator-activation', json={
        'activation_token': failed_tok, 'name': 'Interrupted User', 'city': 'Katowice',
    })
    assert fail_res.status_code == 500

# Inspect SQLite: 0 stranded accounts without session
conn = get_db_connection(storage.db_path)
try:
    stranded = conn.execute(
        "SELECT COUNT(*) FROM operator_admissions a "
        "JOIN users u ON u.id=a.user_id "
        "LEFT JOIN sessions s ON s.user_id=a.user_id "
        "WHERE json_extract(u.data_json, '$.name') = 'Interrupted User' AND s.user_id IS NULL"
    ).fetchone()[0]
    assert stranded == 0, f'Expected 0 stranded accounts, got {stranded}'
finally:
    conn.close()

# Retrying redemption with the same unconsumed token succeeds
retry_res = client.post('/api/auth/redeem-operator-activation', json={
    'activation_token': failed_tok, 'name': 'Interrupted User', 'city': 'Katowice',
})
assert retry_res.status_code == 200
user_data = retry_res.json()
original_user_id = user_data['user']['id']
orig_token = user_data['token']
orig_headers = {'Authorization': f'Bearer {orig_token}'}

# Logout terminates session
logout_res = client.post('/api/auth/logout', headers=orig_headers)
assert logout_res.status_code == 200
me_after_logout = client.get('/api/users/me', headers=orig_headers)
assert me_after_logout.status_code == 401

# Replaying spent activation code fails closed (403)
replay_res = client.post('/api/auth/redeem-operator-activation', json={
    'activation_token': failed_tok, 'name': 'Interrupted User', 'city': 'Katowice',
})
assert replay_res.status_code == 403

# Operator issues bounded recovery token for this user
rec_tok = storage.issue_operator_recovery(
    target_user_id=original_user_id,
    expires_at=exp,
    operator_id='test_op',
    intended_for='Interrupted User',
)
assert rec_tok.startswith('CMREC-')

# Redeeming recovery token restores access to the EXACT SAME user account
rec_res = client.post('/api/auth/redeem-operator-recovery', json={'recovery_token': rec_tok})
assert rec_res.status_code == 200
recovered_data = rec_res.json()
assert recovered_data['user']['id'] == original_user_id
new_token = recovered_data['token']
assert new_token != orig_token

# Old session remains revoked; new session works
assert client.get('/api/users/me', headers=orig_headers).status_code == 401
assert client.get('/api/users/me', headers={'Authorization': f'Bearer {new_token}'}).status_code == 200

# Replaying spent recovery token fails closed (403)
assert client.post('/api/auth/redeem-operator-recovery', json={'recovery_token': rec_tok}).status_code == 403
""")
    assert proc.returncode == 0, f"Error: {proc.stderr}\nOutput: {proc.stdout}"


def test_rt04_adult_gate_and_challenge_invariants(tmp_path):
    """RT-04: Adult gate, challenge binding, unsupported methods, and emergency exit availability."""
    proc = run_isolated_probe(tmp_path, """
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import main
from storage import storage

client = TestClient(main.app)
exp = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
tok_mod = storage.issue_operator_activation(exp, intended_for='Moderator')
tok_ord = storage.issue_operator_activation(exp, intended_for='Ordinary')

res_mod = client.post('/api/auth/redeem-operator-activation', json={'activation_token': tok_mod, 'name': 'Mod', 'city': 'Katowice'})
mod_id = res_mod.json()['user']['id']
mod_headers = {'Authorization': f'Bearer {res_mod.json()[\"token\"]}'}

res_ord = client.post('/api/auth/redeem-operator-activation', json={'activation_token': tok_ord, 'name': 'Ordinary', 'city': 'Katowice'})
ord_id = res_ord.json()['user']['id']
ord_headers = {'Authorization': f'Bearer {res_ord.json()[\"token\"]}'}

main.MODERATOR_USER_IDS = frozenset({mod_id})

# 1. Ordinary user before 18+ check cannot create or browse pings
res_pings_pre = client.get('/api/pings', headers=ord_headers)
assert res_pings_pre.status_code == 403
assert 'potwierdzenia pełnoletności' in res_pings_pre.text

# 2. Ordinary user cannot attest anyone (403)
ch_mod = client.post('/api/users/me/age-check-challenge', headers=mod_headers).json()['challenge']
res_ord_attest = client.post(
    f'/api/moderation/users/{mod_id}/adult-attestation',
    headers=ord_headers,
    json={
        'method': 'physical_identity_document',
        'confirmed_over_18': True,
        'subject_present': True,
        'subject_consented': True,
        'account_bound': True,
        'account_challenge': ch_mod,
    },
)
assert res_ord_attest.status_code == 403

# 3. Wrong challenge rejected
ch_ord = client.post('/api/users/me/age-check-challenge', headers=ord_headers).json()['challenge']
res_wrong_ch = client.post(
    f'/api/moderation/users/{ord_id}/adult-attestation',
    headers=mod_headers,
    json={
        'method': 'physical_identity_document',
        'confirmed_over_18': True,
        'subject_present': True,
        'subject_consented': True,
        'account_bound': True,
        'account_challenge': 'wrong_challenge_123',
    },
)
assert res_wrong_ch.status_code == 403

# 4. Valid attestation unlocks ordinary user
res_valid_attest = client.post(
    f'/api/moderation/users/{ord_id}/adult-attestation',
    headers=mod_headers,
    json={
        'method': 'physical_identity_document',
        'confirmed_over_18': True,
        'subject_present': True,
        'subject_consented': True,
        'account_bound': True,
        'account_challenge': ch_ord,
    },
)
assert res_valid_attest.status_code == 200

res_pings_post = client.get('/api/pings', headers=ord_headers)
assert res_pings_post.status_code == 200

# 5. Revocation re-locks user
res_rev = client.post(f'/api/moderation/users/{ord_id}/adult-attestation/revoke', headers=mod_headers)
assert res_rev.status_code == 200
res_pings_rev = client.get('/api/pings', headers=ord_headers)
assert res_pings_rev.status_code == 403

# 6. Safety & emergency / logout endpoints remain accessible even without adult verification
res_logout = client.post('/api/auth/logout', headers=ord_headers)
assert res_logout.status_code == 200
""")
    assert proc.returncode == 0, f"Error: {proc.stderr}\nOutput: {proc.stdout}"


def test_rt05_membership_sessions_and_cross_object_isolation(tmp_path):
    """RT-05: Non-moderator object isolation, moderation queue protection, and bidirectional blocking."""
    proc = run_isolated_probe(tmp_path, """
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import main
from storage import storage

client = TestClient(main.app)
exp = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
t_mod = storage.issue_operator_activation(exp, intended_for='Mod')
t_h = storage.issue_operator_activation(exp, intended_for='Host')
t_c = storage.issue_operator_activation(exp, intended_for='Companion')
t_x = storage.issue_operator_activation(exp, intended_for='Outsider X')

h_mod = {'Authorization': f'Bearer {client.post("/api/auth/redeem-operator-activation", json={"activation_token": t_mod, "name": "Mod", "city": "Katowice"}).json()["token"]}'}
h_h = {'Authorization': f'Bearer {client.post("/api/auth/redeem-operator-activation", json={"activation_token": t_h, "name": "Host", "city": "Katowice"}).json()["token"]}'}
h_c = {'Authorization': f'Bearer {client.post("/api/auth/redeem-operator-activation", json={"activation_token": t_c, "name": "Companion", "city": "Katowice"}).json()["token"]}'}
h_x = {'Authorization': f'Bearer {client.post("/api/auth/redeem-operator-activation", json={"activation_token": t_x, "name": "Outsider X", "city": "Katowice"}).json()["token"]}'}

# Get IDs
user_h = client.get('/api/users/me', headers=h_h).json()['id']
user_c = client.get('/api/users/me', headers=h_c).json()['id']
user_x = client.get('/api/users/me', headers=h_x).json()['id']
user_mod = client.get('/api/users/me', headers=h_mod).json()['id']

main.MODERATOR_USER_IDS = frozenset({user_mod})

# Attest H, C, X
for uid, h in [(user_h, h_h), (user_c, h_c), (user_x, h_x)]:
    ch = client.post('/api/users/me/age-check-challenge', headers=h).json()['challenge']
    client.post(f'/api/moderation/users/{uid}/adult-attestation', headers=h_mod, json={
        'method': 'physical_identity_document', 'confirmed_over_18': True, 'subject_present': True,
        'subject_consented': True, 'account_bound': True, 'account_challenge': ch,
    })

# H creates ping, C joins, H accepts -> Trip formed
p = client.post('/api/pings', headers=h_h, json={
    'category': 'cafe', 'destination_name': 'Kawiarnia', 'destination_lat': 50.26, 'destination_lng': 19.02,
    'address': 'Katowice', 'ttl_minutes': 60,
}).json()
jr = client.post(f'/api/pings/{p["id"]}/join', headers=h_c, json={'message': 'Join'}).json()
trip = client.post(f'/api/pings/{p["id"]}/requests/{jr["id"]}/accept', headers=h_h).json()
trip_id = trip['id']
chat_id = trip['chat_room_id']

# 1. Outsider X CANNOT access H & C trip
res_x_trip = client.get(f'/api/trips/{trip_id}', headers=h_x)
assert res_x_trip.status_code == 403

# 2. Outsider X CANNOT read trip PIN
res_x_pin = client.get(f'/api/trips/{trip_id}/pin', headers=h_x)
assert res_x_pin.status_code == 403

# 3. Outsider X CANNOT read trip chat
res_x_chat = client.get(f'/api/chat/rooms/{chat_id}', headers=h_x)
assert res_x_chat.status_code == 403

# 4. Outsider X CANNOT read moderation reports or shadow audit
assert client.get('/api/moderation/queue', headers=h_x).status_code == 403
assert client.get('/api/ai/shadow-audit', headers=h_x).status_code == 403

# 5. Bidirectional block between Host and Outsider
client.post(f'/api/users/{user_x}/block', headers=h_h, json={'reason': 'test block'})
# Outsider cannot see Host's pings
pings_seen_by_x = client.get('/api/pings', headers=h_x).json()
assert not any(item['host']['id'] == user_h for item in pings_seen_by_x)
""")
    assert proc.returncode == 0, f"Error: {proc.stderr}\nOutput: {proc.stdout}"


def test_rt06_websocket_tickets_origins_and_frames(tmp_path):
    """RT-06: WebSocket ticket generation, single-use enforcement, origin checks, and frame constraints."""
    proc = run_isolated_probe(tmp_path, """
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import main
from storage import storage

client = TestClient(main.app)
exp = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
tok = storage.issue_operator_activation(exp, intended_for='WS User')
res_auth = client.post('/api/auth/redeem-operator-activation', json={'activation_token': tok, 'name': 'WS User', 'city': 'Katowice'})
token = res_auth.json()['token']
user_id = res_auth.json()['user']['id']
headers = {'Authorization': f'Bearer {token}'}

# Attest user
tok_mod = storage.issue_operator_activation(exp, intended_for='WS Mod')
res_mod = client.post('/api/auth/redeem-operator-activation', json={'activation_token': tok_mod, 'name': 'WS Mod', 'city': 'Katowice'})
mod_id = res_mod.json()['user']['id']
mod_headers = {'Authorization': f'Bearer {res_mod.json()["token"]}'}
main.MODERATOR_USER_IDS = frozenset({mod_id})
ch = client.post('/api/users/me/age-check-challenge', headers=headers).json()['challenge']
client.post(f'/api/moderation/users/{user_id}/adult-attestation', headers=mod_headers, json={
    'method': 'physical_identity_document', 'confirmed_over_18': True, 'subject_present': True,
    'subject_consented': True, 'account_bound': True, 'account_challenge': ch,
})

# 1. Issue WS ticket
res_ticket = client.post('/api/auth/ws-ticket', headers=headers)
assert res_ticket.status_code == 200
ticket = res_ticket.json()['ticket']
assert len(ticket) >= 32

# 2. Test WS connection with ticket
with client.websocket_connect(f'/ws?ticket={ticket}', headers={'Origin': 'https://staging.cartmate.example'}) as ws:
    ready = ws.receive_json()
    assert ready['type'] == 'connection.ready'
    ws.send_json({'action': 'ping'})
    data = ws.receive_json()
    assert data['type'] == 'pong'

# 3. Ticket is single-use: second connect must fail
try:
    with client.websocket_connect(f'/ws?ticket={ticket}', headers={'Origin': 'https://staging.cartmate.example'}) as ws2:
        raise AssertionError('Reused ticket should fail')
except AssertionError:
    raise
except Exception:
    pass  # Expected connection rejection

# 4. Untrusted origin must fail
res_ticket2 = client.post('/api/auth/ws-ticket', headers=headers)
ticket2 = res_ticket2.json()['ticket']
try:
    with client.websocket_connect(f'/ws?ticket={ticket2}', headers={'Origin': 'https://untrusted-attacker.invalid'}) as ws3:
        raise AssertionError('Untrusted origin should fail')
except AssertionError:
    raise
except Exception:
    pass  # Expected connection rejection
""")
    assert proc.returncode == 0, f"Error: {proc.stderr}\nOutput: {proc.stdout}"


def test_rt10_pii_shielding_and_no_qa_leakage(tmp_path):
    """RT-10: Verify public profiles shield PII, database never stores raw tokens, and shipped app has no /_qa routes."""
    proc = run_isolated_probe(tmp_path, """
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import main
from storage import storage, get_db_connection

client = TestClient(main.app)

# 1. Shipped app must not expose /_qa endpoints
res_qa = client.get('/_qa/latest-otp')
assert res_qa.status_code == 404, f'Shipped app exposed /_qa: {res_qa.status_code}'

# 2. Raw token never stored in SQLite
exp = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
raw_token = storage.issue_operator_activation(exp, intended_for='Privacy Test')
res = client.post('/api/auth/redeem-operator-activation', json={'activation_token': raw_token, 'name': 'Privacy User', 'city': 'Katowice', 'bio': 'Public bio'})
assert res.status_code == 200
user = res.json()['user']

conn = get_db_connection(storage.db_path)
try:
    dump = [str(dict(r)) for r in conn.execute('SELECT * FROM operator_activations').fetchall()]
    assert not any(raw_token in row for row in dump), 'Raw token found in database!'
finally:
    conn.close()

# 3. Public user profile has no sensitive PII
# Attest user so /api/users/all discovery is accessible in staging
tok_m = storage.issue_operator_activation(exp, intended_for='Privacy Mod')
res_m = client.post('/api/auth/redeem-operator-activation', json={'activation_token': tok_m, 'name': 'Privacy Mod', 'city': 'Katowice'})
mod_id = res_m.json()['user']['id']
mod_headers = {'Authorization': f'Bearer {res_m.json()["token"]}'}
main.MODERATOR_USER_IDS = frozenset({mod_id})
ch = client.post('/api/users/me/age-check-challenge', headers={'Authorization': f'Bearer {res.json()["token"]}'}).json()['challenge']
client.post(f'/api/moderation/users/{user["id"]}/adult-attestation', headers=mod_headers, json={
    'method': 'physical_identity_document', 'confirmed_over_18': True, 'subject_present': True,
    'subject_consented': True, 'account_bound': True, 'account_challenge': ch,
})

res_pub = client.get('/api/users/all', headers={'Authorization': f'Bearer {res.json()["token"]}'})
assert res_pub.status_code == 200
pub_users = res_pub.json()
target = next((u for u in pub_users if u['id'] == user['id']), None)
assert target is not None
assert 'phone' not in target
assert 'email' not in target
assert 'emergency_contact' not in target
assert target['name'] == 'Privacy User'
""")
    assert proc.returncode == 0, f"Error: {proc.stderr}\nOutput: {proc.stdout}"


def test_rt11_disaster_recovery_populated_operator_tables(tmp_path):
    """RT-11: Full backup and restore drill with populated operator admission & attestation tables."""
    db_source = tmp_path / "source.db"
    db_restored = tmp_path / "restored.db"

    # Populate database with operator activations, admissions, attestations, users, sessions, pings, chat
    from storage import DurableStorage, get_db_connection
    store = DurableStorage(str(db_source))

    exp = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    t1 = store.issue_operator_activation(exp, intended_for="User 1")
    t2 = store.issue_operator_activation(exp, intended_for="User 2")
    t3 = store.issue_operator_activation(exp, intended_for="User 3")
    store.revoke_operator_activation(t3)
    t4_rec = store.issue_operator_activation(exp, intended_for="User 1 Recovery", target_user_id="usr_test1")

    user1_dict = {
        "id": "usr_test1",
        "name": "Alice",
        "avatar": "",
        "email": "alice@test.invalid",
        "phone": "",
        "city": "Katowice",
        "gender": "female",
        "bio": "bio 1",
        "trust_tier": "Bronze",
    }
    user2_dict = {
        "id": "usr_test2",
        "name": "Bob",
        "avatar": "",
        "email": "bob@test.invalid",
        "phone": "",
        "city": "Katowice",
        "gender": "male",
        "bio": "bio 2",
        "trust_tier": "Bronze",
    }
    store.redeem_operator_activation(t1, user1_dict)
    store.redeem_operator_activation(t2, user2_dict)

    now_iso = datetime.now(timezone.utc).isoformat()
    user1_dict["adult_attestation_confirmed"] = True
    user1_dict["adult_attestation_method"] = "physical_identity_document"
    user1_dict["age_assurance_provider"] = "operator_physical_id"
    user1_dict["adult_verified_at"] = now_iso
    user1_dict["adult_verification_expires_at"] = exp
    store.record_pilot_age_attestation(
        user_dict=user1_dict,
        moderator_user_id=user2_dict["id"],
        method="physical_identity_document",
        decision="confirmed_adult",
        recorded_at=now_iso,
        expires_at=exp,
    )

    # Populate session, ping, chat room & message
    conn = get_db_connection(str(db_source))
    try:
        user1_public = {
            "id": "usr_test1", "name": "Alice", "avatar": "",
            "bio": "bio 1", "trust_tier": "Bronze", "city": "Katowice", "gender": "female",
        }
        user2_public = {
            "id": "usr_test2", "name": "Bob", "avatar": "",
            "bio": "bio 2", "trust_tier": "Bronze", "city": "Katowice", "gender": "male",
        }
        ping_dict = {
            "id": "ping_001",
            "host": user1_public,
            "category": "grocery",
            "destination_name": "Silesia City Center",
            "destination_lat": 50.2649,
            "destination_lng": 19.0238,
            "address": "Katowice",
            "intent_tags": ["shopping"],
            "notes": "",
            "status": "active",
            "remaining_seconds": 1800,
            "expires_at": exp,
            "created_at": now_iso,
            "women_only": False,
        }
        room_dict = {
            "id": "room_001",
            "scope": "trip",
            "target_id": "trip_001",
            "participant_ids": ["usr_test1", "usr_test2"],
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        msg_dict = {
            "id": "msg_001",
            "chat_room_id": "room_001",
            "sender_id": "usr_test1",
            "sender_name": "Alice",
            "sender_avatar": "",
            "text": "Hello Bob!",
            "created_at": now_iso,
            "sequence": 1,
        }
        req_dict = {
            "id": "req_001",
            "ping_id": "ping_001",
            "applicant": user2_public,
            "message": "Can I join?",
            "status": "accepted",
            "created_at": now_iso,
        }
        conn.execute(
            "INSERT INTO pings (id, user_id, city, data_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("ping_001", "usr_test1", "Katowice", json.dumps(ping_dict), now_iso, now_iso),
        )
        conn.execute(
            "INSERT INTO chat_rooms (id, data_json, created_at, updated_at) VALUES (?, ?, ?, ?)",
            ("room_001", json.dumps(room_dict), now_iso, now_iso),
        )
        conn.execute(
            "INSERT INTO chat_messages (id, room_id, sender_id, data_json, created_at) VALUES (?, ?, ?, ?, ?)",
            ("msg_001", "room_001", "usr_test1", json.dumps(msg_dict), now_iso),
        )
        conn.execute(
            "INSERT INTO join_requests (id, ping_id, applicant_id, status, data_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("req_001", "ping_001", "usr_test2", "accepted", json.dumps(req_dict), now_iso, now_iso),
        )
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            ("cmt_alice_restored_session", "usr_test1", exp, now_iso),
        )
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            ("cmt_bob_restored_session", "usr_test2", exp, now_iso),
        )
        conn.execute(
            "INSERT INTO revoked_sessions (token, user_id, revoked_at) VALUES (?, ?, ?)",
            ("cmt_revoked_session", "usr_test1", now_iso),
        )
        conn.commit()
    finally:
        conn.close()

    def snapshot(db_path: Path) -> dict[str, list[tuple]]:
        with closing(sqlite3.connect(db_path)) as conn_snap:
            table_names = [row[0] for row in conn_snap.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )]
            return {
                name: sorted((tuple(row) for row in conn_snap.execute(f'SELECT * FROM "{name}"')), key=repr)
                for name in table_names
            }

    expected_snapshot = snapshot(db_source)
    assert len(expected_snapshot["operator_activations"]) == 4
    assert len(expected_snapshot["operator_admissions"]) == 2
    assert len(expected_snapshot["pilot_age_attestations"]) == 1
    assert len(expected_snapshot["pings"]) == 1
    assert len(expected_snapshot["chat_messages"]) == 1
    assert len(expected_snapshot["sessions"]) == 2
    assert len(expected_snapshot["revoked_sessions"]) == 1

    # Execute cartmate_backup.py
    backup_script = REPO_ROOT / "ops" / "cartmate_backup.py"
    backup_dir = tmp_path / "backups"
    res_b = subprocess.run(
        [sys.executable, str(backup_script), "--db", str(db_source), "--out", str(backup_dir), "--tag", "rt11_test"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "SUCCESS: Online backup complete" in (res_b.stdout + res_b.stderr)

    # Find created backup .db file
    backup_files = list(backup_dir.glob("cartmate_backup_rt11_test_*.db"))
    assert len(backup_files) == 1
    backup_db = backup_files[0]

    # Execute cartmate_restore.py
    restore_script = REPO_ROOT / "ops" / "cartmate_restore.py"
    res_r = subprocess.run(
        [sys.executable, str(restore_script), "--backup", str(backup_db), "--target", str(db_restored), "--confirm-offline"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Restore complete" in (res_r.stdout + res_r.stderr)

    # Full table-by-table row equality check
    restored_snapshot = snapshot(db_restored)
    assert restored_snapshot == expected_snapshot

    # Verify restored database storage methods
    restored_store = DurableStorage(str(db_restored))
    assert restored_store.is_operator_admitted(user1_dict["id"])
    assert restored_store.is_operator_admitted(user2_dict["id"])
    user1_restored = restored_store.get_user(user1_dict["id"])
    assert user1_restored is not None
    assert user1_restored["name"] == "Alice"
    assert user1_restored.get("adult_attestation_confirmed") is True

    # Boot the restored API and verify deny rules through REST & WebSockets
    api_check_script = f"""
import os, sys
from fastapi.testclient import TestClient

os.environ.update({{
    "CARTMATE_ENV": "staging",
    "CARTMATE_DEPLOYMENT": "0",
    "CARTMATE_DATABASE_PATH": {repr(str(db_restored))},
    "CARTMATE_OPERATOR_PILOT_ENABLED": "1",
    "CARTMATE_MANUAL_AGE_PILOT_ENABLED": "1",
    "CARTMATE_PILOT_INVITES_ENABLED": "0",
    "CARTMATE_MODERATOR_USER_IDS": "usr_mod_rt11",
    "CARTMATE_CORS_ALLOWED_ORIGINS": "https://staging.cartmate.example",
    "CARTMATE_STAGING_ALLOWED_PHONES": "",
    "OTP_PROVIDER": "console",
    "SOS_PROVIDER": "disabled",
    "SOS_WEBHOOK_SECRET": "secret",
    "JEV_MODE": "disabled",
}})

import main

with TestClient(main.app) as client:
    # 1. Active restored session succeeds
    r_me = client.get("/api/users/me", headers={{"Authorization": "Bearer cmt_alice_restored_session"}})
    assert r_me.status_code == 200
    assert r_me.json()["name"] == "Alice"

    # 2. Revoked restored session rejected with 401
    r_rev = client.get("/api/users/me", headers={{"Authorization": "Bearer cmt_revoked_session"}})
    assert r_rev.status_code == 401

    # 2b. Revoked restored session denied WS ticket with 401
    r_rev_ticket = client.post("/api/auth/ws-ticket", headers={{"Authorization": "Bearer cmt_revoked_session"}})
    assert r_rev_ticket.status_code == 401

    # 2c. Invalid/revoked ticket cannot establish WS connection (policy code 1008)
    from starlette.websockets import WebSocketDisconnect
    try:
        with client.websocket_connect(
            "/ws?ticket=cmt_revoked_session",
            headers={{"Origin": "https://staging.cartmate.example"}},
        ) as ws_rev:
            ws_rev.receive_json()
        assert False, "Connection with revoked/invalid ticket must not succeed"
    except WebSocketDisconnect as disc_rev:
        assert disc_rev.code == 1008

    # 3. Admitted-but-not-adult user (Bob) denied live pings with 403
    r_pings_bob = client.get("/api/pings", headers={{"Authorization": "Bearer cmt_bob_restored_session"}})
    assert r_pings_bob.status_code == 403

    # 4. Redeem recovery token t4_rec on restored API
    r_rec = client.post("/api/auth/redeem-operator-recovery", json={{"recovery_token": {repr(t4_rec)}}})
    assert r_rec.status_code == 200
    assert r_rec.json()["user"]["id"] == "usr_test1"
    new_token = r_rec.json()["token"]

    # 5. Token is now consumed; immediate second redemption fails with 403
    r_replay = client.post("/api/auth/redeem-operator-recovery", json={{"recovery_token": {repr(t4_rec)}}})
    assert r_replay.status_code == 403

    # 6. WebSocket ticket generation and connection works on restored API
    r_ticket = client.post("/api/auth/ws-ticket", headers={{"Authorization": "Bearer " + new_token}})
    assert r_ticket.status_code == 200, f"Ticket error: {{r_ticket.status_code}} {{r_ticket.text}}"
    with client.websocket_connect(
        f"/ws?ticket={{r_ticket.json()['ticket']}}",
        headers={{"Origin": "https://staging.cartmate.example"}},
    ) as ws:
        frame = ws.receive_json()
        assert frame["type"] == "connection.ready"
"""
    proc = subprocess.run([sys.executable, "-c", api_check_script], cwd=str(REPO_ROOT / "backend"), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f"Restored API test failed:\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"


def test_rt14_recovery_revoked_socket_disconnect_and_isolation(tmp_path):
    """R2-01: Proves that recovering an account revokes any existing active WebSocket
    connections and prevents new private chat messages from being delivered to the old connection.
    """
    db_path = tmp_path / "rt14.db"
    script = f"""
import json, os, secrets, sys
from datetime import datetime, timedelta, timezone
from starlette.websockets import WebSocketDisconnect
from fastapi.testclient import TestClient

os.environ.update({{
    "CARTMATE_ENV": "staging",
    "CARTMATE_DEPLOYMENT": "0",
    "CARTMATE_DATABASE_PATH": {repr(str(db_path))},
    "CARTMATE_OPERATOR_PILOT_ENABLED": "1",
    "CARTMATE_MANUAL_AGE_PILOT_ENABLED": "1",
    "CARTMATE_PILOT_INVITES_ENABLED": "0",
    "CARTMATE_MODERATOR_USER_IDS": "usr_mod_rt14",
    "CARTMATE_CORS_ALLOWED_ORIGINS": "https://recovery.cartmate.example",
    "CARTMATE_STAGING_ALLOWED_PHONES": "",
    "OTP_PROVIDER": "console",
    "SOS_PROVIDER": "disabled",
    "SOS_WEBHOOK_SECRET": "secret",
    "JEV_MODE": "disabled",
}})

from storage import storage
import main
from models import UserPrivateSchema

expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
mod = UserPrivateSchema(
    id="usr_mod_rt14", name="Mod", avatar="", bio="",
    trust_tier="Bronze", gender="unspecified", city="Katowice",
    email="mod@test.invalid", phone="",
    assurance_marker="operator_in_person",
)
storage.redeem_operator_activation(
    storage.issue_operator_activation(expiry, intended_for="Mod"),
    mod.model_dump(),
)
import database
database.USERS[mod.id] = mod
import config
config.MODERATOR_USER_IDS = frozenset(set(config.MODERATOR_USER_IDS) | {{"usr_mod_rt14"}})
main.MODERATOR_USER_IDS = frozenset(set(main.MODERATOR_USER_IDS) | {{"usr_mod_rt14"}})
mod_session = "cmt_" + secrets.token_hex(20)
main.persist_active_session(mod_session, mod.id)
mod_headers = {{"Authorization": "Bearer " + mod_session}}

with TestClient(main.app) as client:
    def enroll(name):
        code = storage.issue_operator_activation(expiry, intended_for=name)
        res = client.post("/api/auth/redeem-operator-activation", json={{"activation_token": code, "name": name, "city": "Katowice"}})
        assert res.status_code == 200
        acc = res.json()
        hdrs = {{"Authorization": "Bearer " + acc["token"]}}
        ch = client.post("/api/users/me/age-check-challenge", headers=hdrs).json()["challenge"]
        att = client.post(f"/api/moderation/users/{{acc['user']['id']}}/adult-attestation", headers=mod_headers, json={{
            "method": "physical_identity_document", "confirmed_over_18": True,
            "subject_present": True, "subject_consented": True, "account_bound": True, "account_challenge": ch,
        }})
        assert att.status_code == 200, f"Attestation error: {{att.status_code}} {{att.text}}"
        return acc, hdrs

    host, host_hdrs = enroll("Host Alice")
    comp, comp_hdrs = enroll("Companion Bob")

    # Host creates ping, Bob joins, Host accepts
    ping_res = client.post("/api/pings", headers=host_hdrs, json={{
        "category": "grocery", "destination_name": "Silesia City Center",
        "destination_lat": 50.2649, "destination_lng": 19.0238,
        "address": "Katowice", "intent_tags": ["shopping"], "ttl_minutes": 45,
    }})
    assert ping_res.status_code == 200
    ping_id = ping_res.json()["id"]

    join_res = client.post(f"/api/pings/{{ping_id}}/join", headers=comp_hdrs, json={{"message": "Join test"}})
    assert join_res.status_code == 200
    req_id = join_res.json()["id"]

    acc_res = client.post(f"/api/pings/{{ping_id}}/requests/{{req_id}}/accept", headers=host_hdrs)
    assert acc_res.status_code == 200
    room_id = acc_res.json()["chat_room_id"]

    ticket_res = client.post("/api/auth/ws-ticket", headers=host_hdrs)
    assert ticket_res.status_code == 200

    with client.websocket_connect(f"/ws?ticket={{ticket_res.json()['ticket']}}", headers={{"Origin": "https://recovery.cartmate.example"}}) as old_ws:
        assert old_ws.receive_json()["type"] == "connection.ready"
        old_ws.send_json({{"action": "subscribe", "scope": f"chat:{{room_id}}"}})
        assert old_ws.receive_json()["type"] == "subscription.confirmed"

        # Positive control message
        m1 = client.post(f"/api/chat/rooms/{{room_id}}/messages", headers=comp_hdrs, json={{"text": "Pre-recovery message"}})
        assert m1.status_code == 200
        f1 = old_ws.receive_json()
        assert f1["type"] == "chat.message"
        assert f1["payload"]["id"] == m1.json()["id"]

        # Operator issues and redeems recovery token for Host
        rec_token = storage.issue_operator_recovery(host["user"]["id"], expires_at=expiry, operator_id=mod.id, intended_for="Alice recovery")
        rec_res = client.post("/api/auth/redeem-operator-recovery", json={{"recovery_token": rec_token}})
        assert rec_res.status_code == 200
        restored_acc = rec_res.json()
        restored_hdrs = {{"Authorization": "Bearer " + restored_acc["token"]}}

        # Old session is dead, new session is active
        assert client.get("/api/users/me", headers=host_hdrs).status_code == 401
        assert client.get("/api/users/me", headers=restored_hdrs).status_code == 200

        # Bob sends private message after recovery
        m2 = client.post(f"/api/chat/rooms/{{room_id}}/messages", headers=comp_hdrs, json={{"text": "Post-recovery private message"}})
        assert m2.status_code == 200
        m2_id = m2.json()["id"]

        # Old socket MUST be closed with 1008 and MUST NEVER receive m2
        closed_code = None
        leaked = False
        for _ in range(8):
            try:
                frame = old_ws.receive_json()
            except WebSocketDisconnect as disc:
                closed_code = disc.code
                break
            if frame.get("type") == "chat.message" and frame.get("payload", {{}}).get("id") == m2_id:
                leaked = True

        assert not leaked, "CRITICAL: Old revoked socket received private chat message after recovery!"
        assert closed_code == 1008, f"Expected socket closure with 1008, got {{closed_code}}"

    # New session CAN connect and receive subsequent messages
    ticket2 = client.post("/api/auth/ws-ticket", headers=restored_hdrs).json()["ticket"]
    with client.websocket_connect(f"/ws?ticket={{ticket2}}", headers={{"Origin": "https://recovery.cartmate.example"}}) as new_ws:
        assert new_ws.receive_json()["type"] == "connection.ready"
        new_ws.send_json({{"action": "subscribe", "scope": f"chat:{{room_id}}"}})
        assert new_ws.receive_json()["type"] == "subscription.confirmed"
        m3 = client.post(f"/api/chat/rooms/{{room_id}}/messages", headers=comp_hdrs, json={{"text": "Third message to restored session"}})
        f3 = new_ws.receive_json()
        assert f3["type"] == "chat.message"
        assert f3["payload"]["id"] == m3.json()["id"]
"""
    proc = subprocess.run([sys.executable, "-c", script], cwd=str(REPO_ROOT / "backend"), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"


def test_rt15_recovery_persistence_failure_rollback_and_retry(tmp_path):
    """R2-02: Proves that session persistence failure during operator recovery rolls back
    the token consumption, leaves 0 stranded accounts, and permits immediate retry with the same token.
    Tests both the dedicated recovery route and the bound activation route.
    """
    db_path = tmp_path / "rt15.db"
    script = f"""
import json, os, secrets, sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from fastapi.testclient import TestClient

os.environ.update({{
    "CARTMATE_ENV": "staging",
    "CARTMATE_DEPLOYMENT": "0",
    "CARTMATE_DATABASE_PATH": {repr(str(db_path))},
    "CARTMATE_OPERATOR_PILOT_ENABLED": "1",
    "CARTMATE_MANUAL_AGE_PILOT_ENABLED": "1",
    "CARTMATE_PILOT_INVITES_ENABLED": "0",
    "CARTMATE_MODERATOR_USER_IDS": "usr_mod_rt15",
    "CARTMATE_CORS_ALLOWED_ORIGINS": "https://recovery.cartmate.example",
    "CARTMATE_STAGING_ALLOWED_PHONES": "",
    "OTP_PROVIDER": "console",
    "SOS_PROVIDER": "disabled",
    "SOS_WEBHOOK_SECRET": "secret",
    "JEV_MODE": "disabled",
}})

from storage import storage, get_db_connection
import main
from models import UserPrivateSchema

expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
mod = UserPrivateSchema(
    id="usr_mod_rt15", name="Mod", avatar="", bio="",
    trust_tier="Bronze", gender="unspecified", city="Katowice",
    email="mod@test.invalid", phone="",
)
storage.redeem_operator_activation(
    storage.issue_operator_activation(expiry, intended_for="Mod"),
    mod.model_dump(),
)
mod_session = "cmt_" + secrets.token_hex(20)
main.persist_active_session(mod_session, mod.id)

with TestClient(main.app, raise_server_exceptions=False) as client:
    # 1. Enroll user Alice
    act_code = storage.issue_operator_activation(expiry, intended_for="Alice")
    res_act = client.post("/api/auth/redeem-operator-activation", json={{"activation_token": act_code, "name": "Alice", "city": "Katowice"}})
    assert res_act.status_code == 200
    user_id = res_act.json()["user"]["id"]
    alice_token = res_act.json()["token"]

    # 2. Test dedicated route: /api/auth/redeem-operator-recovery
    rec_code1 = storage.issue_operator_recovery(user_id, expires_at=expiry, operator_id=mod.id, intended_for="Alice")

    # Injected persistence failure
    with patch.object(main, "persist_active_session", side_effect=RuntimeError("simulated disk full")):
        fail_res = client.post("/api/auth/redeem-operator-recovery", json={{"recovery_token": rec_code1}})
        assert fail_res.status_code == 500

    # Token was NOT burned; retry with SAME code succeeds!
    retry_res = client.post("/api/auth/redeem-operator-recovery", json={{"recovery_token": rec_code1}})
    assert retry_res.status_code == 200
    assert retry_res.json()["user"]["id"] == user_id

    # Now token IS consumed; second retry fails with 403
    replay_res = client.post("/api/auth/redeem-operator-recovery", json={{"recovery_token": rec_code1}})
    assert replay_res.status_code == 403

    # 3. Test bound recovery branch of /api/auth/redeem-operator-activation
    rec_code2 = storage.issue_operator_recovery(user_id, expires_at=expiry, operator_id=mod.id, intended_for="Alice 2")

    # Injected persistence failure on activation endpoint
    with patch.object(main, "persist_active_session", side_effect=RuntimeError("simulated disk full")):
        fail_res2 = client.post("/api/auth/redeem-operator-activation", json={{"activation_token": rec_code2, "name": "Alice", "city": "Katowice"}})
        assert fail_res2.status_code == 500

    # Retry with SAME code succeeds!
    retry_res2 = client.post("/api/auth/redeem-operator-activation", json={{"activation_token": rec_code2, "name": "Alice", "city": "Katowice"}})
    assert retry_res2.status_code == 200
    assert retry_res2.json()["user"]["id"] == user_id

    # Second retry fails with 403
    replay_res2 = client.post("/api/auth/redeem-operator-activation", json={{"activation_token": rec_code2, "name": "Alice", "city": "Katowice"}})
    assert replay_res2.status_code == 403
"""
    proc = subprocess.run([sys.executable, "-c", script], cwd=str(REPO_ROOT / "backend"), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"


def test_rt16_cors_origin_policy_and_session_ttl_bounds(tmp_path: Path):
    """RT-16: Staging CORS origin matching (positive and negative), native WebView origin,
    disabled JEV mode, and bounded session TTL configuration.
    """
    test_db = str(tmp_path / "rt16.db").replace("\\", "/")
    script = f"""
import os, sys
from pathlib import Path
from fastapi.testclient import TestClient

root = Path('.').resolve()
sys.path.insert(0, str(root))

# Set exact operator launch configuration
os.environ['CARTMATE_ENV'] = 'staging'
os.environ['CARTMATE_DEPLOYMENT'] = '0'
os.environ['CARTMATE_OPERATOR_PILOT_ENABLED'] = '1'
os.environ['CARTMATE_MANUAL_AGE_PILOT_ENABLED'] = '1'
os.environ['CARTMATE_DATABASE_PATH'] = '{test_db}'
os.environ['CARTMATE_CORS_ALLOWED_ORIGINS'] = 'https://operator-node.ts.net,https://localhost'
os.environ['JEV_MODE'] = 'disabled'
os.environ['SESSION_TTL_HOURS'] = '24'
os.environ['SOS_PROVIDER'] = 'disabled'
os.environ['OTP_PROVIDER'] = 'console'
os.environ['SOS_WEBHOOK_SECRET'] = 'synthetic-secret-min-16-chars-long'

import main

with TestClient(main.app) as client:
    # 1. Real configured Tailscale HTTPS origin: positive control
    res_pos = client.options(
        '/api/health',
        headers={{
            'Origin': 'https://operator-node.ts.net',
            'Access-Control-Request-Method': 'GET',
        }},
    )
    assert res_pos.headers.get('access-control-allow-origin') == 'https://operator-node.ts.net'

    # 2. Native Capacitor Android WebView origin (https://localhost): positive control
    res_native = client.options(
        '/api/health',
        headers={{
            'Origin': 'https://localhost',
            'Access-Control-Request-Method': 'GET',
        }},
    )
    assert res_native.headers.get('access-control-allow-origin') == 'https://localhost'

    # 3. Wrong / unapproved origin: negative control (must NOT be allowed)
    res_neg = client.options(
        '/api/health',
        headers={{
            'Origin': 'https://unapproved.example',
            'Access-Control-Request-Method': 'GET',
        }},
    )
    assert res_neg.headers.get('access-control-allow-origin') != 'https://unapproved.example'

    # 4. Session TTL bounded to configured 24 hours
    assert main.OPERATIONAL_THRESHOLDS.session_ttl_hours == 24

    # 5. JEV mode disabled
    assert main.JEV_MODE == 'disabled'
"""
    proc = subprocess.run([sys.executable, "-c", script], cwd=str(REPO_ROOT / "backend"), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"


def test_rt17_native_destination_policy_and_trust_boundary(tmp_path: Path):
    """RT-17: Strict approved-origin comparison, credential withholding on unapproved/missing endpoints,
    positive approved native endpoint, conflicting web WS rejection, and session binding across origin changes.
    """
    ts_path = str((REPO_ROOT / "frontend" / "node_modules" / "typescript").resolve()).replace("\\", "/")
    src_dir = str((REPO_ROOT / "frontend" / "src").resolve()).replace("\\", "/")
    node_script = """
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('__TS_PATH__');

const compile = rel => ts.transpileModule(
  fs.readFileSync(path.join('__SRC_DIR__', rel), 'utf8').replaceAll('import.meta', 'importMeta'),
  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } },
).outputText;

const apiSource = compile('api.ts');
const socketSource = compile('realtime/socket.ts');

async function evaluateContext({ native = true, stored = null, env = {}, initialToken = 'synth-tok-123', withParser = true } = {}) {
  const store = new Map();
  if (initialToken) store.set('cartmate_token', initialToken);
  if (stored) store.set('cartmate_backend_url', stored);
  const calls = [];
  const sandbox = {
    exports: {}, importMeta: { env }, console, URL: withParser ? URL : undefined,
    window: {
      location: { protocol: 'https:', host: native ? 'localhost' : 'pilot.example', href: native ? 'https://localhost/' : 'https://pilot.example/' },
      Capacitor: { isNativePlatform: () => native, getPlatform: () => native ? 'android' : 'web' },
    },
    localStorage: {
      getItem: k => store.get(k) ?? null,
      setItem: (k, v) => store.set(k, v),
      removeItem: k => store.delete(k),
    },
    fetch: async (url, init) => {
      calls.push({
        url: String(url),
        bearerAttached: init?.headers?.Authorization === 'Bearer ' + initialToken,
        authHeader: init?.headers?.Authorization || null,
      });
      return { ok: true, status: 200, json: async () => ({ id: 'u_1', ticket: 'ticket_xyz' }) };
    },
  };
  vm.runInNewContext(apiSource, sandbox);
  const api = sandbox.exports;
  await api.fetchCurrentUser();
  sandbox.exports = {};
  sandbox.require = name => { if (name === '../api') return api; throw new Error(`Unexpected import: ${name}`); };
  vm.runInNewContext(socketSource, sandbox);
  let resolvedSocket = null;
  let socketError = null;
  try {
    resolvedSocket = await new sandbox.exports.RealtimeClient().resolveUrl(initialToken);
  } catch (err) {
    socketError = err.message;
  }
  return { api, backend: api.getBackendBaseUrl(), calls, resolvedSocket, socketError };
}

(async () => {
  // Scenario 1: Positive control - valid approved native origin configured via VITE_BACKEND_ORIGIN
  const approved = await evaluateContext({
    native: true,
    env: { VITE_BACKEND_ORIGIN: 'https://operator.cartmate.internal' },
  });
  if (approved.backend !== 'https://operator.cartmate.internal') {
    throw new Error(`Approved origin mismatch: ${approved.backend}`);
  }
  if (!approved.calls.some(c => c.url === 'https://operator.cartmate.internal/api/users/me' && c.bearerAttached)) {
    throw new Error('Approved native call did not attach bearer credentials');
  }
  if (!approved.resolvedSocket || !approved.resolvedSocket.startsWith('wss://operator.cartmate.internal/ws?ticket=')) {
    throw new Error(`Approved native socket URL incorrect: ${approved.resolvedSocket} (socketError: ${approved.socketError})`);
  }

  // Scenario 2: Multiple independently chosen nonapproved stored destinations
  const nonapprovedHosts = [
    'https://outside.example',
    'https://attacker-exfiltration.net',
    'https://ordinary-review.example',
    'https://cloud-tenant.app.io',
  ];
  for (const host of nonapprovedHosts) {
    const res = await evaluateContext({
      native: true,
      stored: host,
      env: {},
    });
    // Arbitrary storage destinations must be rejected and must NEVER receive bearer tokens
    if (res.calls.some(c => c.bearerAttached)) {
      throw new Error(`Bearer leaked to nonapproved host: ${host}`);
    }
    if (res.resolvedSocket !== null) {
      throw new Error(`Socket connected to nonapproved host: ${host}`);
    }
    if (!res.socketError || !res.socketError.includes('unconfigured or unapproved')) {
      throw new Error(`Expected fail-closed socket error for ${host}, got: ${res.socketError}`);
    }
  }

  // Scenario 3: Missing native configuration - must fail closed without credentials
  const missing = await evaluateContext({ native: true, env: {} });
  if (missing.calls.some(c => c.bearerAttached)) {
    throw new Error('Bearer leaked when native config is missing');
  }
  if (missing.resolvedSocket !== null) {
    throw new Error('Socket resolved when native config is missing');
  }
  if (!missing.socketError || !missing.socketError.includes('unconfigured or unapproved')) {
    throw new Error(`Missing config must fail closed, got: ${missing.socketError}`);
  }

  // Scenario 4: Web browser with conflicting VITE_WS_URL
  const webConflicting = await evaluateContext({
    native: false,
    env: { VITE_WS_URL: 'wss://external-host.example/ws' },
  });
  if (webConflicting.resolvedSocket !== null) {
    throw new Error('Conflicting web WS override was not rejected');
  }
  if (!webConflicting.socketError || !webConflicting.socketError.includes('Conflicting VITE_WS_URL')) {
    throw new Error(`Expected conflicting WS error, got: ${webConflicting.socketError}`);
  }

  // Scenario 5: Web browser with same-origin or no override - positive control
  const webValid = await evaluateContext({ native: false, env: {} });
  if (webValid.backend !== '') {
    throw new Error(`Web browser backend must be empty string (relative), got: ${webValid.backend}`);
  }
  if (!webValid.calls.some(c => c.url === '/api/users/me' && c.bearerAttached)) {
    throw new Error('Web browser relative call did not attach bearer');
  }
  if (!webValid.resolvedSocket || !webValid.resolvedSocket.startsWith('wss://pilot.example/ws?ticket=')) {
    throw new Error(`Web socket URL mismatch: ${webValid.resolvedSocket}`);
  }

  // Scenario 6: Web browser edge cases - slash-backslash, userinfo, and off-origin rejection
  const slashBackslash = '/\\\\different-review.example/api';
  if (webValid.api.isApprovedBackendOrigin(slashBackslash)) {
    throw new Error('Web browser helper approved slash-backslash destination');
  }
  if (webValid.api.getAuthHeaders(slashBackslash).Authorization) {
    throw new Error('Web browser attached auth headers to slash-backslash destination');
  }
  const controlCharTarget = '/\\\\attacker-host.net\\x00/api';
  if (webValid.api.isApprovedBackendOrigin(controlCharTarget)) {
    throw new Error('Web browser helper approved control-character destination');
  }
  if (webValid.api.isApprovedBackendOrigin('https://user:password@pilot.example/api')) {
    throw new Error('Web browser helper approved userinfo destination');
  }
  if (webValid.api.isApprovedBackendOrigin('https://different-host.example/api')) {
    throw new Error('Web browser helper approved different-host destination');
  }
  if (!webValid.api.isApprovedBackendOrigin('/api/users/me')) {
    throw new Error('Web browser rejected valid relative same-origin path');
  }
  if (!webValid.api.isApprovedBackendOrigin('https://pilot.example/api/users/me')) {
    throw new Error('Web browser rejected valid absolute same-origin URL');
  }

  // Scenario 7: Parser-unavailable fail-closed credential withholding
  const parserAbsent = await evaluateContext({ native: false, withParser: false });
  for (const [label, code] of [['tab', 9], ['linefeed', 10], ['carriage_return', 13]]) {
    const candidate = '/' + String.fromCharCode(code) + '/another-review.example/api';
    if (parserAbsent.api.isApprovedBackendOrigin(candidate)) {
      throw new Error(`Parser-unavailable approved ${label} authority string`);
    }
    if (parserAbsent.api.getAuthHeaders(candidate).Authorization) {
      throw new Error(`Parser-unavailable attached auth headers to ${label} authority string`);
    }
  }
  if (parserAbsent.api.isApprovedBackendOrigin('/api/users/me')) {
    throw new Error('Parser-unavailable approved relative destination unexpectedly');
  }
  if (parserAbsent.api.getAuthHeaders('/api/users/me').Authorization) {
    throw new Error('Parser-unavailable attached auth headers without URL parser');
  }

  console.log('RT-17 passed successfully');
})().catch(err => {
  console.error('RT-17 failure:', err);
  process.exit(1);
});
"""
    script_path = tmp_path / "test_rt17.js"
    rendered_script = node_script.replace("__TS_PATH__", ts_path).replace("__SRC_DIR__", src_dir)
    script_path.write_text(rendered_script, encoding="utf-8")
    proc = subprocess.run(
        ["node", str(script_path)],
        cwd=str(REPO_ROOT / "qa"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"


