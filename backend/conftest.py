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
