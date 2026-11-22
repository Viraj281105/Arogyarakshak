"""Chaos: the database becomes unavailable.

Liveness must stay green (a database outage must not restart-loop the container: ADR-021),
readiness must go red so traffic stops, errors must keep the documented payload and carry no
connection string, and the service must recover by itself when the database returns.
"""

import logging

import pytest

from chaos_harness import (
    K, SECRET_CONNECTION, TEXT_BILL, assert_no_leak, client, database_unavailable, db_down,
    jobs, main_module, new_case, ready_schema, upload,
)
from chaos_harness import *  # noqa: F401,F403  (fixtures: setup_database, network_guard, ...)


def test_liveness_stays_up_while_the_database_is_down(db_down):
    res = client.get("/health/live")
    assert res.status_code == 200 and res.json() == {"status": "ok"}


def test_health_does_not_need_the_database(db_down):
    assert client.get("/health").status_code == 200


def test_readiness_goes_503_and_reports_booleans_only(db_down, ready_schema, caplog):
    with caplog.at_level(logging.DEBUG):
        res = client.get("/health/ready")
    assert res.status_code == 503
    body = res.json()
    assert body["status"] == "not_ready" and body["database"] is False
    assert set(body) == {"status", "database", "schema"}
    assert_no_leak(res.text)
    # The log line names the exception type only, never its message (hostnames, credentials).
    assert "database check failed: OperationalError" in caplog.text
    assert "hunter2-CHAOS" not in caplog.text and SECRET_CONNECTION not in caplog.text


def test_readiness_recovers_when_the_database_returns(ready_schema):
    with database_unavailable():
        assert client.get("/health/ready").status_code == 503
    ready = client.get("/health/ready")
    assert ready.status_code == 200 and ready.json()["database"] is True


def test_probes_are_not_rate_limited_during_an_outage(db_down, monkeypatch):
    monkeypatch.setattr(main_module.limiter, "check", lambda key: (False, 30))
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 503


def test_a_request_that_needs_the_database_fails_with_the_documented_500_payload(db_down):
    res = client.post(f"{K}/cases", json={"consent_opt_in": False})
    assert res.status_code == 500
    body = res.json()
    assert body["detail"] == "An unexpected server error occurred."
    assert len(body["error_id"]) == 12, "an operator-traceable id replaces the exception text"
    assert_no_leak(res.text)


@pytest.mark.xfail(
    reason="DEFECT: an unhandled exception (500) is answered by Starlette's outermost ServerErrorMiddleware, "
           "outside RequestContextMiddleware, so the response has no X-Request-ID / X-Content-Type-Options / "
           "Cache-Control: no-store and the error log line shows req=-. test_platform_foundation only covers "
           "handled errors (404). Fix belongs in app/main.py / observability.py (not a trivial isolated fix).",
    strict=True,
)
def test_an_unhandled_500_carries_the_request_id_and_hardening_headers(db_down):
    res = client.post(f"{K}/cases", json={"consent_opt_in": False})
    assert res.status_code == 500
    assert len(res.headers["X-Request-ID"]) == 32
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["Cache-Control"] == "no-store"


def test_the_error_handler_logs_the_cause_server_side_only(db_down, caplog):
    with caplog.at_level(logging.ERROR):
        res = client.post(f"{K}/cases", json={"consent_opt_in": False})
    error_id = res.json()["error_id"]
    assert error_id in caplog.text, "operators can find the failure by its correlation id"
    assert error_id not in SECRET_CONNECTION


@pytest.mark.xfail(
    reason="DEFECT (contract): the 500 and 429 payloads carry `detail` but no `message`, unlike the "
           "401/403/404/422 payloads; AGENTS.md §4.2 and apps/api/app/main.py's docstring promise "
           "{detail, message}. See docs/superpowers/handoff/wave2-e-platform.md.",
    strict=True,
)
def test_every_error_payload_has_detail_and_message(db_down):
    body = client.post(f"{K}/cases", json={"consent_opt_in": False}).json()
    assert "detail" in body and "message" in body


def test_the_service_recovers_without_a_restart(ready_schema):
    with database_unavailable():
        assert client.post(f"{K}/cases", json={"consent_opt_in": False}).status_code == 500
    assert client.post(f"{K}/cases", json={"consent_opt_in": False}).status_code == 201


def test_pipeline_database_failure_is_recorded_as_failed_without_leaking(monkeypatch):
    """The database dies mid-pipeline (entity-resolution write). The job must end `failed` with
    the correlation id, and the progress stream must show a generic message."""
    from app.services import case_ingestion

    async def boom(*args, **kwargs):
        from chaos_harness import UnavailableSession

        await UnavailableSession().execute()

    monkeypatch.setattr(case_ingestion, "resolve_and_attach", boom)
    case_id = new_case()
    assert upload(case_id).status_code == 202
    [(state, error_id)] = jobs(case_id)
    assert state == "failed" and error_id and len(error_id) == 12
    from chaos_harness import stream_events

    events = stream_events(case_id)
    assert events[-1]["status"] == "failed" and events[-1]["error_id"] == error_id
    assert_no_leak(str(events))


def test_job_bookkeeping_failure_never_fails_the_upload(monkeypatch):
    """Recording job state needs the database too; if only that fails the document is still
    processed and nothing raises (ADR-019: bookkeeping never fails the pipeline)."""
    from app.services import document_jobs

    class Broken:
        async def __aenter__(self):
            raise ConnectionRefusedError(SECRET_CONNECTION)

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(document_jobs, "get_background_session", lambda: Broken())
    case_id = new_case()
    assert upload(case_id, TEXT_BILL).status_code == 202
    events = __import__("chaos_harness").stream_events(case_id)
    assert events[-1]["status"] == "completed"
    assert_no_leak(str(events))
