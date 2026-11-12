import os
import sys
import tempfile
import atexit
import shutil
from pathlib import Path

# Add backend to sys.path so root pytest runs can import backend modules cleanly
_backend_path = str(Path(__file__).resolve().parent / "backend")
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

# Guarantee test database isolation across all pytest runs from repo root
if "CARTMATE_DATABASE_PATH" not in os.environ:
    _test_db_dir = tempfile.mkdtemp(prefix="cartmate_pytest_root_")
    _test_db_path = os.path.join(_test_db_dir, "test_cartmate.db")
    os.environ["CARTMATE_DATABASE_PATH"] = _test_db_path

    def _cleanup_test_db():
        shutil.rmtree(_test_db_dir, ignore_errors=True)

    atexit.register(_cleanup_test_db)
