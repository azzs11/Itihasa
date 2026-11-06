# 003 — Provenance and versioning model

**Date proposed:** 2026-11-06
**Status:** Proposed — decision pending

## Context

Itihasa must satisfy three requirements simultaneously:

1. **Auditability:** every machine-produced field (OCR text, entity link, date parse,
   duplicate verdict) records which tool, model, model version and configuration produced
   it, the confidence score, and when.
2. **Reproducibility:** any snapshot of the corpus can be reconstructed from a tagged
   commit plus the provenance log. OAIS (ISO 14721) requires a complete trail.
3. **Queryability:** "which records were updated after date X", "which links were
   produced by model Y version Z with confidence below 0.6", and "show all changes
   to record R" must be answerable without full table scans.

## Options

| Option | Description |
|--------|-------------|
| **3-table design** (owner-specified) | `records` (current state) + `record_versions` (immutable snapshots, one row per change) + `provenance_events` (PREMIS-style: event type, datetime, detail, agent, tool, model version, outcome, linked to record + version) |
| **Event sourcing** | Store only events; derive current state at query time by replaying. No `records` table; all state is recomputed. |
| **PostgreSQL bi-temporal tables** | System time + valid time on the records table; built-in versioning via `FOR SYSTEM_TIME AS OF`. |
| **JSONB event array in `records`** | Append provenance events as a JSONB array column on the same row as the current record. No separate events table. |

## Literature

- **PREMIS Data Dictionary v3.0** (Library of Congress, 2015, updated 2021):
  defines semantic units for digital preservation events — `eventType`,
  `eventDateTime`, `eventDetail`, `linkingAgentIdentifier`,
  `linkingObjectIdentifier`. The 3-table design maps directly onto these.
- **OAIS Reference Model (ISO 14721:2012):** requires a complete and auditable
  Provenance Information package for every stored object. Separate event rows
  satisfy this more cleanly than embedded JSONB arrays.
- **PROV-O** (W3C Recommendation, 2013): OWL2 ontology for provenance; the
  `provenance_events` table can be mapped to PROV-O Activity, Agent and Entity
  for future RDF export.
- Fedora Commons 6 and Archivematica (both GLAM-sector tools) store provenance
  as separate event tables linked to object versions.

## Comparison

| Criterion | 3-table design | Event sourcing | Bi-temporal | JSONB array |
|-----------|---------------|----------------|-------------|-------------|
| Auditability | Full: separate event rows | Full: event log is the truth | Full: system-time history | Partial: harder to query across records |
| Current-state read speed | Fast (direct read of `records`) | Slow (must replay events) | Fast (current row) | Fast |
| "History of record R" | Simple join | Replay events | `FOR SYSTEM_TIME` query | JSONB traversal (slow at scale) |
| "All events by agent X" | Simple query on `provenance_events` | Full scan of events log | Not supported | JSONB containment query (slow) |
| PREMIS alignment | Direct | Requires mapping | Partial | Partial |
| Schema complexity | Medium (3 tables + FK relations) | Low (1 table) | Low (1 table with temporal) | Low (1 table, complex JSONB) |
| Alembic migration risk | Low | Low | Low | Low |
| PostgreSQL 18 support | Full | Full | Full (native temporal) | Full |

## Recommendation

**3-table design as specified.**

The separate `provenance_events` table is the strongest choice for auditability
and PREMIS alignment. Event sourcing's reconstruction cost grows with corpus size
and is unnecessary when the current state is small enough to store directly.
Bi-temporal tables are elegant but query syntax is unfamiliar and tool support
is immature. JSONB arrays cannot be efficiently queried across records.

**Main risk:** The `record_versions` table grows large over time (one immutable row per
change to any record). Mitigated by storing only changed fields in a JSONB `delta`
column alongside the full snapshot for the first version, or by periodic archiving of
old versions.

## Decision

> *Owner to record decision and date here.*

## Consequences

The three tables and their relationships:

```
records            record_versions            provenance_events
----------         ---------------            -----------------
record_id (PK)     version_id (PK)            event_id (PK)
source             record_id (FK)             record_id (FK)
source_url         version_number             version_id (FK)
...common fields   snapshot JSONB             event_type
raw_metadata JSONB created_at                 event_datetime
current_version_id superseded_at             event_detail
created_at                                    agent
updated_at                                    tool_name
                                              tool_version
                                              model_name
                                              model_version
                                              config JSONB
                                              outcome
                                              confidence
```

- Every connector write creates one row in `records` (upsert) and one in
  `record_versions` (insert only, never update).
- Every machine-produced field update (OCR, entity linking, dedup) creates one row in
  `provenance_events` linked to the new version.
- The `raw_metadata JSONB` column in `records` stores the full source response before
  any normalisation, so nothing is ever lost in mapping.
- Confidence values live in `provenance_events.confidence`, not in the `records` table;
  the records table holds only the current best value for each field.
