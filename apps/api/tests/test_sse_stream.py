"""
Tests for GET /cases/{case_id}/stream (P0-2).

Prior implementation: `while True: ... await asyncio.sleep(0.3)` with no case-existence
check, no authorization, and no use of `settings.sse_timeout_seconds` despite that
setting existing and being unit-tested for its VALUE (test_api.py's
`test_sse_stream_has_a_bounded_timeout` asserted `settings.sse_timeout_seconds > 0` and
never actually called the endpoint) — a request for a nonexistent or never-completing
case held the connection open forever. Fixed to require case access, enforce a real
timeout, and check for client disconnect every iteration.
"""

import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings

client = TestClient(app)


def _create_case() -> "tuple[str, str]":
    res = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True})
    data = res.json()
    return data["id"], data["access_token"]


def test_stream_requires_a_valid_case_id_not_just_any_string():
    """A nonexistent case must not open the SSE generator at all — the connection is
    rejected with a normal HTTP error, not held open polling an empty status list."""
    res = client.get(
        "/api/v1/kadi/cases/CASE-doesnotexist12/stream",
        headers={"X-Case-Access-Token": "irrelevant"},
    )
    assert res.status_code == 404


def test_stream_requires_authorization():
    case_id, _token = _create_case()
    res = client.get(f"/api/v1/kadi/cases/{case_id}/stream")
    assert res.status_code == 401


def test_stream_rejects_a_foreign_case_token():
    case_a, _token_a = _create_case()
    _case_b, token_b = _create_case()
    res = client.get(
        f"/api/v1/kadi/cases/{case_a}/stream",
        headers={"X-Case-Access-Token": token_b},
    )
    assert res.status_code == 403


def test_stream_accepts_the_token_via_query_string_for_eventsource_compatibility():
    """The browser's native EventSource cannot set custom headers, so this one route
    also accepts ?access_token= — documented as a deliberate, narrower trade-off in
    ADR-009, not a general pattern used elsewhere.

    Uploads a document first so the stream reaches `completed` almost immediately
    rather than idling until the (real, ~120s default) sse_timeout_seconds — this test
    is about the query-string auth path, not the timeout, which has its own test below
    with the timeout deliberately shortened."""
    case_id, token = _create_case()
    client.post(
        f"/api/v1/kadi/cases/{case_id}/upload",
        files={"file": ("bill.txt", b"Consultation: 500\nTotal Amount: 500\n")},
        headers={"X-Case-Access-Token": token},
    )
    res = client.get(f"/api/v1/kadi/cases/{case_id}/stream?access_token={token}")
    assert res.status_code == 200


def test_stream_times_out_instead_of_holding_the_connection_forever(monkeypatch):
    """The core P0-2 fix: settings.sse_timeout_seconds must actually bound the stream.
    A case that is created but never processed (no upload) would previously poll an
    empty/never-completing status list forever."""
    monkeypatch.setattr(settings, "sse_timeout_seconds", 1)
    case_id, token = _create_case()

    started = time.time()
    res = client.get(
        f"/api/v1/kadi/cases/{case_id}/stream",
        headers={"X-Case-Access-Token": token},
    )
    elapsed = time.time() - started

    assert res.status_code == 200
    assert "timeout" in res.text
    # Bounded: allow generous scheduling slack, but this must not be "forever."
    assert elapsed < 10, f"stream took {elapsed:.1f}s despite a 1s configured timeout"


def test_stream_completes_promptly_for_a_case_that_finishes_processing():
    """Regression guard: the timeout fix must not have broken the legitimate fast path —
    a case whose document has already finished processing streams its events and closes
    immediately, well under the timeout."""
    case_id, token = _create_case()
    upload = client.post(
        f"/api/v1/kadi/cases/{case_id}/upload",
        files={"file": ("bill.txt", b"Consultation: 500\nTotal Amount: 500\n")},
        headers={"X-Case-Access-Token": token},
    )
    assert upload.status_code == 202  # background task already ran under TestClient

    started = time.time()
    res = client.get(
        f"/api/v1/kadi/cases/{case_id}/stream",
        headers={"X-Case-Access-Token": token},
    )
    elapsed = time.time() - started

    assert res.status_code == 200
    assert '"status": "completed"' in res.text or "completed" in res.text
    assert elapsed < 5
