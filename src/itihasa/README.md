# itihasa Python package

The top-level package for the Itihasa platform. Sub-packages are added one phase
at a time; only what exists is listed here.

## Current sub-packages

| Sub-package | Purpose |
|-------------|---------|
| `itihasa.schema` | Common record schema (`Record`) and custom field validators |
| `itihasa.db` | SQLAlchemy engine, session factory, and ORM models |

## Entry points

None yet. Command-line entry points will live in `scripts/` and import from here.

## See also

- [docs/architecture.md](../../docs/architecture.md) — how the sub-packages connect
- [docs/decisions/](../../docs/decisions/) — why each tool was chosen
