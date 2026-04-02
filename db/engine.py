"""
Database engine configuration.

Provides both sync and async engines/sessions:
- Sync: Used by pipeline code (main.py, scheduler, orchestrator)
- Async: Used by FastAPI routes

Both read DATABASE_URL from environment.
"""

import os
import logging
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

# Load .env from project root so DATABASE_URL is always available
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)


def _get_database_url() -> str:
    """Get the database URL from environment."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL not set. Example: postgresql://user:pass@localhost:5432/linkedin_machine"
        )
    return url


def _sync_url(url: str) -> str:
    """Ensure URL uses psycopg2 driver for sync operations."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def _async_url(url: str) -> str:
    """Ensure URL uses asyncpg driver for async operations."""
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


# Lazy-initialized engines
_sync_engine = None
_async_engine = None


def get_sync_engine():
    """Get or create the sync SQLAlchemy engine."""
    global _sync_engine
    if _sync_engine is None:
        url = _sync_url(_get_database_url())
        _sync_engine = create_engine(
            url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=os.getenv("DB_ECHO", "").lower() == "true",
        )
        logger.info("Sync database engine initialized")
    return _sync_engine


def get_async_engine():
    """Get or create the async SQLAlchemy engine."""
    global _async_engine
    if _async_engine is None:
        url = _async_url(_get_database_url())
        _async_engine = create_async_engine(
            url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=os.getenv("DB_ECHO", "").lower() == "true",
        )
        logger.info("Async database engine initialized")
    return _async_engine


def get_sync_session_factory() -> sessionmaker:
    """Get a sync session factory."""
    return sessionmaker(bind=get_sync_engine(), expire_on_commit=False)


def get_async_session_factory() -> async_sessionmaker:
    """Get an async session factory."""
    return async_sessionmaker(
        bind=get_async_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


@contextmanager
def sync_session():
    """Context manager for sync database sessions."""
    factory = get_sync_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
