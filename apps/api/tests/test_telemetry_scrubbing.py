"""WS1: spans must never carry case ids, query strings, bound SQL parameters or exception text.

Runs a real instrumented FastAPI app (and a real SQLAlchemy engine) through the same
``setup_tracing`` the API uses, with an in-memory exporter behind the scrubbing exporter,
and inspects every exported span: attributes, events, status and name.
"""

import json

import pytest

pytest.importorskip("opentelemetry.sdk.trace")

from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.telemetry import tracing  # noqa: E402
from app.telemetry.settings import TelemetrySettings  # noqa: E402

SECRETS = ("CASE-SECRET-123", "John", "Doe", "patient=")


class Collect(SpanExporter):
    def __init__(self):
        self.spans = []

    def export(self, spans):
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


def dump(span):
    """Everything a collector would receive for the span, as one string."""
    return json.dumps(
        {
            "name": span.name,
            "attributes": dict(span.attributes or {}),
            "events": [{"name": e.name, "attributes": dict(e.attributes or {})} for e in span.events],
            "status": [str(span.status.status_code), span.status.description],
            "links": [dict(link.attributes or {}) for link in span.links],
        },
        default=str,
    )


@pytest.fixture
def traced(tmp_path):
    exporter = Collect()
    app = FastAPI()
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 't.db'}")

    @app.get("/api/v1/kadi/cases/{case_id}/boom")
    async def boom(case_id: str):
        raise ValueError("patient John Doe cannot be processed")

    @app.get("/api/v1/kadi/cases/{case_id}/sql")
    async def sql(case_id: str):
        async with engine.connect() as conn:
            await conn.execute(text("select * from missing_table where name = :n"), {"n": "John Doe"})

    @app.get("/api/v1/kadi/metrics/latency/summary")
    async def latency():
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.get("/health/ready")
    async def ready():
        return {"ok": True}

    @app.get("/metrics")
    async def metrics():
        return {"ok": True}

    settings = TelemetrySettings(otel_enabled=True, otel_exporter_otlp_endpoint="http://127.0.0.1:1")
    assert tracing.setup_tracing(app, settings, engine, exporter=exporter)
    yield app, exporter
    tracing.shutdown_tracing()


async def get(app, path):
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as c:
        return await c.get(path)


@pytest.mark.asyncio
async def test_no_case_id_query_or_exception_text_in_any_span(traced):
    app, exporter = traced
    r = await get(app, "/api/v1/kadi/cases/CASE-SECRET-123/boom?patient=John")
    assert r.status_code == 500
    r = await get(app, "/api/v1/kadi/cases/CASE-SECRET-123/sql?patient=John")
    assert r.status_code == 500
    assert exporter.spans, "no spans were exported - the test would pass vacuously"
    for span in exporter.spans:
        blob = dump(span)
        for secret in SECRETS:
            assert secret not in blob, f"{secret!r} leaked in span {span.name!r}: {blob}"


@pytest.mark.asyncio
async def test_exception_type_is_kept_but_message_and_stacktrace_are_not(traced):
    app, exporter = traced
    await get(app, "/api/v1/kadi/cases/CASE-SECRET-123/boom")
    events = [e for s in exporter.spans for e in s.events if e.name == "exception"]
    assert events, "the failing request should record an exception event"
    for e in events:
        assert e.attributes.get("exception.type")
        assert "exception.message" not in e.attributes
        assert "exception.stacktrace" not in e.attributes


@pytest.mark.asyncio
async def test_sql_spans_drop_statement_and_bound_parameters(traced):
    app, exporter = traced
    await get(app, "/api/v1/kadi/cases/CASE-SECRET-123/sql")
    db_spans = [s for s in exporter.spans if s.attributes and s.attributes.get("db.system")]
    assert db_spans, "the SQLAlchemy instrumentation produced no span"
    for s in db_spans:
        assert "db.statement" not in s.attributes and "db.query.text" not in s.attributes
        assert "John" not in dump(s)


@pytest.mark.asyncio
async def test_server_span_name_is_the_route_template(traced):
    app, exporter = traced
    await get(app, "/api/v1/kadi/cases/CASE-SECRET-123/boom")
    server = [s for s in exporter.spans if s.kind.name == "SERVER"]
    assert server
    assert any("/api/v1/kadi/cases/{case_id}/boom" in s.name for s in server), [s.name for s in server]
    assert all("CASE-SECRET" not in s.name for s in exporter.spans)
    assert any(s.attributes.get("http.route") == "/api/v1/kadi/cases/{case_id}/boom" for s in server)


@pytest.mark.asyncio
async def test_raw_target_attributes_are_removed(traced):
    app, exporter = traced
    await get(app, "/api/v1/kadi/metrics/latency/summary?x=secretquery")
    server = [s for s in exporter.spans if s.kind.name == "SERVER"]
    assert server
    forbidden = {"http.target", "http.url", "url.full", "url.path", "url.query", "db.statement", "db.query.text"}
    for s in exporter.spans:
        assert not forbidden & set(s.attributes), set(s.attributes) & forbidden
        assert "secretquery" not in dump(s)


@pytest.mark.asyncio
async def test_excluded_urls_are_anchored(traced):
    app, exporter = traced
    await get(app, "/api/v1/kadi/metrics/latency/summary")
    assert [s for s in exporter.spans if s.kind.name == "SERVER"], "/metrics/latency/* must be traced"
    exporter.spans.clear()
    for path in ("/health", "/health/ready", "/metrics"):
        await get(app, path)
    assert [s for s in exporter.spans if s.kind.name == "SERVER"] == []


def test_scrub_function_redacts_case_ids_in_free_text_values():
    from app.telemetry.span_scrub import scrub_value

    assert "CASE-" in scrub_value("x CASE-abc123 y") and "abc123" not in scrub_value("x CASE-abc123 y")
    assert scrub_value(5) == 5


def test_missing_fastapi_instrumentation_is_a_warning(monkeypatch, caplog):
    import builtins

    real = builtins.__import__

    def fake(name, *a, **k):
        if name == "opentelemetry.instrumentation.fastapi":
            raise ImportError(name=name)
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake)
    import logging

    with caplog.at_level(logging.INFO, logger="arogyarakshak.telemetry"):
        tracing._instrument("opentelemetry.instrumentation.fastapi", "FastAPIInstrumentor", "instrument_app", object())
    assert any(r.levelno == logging.WARNING and "fastapi" in r.getMessage() for r in caplog.records)
