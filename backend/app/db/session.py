"""Database connection and session factory management."""

import os
from collections.abc import Generator
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db.base import Base


def normalize_db_url(url: str) -> str:
    """Normalize database connection URL to appropriate SQLAlchemy driver."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def create_app_engine(db_url: str | None = None) -> Engine:
    """Create and configure a SQLAlchemy Engine instance."""
    resolved_url = db_url or os.getenv("DATABASE_URL") or get_settings().DATABASE_URL
    normalized_url = normalize_db_url(resolved_url)

    engine_kwargs: dict[str, Any] = {"echo": False}
    if "sqlite" in normalized_url:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in normalized_url:
            engine_kwargs["poolclass"] = StaticPool

    engine = create_engine(normalized_url, **engine_kwargs)

    # Enable SQLite foreign key enforcement
    if "sqlite" in normalized_url:

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Return default application database engine singleton."""
    global _engine
    if _engine is None:
        _engine = create_app_engine()
    return _engine


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Return sessionmaker bound to specified or default engine."""
    global _SessionFactory
    target_engine = engine or get_engine()
    if _SessionFactory is None or engine is not None:
        factory = sessionmaker(autocommit=False, autoflush=False, bind=target_engine)
        if engine is None:
            _SessionFactory = factory
        return factory
    return _SessionFactory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def init_db(engine: Engine | None = None) -> None:
    """Create all declarative tables in the connected database."""
    target_engine = engine or get_engine()
    Base.metadata.create_all(bind=target_engine)
