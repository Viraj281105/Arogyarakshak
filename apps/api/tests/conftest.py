import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event
from sqlalchemy.pool import StaticPool

from app.main import app as fastapi_app
from app.database import Base, get_db
from app.rate_limit import limiter as rate_limiter
from app.latency_metrics import tracker as latency_tracker
import app.models  # Ensure models are imported to register with metadata

# Use a file-based SQLite database for reliable test persistence across connection lifetimes
DATABASE_URL = "sqlite+aiosqlite:///test_temp.db"

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
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
def setup_database():
    """Fixture to create all tables before each test and drop them after."""
    import asyncio
    import app.models
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
    try:
        import os
        if os.path.exists("test_temp.db"):
            os.remove("test_temp.db")
    except Exception:
        pass


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
