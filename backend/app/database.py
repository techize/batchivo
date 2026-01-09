"""Database configuration and session management."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Log which database connection mode is being used
if settings.rls_enabled and settings.rls_database_url:
    logger.info("Database: Using RLS-enabled connection (app_user role)")
else:
    logger.info("Database: Using standard connection (migrations/superuser)")

# Create async engine using the effective database URL
# When RLS is enabled, this uses app_user role which has RLS policies enforced
engine = create_async_engine(
    settings.effective_database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions (for use outside FastAPI routes).

    Usage:
        async with get_db_context() as db:
            result = await db.execute(select(User))
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database (create tables if they don't exist)."""
    async with engine.begin() as conn:
        # In production, use Alembic migrations instead
        if settings.is_development:
            # await conn.run_sync(Base.metadata.drop_all)  # Uncomment to reset
            await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
