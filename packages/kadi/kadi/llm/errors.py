"""Typed failures raised by the resilient LLM client (ADR-024).

Messages are deliberately short and never include prompt text or provider response
bodies (which can echo the prompt): they end up in logs.
"""

from typing import Optional


class LlmError(Exception):
    """Base class for every failure the resilient client raises."""


class LlmNotConfigured(LlmError):
    """No API key: callers use their offline fallback."""


class LlmTimeout(LlmError):
    """The request timed out (socket/read timeout)."""


class LlmConnectionError(LlmError):
    """The provider could not be reached (DNS, refused, reset)."""


class LlmRateLimited(LlmError):
    """HTTP 429. ``retry_after_s`` is the provider's Retry-After, when it sent a number."""

    def __init__(self, message: str, retry_after_s: Optional[float] = None):
        super().__init__(message)
        self.retry_after_s = retry_after_s


class LlmServerError(LlmError):
    """HTTP 5xx or 408: transient on the provider's side."""

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


class LlmClientError(LlmError):
    """Any other HTTP 4xx (auth, bad request, unknown model). Not retried."""

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


class LlmResponseError(LlmError):
    """HTTP 200 with a body that is not a chat completion."""


class LlmCircuitOpen(LlmError):
    """The model's circuit breaker is open; no request was sent."""


class BudgetExceeded(LlmError):
    """The per-case token budget cannot fit this call; no request was sent."""
