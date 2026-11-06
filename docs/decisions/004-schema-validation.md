# 004 — Schema validation

**Date proposed:** 2026-11-06
**Status:** Proposed — decision pending

## Context

The common record schema (project brief, section 3) has approximately 25 fields with
controlled vocabularies and constrained formats:

- `doc_type`: controlled vocabulary (8 values)
- `language`: BCP 47 tag (e.g. `hi`, `sa`, `ta`)
- `script`: ISO 15924 code (e.g. `Deva`, `Gran`, `Taml`)
- `licence`: SPDX identifier or Creative Commons URI
- `period`: EDTF interval string (e.g. `1630~/1680~`)
- `entities`: list of Wikidata QIDs or Itihasa IDs
- `checksum`: SHA-256 hex string
- `confidence`: float in [0.0, 1.0] on every machine-produced field

Validation must be strict at every ingest boundary (connector output, upload form,
API input), fast enough for batch ingest, and produce clear error messages that
help a contributor fix a malformed record. The schema must also be published for
external data contributors and cited in the data card.

Two functions are needed and they are not the same:
1. **Runtime validation** in Python: check each record as it is produced or ingested.
2. **Published schema** for external users: a language-agnostic, human-readable
   specification they can validate against without installing the Python package.

## Options

| Option | Licence | Notes |
|--------|---------|-------|
| **Pydantic v2** | MIT | Rust-based core; typed Python models; excellent IDE support; auto-generates JSON Schema; used in FastAPI |
| **pandera** | Apache 2.0 | DataFrame-centric; validates pandas/polars frames, not individual record objects |
| **JSON Schema (jsonschema library)** | MIT | Language-agnostic W3C standard; validation logic must be duplicated in Python |
| **Frictionless Data** | MIT | Tabular (CSV/TSV) focus; not designed for nested document records |
| **Cerberus** | ISC | Lightweight dict validation; no IDE support; no JSON Schema export |

## Literature

- Europeana Data Model (EDM) uses JSON-LD with JSON Schema for record interchange.
  Schema is published at schema.org extensions for cultural heritage objects.
- FastAPI (the chosen API framework) has first-class Pydantic v2 integration;
  request and response models are defined once and serve as both runtime validators
  and OpenAPI schema generators.
- The W3C JSON-LD and JSON Schema specifications are the standard interchange
  formats for GLAM sector data (Europeana, Smithsonian, Rijksmuseum all publish
  JSON Schema for their APIs).

## Comparison

| Criterion | Pydantic v2 | pandera | jsonschema | Frictionless | Cerberus |
|-----------|-------------|---------|------------|--------------|---------|
| Record-level validation | Yes | No (frame-level) | Yes | No (tabular) | Yes |
| Typed Python models | Yes | Partial | No | No | No |
| IDE autocomplete | Excellent | Good | None | None | None |
| JSON Schema export | Automatic | Manual | Native | Native | Manual |
| Performance | Fast (Rust core) | Moderate | Moderate | Moderate | Light |
| FastAPI integration | Native | No | No | No | No |
| Indic / Unicode | Full | Full | Full | Full | Full |
| EDTF / BCP 47 validators | Via custom field types | Manual | Via regex | Manual | Manual |
| Licence | MIT | Apache 2.0 | MIT | MIT | ISC |

## Recommendation

**Pydantic v2 for runtime validation, with JSON Schema automatically exported from
the Pydantic models for the data card and external users.** These serve different
purposes and are not alternatives.

- The Pydantic model is the single source of truth; the JSON Schema is derived
  from it, never maintained separately.
- Custom field types (`EDTFDate`, `BCP47Tag`, `SpdxLicence`, `WikidataQID`)
  provide EDTF, BCP 47, SPDX and QID validation with clean error messages.
- The exported JSON Schema ships in `docs/data-card.md` and the API documentation.
- When FastAPI is added in Phase 7, the same Pydantic models validate API requests
  with no additional code.

**Main risk:** Pydantic v2 validators for domain-specific formats (EDTF, Saka era
strings, Wikidata QIDs) must be written and tested. No existing library covers all
of these for Indic heritage data. This is planned work, not a risk to the architecture.

## Decision

> *Owner to record decision and date here.*

## Consequences

- `src/itihasa/schema/record.py` contains the canonical Pydantic v2 `Record` model.
- `src/itihasa/schema/fields.py` contains custom annotated types for domain-specific
  formats.
- JSON Schema is exported to `docs/schema/record.json` as part of the documentation
  build; it is regenerated whenever the Pydantic model changes.
- Every connector and ingest function validates its output against the `Record` model
  before writing to the database. A `ValidationError` aborts the write and logs the
  offending record to the provenance events table with `outcome = "validation_failed"`.
