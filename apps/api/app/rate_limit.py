"""Per-client-IP request rate limiting.

In-memory fixed-window counter, consistent with the existing single-process
`processing_status` store in `app/api/v1/endpoints/kadi.py`: bounded, evicted, and
explicitly documented as not shared across workers. A multi-worker or multi-instance
deployment would need this backed by Redis or the database instead (see the CI
guardrails / ADR notes on `processing_status` for the same caveat) — recorded as a
known limitation, not silently assumed to scale.

This exists because the API has no authentication (accepted-risk decision for this
project's scope — see docs/architecture/decisions/). Without it, nothing stands
between an unauthenticated caller and unlimited automated requests: enumerating
CASE-xxxxxxxx ids, or hammering the LLM-backed extraction/appeal endpoints.
"""

import time
from typing import Dict, Tuple

from app.config import settings

# Hard ceiling on tracked clients so this cannot itself become an unbounded-memory
# vector under a burst from many distinct IPs (the same failure mode already fixed
# for `processing_status`).
_MAX_TRACKED_CLIENTS = 5000


class RateLimiter:
    """Fixed 60-second window, one counter per client key."""

    def __init__(self) -> None:
        self._windows: Dict[str, Tuple[int, int]] = {}

    def reset(self) -> None:
        """Clears all tracked state. Called between tests so limits from one test
        cannot leak into the next — the limiter is a module-level singleton shared
        across the whole pytest session, same as `processing_status`."""
        self._windows.clear()

    def check(self, client_key: str) -> Tuple[bool, int]:
        """Returns (allowed, retry_after_seconds). retry_after_seconds is 0 when allowed."""
        now = int(time.time())
        window_start = now - (now % 60)

        if len(self._windows) >= _MAX_TRACKED_CLIENTS and client_key not in self._windows:
            self._windows.clear()

        start, count = self._windows.get(client_key, (window_start, 0))
        if start != window_start:
            start, count = window_start, 0

        count += 1
        self._windows[client_key] = (start, count)

        if count > settings.rate_limit_per_minute:
            return False, max(1, start + 60 - now)
        return True, 0


limiter = RateLimiter()
