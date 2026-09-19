import logging
from typing import Generator, Optional

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import database.models  # noqa: F401 - register all ORM models before schema creation
from app.config import get_settings, normalize_database_url
from database.base import Base

logger = logging.getLogger(__name__)

_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def get_engine() -> Optional[Engine]:
    """Initialize or retrieve the SQLAlchemy engine."""
    global _engine
    if _engine is not None:
        return _engine

    settings = get_settings()
    db_url = normalize_database_url(settings.database_url)
    if not db_url:
        logger.warning(
            "DATABASE_URL not configured. Database-dependent endpoints will return 503."
        )
        return None

    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    try:
        _engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=1800,
            connect_args=connect_args,
        )
        if db_url.startswith("sqlite"):
            Base.metadata.create_all(bind=_engine)
            logger.info("SQLite schema initialized for local development.")
        logger.info("SQLAlchemy engine initialized.")
    except Exception as exc:
        logger.error("Failed to initialize database engine: %s", exc)
        return None

    return _engine


def get_session_factory() -> Optional[sessionmaker]:
    """Retrieve or create the sessionmaker factory."""
    global _session_factory
    if _session_factory is not None:
        return _session_factory

    engine = get_engine()
    if engine is None:
        return None

    _session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    factory = _session_factory
    if factory is None:
        raise HTTPException(
            status_code=503,
            detail="Database connection is not configured or unavailable.",
        )

    db = factory()
    try:
        yield db
    finally:
        db.close()
