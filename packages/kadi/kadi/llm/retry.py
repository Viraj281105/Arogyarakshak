"""Retry classification and jittered exponential backoff (ADR-024)."""

import random
from dataclasses import dataclass
from typing import Optional

from kadi.llm.errors import LlmConnectionError, LlmRateLimited, LlmServerError, LlmTimeout

# Transient failures: worth another attempt, and evidence the provider is unhealthy.
_TRANSIENT = (LlmTimeout, LlmConnectionError, LlmRateLimited, LlmServerError)


def is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, _TRANSIENT)


def counts_toward_breaker(exc: BaseException) -> bool:
    """Only availability failures open the circuit. A 4xx or a malformed 200 proves the
    provider answered, so it must not lock every other caller out."""
    return isinstance(exc, _TRANSIENT)


@dataclass(frozen=True)
class BackoffPolicy:
    base_s: float = 0.5
    max_s: float = 8.0

    def delay(self, retry_index: int, rng: random.Random, retry_after_s: Optional[float] = None) -> float:
        """Delay before retry number ``retry_index`` (0-based): equal jitter in
        ``[cap/2, cap]`` with ``cap = min(max_s, base_s * 2**retry_index)``. A 429's
        Retry-After raises the delay to at least that value, still capped at ``max_s``."""
        cap = min(self.max_s, self.base_s * (2 ** retry_index))
        delay = rng.uniform(cap / 2, cap)
        if retry_after_s is not None:
            delay = max(delay, retry_after_s)
        return min(delay, self.max_s)
