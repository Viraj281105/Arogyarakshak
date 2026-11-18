"""Observer hook for LLM calls — the WS1<->WS2 interface (Wave 1 plan, ADR-024).

``register_llm_observer(fn)`` receives one ``LlmCallEvent`` per ``ResilientLlmClient.complete``
call. Events carry NO prompt or response text: the only string fields are the configured
model name and three enumerated labels, validated on construction. WS1's metrics adapter
is duck-typed on these fields and does not import this module.
"""

import logging
import re
import threading
from dataclasses import dataclass
from typing import Callable, List, Optional

logger = logging.getLogger("arogyarakshak.kadi.llm")

OUTCOMES = ("ok", "error", "timeout", "rate_limited", "circuit_open", "budget_exceeded", "fallback")
CIRCUIT_STATES = ("closed", "open", "half_open")
KIND_RE = re.compile(r"^[a-z0-9_.]{1,64}$")


@dataclass(frozen=True)
class LlmCallEvent:
    model: str
    kind: str
    outcome: str
    latency_s: float
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    cache_hit: bool
    retries: int
    circuit_state: str

    def __post_init__(self):
        if self.outcome not in OUTCOMES:
            raise ValueError("outcome must be one of OUTCOMES")
        if self.circuit_state not in CIRCUIT_STATES:
            raise ValueError("circuit_state must be one of CIRCUIT_STATES")
        if not KIND_RE.match(self.kind or ""):
            raise ValueError("kind must match ^[a-z0-9_.]{1,64}$")


Observer = Callable[[LlmCallEvent], None]

_lock = threading.Lock()
_observers: List[Observer] = []


def register_llm_observer(fn: Observer) -> Callable[[], None]:
    """Registers ``fn``; returns a function that unregisters it."""
    with _lock:
        _observers.append(fn)

    def unregister() -> None:
        with _lock:
            if fn in _observers:
                _observers.remove(fn)

    return unregister


def clear_llm_observers() -> None:
    with _lock:
        _observers.clear()


def emit_llm_event(event: LlmCallEvent) -> None:
    """Delivers to every observer. An observer failure is logged and never reaches the
    LLM call that produced the event."""
    with _lock:
        observers = list(_observers)
    for fn in observers:
        try:
            fn(event)
        except Exception:  # noqa: BLE001
            logger.exception("LLM observer failed; event dropped for that observer.")
