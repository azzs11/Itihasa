"""SQLAlchemy engine and session factory.

Reads DATABASE_URL from the environment. All other modules obtain a session
via get_session() and must not create engines directly.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError(
                "DATABASE_URL is not set. "
                "Copy .env.example to .env and fill in the values."
            )
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def _get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=_get_engine(), autocommit=False, autoflush=False)
    return _SessionLocal


def get_session() -> Session:
    """Return a new database session.

    The caller is responsible for closing it (use as a context manager or
    call session.close() explicitly).
    """
    return _get_session_factory()()


def reset_engine(url: str | None = None) -> None:
    """Replace the engine with a new one.

    Used in tests to point at the test database without touching the
    environment variable.
    """
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
    if url is not None:
        os.environ["DATABASE_URL"] = url
