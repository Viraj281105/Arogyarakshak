"""Database sessions for work that runs outside a request (FastAPI BackgroundTasks)."""

from contextlib import asynccontextmanager

from app.database import AsyncSessionLocal, get_db


@asynccontextmanager
async def get_background_session():
    """Honors FastAPI dependency_overrides (e.g. in test suites) and falls back to
    AsyncSessionLocal for local and production/Docker runs."""
    from app.main import app as fastapi_app

    override = fastapi_app.dependency_overrides.get(get_db)
    if override:
        async with asynccontextmanager(override)() as session:
            yield session
    else:
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
