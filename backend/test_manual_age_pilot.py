"""Fail-closed contracts for human-attested, invite-only staging age checks."""

import os
import subprocess
import sys

from test_staging_rehearsal import BACKEND_DIR, run_staging_probe


def test_staging_operator_age_attestation_is_witnessed_audited_and_revocable(tmp_path):
    run_staging_probe(tmp_path, """
from datetime import datetime, timezone
from fastapi.testclient import TestClient
import database
import main
from storage import get_db_connection, storage

client = TestClient(main.app)
now = datetime.now(timezone.utc).isoformat()
operator = database.create_user(
    name='Operator', email='operator@example.invalid', phone='+48600111001',
    gender='unspecified', city='Katowice', phone_verified_at=now,
    pilot_invite_code=storage.issue_pilot_invite('2099-01-01T00:00:00+00:00'),
)
friend = database.create_user(
    name='Friend', email='friend@example.invalid', phone='+48600111002',
    gender='unspecified', city='Katowice', phone_verified_at=now,
    pilot_invite_code=storage.issue_pilot_invite('2099-01-01T00:00:00+00:00'),
)
main.MODERATOR_USER_IDS = frozenset({operator.id})
main.persist_active_session('cmt_operator_test', operator.id)
main.persist_active_session('cmt_friend_test', friend.id)
operator_headers = {'Authorization': 'Bearer cmt_operator_test'}
friend_headers = {'Authorization': 'Bearer cmt_friend_test'}
path = f'/api/moderation/users/{friend.id}/adult-attestation'
issued = client.post('/api/users/me/age-check-challenge', headers=friend_headers)
assert issued.status_code == 200, issued.text
assert issued.headers['cache-control'] == 'no-store'
assert issued.json()['account_code'] == friend.id
valid = {
    'method': 'mdowod_qr', 'confirmed_over_18': True,
    'subject_present': True, 'subject_consented': True, 'account_bound': True,
    'account_challenge': issued.json()['challenge'],
}

assert main.MANUAL_AGE_PILOT_ENABLED
assert any('two active moderators' in item for item in client.get('/api/ready').json()['blockers'])
assert client.get('/api/users/me/admission', headers=friend_headers).json()['live_access'] is False
assert client.get('/api/pings', headers=friend_headers).status_code == 403
assert client.post(path, headers=friend_headers, json=valid).status_code == 403
assert client.post(f'/api/moderation/users/{operator.id}/adult-attestation', headers=operator_headers, json=valid).status_code == 403
assert client.post(path, headers=operator_headers, json={**valid, 'subject_consented': False}).status_code == 422
assert client.post(path, headers=operator_headers, json={**valid, 'confirmed_over_18': False}).status_code == 422
assert client.post(path, headers=operator_headers, json={**valid, 'document_number': 'must-not-be-accepted'}).status_code == 422
assert client.post(path, headers=operator_headers, json={**valid, 'account_challenge': 'wrong-challenge'}).status_code == 403
assert client.post('/api/auth/revoke-other-sessions', headers=friend_headers).status_code == 200
assert client.post(path, headers=operator_headers, json=valid).status_code == 403
valid['account_challenge'] = client.post('/api/users/me/age-check-challenge', headers=friend_headers).json()['challenge']

approved = client.post(path, headers=operator_headers, json=valid)
assert approved.status_code == 200, approved.text
assert approved.json()['adult_verified'] is True
assert client.get('/api/users/me/admission', headers=friend_headers).json()['live_access'] is True
assert client.get('/api/pings', headers=friend_headers).status_code == 200
assert client.post(path, headers=operator_headers, json=valid).status_code == 403
assert storage.load_users()[friend.id]['age_assurance_provider'] == 'operator_mdowod_qr'
conn = get_db_connection(storage.db_path)
try:
    audit = dict(conn.execute('SELECT * FROM pilot_age_attestations WHERE subject_user_id = ?', (friend.id,)).fetchone())
finally:
    conn.close()
assert audit['moderator_user_id'] == operator.id
assert audit['method'] == 'mdowod_qr'
assert audit['decision'] == 'confirmed_adult'
assert friend.phone not in str(audit) and friend.email not in str(audit)
assert 'document_number' not in str(audit)

database.USERS[friend.id].phone_verified_at = None
assert client.get('/api/pings', headers=friend_headers).status_code == 403
database.USERS[friend.id].phone_verified_at = now
revoked = client.post(path + '/revoke', headers=operator_headers)
assert revoked.status_code == 200, revoked.text
assert client.get('/api/users/me/admission', headers=friend_headers).json()['live_access'] is False
assert client.get('/api/pings', headers=friend_headers).status_code == 403
assert storage.load_users()[friend.id]['age_assurance_provider'] is None
""", extra_env={
        "CARTMATE_PILOT_INVITES_ENABLED": "1",
        "CARTMATE_MANUAL_AGE_PILOT_ENABLED": "1",
    })


def test_manual_pilot_age_check_never_enables_production(tmp_path):
    env = os.environ.copy()
    env.update({
        "CARTMATE_ENV": "production",
        "CARTMATE_DEPLOYMENT": "0",
        "CARTMATE_PILOT_INVITES_ENABLED": "1",
        "CARTMATE_MANUAL_AGE_PILOT_ENABLED": "1",
        "CARTMATE_DATABASE_PATH": str(tmp_path / "prod_age_probe.db"),
    })
    result = subprocess.run(
        [sys.executable, "-c", "from config import MANUAL_AGE_PILOT_ENABLED; assert not MANUAL_AGE_PILOT_ENABLED"],
        cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stderr
