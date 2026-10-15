import time
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import HTTPException
from config import OPERATIONAL_THRESHOLDS


class SlidingWindowRateLimiter:
    """
    In-memory sliding-window rate limiter.
    Enforces operational safety thresholds across OTP generation, login attempts,
    chat message bursts, reports, and emergency actions.
    """

    def __init__(self):
        # Key -> list of event timestamps (float)
        self._history: Dict[str, List[float]] = defaultdict(list)

    def check(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        now = time.time()
        cutoff = now - window_seconds
        # Filter out expired events
        valid_events = [ts for ts in self._history[key] if ts > cutoff]
        self._history[key] = valid_events

        if len(valid_events) >= max_requests:
            oldest = valid_events[0]
            retry_after = max(1, int(oldest + window_seconds - now))
            return False, retry_after

        self._history[key].append(now)
        return True, 0

    def assert_allowed(self, key: str, max_requests: int, window_seconds: int, action_description: str = "operacji"):
        allowed, retry_after = self.check(key, max_requests, window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Zbyt wiele prób {action_description}. Odczekaj {retry_after} sekund przed kolejną próbą.",
                headers={"Retry-After": str(retry_after)},
            )

    def reset_key(self, key: str):
        if key in self._history:
            del self._history[key]

    def clear(self):
        self._history.clear()


rate_limiter = SlidingWindowRateLimiter()
