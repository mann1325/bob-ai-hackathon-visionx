import logging
from typing import Generator, Optional
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)

_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def get_engine() -> Optional[Engine]:
    """Initialize or retrieve the SQLAlchemy engine."""
    global _engine
    if _engine is not None:
        return _engine

    settings = get_settings()
    if not settings.database_url:
        logger.warning(
            "DATABASE_URL not configured. Database-dependent endpoints will return 503."
        )
        return None

    db_url = settings.database_url
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    try:
        _engine = create_engine(
            db_url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
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
    factory = get_session_factory()
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
