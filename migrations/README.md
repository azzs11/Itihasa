# migrations

Alembic migration scripts for the Itihasa database.

## Running migrations

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Roll back one step
uv run alembic downgrade -1

# Show current revision
uv run alembic current

# Show migration history
uv run alembic history
```

## Adding a migration

```bash
uv run alembic revision -m "short description"
```

Edit the generated file in `versions/`. Always implement both `upgrade()` and
`downgrade()`.

## Naming convention

Files are prefixed with a four-digit sequence number: `0001_initial_schema.py`,
`0002_add_embeddings.py`, and so on. The number is for human readability; Alembic
uses the `revision` string internally.

## Current migrations

| File | What it creates |
|------|----------------|
| `0001_initial_schema.py` | `records`, `record_versions`, `provenance_events`, `graph_nodes`, `graph_edges`; enables the `vector` extension |
