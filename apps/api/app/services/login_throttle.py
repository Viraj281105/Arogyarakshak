"""Per (account, client IP) sign-in throttle (ADR-026 section 7, security review M1/L3).

Replaces a per-account hard lock, which let anyone keep a victim locked out forever by
sending wrong passwords. Here:

- failures are counted per (user id, client IP), so an attacker's failures slow down only
  that attacker's IP for that account — the real user on another network is unaffected;
- failures expire: a pair with no failure for ``LOGIN_FAILURE_WINDOW_MINUTES`` starts over;
- after ``LOGIN_FREE_FAILURES`` failures each further attempt from that pair must wait an
  increasing delay (1 s, 2 s, 4 s, ... capped at ``LOGIN_MAX_DELAY_SECONDS``). An attempt
  inside the delay is answered with the same generic 401 without checking the password.

Wrong current passwords on password change and account deletion count here too.

In memory and bounded, like the per-IP limiter (app/rate_limit.py): the API is one process
(ADR-019), nothing personal is persisted, and a restart only forgets slow-downs.
"""

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Tuple

from app.config import settings

_MAX_TRACKED_PAIRS = 10_000


@dataclass
class _Entry:
    failures: int
    last_failure: datetime
    next_allowed: Optional[datetime]


class LoginThrottle:
    def __init__(self) -> None:
        self._entries: "OrderedDict[Tuple[str, str], _Entry]" = OrderedDict()

    def reset(self) -> None:
        self._entries.clear()

    def _live(self, key: Tuple[str, str], now: datetime) -> Optional[_Entry]:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if now - entry.last_failure >= timedelta(minutes=settings.login_failure_window_minutes):
            del self._entries[key]
            return None
        return entry

    def retry_after_seconds(self, user_id: str, client: str, now: datetime) -> float:
        """0 when an attempt may be evaluated now."""
        entry = self._live((user_id, client), now)
        if entry is None or entry.next_allowed is None or now >= entry.next_allowed:
            return 0.0
        return (entry.next_allowed - now).total_seconds()

    def record_failure(self, user_id: str, client: str, now: datetime) -> int:
        key = (user_id, client)
        entry = self._live(key, now)
        if entry is None:
            if len(self._entries) >= _MAX_TRACKED_PAIRS:
                self._entries.popitem(last=False)
            entry = _Entry(failures=0, last_failure=now, next_allowed=None)
            self._entries[key] = entry
        self._entries.move_to_end(key)
        entry.failures += 1
        entry.last_failure = now
        excess = entry.failures - settings.login_free_failures
        if excess >= 0:
            delay = min(float(settings.login_max_delay_seconds), float(2**min(excess, 30)))
            entry.next_allowed = now + timedelta(seconds=delay)
        return entry.failures

    def record_success(self, user_id: str, client: str) -> None:
        self._entries.pop((user_id, client), None)


throttle = LoginThrottle()
