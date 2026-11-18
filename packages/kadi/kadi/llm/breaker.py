"""Per-model circuit breaker: closed -> open -> half_open -> closed (ADR-024).

Thread-safe: the API's sync LLM code runs on Starlette's threadpool, so several threads
share one breaker. Every state read-modify-write happens under ``self._lock``.
"""

import threading
import time
from typing import Callable

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

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def allow(self) -> bool:
        """May a request go out now? In half_open only one probe is admitted."""
        with self._lock:
            if self._state == CLOSED:
                return True
            if self._state == OPEN:
                if self._clock() - self._opened_at >= self.recovery_s:
                    self._state = HALF_OPEN
                    self._probe_in_flight = True
                    return True
                return False
            # HALF_OPEN
            if self._probe_in_flight:
                return False
            self._probe_in_flight = True
            return True

    def record_success(self) -> None:
        """The provider answered (2xx, or a 4xx that proves it is reachable)."""
        with self._lock:
            self._state = CLOSED
            self._failures = 0
            self._probe_in_flight = False

    def record_failure(self) -> None:
        """An availability failure (timeout, connection, 429, 5xx)."""
        with self._lock:
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
