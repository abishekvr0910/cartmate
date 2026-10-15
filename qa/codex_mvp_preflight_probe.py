"""Compare the real shipped API with the new preflight, without HTTP or real data.

Run from repository root: python qa/codex_mvp_preflight_probe.py
Exit 1 means a reproduced contract mismatch; exit 2 is probe setup failure.
"""
import json
import os
from pathlib import Path
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix="cartmate-codex-preflight-") as scratch:
        os.environ.update({
            "CARTMATE_ENV": "staging", "CARTMATE_DEPLOYMENT": "0",
            "CARTMATE_OPERATOR_PILOT_ENABLED": "1", "CARTMATE_MANUAL_AGE_PILOT_ENABLED": "1",
            "CARTMATE_DATABASE_PATH": str(Path(scratch) / "probe.db"),
            "CARTMATE_FRONTEND_DIST": str(root / "frontend" / "dist"),
            "CARTMATE_CORS_ALLOWED_ORIGINS": "https://pilot.example",
            "CARTMATE_DEFAULT_REGION": "silesia", "OTP_PROVIDER": "console",
            "SOS_PROVIDER": "disabled", "JEV_MODE": "disabled",
            "SOS_WEBHOOK_SECRET": "synthetic-probe-secret-not-deployed",
        })
        sys.path[:0] = [str(root / "backend"), str(root)]
        from fastapi.testclient import TestClient
        import main as application
        from ops import pilot_preflight
        with TestClient(application.app) as client:
            def real_json(origin, route, token=None):
                headers = {"Authorization": f"Bearer {token}"} if token else {}
                res = client.get(route, headers=headers)
                return res.status_code, res.json()

            pilot_preflight.get_json = real_json
            result = {
                "actual_operator_mode": client.get('/api/config/environment').json()['operator_pilot_enabled'],
                "health_contains_operator_flag": 'operator_pilot_enabled' in client.get('/api/health').json(),
            }
            try:
                result['blockers'] = pilot_preflight.run_checks('https://pilot.example')
                result['contract_error'] = None
            except RuntimeError as error:
                result['contract_error'] = str(error)
            print(json.dumps(result, sort_keys=True))
            return 1 if result['contract_error'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
