"""HTTP transport to Groq's OpenAI-compatible chat endpoint (ADR-024).

Stdlib ``urllib`` exactly as the pre-WS2 call sites used, so no dependency is added and the
outgoing request is byte-compatible (same URL, headers and JSON payload). ``urlopen`` is
looked up on the module at call time so tests can patch ``urllib.request.urlopen``.

Only Groq is contacted (AGENTS.md network rule).
"""

import json
import socket
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from kadi.llm.errors import (
    LlmClientError,
    LlmConnectionError,
    LlmError,
    LlmRateLimited,
    LlmResponseError,
    LlmServerError,
    LlmTimeout,
)

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


def _retry_after(headers) -> Optional[float]:
    if headers is None:
        return None
    raw = headers.get("Retry-After")
    if raw is None:
        return None
    try:
        value = float(str(raw).strip())
    except ValueError:
        return None  # HTTP-date form: ignored, the computed backoff applies
    return value if value >= 0 else None


def classify_transport_error(exc: BaseException) -> LlmError:
    """Maps a urllib/socket exception to a typed LlmError. Never copies the provider's
    response body or reason text (either can echo the prompt)."""
    if isinstance(exc, LlmError):
        return exc
    if isinstance(exc, urllib.error.HTTPError):
        code = exc.code
        if code == 429:
            return LlmRateLimited("HTTP 429", retry_after_s=_retry_after(exc.headers))
        if code == 408 or code >= 500:
            return LlmServerError(f"HTTP {code}", status=code)
        return LlmClientError(f"HTTP {code}", status=code)
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return LlmTimeout("request timed out")
    if isinstance(exc, urllib.error.URLError):
        if isinstance(exc.reason, (socket.timeout, TimeoutError)):
            return LlmTimeout("request timed out")
        return LlmConnectionError(f"connection failed ({type(exc.reason).__name__})")
    if isinstance(exc, (ConnectionError, OSError)):
        return LlmConnectionError(f"connection failed ({type(exc).__name__})")
    if isinstance(exc, (ValueError, KeyError, TypeError)):
        return LlmResponseError(f"malformed response ({type(exc).__name__})")
    return LlmConnectionError(f"transport failure ({type(exc).__name__})")


class UrllibGroqTransport:
    """``transport(payload, api_key, timeout_s) -> parsed JSON dict``; raises LlmError."""

    url = GROQ_CHAT_COMPLETIONS_URL

    def __call__(self, payload: Dict[str, Any], api_key: str, timeout_s: float) -> Dict[str, Any]:
        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as response:
                body = response.read()
        except Exception as exc:  # noqa: BLE001 — classified, never swallowed
            raise classify_transport_error(exc) from None
        try:
            return json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise LlmResponseError("response body is not JSON") from None
