#!/usr/bin/env python3
"""Read-only security and readiness preflight for the zero-cost CartMate operator-admission pilot.

Validates that:
1. The server reports staging environment with operator pilot enabled.
2. SOS provider is disabled (direct-112 fallback only).
3. The active launch region is Silesia.
4. Protected routes reject missing credentials and legacy demo tokens.
5. Shipped router contains zero QA/test-helper endpoints.
6. The readiness probe (/api/ready) reports blockers honestly.

This script never sends SMS, creates accounts, issues tokens, or invokes external AI APIs.
"""

import argparse
import json
import sys
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def validate_origin(value: str, allow_loopback: bool = False) -> str:
    parsed = urlparse(value)
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Use only a clean origin, without credentials, path, query, or fragment")
    if parsed.path not in {"", "/"}:
        raise ValueError("Origin must not include a path component")

    is_loopback = parsed.hostname in {"127.0.0.1", "localhost"}
    if is_loopback:
        if not allow_loopback:
            raise ValueError(
                "Origin uses loopback HTTP. For production/pilot use, provide an HTTPS origin (e.g. Tailscale Serve). "
                "Pass --allow-loopback only for isolated local testing."
            )
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Loopback origin must use http or https")
    else:
        if parsed.scheme != "https":
            raise ValueError("Private pilot origin must use HTTPS (e.g. https://<tailnet-node>.ts.net)")

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


def run_checks(origin: str, allow_loopback: bool = False) -> list[str]:
    valid_origin = validate_origin(origin, allow_loopback=allow_loopback)

    # 1. Health and environment configuration
    health_status, health = get_json(valid_origin, "/api/health")
    if health_status != 200 or health.get("environment") != "staging":
        raise RuntimeError(f"Target did not report healthy staging environment (status {health_status}, env: {health.get('environment')})")

    # Operator pilot must be active in staging
    if not health.get("operator_pilot_enabled", False):
        raise RuntimeError("Operator pilot mode is not enabled on the server (expected operator_pilot_enabled=True)")

    # Safety: SOS must be direct-112 only (disabled provider), JEV mode must be disabled
    providers = health.get("providers", {})
    if providers.get("sos") != "disabled":
        raise RuntimeError(f"SOS provider must be 'disabled' (direct 112 voice fallback only), observed: {providers.get('sos')}")
    if providers.get("jev_mode") != "disabled":
        raise RuntimeError(f"JEV mode must be 'disabled' (no AI automation in private pilot), observed: {providers.get('jev_mode')}")

    # Verify environment configuration endpoint matches
    env_status, env_cfg = get_json(valid_origin, "/api/config/environment")
    if env_status != 200 or env_cfg.get("environment") != "staging":
        raise RuntimeError(f"/api/config/environment must report staging environment (status {env_status}, env: {env_cfg.get('environment')})")
    if not env_cfg.get("operator_pilot_enabled", False):
        raise RuntimeError("Operator pilot mode is not reported enabled in /api/config/environment")

    # 2. Region check: Silesia is the approved launch region
    region_status, region = get_json(valid_origin, "/api/config/regions")
    if region_status != 200 or region.get("active_region", {}).get("id") != "silesia":
        raise RuntimeError("The active launch region is not Silesia")

    # 3. Security invariants: demo tokens and missing auth must be rejected (401)
    for path, token in (
        ("/api/users/me", None),
        ("/api/pings", None),
        ("/api/users/me", "token_jakub"),
        ("/api/users/me", "token_zuzanna"),
    ):
        status_code, _ = get_json(valid_origin, path, token)
        if status_code != 401:
            raise RuntimeError(f"Security invariant failed: {path} accepted invalid/demo credential (HTTP {status_code})")

    # 4. QA helper route isolation: shipped app must contain zero QA routes (404)
    for qa_path in (
        "/_op_qa/operator-credentials",
        "/_op_qa/issue-token",
        "/_qa/reset-rate-limits",
    ):
        status_code, _ = get_json(valid_origin, qa_path)
        if status_code != 404:
            raise RuntimeError(f"QA helper isolation failed: {qa_path} returned HTTP {status_code} (expected 404 Not Found on shipped server)")

    # 5. Readiness probe
    ready_status, readiness = get_json(valid_origin, "/api/ready")
    if ready_status == 200 and readiness.get("status") == "ready" and not readiness.get("blockers"):
        return []
    if ready_status == 503 and readiness.get("status") == "blocked":
        blockers = readiness.get("blockers", [])
        return [str(b) for b in blockers]

    raise RuntimeError(f"Unexpected /api/ready response: HTTP {ready_status}, body: {readiness}")


def main() -> int:
    parser = argparse.ArgumentParser(description="CartMate zero-cost operator-pilot security and readiness preflight")
    parser.add_argument("--base-url", required=True, help="Base origin URL (e.g. https://<node>.ts.net)")
    parser.add_argument("--allow-loopback", action="store_true", help="Permit http://127.0.0.1 or localhost for local testing")
    parser.add_argument("--require-ready", action="store_true", help="Exit with code 2 if /api/ready reports blockers")
    args = parser.parse_args()

    try:
        blockers = run_checks(args.base_url, allow_loopback=args.allow_loopback)
        if blockers:
            print("HOLD: Pilot security checks passed, but /api/ready reports blockers:")
            for b in blockers:
                print(f"  - {b}")
            return 2 if args.require_ready else 0

        print("PASS: Pilot security checks and /api/ready passed cleanly.")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
