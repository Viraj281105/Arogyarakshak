"""WS1: tracing is off by default, import-safe, and the trace id lands in JSON logs."""

import json
import logging
import subprocess
import sys

import pytest

from app.observability import JsonFormatter
from app.telemetry import tracing
from app.telemetry.settings import TelemetrySettings


def test_disabled_by_default_and_setup_is_a_noop():
    s = TelemetrySettings()
    assert s.otel_enabled is False
    assert tracing.setup_tracing(object(), s) is False


def test_importing_telemetry_does_not_import_opentelemetry_sdk():
    code = (
        "import sys; import app.telemetry.tracing, app.telemetry.metrics, app.telemetry.llm_metrics, app.observability;"
        "print(any(n.startswith('opentelemetry.sdk') or n.startswith('opentelemetry.instrumentation') for n in sys.modules))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"


def test_json_log_has_null_trace_id_without_a_span():
    rec = logging.LogRecord("x", logging.INFO, __file__, 1, "hello", (), None)
    payload = json.loads(JsonFormatter("svc", "test").format(rec))
    assert payload["trace_id"] is None


def test_json_log_carries_trace_id_inside_a_span():
    pytest.importorskip("opentelemetry.sdk.trace")
    from opentelemetry.sdk.trace import TracerProvider

    tracer = TracerProvider().get_tracer("t")
    with tracer.start_as_current_span("s") as span:
        expected = format(span.get_span_context().trace_id, "032x")
        rec = logging.LogRecord("x", logging.INFO, __file__, 1, "hello", (), None)
        payload = json.loads(JsonFormatter("svc", "test").format(rec))
        assert tracing.current_trace_id() == expected
    assert payload["trace_id"] == expected
    assert tracing.current_trace_id() is None


def test_setup_tracing_enabled_installs_provider_without_network():
    pytest.importorskip("opentelemetry.sdk.trace")
    from fastapi import FastAPI

    s = TelemetrySettings(otel_enabled=True, otel_exporter_otlp_endpoint="http://127.0.0.1:1")
    app = FastAPI()
    assert tracing.setup_tracing(app, s) is True
    # the FastAPI instrumentation really attached (a wrong keyword used to be swallowed)
    assert getattr(app, "_is_instrumented_by_opentelemetry", False) is True
    tracing.shutdown_tracing()


def test_sampler_ratio_validated():
    with pytest.raises(ValueError):
        TelemetrySettings(otel_traces_sampler_ratio=1.5)


def test_external_otlp_endpoint_is_flagged():
    assert TelemetrySettings(otel_exporter_otlp_endpoint="http://otel-collector:4318").endpoint_is_internal()
    assert TelemetrySettings(otel_exporter_otlp_endpoint="http://127.0.0.1:4318").endpoint_is_internal()
    assert not TelemetrySettings(otel_exporter_otlp_endpoint="https://otel.vendor.example").endpoint_is_internal()


def test_metrics_default_follows_environment():
    assert TelemetrySettings(app_env="development").metrics_exposed is True
    assert TelemetrySettings(app_env="production").metrics_exposed is False
    assert TelemetrySettings(app_env="production", metrics_enabled=True).metrics_exposed is True
    assert TelemetrySettings(app_env="development", metrics_enabled=False).metrics_exposed is False


def test_grafana_dev_password_refused_in_production():
    dev = TelemetrySettings(app_env="production").grafana_admin_password
    errs = TelemetrySettings(app_env="production", grafana_admin_password=dev).production_errors()
    assert errs and "GRAFANA_ADMIN_PASSWORD" in errs[0]
    assert dev not in errs[0]
    assert TelemetrySettings(app_env="development").production_errors() == []
    assert TelemetrySettings(app_env="production", grafana_admin_password="a-long-unique-secret-123").production_errors() == []
