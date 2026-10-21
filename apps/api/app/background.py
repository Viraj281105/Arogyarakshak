"""Database sessions for work that runs outside a request (FastAPI BackgroundTasks)."""

from contextlib import asynccontextmanager
from typing import Callable, Dict, Optional

from app.database import AsyncSessionLocal, get_db

# Where to look up FastAPI's dependency_overrides. app.main registers the application's
# map at import time, so this module never imports the entrypoint (ADR-018: nothing below
# the HTTP layer depends on app.main or app.api).
_override_source: Optional[Callable[[], Dict]] = None


def register_dependency_overrides(source: Callable[[], Dict]) -> None:
    global _override_source
    _override_source = source


@asynccontextmanager
async def get_background_session():
    """Honors FastAPI dependency_overrides (e.g. in test suites) and falls back to
    AsyncSessionLocal for local and production/Docker runs."""
    overrides = _override_source() if _override_source else {}
    override = overrides.get(get_db)
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
