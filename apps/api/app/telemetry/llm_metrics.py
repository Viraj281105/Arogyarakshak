"""LLM call metrics (WS1/WS2 interface).

``record_llm_event`` is duck-typed on the fields of WS2's ``LlmCallEvent`` (model, kind,
outcome, latency_s, prompt_tokens, completion_tokens, cache_hit, retries, circuit_state) so
this module imports no WS2 code. Events carry no prompt or response text; labels are
additionally bounded here: the model must be a configured one, the outcome and circuit state
come from closed sets, and ``kind`` is a short identifier with a hard cap on distinct values.
"""

import logging
import os
import re
from typing import Optional, Set

from app.config import settings
from app.telemetry import metrics as m

logger = logging.getLogger("arogyarakshak.telemetry")

OUTCOMES = frozenset(
    {"ok", "error", "timeout", "rate_limited", "circuit_open", "budget_exceeded", "fallback"}
)
CIRCUIT_VALUES = {"closed": 0.0, "half_open": 1.0, "open": 2.0}
_KIND = re.compile(r"^[a-z][a-z0-9_]{0,23}$")
_MAX_KINDS = 12
_kinds: Set[str] = set()


def reset_for_tests() -> None:
    _kinds.clear()


def _configured_models() -> Set[str]:
    models = {settings.groq_model}
    fallback = os.environ.get("GROQ_FALLBACK_MODEL", "").strip()
    if fallback:
        models.add(fallback)
    return models


def _model(value: object) -> str:
    return value if isinstance(value, str) and value in _configured_models() else m.OTHER


def _kind(value: object) -> str:
    if not isinstance(value, str) or not _KIND.match(value):
        return m.OTHER
    if value in _kinds:
        return value
    if len(_kinds) >= _MAX_KINDS:
        return m.OTHER
    _kinds.add(value)
    return value


def _count(value: object) -> Optional[int]:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def record_llm_event(event: object) -> None:
    try:
        model = _model(getattr(event, "model", None))
        kind = _kind(getattr(event, "kind", None))
        outcome = getattr(event, "outcome", None)
        outcome = outcome if outcome in OUTCOMES else m.OTHER
        m.LLM_CALLS.labels(model, kind, outcome).inc()

        latency = getattr(event, "latency_s", None)
        if isinstance(latency, (int, float)) and latency >= 0:
            m.LLM_DURATION.labels(model, kind).observe(float(latency))
        for direction, attr in (("prompt", "prompt_tokens"), ("completion", "completion_tokens")):
            tokens = _count(getattr(event, attr, None))
            if tokens:
                m.LLM_TOKENS.labels(model, kind, direction).inc(tokens)
        retries = _count(getattr(event, "retries", None))
        if retries:
            m.LLM_RETRIES.labels(model, kind).inc(retries)
        if getattr(event, "cache_hit", False) is True:
            m.LLM_CACHE_HITS.labels(kind).inc()
        state = getattr(event, "circuit_state", None)
        if state in CIRCUIT_VALUES:
            m.LLM_CIRCUIT.labels(model).set(CIRCUIT_VALUES[state])
    except Exception:  # an observer must never break the LLM call it observes
        logger.debug("llm metric not recorded", exc_info=True)
