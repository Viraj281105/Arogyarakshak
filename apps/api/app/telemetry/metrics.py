"""Prometheus metrics for the API (WS1, ADR-023).

Rules this module enforces for every label:

- Route labels are route *templates* (``/api/v1/kadi/cases/{case_id}``) that exist in the
  application's OpenAPI paths, or ``<unmatched>``. A raw path, case id, file name or any
  other user-supplied string can never become a label value.
- Every other label comes from a closed vocabulary or collapses to ``other``.
- Recording never raises into the code it measures.

A dedicated registry is used (not the global default) so only the metrics declared here are
exposed and tests can reset them. The API is a single process (ADR-019), so no multiprocess
mode is needed.
"""

import logging
import time
from contextlib import contextmanager
from typing import Iterable

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.gc_collector import GCCollector
from prometheus_client.platform_collector import PlatformCollector
from prometheus_client.process_collector import ProcessCollector

logger = logging.getLogger("arogyarakshak.telemetry")

UNMATCHED_ROUTE = "<unmatched>"
OTHER = "other"
ALLOWED_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})
STAGES = frozenset({"ocr", "extraction", "database_write", "entity_resolution", "module_checks"})
CASE_OUTCOMES = frozenset({"completed", "failed"})
UPLOAD_REASONS = frozenset({"too_large", "unsupported_type", "empty", "bad_request"})
STAGE_OUTCOMES = frozenset({"ok", "error"})

CONTENT_TYPE = CONTENT_TYPE_LATEST

_known_routes: frozenset = frozenset()
_db_engine = None

registry: CollectorRegistry
HTTP_REQUESTS: Counter
HTTP_DURATION: Histogram
UPLOAD_REJECTIONS: Counter
PIPELINE_STAGE: Histogram
CASE_PROCESSING: Histogram
LLM_CALLS: Counter
LLM_DURATION: Histogram
LLM_TOKENS: Counter
LLM_RETRIES: Counter
LLM_CACHE_HITS: Counter
LLM_CIRCUIT: Gauge


class _PoolCollector:
    """Reads the SQLAlchemy pool at scrape time. Pools without counters (SQLite's) report
    nothing rather than failing the scrape."""

    def collect(self):
        pool = getattr(getattr(_db_engine, "sync_engine", None), "pool", None)
        if pool is None:
            return
        for name, attr, doc in (
            ("arogya_db_pool_size", "size", "Configured connection pool size."),
            ("arogya_db_pool_checked_out", "checkedout", "Connections currently checked out."),
            ("arogya_db_pool_overflow", "overflow", "Connections in use beyond the pool size."),
        ):
            fn = getattr(pool, attr, None)
            if not callable(fn):
                continue
            try:
                value = float(fn())
            except Exception:  # pragma: no cover - defensive
                continue
            family = GaugeMetricFamily(name, doc)
            family.add_metric([], value)
            yield family


def _build() -> None:
    global registry, HTTP_REQUESTS, HTTP_DURATION, UPLOAD_REJECTIONS, PIPELINE_STAGE, CASE_PROCESSING
    global LLM_CALLS, LLM_DURATION, LLM_TOKENS, LLM_RETRIES, LLM_CACHE_HITS, LLM_CIRCUIT
    registry = CollectorRegistry(auto_describe=True)
    ProcessCollector(registry=registry)
    PlatformCollector(registry=registry)
    GCCollector(registry=registry)
    registry.register(_PoolCollector())

    HTTP_REQUESTS = Counter(
        "arogya_http_requests_total", "HTTP requests by method, route template and status.",
        ["method", "route", "status"], registry=registry,
    )
    HTTP_DURATION = Histogram(
        "arogya_http_request_duration_seconds", "HTTP request duration by method and route template.",
        ["method", "route"], buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
        registry=registry,
    )
    UPLOAD_REJECTIONS = Counter(
        "arogya_upload_rejections_total", "Document/bundle uploads rejected, by reason and route template.",
        ["reason", "route"], registry=registry,
    )
    PIPELINE_STAGE = Histogram(
        "arogya_pipeline_stage_duration_seconds", "Case pipeline stage duration.",
        ["stage", "outcome"], buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 3, 5, 10, 20, 60), registry=registry,
    )
    CASE_PROCESSING = Histogram(
        "arogya_case_processing_seconds",
        "End-to-end document processing time (upload received to terminal event); SLO target is 10 s.",
        ["outcome"], buckets=(0.5, 1, 2, 3, 5, 7.5, 10, 15, 30, 60, 120), registry=registry,
    )
    LLM_CALLS = Counter(
        "arogya_llm_calls_total", "LLM calls by model, kind and outcome.", ["model", "kind", "outcome"], registry=registry
    )
    LLM_DURATION = Histogram(
        "arogya_llm_call_duration_seconds", "LLM call latency.", ["model", "kind"],
        buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30, 60), registry=registry,
    )
    LLM_TOKENS = Counter(
        "arogya_llm_tokens_total", "LLM tokens by direction (prompt or completion).",
        ["model", "kind", "direction"], registry=registry,
    )
    LLM_RETRIES = Counter("arogya_llm_retries_total", "LLM call retries.", ["model", "kind"], registry=registry)
    LLM_CACHE_HITS = Counter("arogya_llm_cache_hits_total", "LLM response cache hits.", ["kind"], registry=registry)
    LLM_CIRCUIT = Gauge(
        "arogya_llm_circuit_state", "LLM circuit breaker state: 0 closed, 1 half-open, 2 open.",
        ["model"], registry=registry,
    )


_build()


def reset_for_tests() -> None:
    _build()


def set_known_routes(templates: Iterable[str]) -> None:
    global _known_routes
    _known_routes = frozenset(templates)


def get_known_routes() -> frozenset:
    return _known_routes


def register_db_pool(engine) -> None:
    global _db_engine
    _db_engine = engine


def render() -> bytes:
    return generate_latest(registry)


def _route(route: object) -> str:
    return route if isinstance(route, str) and route in _known_routes else UNMATCHED_ROUTE


def _method(method: object) -> str:
    return method if isinstance(method, str) and method in ALLOWED_METHODS else "OTHER"


def _status(status: object) -> str:
    return str(status) if isinstance(status, int) and 100 <= status <= 599 else OTHER


def record_http_request(method: str, route: str, status: int, duration_s: float) -> None:
    try:
        r, me = _route(route), _method(method)
        HTTP_REQUESTS.labels(me, r, _status(status)).inc()
        HTTP_DURATION.labels(me, r).observe(max(0.0, float(duration_s)))
    except Exception:  # pragma: no cover - a metrics hook must never fail a request
        logger.debug("http metric not recorded", exc_info=True)


def record_upload_rejection(reason: str, route: str) -> None:
    try:
        UPLOAD_REJECTIONS.labels(reason if reason in UPLOAD_REASONS else OTHER, _route(route)).inc()
    except Exception:  # pragma: no cover
        logger.debug("upload metric not recorded", exc_info=True)


def record_upload_rejection_from_response(method: str, route: str, status: int) -> None:
    """Derives a rejection from the response, so no endpoint code needs instrumenting."""
    if method not in ("POST", "PUT"):
        return
    if status == 413:
        record_upload_rejection("too_large", route)
    elif status == 415:
        record_upload_rejection("unsupported_type", route)
    elif status == 400 and isinstance(route, str) and route.endswith("/upload"):
        record_upload_rejection("empty", route)


def record_stage(stage: str, duration_s: float, outcome: str = "ok") -> None:
    try:
        PIPELINE_STAGE.labels(
            stage if stage in STAGES else OTHER, outcome if outcome in STAGE_OUTCOMES else OTHER
        ).observe(max(0.0, float(duration_s)))
    except Exception:  # pragma: no cover
        logger.debug("stage metric not recorded", exc_info=True)


@contextmanager
def stage_timer(stage: str):
    started = time.perf_counter()
    outcome = "ok"
    try:
        yield
    except BaseException:
        outcome = "error"
        raise
    finally:
        record_stage(stage, time.perf_counter() - started, outcome)


def record_case_processing(duration_s: float, outcome: str) -> None:
    try:
        CASE_PROCESSING.labels(outcome if outcome in CASE_OUTCOMES else OTHER).observe(max(0.0, float(duration_s)))
    except Exception:  # pragma: no cover
        logger.debug("case metric not recorded", exc_info=True)

