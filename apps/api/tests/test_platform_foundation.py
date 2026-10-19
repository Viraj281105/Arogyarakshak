"""Health probes, request correlation, hardening headers, structured logs and the
production configuration profile."""

import json
import logging

import pytest

from app import main as main_module
from app.config import INSECURE_SIGNING_SECRET, settings
from app.observability import JsonFormatter, RequestContextFilter, request_id_var, resolve_request_id
from tests.clinical_helpers import K, client


def test_liveness_never_depends_on_the_database():
    res = client.get("/health/live")
    assert res.status_code == 200 and res.json() == {"status": "ok"}


def test_readiness_is_503_until_the_schema_step_succeeded(monkeypatch):
    monkeypatch.setitem(main_module.schema_state, "ok", False)
    res = client.get("/health/ready")
    assert res.status_code == 503
    assert res.json()["status"] == "not_ready"
    assert res.json()["database"] is True


def test_readiness_is_200_with_database_and_schema(monkeypatch):
    monkeypatch.setitem(main_module.schema_state, "ok", True)
    monkeypatch.setitem(main_module.schema_state, "revision", "0002_document_jobs")
    res = client.get("/health/ready")
    assert res.status_code == 200
    assert res.json() == {"status": "ready", "database": True,
                          "schema": {"ok": True, "revision": "0002_document_jobs"}}


def test_probes_are_exempt_from_rate_limiting(monkeypatch):
    monkeypatch.setattr(main_module.limiter, "check", lambda key: (False, 30))
    assert client.get("/health/ready").status_code in (200, 503)
    assert client.get("/health/live").status_code == 200
    assert client.post(f"{K}/cases", json={"consent_opt_in": False}).status_code == 429


def test_every_response_carries_a_request_id_and_hardening_headers():
    res = client.post(f"{K}/cases", json={"consent_opt_in": False})
    assert len(res.headers["X-Request-ID"]) == 32
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["Referrer-Policy"] == "no-referrer"
    assert res.headers["Cache-Control"] == "no-store"


def test_error_responses_carry_the_headers_too():
    res = client.get(f"{K}/cases/CASE-doesnotexist")
    assert res.status_code in (401, 403, 404)
    assert "X-Request-ID" in res.headers and res.headers["Cache-Control"] == "no-store"


def test_a_well_formed_incoming_request_id_is_reused_and_a_hostile_one_replaced():
    assert client.get("/health/live", headers={"X-Request-ID": "trace-abc-12345"}).headers["X-Request-ID"] == "trace-abc-12345"
    replaced = client.get("/health/live", headers={"X-Request-ID": "bad id\r\ninjected"}).headers["X-Request-ID"]
    assert replaced != "bad id\r\ninjected" and len(replaced) == 32
    assert resolve_request_id("x" * 200) != "x" * 200


def test_access_log_names_the_route_template_not_the_case_id(caplog):
    case_id = client.post(f"{K}/cases", json={"consent_opt_in": False}).json()["id"]
    with caplog.at_level(logging.INFO, logger="arogyarakshak.access"):
        client.get(f"{K}/cases/{case_id}")
    lines = [r for r in caplog.records if r.name == "arogyarakshak.access"]
    assert lines, "one access line per request"
    assert all(case_id not in r.getMessage() for r in lines)
    assert any(getattr(r, "route", "") == "/api/v1/kadi/cases/{case_id}" for r in lines)


def test_json_log_lines_are_parseable_and_carry_the_request_id():
    record = logging.LogRecord("arogyarakshak.api", logging.WARNING, __file__, 1, "hello %s", ("world",), None)
    token = request_id_var.set("req-123456789")
    try:
        RequestContextFilter().filter(record)
        line = JsonFormatter(service="svc", environment="test").format(record)
    finally:
        request_id_var.reset(token)
    data = json.loads(line)
    assert data["message"] == "hello world" and data["request_id"] == "req-123456789"
    assert data["service"] == "svc" and data["level"] == "WARNING"


# --- Production profile ----------------------------------------------------------

SECURE = {
    "app_env": "production",
    "document_signing_secret": "s" * 48,
    "database_url": "postgresql://app:long-random-password@db:5432/arogyarakshak",
    "cors_origins": "https://arogyarakshak.example",
    "schema_management": "none",
    "clinical_demo_mode": False,
}


def _apply(monkeypatch, **values):
    for key, value in values.items():
        monkeypatch.setattr(settings, key, value)


def test_production_refuses_to_start_with_development_defaults(monkeypatch):
    _apply(monkeypatch, app_env="production", document_signing_secret=INSECURE_SIGNING_SECRET,
           cors_origins="*", schema_management="create_all")
    with pytest.raises(RuntimeError):
        main_module.enforce_production_profile()
    errors = settings.production_config_errors()
    assert any("DOCUMENT_SIGNING_SECRET" in e for e in errors)
    assert any("CORS_ORIGINS" in e for e in errors)
    assert any("SCHEMA_MANAGEMENT" in e for e in errors)
    assert all(INSECURE_SIGNING_SECRET not in e for e in errors), "messages never echo secret values"


def test_production_starts_with_a_secure_configuration(monkeypatch):
    _apply(monkeypatch, **SECURE)
    assert settings.production_config_errors() == []
    main_module.enforce_production_profile()  # does not raise


def test_development_is_never_blocked(monkeypatch):
    _apply(monkeypatch, app_env="development", cors_origins="*")
    main_module.enforce_production_profile()


def test_error_logs_name_the_route_not_the_case_id(caplog):
    with caplog.at_level(logging.WARNING, logger="arogyarakshak.api"):
        res = client.get(f"{K}/cases/CASE-0123456789abcdef", headers={"X-Case-Access-Token": "wrong"})
    assert res.status_code in (401, 403, 404)
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "CASE-0123456789abcdef" not in text
    assert "/api/v1/kadi/cases/{case_id}" in text


def test_validation_error_logs_do_not_copy_submitted_values(caplog):
    marker = "Patient-Name-Should-Not-Be-Logged"
    with caplog.at_level(logging.ERROR, logger="arogyarakshak.api"):
        res = client.post("/api/v1/schemesetu/eligibility", json={"income": marker})
    assert res.status_code == 422
    assert marker in res.text, "the caller still sees its own input in the response"
    assert marker not in " ".join(r.getMessage() for r in caplog.records)
