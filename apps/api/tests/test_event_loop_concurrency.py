"""SEC-01 regression: synchronous, CPU-heavy work (OCR/PyMuPDF/EasyOCR) and synchronous
network calls (the Groq urllib pipeline) must run off FastAPI's single event loop
(run_in_threadpool / asyncio.to_thread), not directly inside an async route/background
task — otherwise one in-flight document upload or appeal draft can stall every other
request, including a bare GET /health, for as long as that work takes.

This test proves the property directly: while a (fake) blocking OCR call is confirmed to
be in progress on a background task, a concurrent GET /health must still complete
promptly. That is only possible if the blocking call is actually running on a worker
thread, not on the event loop itself.
"""

import asyncio
import threading
import time

import pytest
from httpx import ASGITransport, AsyncClient

import app.api.v1.endpoints.kadi as kadi_module
from app.main import app

_started = threading.Event()
_release = threading.Event()


def _blocking_parse_document(file_bytes, filename):
    """Stands in for kadi.ocr.ocr_parser.parse_document. Signals `_started` the instant
    it begins running, then blocks (synchronously — no `await`, exactly like real
    PyMuPDF/EasyOCR work) until the test releases it."""
    _started.set()
    _release.wait(timeout=10)
    return {
        "extraction_ok": True,
        "full_text_content": "Consultation: 500\nTotal Amount: 500\n",
        "line_items": [{"item": "Consultation", "charged": 500.0}],
    }


@pytest.mark.asyncio
async def test_health_stays_responsive_while_document_processing_blocks(monkeypatch):
    _started.clear()
    _release.clear()
    monkeypatch.setattr(kadi_module, "parse_document", _blocking_parse_document)
    monkeypatch.setattr(kadi_module.settings, "groq_api_key", "")  # force offline extraction fallback

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            case_res = await ac.post("/api/v1/kadi/cases", json={"consent_opt_in": True})
            assert case_res.status_code == 201
            case_id = case_res.json()["id"]
            token = case_res.json()["access_token"]

            upload_task = asyncio.create_task(
                ac.post(
                    f"/api/v1/kadi/cases/{case_id}/upload",
                    files={"file": ("bill.txt", b"Consultation: 500\nTotal Amount: 500\n")},
                    headers={"X-Case-Access-Token": token},
                )
            )

            # Wait (on a separate thread, via asyncio.to_thread) until the background
            # task's OCR call has actually started and is blocked inside it — this
            # proves the /health call below races a REAL in-flight blocking call.
            await asyncio.wait_for(asyncio.to_thread(_started.wait, 5), timeout=5)

            # While parse_document is still blocked (never released yet), /health must
            # still respond promptly. This is only possible if parse_document is running
            # on a worker thread (run_in_threadpool) rather than directly on the single
            # event loop — if it were unwrapped, this request could not even be
            # scheduled until the blocking call returned.
            t0 = time.monotonic()
            health_res = await asyncio.wait_for(ac.get("/health"), timeout=3)
            health_elapsed = time.monotonic() - t0

            assert health_res.status_code == 200
            assert health_elapsed < 1.0, (
                f"/health took {health_elapsed:.2f}s while OCR was in-flight — "
                "the event loop appears to be blocked by synchronous OCR work (SEC-01)"
            )

            _release.set()  # let the fake OCR finish so the background task can complete
            upload_res = await asyncio.wait_for(upload_task, timeout=5)
            assert upload_res.status_code == 202
    finally:
        _release.set()  # never leave the fake OCR thread hanging, pass or fail
