# tests

Mirrors `src/itihasa/` one-to-one. Every module in the package has a corresponding
test file here.

## Running tests

```bash
# Schema and unit tests only (no Docker required)
uv run pytest -m "not db"

# All tests including database tests (Docker must be running)
uv run pytest

# With coverage
uv run pytest --cov=src/itihasa
```

## Markers

| Marker | Meaning |
|--------|---------|
| `db` | Requires a live PostgreSQL database. Deselect with `-m "not db"` when Docker is not running. |

## Test database

Database tests use a separate `itihasa_test` database on the same PostgreSQL
instance. Each test runs inside a transaction that is rolled back on teardown,
so tests are isolated and the database is left clean.

The `db_engine` session fixture in `conftest.py` creates the test database if it
does not exist and runs `alembic upgrade head` before the test session starts.
