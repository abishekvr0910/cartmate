"""Runner script for qa/tests/pods-and-voice.spec.ts against a clean isolated backend instance."""
import os
import sys
import time
import shutil
import tempfile
import subprocess
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
PYTHON_EXE = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"

if not PYTHON_EXE.exists():
    PYTHON_EXE = Path(sys.executable)

PORT = 8765
BASE_URL = f"http://127.0.0.1:{PORT}"

temp_dir = tempfile.mkdtemp(prefix="cartmate-e2e-pods-")
temp_db = Path(temp_dir) / "pods_e2e.db"
log_file_path = Path(temp_dir) / "uvicorn.log"

env = os.environ.copy()
env["CARTMATE_ENV"] = "development"
env["CARTMATE_E2E_ISOLATED"] = "1"
env["CARTMATE_DATABASE_PATH"] = str(temp_db)
env["CARTMATE_FRONTEND_DIST"] = str(FRONTEND_DIST)
env["CARTMATE_MODERATOR_USER_IDS"] = "usr_zuzanna"
env["CARTMATE_BASE_URL"] = BASE_URL
env["OTP_PROVIDER"] = "console"
env["SOS_PROVIDER"] = "disabled"
env["CARTMATE_DEFAULT_REGION"] = "silesia"

print(f"[E2E RUNNER] Starting clean backend on {BASE_URL} with DB {temp_db}...")
log_f = open(log_file_path, "w", encoding="utf-8")
server_proc = subprocess.Popen(
    [
        str(PYTHON_EXE),
        "-m",
        "uvicorn",
        "main:app",
        "--app-dir",
        str(BACKEND_DIR),
        "--host",
        "127.0.0.1",
        "--port",
        str(PORT),
    ],
    env=env,
    stdout=log_f,
    stderr=subprocess.STDOUT,
    text=True,
)

try:
    # Wait for server to be responsive
    ready = False
    start_time = time.time()
    while time.time() - start_time < 20:
        if server_proc.poll() is not None:
            log_f.flush()
            with open(log_file_path, "r", encoding="utf-8") as rf:
                out = rf.read()
            raise RuntimeError(f"Server exited prematurely with code {server_proc.returncode}:\n{out}")
        try:
            with urllib.request.urlopen(f"{BASE_URL}/api/stats", timeout=2) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.5)

    if not ready:
        raise TimeoutError("Timed out waiting for backend server to respond.")

    print(f"[E2E RUNNER] Backend is live at {BASE_URL}. Running Playwright suite...")

    test_env = os.environ.copy()
    test_env["CARTMATE_E2E_ISOLATED"] = "1"
    test_env["CARTMATE_BASE_URL"] = BASE_URL

    cmd = ["npx", "playwright", "test", "tests/pods-and-voice.spec.ts"]
    print(f"[E2E RUNNER] Executing: {' '.join(cmd)}")
    pw_proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT / "qa"),
        env=test_env,
        shell=True,
    )
    sys.exit(pw_proc.returncode)

finally:
    print("[E2E RUNNER] Tearing down backend server...")
    server_proc.terminate()
    try:
        server_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_proc.kill()
    try:
        log_f.close()
    except Exception:
        pass
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
    print("[E2E RUNNER] Teardown complete.")
