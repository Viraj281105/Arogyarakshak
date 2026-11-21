"""Context-request metrics (#112, Phase 4 decision D8).

A *context request* is a module (or Kadi itself) reading a case's stored context: entities,
line items or the timeline. Every such read goes through
``app.services.case_context.load_case_entities``, which records one ``ContextRequestEvent``.

``outcome`` is ``served`` when the read returned at least one stored item and ``empty`` when
the case held nothing for it. That is a *hit rate*, not proof of reuse: modules never
re-extract, so nearly every read of a populated case is served.

Counters, registered on the existing private registry through its public API:

- ``arogya_context_requests_total{module,context,outcome}``
- ``arogya_context_ingest_work_total{kind}``: OCR / extraction passes done when a document is
  taken in (the work a no-shared-context design would repeat on every read).

Every label comes from a closed set (anything else collapses to ``other``); events carry
counts only, never a case id, name or text. Recording never raises into the caller, and a
failure is logged by exception type only.
"""

import logging
import threading
from dataclasses import dataclass
from typing import Literal, Optional, Tuple, get_args

from prometheus_client import Counter

from app.telemetry import metrics as m

logger = logging.getLogger("arogyarakshak.telemetry")

Module = Literal["kadi", "billnyay", "daavisetu", "bimanyay", "schemesetu", "dawacheck"]
ContextKind = Literal["entities", "line_items", "timeline"]
Outcome = Literal["served", "empty"]
WorkKind = Literal["ocr", "extraction"]

MODULES = frozenset(get_args(Module))
CONTEXT_KINDS = frozenset(get_args(ContextKind))
OUTCOMES = frozenset(get_args(Outcome))
WORK_KINDS = frozenset(get_args(WorkKind))


@dataclass(frozen=True)
class ContextRequestEvent:
    """One read of stored case context. ``items`` is how many stored items it returned."""

    module: Module
    context: ContextKind
    outcome: Outcome
    items: int = 0


_lock = threading.Lock()
_bound_registry = None
_counters_pair: Optional[Tuple[Counter, Counter]] = None


def _counters() -> Tuple[Counter, Counter]:
    """(Re)binds the counters whenever the telemetry registry was rebuilt (tests do that).
    Both are built first and published together, so there is never a half-registered state."""
    global _bound_registry, _counters_pair
    with _lock:
        if _counters_pair is None or _bound_registry is not m.registry:
            registry = m.registry
            requests = Counter(
                "arogya_context_requests_total",
                "Reads of stored case context, by module, context kind and outcome (served or empty).",
                ["module", "context", "outcome"], registry=registry,
            )
            work = Counter(
                "arogya_context_ingest_work_total",
                "OCR/extraction passes done at document ingestion.",
                ["kind"], registry=registry,
            )
            _counters_pair = (requests, work)
            _bound_registry = registry
        return _counters_pair


def _closed(value: object, allowed: frozenset) -> str:
    return value if isinstance(value, str) and value in allowed else m.OTHER


def record_context_request(event: object) -> None:
    try:
        requests, _ = _counters()
        requests.labels(
            _closed(getattr(event, "module", None), MODULES),
            _closed(getattr(event, "context", None), CONTEXT_KINDS),
            _closed(getattr(event, "outcome", None), OUTCOMES),
        ).inc()
    except Exception as exc:  # an observer must never break the request it observes
        logger.debug("context request metric not recorded (%s)", type(exc).__name__)


def record_context_work(kind: str, units: int = 1) -> None:
    try:
        _, work = _counters()
        if isinstance(units, int) and not isinstance(units, bool) and units > 0:
            work.labels(_closed(kind, WORK_KINDS)).inc(units)
    except Exception as exc:
        logger.debug("context work metric not recorded (%s)", type(exc).__name__)
