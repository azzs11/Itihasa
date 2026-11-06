# 002 — Record store

**Date proposed:** 2026-11-06
**Status:** Proposed — decision pending

## Context

Every source document (Wikidata entity, Wikipedia article, Internet Archive scan,
museum object record, uploaded manuscript) is normalised into a common record schema
(~25 fields; see section 3 of the project brief). Records must support:

- structured queries (by period, region, language, licence, source, entity);
- flexible storage of raw source metadata without loss;
- versioning and provenance (covered in decision 003);
- incremental ingest from multiple connectors running in parallel;
- analytical queries during evaluation (counts by source, type, licence).

The record store is the operational database; analytical queries during evaluation
may use a separate query layer (DuckDB over Parquet exports) if needed.

## Options

| Option | Licence | Notes |
|--------|---------|-------|
| PostgreSQL 18 + SQLAlchemy 2 + Alembic | PostgreSQL licence | Relational + JSONB for raw metadata; ACID; PostGIS for geo; `pg_trgm` for fuzzy name search; mature migration toolchain |
| MongoDB 7 Community | SSPL | Flexible document schema; SSPL licence restricts redistribution of scripts that call it as a service |
| DuckDB 1.x | MIT | Embedded OLAP; excellent for analytical queries; single-writer, not suitable as the operational ingest database |
| CouchDB 3 | Apache 2.0 | Document store with multi-master replication; good for distributed ingest but adds complexity for a single-machine setup |
| SQLite 3 | Public domain | Embedded, zero overhead; single-writer limitation makes concurrent ingest impractical |

## Literature

- Europeana (cultural heritage aggregator at scale) uses PostgreSQL as its metadata
  store alongside Solr and Cassandra. See Haslhofer & Isaac (2011), "data.europeana.eu:
  The Europeana Linked Open Data pilot", *WWW*.
- DSpace 7 (widely deployed institutional repository) uses PostgreSQL 12+ with
  Hibernate ORM and Flyway migrations.
- Fedora Commons 6 (GLAM digital repository) supports PostgreSQL as its primary store.
- PREMIS-based provenance implementations in the library sector almost universally
  use relational databases for the event log (see decision 003).

## Comparison

| Criterion | PostgreSQL 18 | MongoDB 7 | DuckDB | CouchDB | SQLite |
|-----------|---------------|-----------|--------|---------|--------|
| ACID guarantees | Full | Per-document | Full (embedded) | Eventual | Full |
| Concurrent ingest | Yes | Yes | No (single-writer) | Yes | No |
| Raw metadata (JSONB) | Yes | Native | Via JSON type | Native | Via JSON1 |
| Geo queries | PostGIS | Geo indexes | Limited | No | No |
| Fuzzy name search | `pg_trgm`, `unaccent` | Text index | Limited | Limited | Limited |
| Schema migration | Alembic (mature) | Manual | Not needed | CouchDB migrations | Alembic |
| Licence | Permissive | SSPL | MIT | Apache 2.0 | Public domain |
| Heritage / GLAM use | Very common | Rare | Rare (analytics) | Rare | Prototype only |
| Compute (laptop) | ~200 MB idle | ~400 MB idle | Embedded | ~150 MB | Embedded |

## Recommendation

**PostgreSQL 18 + SQLAlchemy 2 + Alembic.**

Structured fields (period, language, licence, entities) are queried relationally.
Raw source metadata is preserved losslessly in a `raw_metadata JSONB` column, so
no information is discarded during normalisation. PostGIS covers place queries.
Alembic manages schema evolution as new sources require new fields.

MongoDB's SSPL licence is a concern for open-source reproducibility; SQLite and
DuckDB do not support concurrent writes needed during parallel ingest.

**Main risk:** Schema migrations with Alembic require discipline. Each source connector
may reveal new fields that require migration. Mitigated by keeping source-specific
fields in the `raw_metadata` JSONB column and migrating only when a field graduates
to the common schema.

## Decision

> *Owner to record decision and date here.*

## Consequences

- PostgreSQL 18 runs in Docker Compose (see decision on service stack).
- SQLAlchemy 2 ORM manages all database access; raw SQL only for complex analytical
  queries or Alembic migration scripts.
- Alembic handles all schema changes; no hand-editing of tables.
- Each source connector stores its full API or SPARQL response in `raw_metadata`
  before any field is mapped to the common schema.
- DuckDB may be used as a read-only analytical layer over PostgreSQL exports during
  evaluation, but it is not the operational record store.
