"""Unit and contract tests for ops/pilot_preflight.py."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import pytest

from ops.pilot_preflight import validate_origin, run_checks


class MockPreflightHandler(BaseHTTPRequestHandler):
    scenario = "happy"  # happy, non_staging, no_operator, sos_enabled, wrong_region, demo_leak, qa_leak, blocked_ready

    def log_message(self, format, *args):
        pass  # Suppress logging

    def do_GET(self):
        auth = self.headers.get("Authorization", "")

        if self.path == "/api/health":
            if self.scenario == "non_staging":
                self._send_json(200, {"environment": "development", "operator_pilot_enabled": True, "providers": {"sos": "disabled", "jev_mode": "disabled"}})
            elif self.scenario == "no_operator":
                self._send_json(200, {"environment": "staging", "operator_pilot_enabled": False, "providers": {"sos": "disabled", "jev_mode": "disabled"}})
            elif self.scenario == "sos_enabled":
                self._send_json(200, {"environment": "staging", "operator_pilot_enabled": True, "providers": {"sos": "twilio", "jev_mode": "disabled"}})
            elif self.scenario == "jev_enabled":
                self._send_json(200, {"environment": "staging", "operator_pilot_enabled": True, "providers": {"sos": "disabled", "jev_mode": "shadow"}})
            else:
                self._send_json(200, {"environment": "staging", "operator_pilot_enabled": True, "providers": {"sos": "disabled", "jev_mode": "disabled"}})

        elif self.path == "/api/config/environment":
            if self.scenario == "non_staging":
                self._send_json(200, {"environment": "development", "operator_pilot_enabled": True})
            elif self.scenario == "no_operator":
                self._send_json(200, {"environment": "staging", "operator_pilot_enabled": False})
            else:
                self._send_json(200, {"environment": "staging", "operator_pilot_enabled": True})

        elif self.path == "/api/config/regions":
            if self.scenario == "wrong_region":
                self._send_json(200, {"active_region": {"id": "warsaw"}})
            else:
                self._send_json(200, {"active_region": {"id": "silesia"}})

        elif self.path in ("/api/users/me", "/api/pings"):
            if self.scenario == "demo_leak" and "token_jakub" in auth:
                self._send_json(200, {"id": "usr_jakub"})
            else:
                self._send_json(401, {"detail": "Not authenticated"})

        elif self.path.startswith("/_op_qa/") or self.path.startswith("/_qa/"):
            if self.scenario == "qa_leak":
                self._send_json(200, {"status": "debug"})
            else:
                self._send_json(404, {"detail": "Not found"})

        elif self.path == "/api/ready":
            if self.scenario == "blocked_ready":
                self._send_json(503, {"status": "blocked", "blockers": ["age_provider_missing"]})
            else:
                self._send_json(200, {"status": "ready", "blockers": []})

        else:
            self._send_json(404, {"detail": "Not found"})

    def _send_json(self, status: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(scope="module")
def mock_server():
    server = HTTPServer(("127.0.0.1", 0), MockPreflightHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, f"http://127.0.0.1:{port}"
    server.shutdown()


def test_validate_origin_positive():
    assert validate_origin("https://operator-host.ts.net") == "https://operator-host.ts.net"
    assert validate_origin("https://operator-host.ts.net/") == "https://operator-host.ts.net"
    assert validate_origin("http://127.0.0.1:8000", allow_loopback=True) == "http://127.0.0.1:8000"


def test_validate_origin_negative():
    with pytest.raises(ValueError, match="Private pilot origin must use HTTPS"):
        validate_origin("http://operator-host.ts.net")

    with pytest.raises(ValueError, match="loopback HTTP"):
        validate_origin("http://127.0.0.1:8000", allow_loopback=False)

    with pytest.raises(ValueError, match="path component"):
        validate_origin("https://operator-host.ts.net/api")

    with pytest.raises(ValueError, match="clean origin"):
        validate_origin("https://user:pass@operator-host.ts.net")


def test_run_checks_happy_path(mock_server):
    server, base_url = mock_server
    server.RequestHandlerClass.scenario = "happy"
    blockers = run_checks(base_url, allow_loopback=True)
    assert blockers == []


def test_run_checks_blocked_ready(mock_server):
    server, base_url = mock_server
    server.RequestHandlerClass.scenario = "blocked_ready"
    blockers = run_checks(base_url, allow_loopback=True)
    assert blockers == ["age_provider_missing"]


def test_run_checks_non_staging(mock_server):
    server, base_url = mock_server
    server.RequestHandlerClass.scenario = "non_staging"
    with pytest.raises(RuntimeError, match="healthy staging environment"):
        run_checks(base_url, allow_loopback=True)


def test_run_checks_operator_pilot_disabled(mock_server):
    server, base_url = mock_server
    server.RequestHandlerClass.scenario = "no_operator"
    with pytest.raises(RuntimeError, match="Operator pilot mode is not enabled"):
        run_checks(base_url, allow_loopback=True)


def test_run_checks_sos_enabled(mock_server):
    server, base_url = mock_server
    server.RequestHandlerClass.scenario = "sos_enabled"
    with pytest.raises(RuntimeError, match="SOS provider must be 'disabled'"):
        run_checks(base_url, allow_loopback=True)


def test_run_checks_jev_enabled(mock_server):
    server, base_url = mock_server
    server.RequestHandlerClass.scenario = "jev_enabled"
    with pytest.raises(RuntimeError, match="JEV mode must be 'disabled'"):
        run_checks(base_url, allow_loopback=True)


def test_run_checks_wrong_region(mock_server):
    server, base_url = mock_server
    server.RequestHandlerClass.scenario = "wrong_region"
    with pytest.raises(RuntimeError, match="active launch region is not Silesia"):
        run_checks(base_url, allow_loopback=True)


def test_run_checks_demo_leak(mock_server):
    server, base_url = mock_server
    server.RequestHandlerClass.scenario = "demo_leak"
    with pytest.raises(RuntimeError, match="Security invariant failed"):
        run_checks(base_url, allow_loopback=True)


def test_run_checks_qa_leak(mock_server):
    server, base_url = mock_server
    server.RequestHandlerClass.scenario = "qa_leak"
    with pytest.raises(RuntimeError, match="QA helper isolation failed"):
        run_checks(base_url, allow_loopback=True)


def test_preflight_real_fastapi_app(monkeypatch, tmp_path):
    """Real FastAPI integration verifying preflight against the actual application endpoints."""
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    if str(root / "backend") not in sys.path:
        sys.path.insert(0, str(root / "backend"))
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    test_db = str(tmp_path / "real_preflight.db")
    monkeypatch.setenv("CARTMATE_ENV", "staging")
    monkeypatch.setenv("CARTMATE_DEPLOYMENT", "0")
    monkeypatch.setenv("CARTMATE_OPERATOR_PILOT_ENABLED", "1")
    monkeypatch.setenv("CARTMATE_MANUAL_AGE_PILOT_ENABLED", "1")
    monkeypatch.setenv("CARTMATE_DATABASE_PATH", test_db)
    monkeypatch.setenv("CARTMATE_CORS_ALLOWED_ORIGINS", "https://operator-host.ts.net")
    monkeypatch.setenv("CARTMATE_DEFAULT_REGION", "silesia")
    monkeypatch.setenv("OTP_PROVIDER", "console")
    monkeypatch.setenv("SOS_PROVIDER", "disabled")
    monkeypatch.setenv("JEV_MODE", "disabled")
    monkeypatch.setenv("SOS_WEBHOOK_SECRET", "synthetic-secret-for-preflight-test")

    from fastapi.testclient import TestClient
    import main as application
    from ops import pilot_preflight

    with TestClient(application.app) as client:
        def test_client_get_json(origin, route, token=None):
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            res = client.get(route, headers=headers)
            return res.status_code, res.json()

        monkeypatch.setattr(pilot_preflight, "get_json", test_client_get_json)
        blockers = pilot_preflight.run_checks("https://operator-host.ts.net")
        assert isinstance(blockers, list)
        # Without populated moderators, blockers will correctly list moderator requirement
        assert any("moderator" in b.lower() for b in blockers)

