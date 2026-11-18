"""Optional OpenTelemetry tracing, off by default (``OTEL_ENABLED=false``).

Nothing from ``opentelemetry.sdk`` or the instrumentation packages is imported at module
import time: ``setup_tracing`` imports them lazily and only when enabled, so a deployment
without them (or with tracing off) behaves exactly as before. Spans go to an OTLP/HTTP
collector configured by ``OTEL_EXPORTER_OTLP_ENDPOINT``.

What the standard instrumentations record is NOT inherently safe: the raw request target (with
the case id and query string), SQL text, and exception messages (SQLAlchemy errors include
bound parameters). Every span therefore passes through ``span_scrub.ScrubbingExporter`` before
export, which removes those attributes, redacts ``CASE-<id>`` tokens, keeps only
``exception.type`` on exception events and drops status descriptions; the collector scrubs again
(second layer). What remains: method, route template (``http.route`` and the span name),
status code, peer address, user agent, timings, and DB system/name.
"""

import logging
import sys
from typing import Optional

from app.telemetry.settings import TelemetrySettings

logger = logging.getLogger("arogyarakshak.telemetry")

_provider = None

# Matched with re.search against the full URL (scheme://host/path), so anchor to the path:
# /health, /health/..., /metrics are skipped; /api/v1/kadi/metrics/latency/* is traced.
EXCLUDED_URLS = r"^https?://[^/]+/health(/|\?|$),^https?://[^/]+/metrics(\?|$)"


def current_trace_id() -> Optional[str]:
    """Hex trace id of the active span, or None. Never imports OpenTelemetry itself: if the
    API was not set up with tracing nothing has loaded it."""
    trace = sys.modules.get("opentelemetry.trace")
    if trace is None:
        return None
    try:
        ctx = trace.get_current_span().get_span_context()
        return format(ctx.trace_id, "032x") if ctx.is_valid else None
    except Exception:  # pragma: no cover - defensive
        return None


def setup_tracing(app, settings: TelemetrySettings, engine=None, exporter=None) -> bool:
    """Installs the tracer provider and instrumentations. Returns whether tracing is on."""
    global _provider
    if not settings.otel_enabled:
        return False
    if not settings.endpoint_is_internal():
        logger.warning(
            "OTEL_EXPORTER_OTLP_ENDPOINT points outside this machine / the compose stack; "
            "ADR-023 expects the self-hosted collector. Spans carry route templates and timings only."
        )
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
    except ImportError as exc:
        logger.warning("OTEL_ENABLED=true but the OpenTelemetry SDK/exporter is not installed (%s).", exc.name)
        return False

    endpoint = settings.otel_exporter_otlp_endpoint.rstrip("/") + "/v1/traces"
    _provider = TracerProvider(
        resource=Resource.create({"service.name": settings.otel_service_name, "deployment.environment": settings.app_env}),
        sampler=ParentBased(TraceIdRatioBased(settings.otel_traces_sampler_ratio)),
    )
    from app.telemetry.span_scrub import ScrubbingExporter

    if exporter is None:
        _provider.add_span_processor(BatchSpanProcessor(ScrubbingExporter(OTLPSpanExporter(endpoint=endpoint))))
    else:  # tests: synchronous, in-memory
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor

        _provider.add_span_processor(SimpleSpanProcessor(ScrubbingExporter(exporter)))
    trace.set_tracer_provider(_provider)

    _instrument("opentelemetry.instrumentation.fastapi", "FastAPIInstrumentor", "instrument_app", app, excluded_urls=EXCLUDED_URLS, tracer_provider=_provider)
    _instrument("opentelemetry.instrumentation.httpx", "HTTPXClientInstrumentor", "instrument", tracer_provider=_provider)
    if engine is not None:
        _instrument(
            "opentelemetry.instrumentation.sqlalchemy", "SQLAlchemyInstrumentor", "instrument",
            engine=getattr(engine, "sync_engine", engine), tracer_provider=_provider,
        )
    logger.info("OpenTelemetry tracing enabled (sampler ratio %s).", settings.otel_traces_sampler_ratio)
    return True


def _instrument(module: str, cls: str, method: str, *args, **kwargs) -> None:
    try:
        mod = __import__(module, fromlist=[cls])
        instrumentor = getattr(mod, cls)
        target = instrumentor if method == "instrument_app" else instrumentor()
        getattr(target, method)(*args, **kwargs)
    except ImportError:
        logger.warning("Optional instrumentation %s is not installed; those spans are not produced.", module)
    except Exception as exc:
        logger.warning("Instrumentation %s failed: %s", module, type(exc).__name__)


def shutdown_tracing() -> None:
    global _provider
    # The httpx / SQLAlchemy instrumentors are process-wide singletons that ignore a second
    # instrument() call, so undo them for a clean re-setup (tests, reloads).
    for module, cls in (
        ("opentelemetry.instrumentation.httpx", "HTTPXClientInstrumentor"),
        ("opentelemetry.instrumentation.sqlalchemy", "SQLAlchemyInstrumentor"),
    ):
        mod = sys.modules.get(module)
        if mod is not None:
            try:
                getattr(mod, cls)().uninstrument()
            except Exception:  # pragma: no cover
                pass
    if _provider is not None:
        try:
            _provider.shutdown()
        except Exception:  # pragma: no cover
            pass
        _provider = None
