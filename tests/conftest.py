"""Shared pytest fixtures.

The ``db_session`` fixture spins up a real PostgreSQL connection, runs all
Alembic migrations, yields a session whose every test runs inside a transaction
that is rolled back on teardown, then drops all tables.  Tests that need this
fixture must be marked ``@pytest.mark.db`` and will be skipped automatically
when Docker is not running.

Run only schema tests (no Docker needed):
    pytest -m "not db"

Run everything (Docker must be up):
    pytest
"""

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker


def _test_url() -> str:
    base = os.environ.get("DATABASE_URL", "")
    if not base:
        return ""
    # Point at a separate test database to keep the dev database clean.
    if base.endswith("/itihasa"):
        return base[: -len("/itihasa")] + "/itihasa_test"
    return base + "_test"


def _alembic_cfg(url: str) -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture(scope="session")
def db_engine():
    """Create the test database, run migrations, yield the engine, drop all."""
    url = _test_url()
    if not url:
        pytest.skip("DATABASE_URL not set; skipping database tests")

    # Create the test database if it does not exist.
    admin_url = url.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    db_name = url.rsplit("/", 1)[-1]
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": db_name}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin_engine.dispose()

    engine = create_engine(url)
    command.upgrade(_alembic_cfg(url), "head")
    yield engine

    from itihasa.db.models import Base
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Yield a session that rolls back after each test."""
    factory = sessionmaker(bind=db_engine)
    session = factory()
    session.begin_nested()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
