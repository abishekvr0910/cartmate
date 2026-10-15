#!/usr/bin/env python3
"""Operator-run staging OTP smoke check; sends one real SMS only with explicit opt-in."""

import argparse
import getpass
import json
import re
import sys
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

IMPOSSIBLE_OTP_CODE = "000000"  # Generated codes are 100000-999999.


def validate_target(base_url: str, phone: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("Use only the HTTPS staging origin, without credentials, path, query, or fragment")
    if not re.fullmatch(r"\+48\d{9}", phone):
        raise ValueError("Use an approved Polish test number in +48 followed by nine digits format")
    return base_url.rstrip("/")


def validate_otp_code(code: str) -> str:
    if not re.fullmatch(r"\d{6}", code):
        raise ValueError("Expected a six-digit code; stopping without verification")
    return code


def call_api(base_url: str, path: str, *, method: str = "GET", payload: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{base_url}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        # Do not print response bodies: gateways and auth endpoints may include PII.
        error.read()
        return error.code, {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify one real OTP on a controlled staging handset")
    parser.add_argument("--base-url", required=True, help="HTTPS staging origin")
    parser.add_argument("--test-phone", required=True, help="Approved test phone, +48XXXXXXXXX")
    parser.add_argument("--yes-send-one-sms", action="store_true", help="Explicitly authorize one carrier SMS")
    args = parser.parse_args()
    try:
        base_url = validate_target(args.base_url, args.test_phone)
        if not args.yes_send_one_sms:
            raise ValueError("No SMS sent. Add --yes-send-one-sms only after approving the controlled test number")

        health_status, health = call_api(base_url, "/api/health")
        if health_status != 200 or health.get("environment") != "staging":
            raise RuntimeError("Target is not a healthy staging API; no SMS sent")
        if health.get("providers", {}).get("sos") != "disabled":
            raise RuntimeError("Staging SOS is not direct-112-only; no SMS sent")
        if health.get("providers", {}).get("otp") not in {"smsapi", "twilio"}:
            raise RuntimeError("Staging OTP provider is not a carrier gateway; no SMS sent")

        print("Staging target checked. Requesting one OTP on the approved handset...")
        status, requested = call_api(base_url, "/api/auth/otp/request", method="POST", payload={"identifier": args.test_phone})
        if status != 200 or requested.get("status") != "sent":
            raise RuntimeError(f"OTP was not confirmed sent (HTTP {status}); no success claimed")
        if requested.get("dev_code") is not None:
            raise RuntimeError("Staging exposed a development OTP code")

        code = validate_otp_code(getpass.getpass("Enter the code received on the test handset (not logged): ").strip())

        token = None
        try:
            # Exercise the incorrect-code path with a valid-shape code.
            wrong_status, _ = call_api(base_url, "/api/auth/otp/verify", method="POST", payload={"identifier": args.test_phone, "code": IMPOSSIBLE_OTP_CODE})
            if wrong_status != 400:
                raise RuntimeError(f"Wrong OTP was not rejected as expected (HTTP {wrong_status})")
            verified_status, verified = call_api(base_url, "/api/auth/otp/verify", method="POST", payload={"identifier": args.test_phone, "code": code})
            if verified_status != 200 or not str(verified.get("token", "")).startswith("cmt_"):
                raise RuntimeError(f"Correct OTP did not create a session (HTTP {verified_status})")
            token = verified["token"]
            replay_status, _ = call_api(base_url, "/api/auth/otp/verify", method="POST", payload={"identifier": args.test_phone, "code": code})
            if replay_status != 400:
                raise RuntimeError(f"OTP replay was not rejected (HTTP {replay_status})")
            me_status, _ = call_api(base_url, "/api/users/me", token=token)
            if me_status != 200:
                raise RuntimeError(f"Authenticated profile read failed (HTTP {me_status})")
            queue_status, _ = call_api(base_url, "/api/moderation/queue", token=token)
            if queue_status != 403:
                raise RuntimeError(f"Ordinary test account reached moderation queue (HTTP {queue_status})")
            switch_status, _ = call_api(base_url, "/api/auth/switch-user?user_id=usr_jakub", method="POST", token=token)
            if switch_status != 403:
                raise RuntimeError(f"Demo user-switching was not blocked (HTTP {switch_status})")
        finally:
            if token:
                logout_status, _ = call_api(base_url, "/api/auth/logout", method="POST", token=token)
                revoked_status, _ = call_api(base_url, "/api/users/me", token=token)
                if logout_status != 200 or revoked_status != 401:
                    raise RuntimeError("Session logout/revocation check failed")
        print("PASS: carrier OTP received, denial/replay rules held, and session was revoked.")
        return 0
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
