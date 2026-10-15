#!/usr/bin/env python3
"""Read-only HTTPS staging checks. This script never requests an OTP or sends SMS."""

import argparse
import json
import sys
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def validate_origin(value: str) -> str:
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("Use only the HTTPS staging origin, without credentials, path, query, or fragment")
    return value.rstrip("/")


def get_json(origin: str, path: str, token: str | None = None) -> tuple[int, dict]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{origin}{path}", headers=headers, method="GET")
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        try:
            payload = json.load(error)
        except (ValueError, UnicodeDecodeError):
            payload = {}
        return error.code, payload if isinstance(payload, dict) else {}


def run_checks(origin: str) -> list[str]:
    health_status, health = get_json(origin, "/api/health")
    if health_status != 200 or health.get("environment") != "staging":
        raise RuntimeError("Target did not report a healthy staging environment")
    providers = health.get("providers", {})
    if providers.get("otp") not in {"smsapi", "twilio"} or providers.get("sos") != "disabled":
        raise RuntimeError("Staging must use a carrier-backed OTP provider and direct-112-only SOS")

    region_status, region = get_json(origin, "/api/config/regions")
    if region_status != 200 or region.get("active_region", {}).get("id") != "silesia":
        raise RuntimeError("The active launch region is not Silesia")

    for path, token in (
        ("/api/users/me", None),
        ("/api/pings", None),
        ("/api/users/me", "token_jakub"),
    ):
        status_code, _ = get_json(origin, path, token)
        if status_code != 401:
            raise RuntimeError(f"Protected path {path} accepted a missing or demo credential (HTTP {status_code})")

    ready_status, readiness = get_json(origin, "/api/ready")
    if ready_status == 200 and readiness.get("status") == "ready" and not readiness.get("blockers"):
        return []
    if ready_status != 503 or readiness.get("status") != "blocked":
        raise RuntimeError(f"Unexpected readiness response (HTTP {ready_status})")
    blockers = readiness.get("blockers")
    if not isinstance(blockers, list) or not blockers:
        raise RuntimeError("Readiness is blocked without specific reasons")
    return [str(blocker) for blocker in blockers]


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only CartMate staging security and readiness preflight")
    parser.add_argument("--base-url", required=True, help="HTTPS staging origin, without a path")
    parser.add_argument("--require-ready", action="store_true", help="Fail if /api/ready is not 200")
    args = parser.parse_args()
    try:
        blockers = run_checks(validate_origin(args.base_url))
        if blockers:
            print("HOLD: staging security checks passed, but /api/ready is blocked:")
            for blocker in blockers:
                print(f"- {blocker}")
            return 2 if args.require_ready else 0
        print("PASS: staging security checks and /api/ready passed. Carrier, backup, and human review require separate evidence.")
        return 0
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
