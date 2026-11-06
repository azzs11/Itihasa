# Itihasa

An open knowledge graph and discovery platform for India's cultural heritage documents.

## Overview

Itihasa ingests heritage documents from open institutional sources (Wikidata, Wikipedia,
Internet Archive, museum APIs) and from public uploads such as family manuscripts and
land deeds. Every record carries its source, licence and provenance. Users search and
receive ranked results with graph-based recommendations, nearby entities and explanations
that show which graph path connects a result, where the evidence appears in the document,
and how certain the underlying facts are.

```
Sources → Collect → Normalise → Ingest → Graph → Retrieve → Rank → Explain → API
                                            ↑
                                        Public uploads (Phase 4)
```

The project produces five research outputs: Itihasa-Bench (the first public test
collection for Indian heritage retrieval), a study of cost-aware human-in-the-loop
curation, a study of cataloguing under uncertain Indic OCR, trust-aware graph
recommendation with a user study, and a public corpus and demo.

## Quick start

Requirements: Python 3.12+, Docker.

```bash
# 1. Clone and enter the repo
git clone https://github.com/Akchhya1108/Itihasa.git
cd Itihasa

# 2. Install uv (if not already installed)
#    Windows: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
#    macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install dependencies
uv sync --extra dev

# 4. Copy and edit the environment file
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD to something other than "changeme"

# 5. Start the database
docker compose up -d

# 6. Run migrations
uv run alembic upgrade head

# 7. Run tests
uv run pytest -m "not db"          # schema tests only, no Docker needed
uv run pytest                       # all tests, requires Docker
```

## Repository map

| Path | Contents |
|------|----------|
| `src/itihasa/` | Python package — collect, normalise, ingest, graph, retrieve, rank, explain, api |
| `tests/` | Tests mirroring `src/itihasa/` one-to-one |
| `migrations/` | Alembic migration scripts |
| `configs/` | YAML configs per pipeline and experiment |
| `scripts/` | Thin command-line entry points |
| `docs/` | Architecture, data card, decision records, guides |
| `docs/decisions/` | One decision record per tool or method chosen |
| `docs/planning/` | Candidate options for Phase 2 evaluation |
| `evaluation/` | Query files, qrels, and annotation protocols (data not committed) |
| `results/` | Generated; each run in its own dated folder (not committed) |
| `notebooks/` | Exploration only; nothing a result depends on |

## Reproducing paper results

Not yet available.

## How to cite

Placeholder — to be filled when the first paper is submitted.

## Licence

Code: Apache 2.0. See [LICENSE](LICENSE).

Data licensing is set per source in [docs/data-card.md](docs/data-card.md).
Uploaded documents keep their source terms; annotations and the benchmark are
expected to be CC BY 4.0 (to be confirmed before release).
