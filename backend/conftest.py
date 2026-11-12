import os
import tempfile
import atexit
import shutil

# Guarantee test database isolation: pytest must NEVER touch backend/cartmate.db
if "CARTMATE_DATABASE_PATH" not in os.environ:
    _test_db_dir = tempfile.mkdtemp(prefix="cartmate_pytest_backend_")
    _test_db_path = os.path.join(_test_db_dir, "test_cartmate.db")
    os.environ["CARTMATE_DATABASE_PATH"] = _test_db_path

    def _cleanup_test_db():
        shutil.rmtree(_test_db_dir, ignore_errors=True)

    atexit.register(_cleanup_test_db)

import pytest
from rate_limiter import rate_limiter
import database
from main import ACTIVE_SESSIONS, DEMO_SESSIONS, REVOKED_TOKENS
from storage import storage


@pytest.fixture(autouse=True)
def test_environment_reset():
    """
    Autouse test fixture: clears rate limiter sliding windows, restores demo sessions,
    clears revoked tokens cache, and resets seeded trip_makro_01 between test cases.
    """
    rate_limiter.clear()
    ACTIVE_SESSIONS.update(dict(DEMO_SESSIONS))
    REVOKED_TOKENS.clear()

    if "trip_makro_01" in database.TRIPS:
        trip = database.TRIPS["trip_makro_01"]
        trip.host_accepted = True
        trip.companion_accepted = True
        trip.status = database.TripStatus.SCHEDULED
        trip.pin_attempts_left = 5
        trip.rendezvous_verified = False
        trip.sos_triggered = False
        trip.host_checked_in = True

    yield

    rate_limiter.clear()
