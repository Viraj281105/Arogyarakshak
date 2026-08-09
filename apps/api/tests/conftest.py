import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import app as fastapi_app
from app.database import Base, get_db
import app.models  # Ensure models are imported to register with metadata

# Use a file-based SQLite database for reliable test persistence across connection lifetimes
DATABASE_URL = "sqlite+aiosqlite:///test_temp.db"

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


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
