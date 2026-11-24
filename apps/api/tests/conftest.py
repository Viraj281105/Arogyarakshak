import os

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event
from sqlalchemy.pool import NullPool

from app.main import app as fastapi_app
from app.database import Base, get_db
from app.rate_limit import limiter as rate_limiter
from app.latency_metrics import tracker as latency_tracker
import app.models  # Ensure models are imported to register with metadata

# Use a file-based SQLite database for reliable test persistence across connection lifetimes
# The file name carries the process id so two pytest processes started in the same directory
# never share (and corrupt) one database. Removed when the session ends.
TEST_DB_FILE = f"test_temp_{os.getpid()}.db"
DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=NullPool,
)


# SQLite ignores foreign keys unless asked; Postgres (the real database) enforces them.
# Without this, an insert-ordering bug that Postgres rejects passes every test — which is
# exactly how DaaviSetu's doctor-confirmation request shipped broken on Postgres.
@event.listens_for(engine.sync_engine, "connect")
def _enforce_foreign_keys(dbapi_connection, _record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def _remove_test_database_files():
    for suffix in ("", "-journal", "-wal", "-shm"):
        try:
            os.remove(TEST_DB_FILE + suffix)
        except OSError:
            pass


@pytest.fixture(autouse=True, scope="session")
def cleanup_test_database_session():
    """Remove this process's test database file before and after the whole session."""
    _remove_test_database_files()
    yield
    _remove_test_database_files()


@pytest.fixture(autouse=True, scope="function")
def reset_rate_limiter():
    """The rate limiter is a module-level singleton shared across the whole pytest
    session (same as `processing_status`) — without a reset, one test's request volume
    would count against the next test's limit and produce spurious 429s."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture(autouse=True, scope="function")
def reset_latency_tracker():
    """Same rationale as reset_rate_limiter — the latency tracker is a module-level
    singleton; without a reset, samples from unrelated tests would pollute a test that
    asserts a specific sample count or percentile."""
    latency_tracker.reset()
    yield
    latency_tracker.reset()


@pytest.fixture(autouse=True, scope="function")
def reset_llm_runtime():
    """Same rationale again for the resilient LLM client's process runtime (ADR-024):
    its circuit breakers and optional cache must not carry over between tests."""
    from kadi.llm import reset_default_runtime

    reset_default_runtime()
    yield
    reset_default_runtime()


@pytest.fixture(autouse=True, scope="function")
def no_groq_key(monkeypatch):
    """No test sees a Groq key (AGENTS.md network rule; WS2 review). CI used to set a mock
    GROQ_API_KEY, which made every unpatched appeal draft send a real request to
    api.groq.com. A test that needs the live-client code path sets a key itself with
    monkeypatch (which overrides this) AND patches the transport."""
    from app.config import settings

    monkeypatch.setattr(settings, "groq_api_key", "")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)


@pytest.fixture(autouse=True, scope="function")
def network_guard(monkeypatch):
    """Second layer: ``urllib.request.urlopen`` — the only outbound HTTP path the API and
    kadi.llm use — records the attempt and raises. A test that patches urlopen itself
    overrides this. Request this fixture by name to assert on the recorded URLs.

    No exceptions: the OCR parser never downloads model weights (download_enabled=False), so
    nothing in the test suite may reach the network."""
    import urllib.request

    attempts = []

    def guarded_urlopen(req, *args, **kwargs):
        attempts.append(getattr(req, "full_url", req))
        raise RuntimeError("live network calls are forbidden in tests")

    monkeypatch.setattr(urllib.request, "urlopen", guarded_urlopen)
    return attempts


@pytest.fixture(autouse=True, scope="function")
def setup_database():
    """Fixture to create all tables before each test and drop them after."""
    import asyncio
    from app.database import Base as db_base

    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(db_base.metadata.create_all)
            
    async def drop_tables():
        async with engine.begin() as conn:
            await conn.run_sync(db_base.metadata.drop_all)

    asyncio.run(create_tables())
    yield
    asyncio.run(drop_tables())
    asyncio.run(engine.dispose())


async def override_get_db():
    """Dependency override to yield the testing session."""
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Apply dependency override globally for all tests
fastapi_app.dependency_overrides[get_db] = override_get_db


# --- Accounts (ADR-026) ------------------------------------------------------------------
# Cheap scrypt parameters for every test (the hashing code path is the same), plus opt-in
# fixtures for the account tests: a fake service clock, an in-memory mail outbox and a
# relaxed per-IP auth bucket. Helpers live in tests/account_helpers.py.
from app.config import settings as _settings  # noqa: E402
from app.services import accounts as _account_service  # noqa: E402
from app.services.login_throttle import throttle as _login_throttle  # noqa: E402
from app.services.mail import InMemoryMailTransport, get_mail_transport  # noqa: E402
from tests.account_helpers import FakeClock  # noqa: E402


@pytest.fixture(autouse=True)
def fast_scrypt(monkeypatch):
    """Cheap scrypt parameters so the suite stays fast; the hashing code path is the same."""
    monkeypatch.setattr(_settings, "password_scrypt_n", 2**10)
    monkeypatch.setattr(_settings, "password_scrypt_r", 8)
    monkeypatch.setattr(_settings, "password_scrypt_p", 1)


@pytest.fixture
def clock(monkeypatch) -> FakeClock:
    fake = FakeClock()
    monkeypatch.setattr(_account_service, "utcnow", fake)
    return fake


@pytest.fixture
def outbox():
    transport = InMemoryMailTransport()
    fastapi_app.dependency_overrides[get_mail_transport] = lambda: transport
    yield transport.outbox
    fastapi_app.dependency_overrides.pop(get_mail_transport, None)


@pytest.fixture
def relaxed_auth_limit(monkeypatch):
    monkeypatch.setattr(_settings, "auth_rate_limit_per_minute", 10_000)


@pytest.fixture(autouse=True)
def reset_login_throttle():
    """The sign-in throttle is an in-memory singleton like the rate limiter."""
    _login_throttle.reset()
    yield
    _login_throttle.reset()
