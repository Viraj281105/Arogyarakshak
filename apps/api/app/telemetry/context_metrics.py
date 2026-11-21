"""Context-request metrics (#112, Phase 4 decision D8).

A *context request* is a module asking Kadi's stored case context (entities, line items,
timeline) for what it needs. ``outcome`` is ``reused`` when the case already held that
context and the module was served from it, ``fresh`` when nothing usable was stored (or
reuse is switched off, which is the measurement baseline).

Two counters, both registered on the existing private registry through its public API:

- ``arogya_context_requests_total{module,outcome}``
- ``arogya_context_work_total{kind,phase}``: units of OCR / extraction work, ``ingest`` for
  the one pass done when a document is taken in, ``repeat`` for work a module would have to
  redo without reuse (counted only while ``CONTEXT_REUSE_ENABLED=false``).

Every label comes from a closed set (anything else collapses to ``other``); events carry
counts only, never a case id, name or text. Recording never raises into the caller.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from prometheus_client import Counter

from app.telemetry import metrics as m

logger = logging.getLogger("arogyarakshak.telemetry")

MODULES = frozenset({"kadi", "billnyay", "daavisetu", "bimanyay", "schemesetu", "dawacheck"})
OUTCOMES = frozenset({"reused", "fresh"})
CONTEXT_KINDS = frozenset({"entities", "line_items", "timeline"})
WORK_KINDS = frozenset({"ocr", "extraction"})
WORK_PHASES = frozenset({"ingest", "repeat"})


@dataclass(frozen=True)
class ContextRequestEvent:
    """One module's request for case context. ``items`` is how many stored items answered it."""

    module: str
    context: str  # one of CONTEXT_KINDS
    outcome: str  # one of OUTCOMES
    items: int = 0


_bound_registry = None
_requests: Optional[Counter] = None
_work: Optional[Counter] = None


def _counters():
    """(Re)binds the counters whenever the telemetry registry was rebuilt (tests do that)."""
    global _bound_registry, _requests, _work
    if _bound_registry is not m.registry:
        _requests = Counter(
            "arogya_context_requests_total",
            "Module requests for case context, by module and outcome (reused or fresh).",
            ["module", "outcome"], registry=m.registry,
        )
        _work = Counter(
            "arogya_context_work_total",
            "OCR/extraction work units: ingest (once per document) or repeat (redone without reuse).",
            ["kind", "phase"], registry=m.registry,
        )
        _bound_registry = m.registry
    return _requests, _work


def _closed(value: object, allowed: frozenset) -> str:
    return value if isinstance(value, str) and value in allowed else m.OTHER


def record_context_request(event: object) -> None:
    try:
        requests, _ = _counters()
        requests.labels(
            _closed(getattr(event, "module", None), MODULES),
            _closed(getattr(event, "outcome", None), OUTCOMES),
        ).inc()
    except Exception:  # an observer must never break the request it observes
        logger.debug("context request metric not recorded", exc_info=True)


def record_context_work(kind: str, phase: str, units: int = 1) -> None:
    try:
        _, work = _counters()
        if isinstance(units, int) and not isinstance(units, bool) and units > 0:
            work.labels(_closed(kind, WORK_KINDS), _closed(phase, WORK_PHASES)).inc(units)
    except Exception:
        logger.debug("context work metric not recorded", exc_info=True)


def totals() -> dict:
    """Current counter values keyed ``requests/<module>/<outcome>`` and ``work/<phase>/<kind>``.
    Read straight from the registry; used by the evaluation harness and tests."""
    _counters()
    out: dict = {}
    for family in m.registry.collect():
        if family.name == "arogya_context_requests":
            for s in family.samples:
                if s.name.endswith("_total"):
                    out[f"requests/{s.labels['module']}/{s.labels['outcome']}"] = s.value
        elif family.name == "arogya_context_work":
            for s in family.samples:
                if s.name.endswith("_total"):
                    out[f"work/{s.labels['phase']}/{s.labels['kind']}"] = s.value
    return out
