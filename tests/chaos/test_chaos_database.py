"""Chaos: the database becomes unavailable.

Liveness must stay green (a database outage must not restart-loop the container: ADR-021),
readiness must go red so traffic stops, errors must keep the documented payload and carry no
connection string, and the service must recover by itself when the database returns.
"""

import logging

import pytest

from chaos_harness import (
    K, SECRET_CONNECTION, TEXT_BILL, UnavailableSession, assert_no_leak, client, database_unavailable, db_down,
    jobs, main_module, new_case, ready_schema, stream_events, upload,
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
    # Control: under the same patch a non-probe route IS limited, so the probes above passed
    # because they are exempt, not because the limiter was never consulted.
    assert client.post(f"{K}/cases", json={"consent_opt_in": False}).status_code == 429


def test_a_request_that_needs_the_database_fails_with_the_documented_500_payload(db_down):
    res = client.post(f"{K}/cases", json={"consent_opt_in": False})
    assert UnavailableSession.failures >= 1, "the database fault was really injected"
    assert res.status_code == 500
    body = res.json()
    assert body["detail"] == "An unexpected server error occurred."
    assert len(body["error_id"]) == 12, "an operator-traceable id replaces the exception text"
    assert_no_leak(res.text)


def test_an_unhandled_500_carries_the_request_id_and_hardening_headers(db_down):
    res = client.post(f"{K}/cases", json={"consent_opt_in": False})
    assert UnavailableSession.failures >= 1, "precondition: the fault fired"
    assert res.status_code == 500, "precondition: it surfaced as an unhandled 500"
    assert res.json()["detail"] == "An unexpected server error occurred."
    assert len(res.headers["X-Request-ID"]) == 32
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["Cache-Control"] == "no-store"


def test_the_error_handler_logs_the_type_and_ids_but_not_the_exception_text(db_down, caplog):
    """PHI rule: the log names the exception TYPE, the route and the correlation ids; the
    message (which can quote connection strings or document content) never appears."""
    with caplog.at_level(logging.DEBUG):
        res = client.post(f"{K}/cases", json={"consent_opt_in": False})
    assert UnavailableSession.failures >= 1 and res.status_code == 500
    error_id = res.json()["error_id"]
    record = next(r for r in caplog.records if error_id in r.getMessage())
    assert "OperationalError" in record.getMessage()
    assert record.request_id == res.headers["X-Request-ID"], "the line carries the request id"
    for text in (caplog.text, record.getMessage()):
        assert "could not connect" not in text and "ConnectionRefusedError" not in text
        assert "hunter2-CHAOS" not in text and SECRET_CONNECTION not in text and "10.9.8.7" not in text
    assert record.exc_info is None and "Traceback" not in caplog.text


def test_every_error_payload_has_detail_and_message(db_down):
    res = client.post(f"{K}/cases", json={"consent_opt_in": False})
    assert res.status_code == 500 and UnavailableSession.failures >= 1, "precondition: injected 500"
    body = res.json()
    assert "detail" in body and "message" in body


def test_the_service_recovers_without_a_restart(ready_schema):
    with database_unavailable():
        assert client.post(f"{K}/cases", json={"consent_opt_in": False}).status_code == 500
    assert client.post(f"{K}/cases", json={"consent_opt_in": False}).status_code == 201


def test_a_database_error_at_the_resolution_step_is_recorded_as_failed_without_leaking(monkeypatch):
    """A database-style error is injected at the entity-resolution step (the rest of the app keeps
    its working database, so job bookkeeping works). The job must end `failed` with the
    correlation id, and the progress stream must show a generic message."""
    from app.services import case_ingestion

    fired = []

    async def boom(*args, **kwargs):
        fired.append(1)
        await UnavailableSession().execute()

    monkeypatch.setattr(case_ingestion, "resolve_and_attach", boom)
    case_id = new_case()
    assert upload(case_id).status_code == 202
    assert fired, "the injected fault ran"
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

    entered = []

    class Broken:
        async def __aenter__(self):
            entered.append(1)
            raise ConnectionRefusedError(SECRET_CONNECTION)

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(document_jobs, "get_background_session", lambda: Broken())
    case_id = new_case()
    assert upload(case_id, TEXT_BILL).status_code == 202
    events = stream_events(case_id)
    assert entered, "the broken bookkeeping session was really used"
    assert events[-1]["status"] == "completed"
    # The request session (not the broken background one) recorded `queued`; nothing could advance it.
    assert jobs(case_id) == [("queued", None)], "no job row beyond the initial queued one was written"
    assert_no_leak(str(events))


def test_429_and_error_statuses_keep_their_codes_and_carry_detail_and_message(monkeypatch):
    monkeypatch.setattr(main_module.limiter, "check", lambda key: (False, 30))
    limited = client.post(f"{K}/cases", json={"consent_opt_in": False})
    assert limited.status_code == 429 and limited.headers["Retry-After"] == "30"
    assert {"detail", "message", "retry_after_seconds"} <= set(limited.json())
    monkeypatch.undo()
    for res, code in (
        (client.get("/api/v1/nope"), 404),
        (client.delete(f"{K}/cases/x/upload"), 405),
        (client.post(f"{K}/cases", json={"consent_opt_in": "maybe"}), 422),
    ):
        assert res.status_code == code, (code, res.text)
        assert {"detail", "message"} <= set(res.json()), (code, res.text)
