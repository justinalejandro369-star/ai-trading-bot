"""
Async database engine and session factory.

Supports SQLite (dev) and PostgreSQL+TimescaleDB (prod) via DATABASE_URL env var.
All application code uses get_session() as an async context manager.
"""
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

__all__ = ["engine", "async_session_factory", "get_session"]

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """
    Async context manager for database sessions.

    Automatically commits on success and rolls back on exception.
    Usage:
        async with get_session() as session:
            session.add(record)
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
