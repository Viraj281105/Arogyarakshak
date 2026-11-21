"""Shared fixtures and helpers for the chaos (fault-injection) tests.

Why a helper module and not ``conftest.py``: a second ``conftest.py`` outside a package would be
imported as the top-level name ``conftest`` and collide with ``packages/kadi/tests/conftest.py``
(the same failure that broke CI once before). The API test suite's fixtures (SQLite database
per test, rate-limiter and LLM-runtime resets, no Groq key, the live-network guard) are
re-used from ``apps/api/tests/conftest.py`` so the chaos tests run against the REAL FastAPI app
under the same isolation rules. Test modules do ``from chaos_harness import *``.
"""

import asyncio
import json
from contextlib import contextmanager
from typing import List

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

# Re-exported so pytest registers them in each chaos test module (autouse fixtures).
from tests.conftest import (  # noqa: F401
    TEST_DB_FILE,
    TestingSessionLocal,
    cleanup_test_database_session,
    network_guard,
    no_groq_key,
    reset_latency_tracker,
    reset_llm_runtime,
    reset_rate_limiter,
    setup_database,
)
from tests.auth_test_client import AuthAwareTestClient

from app import main as main_module
from app.database import get_db
from app.main import app
from app.models import KadiDocumentJob

K = "/api/v1/kadi"

# Strings that must never appear in a response body, an SSE event or a job row. They stand in
# for connection strings, credentials and document content that an exception message could carry.
SECRET_CONNECTION = "postgresql://svc:hunter2-CHAOS@10.9.8.7:5432/arogya"
SECRET_DOCUMENT = "PATIENT-ASHA-RAO-AADHAAR-1234-5678-9012"
LEAK_MARKERS = (SECRET_CONNECTION, "hunter2-CHAOS", "10.9.8.7", SECRET_DOCUMENT, "Traceback", "OperationalError")

TEXT_BILL = b"Hospital bill\nConsultation 500\nX-Ray 400\nTotal: 900\n"

# raise_server_exceptions=False: a deployed server turns an unhandled error into a 500 response
# (the TestClient default would re-raise it into the test instead).
client = AuthAwareTestClient(app, raise_server_exceptions=False)

__all__ = [
    "TEST_DB_FILE", "K", "LEAK_MARKERS", "SECRET_CONNECTION", "SECRET_DOCUMENT", "TEXT_BILL", "TestingSessionLocal",
    "client", "main_module", "new_case", "upload", "stream_events", "jobs", "assert_no_leak",
    "database_unavailable", "db_down", "ready_schema", "cleanup_test_database_session",
    "network_guard", "no_groq_key", "reset_latency_tracker", "reset_llm_runtime",
    "reset_rate_limiter", "setup_database",
]


class UnavailableSession:
    """Stands in for an AsyncSession whose database has gone away: every statement fails with
    the error a lost Postgres connection produces, and the message carries credentials."""

    is_active = True
    failures = 0  # how many statements failed: proves the injected fault really fired

    def _fail(self):
        UnavailableSession.failures += 1
        raise OperationalError("SELECT 1", {}, ConnectionRefusedError(f"could not connect to {SECRET_CONNECTION}"))

    async def execute(self, *args, **kwargs):
        self._fail()

    async def commit(self):
        self._fail()

    async def flush(self, *args, **kwargs):
        self._fail()

    async def refresh(self, *args, **kwargs):
        self._fail()

    async def rollback(self):
        return None

    async def close(self):
        return None

    def add(self, *args, **kwargs):
        return None


@contextmanager
def database_unavailable():
    """Every request (and every background task) gets a session that cannot reach the database."""

    async def failing_get_db():
        yield UnavailableSession()

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = failing_get_db
    try:
        yield
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous


@pytest.fixture
def db_down():
    UnavailableSession.failures = 0
    with database_unavailable():
        yield


@pytest.fixture
def ready_schema(monkeypatch):
    """The start-up schema step succeeded (the TestClient does not run the lifespan)."""
    monkeypatch.setitem(main_module.schema_state, "ok", True)
    monkeypatch.setitem(main_module.schema_state, "revision", "chaos-test")


def new_case() -> str:
    res = client.post(f"{K}/cases", json={"consent_opt_in": True})
    assert res.status_code == 201, res.text
    return res.json()["id"]


def upload(case_id: str, data: bytes = TEXT_BILL, name: str = "bill.txt"):
    return client.post(f"{K}/cases/{case_id}/upload", files={"file": (name, data)})


def stream_events(case_id: str) -> List[dict]:
    res = client.get(f"{K}/cases/{case_id}/stream")
    assert res.status_code == 200
    return [json.loads(line[6:]) for line in res.text.splitlines() if line.startswith("data: ")]


def jobs(case_id: str):
    """(state, error_id) of every document job of the case, from the database."""

    async def run():
        async with TestingSessionLocal() as s:
            rows = await s.execute(select(KadiDocumentJob).where(KadiDocumentJob.case_id == case_id))
            return [(j.state, j.error_id) for j in rows.scalars().all()]

    return asyncio.run(run())


def assert_no_leak(text: str, *extra: str) -> None:
    for marker in LEAK_MARKERS + extra:
        assert marker not in text, f"{marker!r} leaked into: {text[:300]}"


