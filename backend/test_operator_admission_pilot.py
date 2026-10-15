"""Contract and security tests for Slice B: Durable, bounded operator admission.

Verifies:
- Migration 9 and schema integrity
- Cryptographic token format & SHA-256 one-way hashing
- CLI issuance and revocation (never logs or stores raw token)
- Atomic, single-use redemption with rate limits
- Explicit operator_in_person assurance without faking SMS
- Separation of admission from adult 18+ attestation
- Production fail-closed enforcement
- Concurrent redemption race safety
- /api/ready status in operator staging mode
"""

import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent


def run_isolated_probe(tmp_path: Path, script: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update({
        "CARTMATE_ENV": "staging",
        "CARTMATE_DEPLOYMENT": "1",
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


def test_migration_9_and_schema_integrity(tmp_path):
    from storage import DurableStorage, get_db_connection

    db_file = tmp_path / "migration9.db"
    store = DurableStorage(str(db_file))
    conn = get_db_connection(str(db_file))
    try:
        schema_version = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
        assert schema_version >= 9

        act_cols = {row[1] for row in conn.execute("PRAGMA table_info(operator_activations)").fetchall()}
        expected_act_cols = {
            "token_hash", "intended_for", "created_at", "expires_at",
            "consumed_at", "consumed_by_user_id", "revoked_at", "created_by_operator",
        }
        assert expected_act_cols.issubset(act_cols)

        adm_cols = {row[1] for row in conn.execute("PRAGMA table_info(operator_admissions)").fetchall()}
        expected_adm_cols = {"user_id", "token_hash", "assurance_marker", "admitted_at", "revoked_at"}
        assert expected_adm_cols.issubset(adm_cols)
    finally:
        conn.close()


def test_operator_activation_hash_validation():
    from storage import operator_activation_hash

    valid_token = "CMACT-" + "A" * 24
    h = operator_activation_hash(valid_token)
    assert len(h) == 64
    assert h == hashlib.sha256(valid_token.encode("ascii")).hexdigest()

    # Normalization (lowercase input becomes uppercase)
    assert operator_activation_hash("cmact-" + "a" * 24) == h
    assert operator_activation_hash("  CMACT-" + "A" * 24 + "  ") == h

    # Rejection of invalid formats
    with pytest.raises(ValueError, match="Invalid operator activation token format"):
        operator_activation_hash("INVALID")
    with pytest.raises(ValueError, match="Invalid operator activation token format"):
        operator_activation_hash("CMACT-123")
    with pytest.raises(ValueError, match="Invalid operator activation token format"):
        operator_activation_hash("CMACT-" + "Z" * 24)  # Z is not hex


def test_issue_and_revoke_operator_activation_cli(tmp_path):
    from storage import DurableStorage, get_db_connection

    db_path = tmp_path / "cli_test.db"
    store = DurableStorage(str(db_path))

    # Test issue-activation CLI
    cli_path = REPO_ROOT / "ops" / "pilot_invites.py"
    res = subprocess.run(
        [sys.executable, str(cli_path), "--db", str(db_path), "issue-activation", "--for", "Alicja Test", "--hours", "12"],
        capture_output=True,
        text=True,
        check=True,
    )
    match = re.search(r"(CMACT-[A-F0-9]{24})", res.stdout)
    assert match is not None, f"CLI output did not contain valid token: {res.stdout}"
    raw_token = match.group(1)

    # Verify raw token is NOT stored in the database
    conn = get_db_connection(str(db_path))
    try:
        row = conn.execute("SELECT * FROM operator_activations").fetchone()
        assert row is not None
        assert row["token_hash"] == hashlib.sha256(raw_token.encode("ascii")).hexdigest()
        assert raw_token not in json.dumps(dict(row))
        assert row["intended_for"] == "Alicja Test"
        assert row["consumed_at"] is None
        assert row["revoked_at"] is None
    finally:
        conn.close()

    assert store.is_operator_activation_available(raw_token)

    # Test revoke-activation CLI
    res_rev = subprocess.run(
        [sys.executable, str(cli_path), "--db", str(db_path), "revoke-activation", "--token", raw_token],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Unconsumed activation token revoked." in res_rev.stdout
    assert not store.is_operator_activation_available(raw_token)


def test_redeem_operator_activation_valid_and_single_use(tmp_path):
    proc = run_isolated_probe(tmp_path, """
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import main
from storage import DurableStorage, storage, get_db_connection

client = TestClient(main.app)
expiry = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
raw_token = storage.issue_operator_activation(expiry, intended_for='Tester Anna')

# 1. Redeem valid token
res = client.post('/api/auth/redeem-operator-activation', json={
    'activation_token': raw_token,
    'name': 'Anna Kowalska',
    'city': 'Katowice',
    'bio': 'Pilot participant',
    'gender': 'female',
})
assert res.status_code == 200, res.text
data = res.json()
assert 'token' in data
assert data['token'].startswith('cmt_')
user = data['user']
assert user['name'] == 'Anna Kowalska'
assert user['assurance_marker'] == 'operator_in_person'
assert user['operator_admitted_at'] is not None
assert user['phone_verified_at'] is None
assert user['phone'] == ''
assert user['adult_verified_at'] is None

# User is admitted in storage
assert storage.is_operator_admitted(user['id'])
assert storage.is_pilot_member(user['id'])

# 2. Replay redemption fails (token consumed)
res2 = client.post('/api/auth/redeem-operator-activation', json={
    'activation_token': raw_token,
    'name': 'Anna Replay',
    'city': 'Katowice',
})
assert res2.status_code == 403
assert 'already consumed' in res2.text or 'invalid' in res2.text
""")
    assert proc.returncode == 0, f"Error: {proc.stderr}\nOutput: {proc.stdout}"


def test_redeem_operator_activation_expired_fails(tmp_path):
    proc = run_isolated_probe(tmp_path, """
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import main
from storage import storage, get_db_connection, operator_activation_hash

client = TestClient(main.app)
# Insert an already-expired token directly into DB
past_expiry = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
now_str = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
raw_token = 'CMACT-' + 'E' * 24
token_hash = operator_activation_hash(raw_token)

conn = get_db_connection(storage.db_path)
try:
    conn.execute(
        '''INSERT INTO operator_activations (token_hash, intended_for, created_at, expires_at)
           VALUES (?, ?, ?, ?)''',
        (token_hash, 'Expired User', now_str, past_expiry),
    )
    conn.commit()
finally:
    conn.close()

res = client.post('/api/auth/redeem-operator-activation', json={
    'activation_token': raw_token,
    'name': 'Expired Person',
    'city': 'Katowice',
})
assert res.status_code == 403, res.text
assert 'expired' in res.text or 'invalid' in res.text
""")
    assert proc.returncode == 0, f"Error: {proc.stderr}\nOutput: {proc.stdout}"


def test_redeem_operator_activation_malformed_and_unknown(tmp_path):
    proc = run_isolated_probe(tmp_path, """
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

# Malformed format fails with 422
res = client.post('/api/auth/redeem-operator-activation', json={
    'activation_token': 'NOT-A-TOKEN',
    'name': 'Malformed User',
    'city': 'Katowice',
})
assert res.status_code == 422, res.text

# Valid format but non-existent token fails with 403
res2 = client.post('/api/auth/redeem-operator-activation', json={
    'activation_token': 'CMACT-' + 'F' * 24,
    'name': 'Unknown User',
    'city': 'Katowice',
})
assert res2.status_code == 403, res2.text
""")
    assert proc.returncode == 0, f"Error: {proc.stderr}\nOutput: {proc.stdout}"


def test_redeem_operator_activation_city_boundary(tmp_path):
    proc = run_isolated_probe(tmp_path, """
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import main
from storage import storage

client = TestClient(main.app)
expiry = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
raw_token = storage.issue_operator_activation(expiry, intended_for='Tester')

# Out-of-boundary city fails with 400
res = client.post('/api/auth/redeem-operator-activation', json={
    'activation_token': raw_token,
    'name': 'Out Of Boundary',
    'city': 'Krakow',
})
assert res.status_code == 400, res.text
assert 'poza obszarem pilotażu' in res.text
""")
    assert proc.returncode == 0, f"Error: {proc.stderr}\nOutput: {proc.stdout}"


def test_redeem_operator_activation_rate_limiting(tmp_path):
    proc = run_isolated_probe(tmp_path, """
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)
for i in range(5):
    res = client.post('/api/auth/redeem-operator-activation', json={
        'activation_token': f'CMACT-{i:024X}',
        'name': 'Rate Limit Tester',
        'city': 'Katowice',
    })
    assert res.status_code in {403, 422}

# 6th attempt is rate-limited (429)
res6 = client.post('/api/auth/redeem-operator-activation', json={
    'activation_token': 'CMACT-AAAAAAAAAAAAAAAAAAAAAAAA',
    'name': 'Rate Limit Tester',
    'city': 'Katowice',
})
assert res6.status_code == 429, res6.text
assert 'Zbyt wiele prób' in res6.text
""")
    assert proc.returncode == 0, f"Error: {proc.stderr}\nOutput: {proc.stdout}"


def test_production_and_disabled_modes_strictly_fail_closed(tmp_path):
    # CARTMATE_ENV="production" strictly forbids operator activation
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
assert res.status_code == 403, res.text
assert 'prohibited in production' in res.text
""",
        extra_env={"CARTMATE_ENV": "production", "CARTMATE_OPERATOR_PILOT_ENABLED": "1"},
    )
    assert proc_prod.returncode == 0, f"Prod fail: {proc_prod.stderr}\n{proc_prod.stdout}"

    # Staging with OPERATOR_PILOT_ENABLED="0" also rejects
    proc_disabled = run_isolated_probe(
        tmp_path,
        """
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)
res = client.post('/api/auth/redeem-operator-activation', json={
    'activation_token': 'CMACT-AAAAAAAAAAAAAAAAAAAAAAAA',
    'name': 'Disabled Attempter',
    'city': 'Katowice',
})
assert res.status_code == 403, res.text
assert 'explicitly enabled' in res.text
""",
        extra_env={"CARTMATE_OPERATOR_PILOT_ENABLED": "0"},
    )
    assert proc_disabled.returncode == 0, f"Disabled fail: {proc_disabled.stderr}\n{proc_disabled.stdout}"


def test_operator_admitted_user_separate_18_plus_attestation_flow(tmp_path):
    proc = run_isolated_probe(tmp_path, """
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import main
from storage import storage
import database

client = TestClient(main.app)
expiry = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

# Issue tokens for operator moderator and participant friend
mod_token = storage.issue_operator_activation(expiry, intended_for='Moderator')
friend_token = storage.issue_operator_activation(expiry, intended_for='Friend')

# Redeem moderator account
res_mod = client.post('/api/auth/redeem-operator-activation', json={
    'activation_token': mod_token,
    'name': 'Moderator Jan',
    'city': 'Katowice',
})
assert res_mod.status_code == 200
mod_data = res_mod.json()
mod_user_id = mod_data['user']['id']
mod_headers = {'Authorization': f'Bearer {mod_data[\"token\"]}'}

# Redeem friend account
res_friend = client.post('/api/auth/redeem-operator-activation', json={
    'activation_token': friend_token,
    'name': 'Friend Anna',
    'city': 'Katowice',
})
assert res_friend.status_code == 200
friend_data = res_friend.json()
friend_user_id = friend_data['user']['id']
friend_headers = {'Authorization': f'Bearer {friend_data[\"token\"]}'}

# Configure Jan as an allowed moderator in main
main.MODERATOR_USER_IDS = frozenset({mod_user_id})

# 1. Before 18+ attestation: friend cannot access live social outings / pings
res_pings = client.get('/api/pings', headers=friend_headers)
assert res_pings.status_code == 403, f'Expected 403, got {res_pings.status_code}: {res_pings.text}'
assert 'potwierdzenia pełnoletności' in res_pings.text

# 2. Friend requests challenge for witnessed in-person check
res_challenge = client.post('/api/users/me/age-check-challenge', headers=friend_headers)
assert res_challenge.status_code == 200
challenge = res_challenge.json()['challenge']

# 3. Moderator cannot attest their own age
self_attest = client.post(
    f'/api/moderation/users/{mod_user_id}/adult-attestation',
    headers=mod_headers,
    json={
        'method': 'mdowod_qr',
        'confirmed_over_18': True,
        'subject_present': True,
        'subject_consented': True,
        'account_bound': True,
        'account_challenge': challenge,
    },
)
assert self_attest.status_code == 403
assert 'cannot approve their own age' in self_attest.text

# 4. Moderator attests friend
attest = client.post(
    f'/api/moderation/users/{friend_user_id}/adult-attestation',
    headers=mod_headers,
    json={
        'method': 'mdowod_qr',
        'confirmed_over_18': True,
        'subject_present': True,
        'subject_consented': True,
        'account_bound': True,
        'account_challenge': challenge,
    },
)
assert attest.status_code == 200, attest.text
assert attest.json()['adult_verified'] is True

# 5. After attestation: friend CAN access live pings!
res_pings_after = client.get('/api/pings', headers=friend_headers)
assert res_pings_after.status_code == 200, res_pings_after.text

# 6. Revocation locks friend back out
rev = client.post(
    f'/api/moderation/users/{friend_user_id}/adult-attestation/revoke',
    headers=mod_headers,
)
assert rev.status_code == 200
assert rev.json()['adult_verified'] is False

res_pings_revoked = client.get('/api/pings', headers=friend_headers)
assert res_pings_revoked.status_code == 403
""")
    assert proc.returncode == 0, f"Error: {proc.stderr}\nOutput: {proc.stdout}"


def test_concurrent_redemption_allows_only_one_winner(tmp_path):
    proc = run_isolated_probe(tmp_path, """
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import main
from storage import storage

expiry = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
raw_token = storage.issue_operator_activation(expiry, intended_for='Race Tester')

def try_redeem(name):
    client = TestClient(main.app)
    return client.post('/api/auth/redeem-operator-activation', json={
        'activation_token': raw_token,
        'name': name,
        'city': 'Katowice',
    }).status_code

with ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(try_redeem, ['User One', 'User Two']))

assert sorted(results) == [200, 403], f'Expected [200, 403], got {sorted(results)}'
""")
    assert proc.returncode == 0, f"Error: {proc.stderr}\nOutput: {proc.stdout}"


def test_launch_readiness_in_operator_pilot_staging(tmp_path):
    proc = run_isolated_probe(tmp_path, """
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import main
from storage import storage

client = TestClient(main.app)
ready = client.get('/api/ready')
assert ready.status_code == 503
data = ready.json()
blockers = data['blockers']

# In operator pilot mode, SMS OTP provider must NOT be a blocker
assert not any('SMS OTP' in b or 'SMSAPI' in b or 'Twilio' in b for b in blockers), f'Found SMS blockers: {blockers}'
assert data['operator_pilot_enabled'] is True
assert data['ordinary_outings_require'] == 'operator_admission_or_sms_and_approved_18_plus_proof'
""")
    assert proc.returncode == 0, f"Error: {proc.stderr}\nOutput: {proc.stdout}"


def test_full_no_sms_outing_join_chat_flow(tmp_path):
    proc = run_isolated_probe(tmp_path, """
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import main
from storage import storage

client = TestClient(main.app)
expiry = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

# 1. Issue operator activation tokens for two participants
token_host = storage.issue_operator_activation(expiry, intended_for='Host Friend')
token_guest = storage.issue_operator_activation(expiry, intended_for='Guest Friend')

# 2. Redeem activation tokens (no SMS phone verification)
res_host = client.post('/api/auth/redeem-operator-activation', json={
    'activation_token': token_host,
    'name': 'Anna Host',
    'city': 'Katowice',
})
assert res_host.status_code == 200, res_host.text
host_user = res_host.json()['user']
host_headers = {'Authorization': f'Bearer {res_host.json()[\"token\"]}'}
assert host_user['phone_verified_at'] is None
assert host_user['assurance_marker'] == 'operator_in_person'

res_guest = client.post('/api/auth/redeem-operator-activation', json={
    'activation_token': token_guest,
    'name': 'Piotr Guest',
    'city': 'Katowice',
})
assert res_guest.status_code == 200, res_guest.text
guest_user = res_guest.json()['user']
guest_headers = {'Authorization': f'Bearer {res_guest.json()[\"token\"]}'}
assert guest_user['phone_verified_at'] is None
assert guest_user['assurance_marker'] == 'operator_in_person'

# Allow both in moderator set for mutual peer attestation
main.MODERATOR_USER_IDS = frozenset({host_user['id'], guest_user['id']})

# 3. Adult 18+ attestation flow
# Guest attests Host
ch_host = client.post('/api/users/me/age-check-challenge', headers=host_headers).json()['challenge']
attest_host = client.post(
    f'/api/moderation/users/{host_user[\"id\"]}/adult-attestation',
    headers=guest_headers,
    json={
        'method': 'mdowod_qr',
        'confirmed_over_18': True,
        'subject_present': True,
        'subject_consented': True,
        'account_bound': True,
        'account_challenge': ch_host,
    },
)
assert attest_host.status_code == 200, attest_host.text

# Host attests Guest
ch_guest = client.post('/api/users/me/age-check-challenge', headers=guest_headers).json()['challenge']
attest_guest = client.post(
    f'/api/moderation/users/{guest_user[\"id\"]}/adult-attestation',
    headers=host_headers,
    json={
        'method': 'mdowod_qr',
        'confirmed_over_18': True,
        'subject_present': True,
        'subject_consented': True,
        'account_bound': True,
        'account_challenge': ch_guest,
    },
)
assert attest_guest.status_code == 200, attest_guest.text

# 4. Host creates an outing (LivePing) - VERIFIES FIX FOR NO-SMS BLOCKER
res_ping = client.post('/api/pings', headers=host_headers, json={
    'category': 'grocery',
    'destination_name': 'Biedronka Katowice',
    'destination_lat': 50.2649,
    'destination_lng': 19.0238,
    'address': 'ul. Stawowa 10, Katowice',
    'intent_tags': ['zakupy', 'owoce'],
    'ttl_minutes': 45,
    'notes': 'Szybkie zakupy spożywcze',
})
assert res_ping.status_code == 200, f'Expected 200, got {res_ping.status_code}: {res_ping.text}'
ping = res_ping.json()
assert ping['host']['id'] == host_user['id']

# 5. Guest requests to join the outing
res_join = client.post(
    f'/api/pings/{ping[\"id\"]}/join',
    headers=guest_headers,
    json={'message': 'Cześć! Chętnie dołączę do zakupów.'},
)
assert res_join.status_code == 200, res_join.text
join_req = res_join.json()
assert join_req['applicant']['id'] == guest_user['id']

# 6. Host accepts the join request -> spawns trip & chat room
res_accept = client.post(
    f'/api/pings/{ping[\"id\"]}/requests/{join_req[\"id\"]}/accept',
    headers=host_headers,
)
assert res_accept.status_code == 200, res_accept.text
trip = res_accept.json()
assert trip['companion']['id'] == guest_user['id']
chat_room_id = trip['chat_room_id']
assert chat_room_id

# 7. Guest sends a message in the outing chat room
res_msg1 = client.post(
    f'/api/chat/rooms/{chat_room_id}/messages',
    headers=guest_headers,
    json={'text': 'Hej, będę pod Biedronką za 10 minut.'},
)
assert res_msg1.status_code == 200, res_msg1.text
msg1 = res_msg1.json()
assert msg1['sender_id'] == guest_user['id']

# 8. Host replies in the chat room
res_msg2 = client.post(
    f'/api/chat/rooms/{chat_room_id}/messages',
    headers=host_headers,
    json={'text': 'Super, czekam przy wejściu!'},
)
assert res_msg2.status_code == 200, res_msg2.text
msg2 = res_msg2.json()
assert msg2['sender_id'] == host_user['id']

# 9. Verify chat room messages history (initial system greeting + 2 user messages)
room = client.get(f'/api/chat/rooms/{chat_room_id}', headers=host_headers).json()
assert len(room['messages']) == 3
assert room['messages'][0]['sender_id'] == 'system'
assert room['messages'][1]['text'] == 'Hej, będę pod Biedronką za 10 minut.'
assert room['messages'][2]['text'] == 'Super, czekam przy wejściu!'
""")
    assert proc.returncode == 0, f"Error: {proc.stderr}\nOutput: {proc.stdout}"
