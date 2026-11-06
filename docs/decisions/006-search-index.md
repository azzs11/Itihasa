# 006 — Search index

**Date proposed:** 2026-11-06
**Status:** Accepted — 2026-11-06

## Context

Search serves two roles that must be kept strictly separate to produce reproducible
research numbers:

**Role A — Application search:** the live query interface (ranked results, facets,
autocomplete, hybrid BM25 + dense retrieval). Users submit queries; the app returns
ranked documents.

**Role B — Research experiments:** baselines for Itihasa-Bench (Phase 2). Numbers
published in papers must come from a standard IR toolkit that other researchers can
reproduce without running Itihasa's application stack. BM25+RM3 and NDCG@10 figures
computed inside OpenSearch are not directly comparable with published TREC/BEIR results.

Conflating the two roles risks publishing numbers that cannot be reproduced from a
clean environment.

**OpenSearch version:** OpenSearch 3.9.0 is the current stable release (released
29 September 2026). OpenSearch 3.10.0 is scheduled for 3–17 November 2026. Pin the
newest 3.x patch release listed on opensearch.org at the time of setup. OpenSearch
is introduced in Phase 2, not Phase 0; it is not in the Phase 0 Docker Compose file.

## Options

### Role A — Application search

| Option | Licence | Notes |
|--------|---------|-------|
| **OpenSearch** (current stable) | Apache 2.0 | Fork of Elasticsearch 7.10; Elasticsearch-compatible API; LTR plugin; ICU analysis plugin for Indic scripts; native k-NN (HNSW via FAISS/nmslib engines) |
| Elasticsearch 8 | SSPL | SSPL restricts redistribution of scripts that call it; not suitable for an open-source research system |
| Apache Solr 9 | Apache 2.0 | 20+ years' maturity; Blacklight and VuFind (library discovery systems) are built on Solr; native LTR plugin; ICU tokeniser; credible alternative |

Elasticsearch 8 is excluded on licence grounds. The choice is between OpenSearch and Solr.

### Role B — Research experiments

| Option | Licence | Notes |
|--------|---------|-------|
| **Pyserini** | Apache 2.0 | Built on Anserini / Lucene; BM25, BM25+RM3, uniCOIL, SPLADE, dense retrieval via Tevatron; TREC-compatible output; used in BEIR, MS MARCO, TREC papers; requires JVM |
| **bm25s** | MIT | Pure-Python BM25; NumPy/SciPy sparse matrices; no Java; no RM3; good for rapid prototyping and JVM-free environments |

## Literature

- Thakur et al. (2021), "BEIR: A heterogeneous benchmark for zero-shot evaluation
  of information retrieval models" (NeurIPS): uses Pyserini for BM25 baseline.
  Results are reproduced by dozens of subsequent papers using the same toolkit.
- Lin et al. (2021), "Pyserini: A Python interface to the Anserini IR toolkit for
  replicable research", *SIGIR*. This is the standard citation for research baselines.
- Veyseh et al. (2024, bm25s): "BM25S: Orders of magnitude faster lexical search
  via eager sparse scores", arXiv 2407.03618. Establishes bm25s as a fast BM25
  alternative without Java.
- Library discovery systems: Blacklight (used by Yale, Stanford, Chicago) and
  VuFind (used by hundreds of institutions) are built on Solr 9, demonstrating
  Solr's fitness for heritage search.

## Comparison

### Role A — application search

| Criterion | OpenSearch (current stable) | Apache Solr 9 |
|-----------|---------------------------|---------------|
| Licence | Apache 2.0 | Apache 2.0 |
| BM25 | Yes | Yes |
| BM25+RM3 | Via Elasticsearch-LTR plugin | Native Solr plugin |
| Learning to rank | OpenSearch LTR plugin (RankLib / XGBoost) | Native Solr LTR (RankLib) |
| Indic tokenisation | ICU analysis plugin (all Indic scripts) | ICU tokeniser (all Indic scripts) |
| Dense / hybrid retrieval | Native k-NN (HNSW, FAISS engine) | Experimental (Solr 9.x kNN) |
| Heritage / GLAM use | Growing | Very high (Blacklight, VuFind) |
| Elasticsearch API compat. | Yes (drop-in) | No |
| Docker image | Official (verify current tag) | Official |
| Community size | Large | Very large |

### Role B — research toolkit

| Criterion | Pyserini | bm25s |
|-----------|----------|-------|
| Licence | Apache 2.0 | MIT |
| BM25 | Yes | Yes |
| BM25+RM3 | Yes | No |
| Dense retrieval | Yes (via Tevatron, Faiss) | No |
| TREC output | Yes | Partial |
| Java dependency | Yes (JVM required) | No |
| Indic tokenisation | Lucene ICU (via Anserini) | Unicode whitespace only |
| Paper comparability | High (BEIR, TREC standard) | Low (newer, rarely cited) |
| Use on Colab (no JVM) | Requires setup | Works out of the box |

## Indic tokenisation detail

Both OpenSearch ICU and Pyserini/Anserini ICU analysis use the ICU4J library, which
handles Unicode normalization (NFC), script detection, and word breaking for all Indic
scripts (Devanagari, Bengali, Tamil, Telugu, Kannada, Malayalam, Gujarati, Odia, Gurmukhi,
and others). This is sufficient for retrieval in Phase 1–2.

Deeper morphological analysis (compound splitting for Sanskrit, verbal morphology for
Tamil and Malayalam, transliteration variant normalisation) is a Phase 4+ research
question and requires domain-specific tools beyond ICU. Those tools are out of scope
for the search-index decision.

## Recommendation

**Role A:** OpenSearch at the current stable version (verify at opensearch.org before
pinning). ICU analysis plugin enabled from day one for all Indic script fields.

**Role B:** Pyserini as the primary research toolkit for all published baselines. Its
Lucene foundation and TREC-compatible output ensure that BM25 and BM25+RM3 numbers
are directly comparable with published BEIR and TREC results. bm25s is a secondary
option for quick experiments in environments where the JVM is unavailable (e.g. some
Colab configurations).

**Main risk:** Pyserini requires a JVM; if the Colab environment has JVM version
conflicts, BM25-only experiments fall back to bm25s and RM3 experiments require a
local machine. Document this constraint explicitly when reporting evaluation numbers.

## Decision

> **Decision:** OpenSearch 3.x — pin the newest 3.x patch release listed on
> opensearch.org at the time it is added (3.9.0 is the current stable release,
> released 29 September 2026; 3.10.0 is scheduled for 3–17 November 2026).
> OpenSearch is introduced in Phase 2, not Phase 0; it is not in the Phase 0
> Docker Compose file. Research experiments: Pyserini as the primary toolkit;
> bm25s as the fallback for JVM-free environments.
>
> **Date decided:** 2026-11-06

## Consequences

- `docker-compose.yml` runs OpenSearch at the pinned stable version with the ICU
  analysis plugin and the LTR plugin installed.
- `src/itihasa/retrieve/opensearch.py` handles application search queries.
- `src/itihasa/retrieve/bm25.py` and `src/itihasa/retrieve/dense.py` are thin
  wrappers around Pyserini for research experiments; they write TREC-format run files
  to `results/`.
- Every evaluation run records the Pyserini version, Anserini index commit hash,
  and query file in the results folder alongside the NDCG/MAP numbers.
- OpenSearch query results and Pyserini results are never mixed in the same reported
  number; the source is always stated explicitly.
