# 009 — Data scope and collection stages

**Date decided:** 2026-11-06
**Status:** Accepted

## Context

Before writing any connector, the team needed to agree on what data to collect,
in what order, and how to know when enough has been collected. Without this, there
is a risk of building connectors for sources that add little to the graph, or
collecting data that cannot be released alongside the benchmark.

A second question was geographic scope. Itihasa covers all of India, but building
and evaluating the whole corpus in one pass is impractical for a thesis. A pilot
slice was needed that is small enough to finish quickly but representative enough
to validate the full pipeline.

## Decision

**Pilot region:** Karnataka. Karnataka is a filter, not a separate system.
All code must be region-agnostic (filter by region/language tag, not by hard-coded
place names). Expanding to all of India means loosening the filter and re-running,
not rewriting.

**Three collection stages:**

| Stage | Target records | Key work |
|-------|---------------|----------|
| Start | 2,000–5,000 Karnataka records from 5–6 sources | Clean into Record schema, store with provenance, link to Wikidata entities, build first graph, measure richness |
| Intermediate | ~20,000–50,000 | Fill gaps shown by richness numbers, deduplicate entities across sources, OCR a small manuscript set with confidence scores, build evaluation set (50–100 queries, 2–3 judges, agreement measured), write docs/data-card.md |
| Advanced | All-India | Expand filter, add Tier 2 sources after permission, open Contribute feature, full preservation (BagIt, fixity, 3-2-1 backups), publish dataset and benchmark on Zenodo |

**Pilot sources (Start stage only):**

| Source | Licence | Notes |
|--------|---------|-------|
| Wikidata | CC0 1.0 | SPARQL endpoint |
| Wikipedia (English + Kannada) | CC BY-SA 4.0 | MediaWiki API |
| Wikimedia Commons | Mixed (CC BY-SA, CC0, PD) | MediaWiki API |
| Internet Archive | Mixed (per item) | S3-like API or search API |
| SIDDHAM | Varies (check per Zenodo record) | Inscription corpus. For each Zenodo record, fetch the licence from `metadata.license.id` in the Zenodo API response. Ingest only records with a recognised open licence (store it on the record). Records with a missing, restricted, or unrecognised licence are not ingested; write them to `logs/siddham_skipped.jsonl` with the reason, for owner review. |
| Pandit | CC BY-NC-SA 4.0 | Sanskrit text repository |

**Later sources** — added only when a richness metric shows a gap, not before:
Getty AAT / TGN / ULAN (ODC-By 1.0); Digital Corpus of Sanskrit (CC BY 4.0);
GRETIL (CC BY-NC-SA 4.0); SARIT (licence varies per text); Wellcome Collection
(CC BY 4.0 or PDM per item); OpenStreetMap (ODbL); existing Tier 1 museum and
scholarly sources; ASI monuments via Wikidata (ASI monument IDs), not a separate
permission request.

**Richness metrics** — computed after every collection run, results saved to `results/`:
- % of records linked to 2 or more entities
- average entity degree
- share of records in the largest connected component
- number of cross-source links (same entity in 2+ sources)
- number of relation types
- language distribution
- licence distribution

**Connector rules:**
- One Python module per source under `src/itihasa/collect/`.
- Raw downloads are saved untouched before any cleaning step.
- Licence is stored on every record. NonCommercial and ShareAlike data must be
  filterable so released datasets can include or exclude it.
- Before writing each connector, check the source's current API, rate limits and
  terms of use and confirm findings with the owner.

## Consequences

- The first graph will cover Karnataka heritage only; richness metrics will
  determine which sources to add next.
- The evaluation set (Itihasa-Bench) will be built from this pilot slice.
- NC and SA licences (Pandit, SIDDHAM where applicable, Wikipedia/Commons) are
  stored with a flag; released datasets will offer a CC-only subset and a full
  subset under their respective terms.
- Each new source requires a check of current API terms before a connector is
  written, even for Tier 1 sources whose terms can change.
- Expanding to all-India is a configuration change, not a code change.
