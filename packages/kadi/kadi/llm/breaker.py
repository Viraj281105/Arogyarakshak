"""Per-model circuit breaker: closed -> open -> half_open -> closed (ADR-024).

Thread-safe: the API's sync LLM code runs on Starlette's threadpool, so several threads
share one breaker. Every state read-modify-write happens under ``self._lock``.

Generation guard: ``acquire()`` returns the current generation as a token, and every trip
or close bumps the generation. A result reported with an older token is ignored, so a call
that started before a trip cannot close an OPEN breaker with its late success, and a late
failure cannot clear the in-flight half-open probe. ``record_*`` without a token (``None``)
always applies (backward compatible).
"""

import threading
import time
from typing import Callable, Optional

CLOSED = "closed"
OPEN = "open"
HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_s: float = 30.0,
                 clock: Callable[[], float] = time.monotonic):
        self.failure_threshold = max(1, int(failure_threshold))
        self.recovery_s = float(recovery_s)
        self._clock = clock
        self._lock = threading.Lock()
        self._state = CLOSED
        self._failures = 0
        self._opened_at = 0.0
        self._probe_in_flight = False
        self._generation = 0

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def acquire(self) -> Optional[int]:
        """The generation token if a request may go out now, else None. In half_open only
        one probe is admitted."""
        with self._lock:
            if self._state == CLOSED:
                return self._generation
            if self._state == OPEN:
                if self._clock() - self._opened_at >= self.recovery_s:
                    self._state = HALF_OPEN
                    self._probe_in_flight = True
                    return self._generation
                return None
            # HALF_OPEN
            if self._probe_in_flight:
                return None
            self._probe_in_flight = True
            return self._generation

    def allow(self) -> bool:
        return self.acquire() is not None

    def _stale(self, token: Optional[int]) -> bool:
        return token is not None and token != self._generation

    def record_success(self, token: Optional[int] = None) -> None:
        """The provider answered (2xx, or a 4xx that proves it is reachable)."""
        with self._lock:
            if self._stale(token):
                return
            if self._state != CLOSED:
                self._generation += 1
            self._state = CLOSED
            self._failures = 0
            self._probe_in_flight = False

    def record_failure(self, token: Optional[int] = None) -> None:
        """An availability failure (timeout, connection, 429, 5xx)."""
        with self._lock:
            if self._stale(token):
                return
            self._probe_in_flight = False
            if self._state == HALF_OPEN:
                self._trip()
                return
            self._failures += 1
            if self._state == CLOSED and self._failures >= self.failure_threshold:
                self._trip()

    def _trip(self) -> None:
        self._state = OPEN
        self._opened_at = self._clock()
        self._failures = 0
        self._generation += 1
