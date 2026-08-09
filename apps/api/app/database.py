"""
Database Configuration.

Configures asynchronous SQLAlchemy connections to PostgreSQL.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

from app.config import settings

# In production settings.database_url could use postgresql://, but asyncpg requires postgresql+asyncpg://
async_db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

# Enable connection pooling for production stability
engine = create_async_engine(
    async_db_url,
    pool_size=20,
    max_overflow=10,
    pool_recycle=1800,
    pool_pre_ping=True,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency to retrieve async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
