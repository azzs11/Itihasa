# 008 — Vector index

**Date proposed:** 2026-11-06
**Status:** Proposed — decision pending

## Context

Dense retrieval in Phase 2 requires indexing high-dimensional embedding vectors and
performing approximate nearest-neighbour (ANN) search at query time. The primary
embedding model is BGE-M3 (see `docs/planning/discovery-options.md`), which produces
three outputs per document:

- **Dense vector:** 1024-dimensional float32 (used for dense retrieval).
- **Sparse vector:** SPLADE-style lexical weights (used for sparse retrieval,
  comparable to learned BM25).
- **Multi-vector (ColBERT-style):** one vector per token, scored with MaxSim.

Decisions 005–007 have fixed the services running on the laptop to PostgreSQL and
OpenSearch (and optionally Oxigraph). Any vector index option that adds another
service must justify that overhead.

Pilot scale: up to ~100,000 documents (generous upper bound for Phase 2).
Full scale: up to ~1,000,000 documents.

## Options

| Option | Licence | Integration | Notes |
|--------|---------|-------------|-------|
| **pgvector** | MIT | PostgreSQL extension (no new service) | HNSW and IVFFlat indexes; SQL-native filtering; direct join with records table |
| **FAISS** | MIT | Python library (no service) | Research-grade ANN; CPU and GPU; many index types; index files managed separately |
| **OpenSearch k-NN** | Apache 2.0 | Built into OpenSearch (no new service) | HNSW via FAISS or nmslib engine; native hybrid BM25 + dense query; Lucene k-NN option also available |

## Literature

- Johnson et al. (2017), "Billion-scale similarity search with GPUs," *IEEE
  Transactions on Big Data*: original FAISS paper. FAISS is the standard research
  tool for ANN index quality comparisons.
- pgvector GitHub (ankane/pgvector, 2021–present): MIT, 14,000+ stars; widely adopted
  in production systems since HNSW support was added in 0.5.0 (2023).
- Santhanam et al. (2022), "ColBERTv2: Effective and efficient retrieval via lightweight
  late interaction," *NAACL*: motivates multi-vector retrieval. OpenSearch does not
  natively support MaxSim; both pgvector and FAISS require application-level
  implementation.
- Xiong et al. (2021), "Approximate nearest neighbor negative contrastive estimation
  for dense text retrieval," *ICLR*: standard reference for ANN in dense retrieval
  pipelines.

## Comparison

| Criterion | pgvector | FAISS | OpenSearch k-NN |
|-----------|----------|-------|-----------------|
| Licence | MIT | MIT | Apache 2.0 |
| New Docker service | No | No | No (uses existing OpenSearch) |
| Index type | HNSW, IVFFlat | IVF, HNSW, IVFPQ, PQ, ... | HNSW (faiss / nmslib / Lucene engines) |
| SQL / query language | Native SQL `<=>` cosine | Python API | OpenSearch DSL |
| Pre-filter with metadata | SQL WHERE (exact, before ANN) | Manual (requires FAISS `IDMap` + post-filter) | Native OpenSearch filters (approximate) |
| Hybrid BM25 + dense | Application-level fusion | Application-level fusion | Native hybrid query in one request |
| Dense vector (1024-dim) | Yes | Yes | Yes |
| Sparse vector storage | As PostgreSQL array column; queried manually | Separate inverted index (manual) | Neural sparse search (OpenSearch 2.9+) |
| Multi-vector (ColBERT) | Manual: store token vectors as JSONB array | Manual: MaxSim in Python | Not natively supported |
| Persistence | PostgreSQL-managed | Manual index file serialisation | OpenSearch-managed |
| Backup | Same as PostgreSQL | Manual (`faiss.write_index`) | Same as OpenSearch |
| Scale (100 K, 1024-dim) | Excellent (HNSW) | Excellent | Good |
| Scale (1 M, 1024-dim) | Good with tuning (HNSW m=16, ef_construction=64) | Excellent (IVFPQ for memory) | Good |
| RAM for HNSW (100 K, 1024-dim) | ~400 MB (HNSW graph + vectors) | ~400 MB | ~400 MB |
| Research / paper comparability | Good | Highest (standard in IR papers) | Moderate |

## Recommendation

**pgvector for the application vector index (Phases 2–7). FAISS for offline
research experiments and ANN quality comparisons.**

**pgvector** eliminates a third service: PostgreSQL is already running, already backed
up, and pgvector indexes live inside it. At Phase 2 scale (up to 100,000 documents),
HNSW in pgvector gives recall@10 of 0.95+ and latency under 20 ms on a modern laptop.
Filtering by metadata (period, region, language, licence) uses SQL WHERE clauses that
run before or inside the HNSW scan, which is more precise than post-filtering in FAISS.

**FAISS** is the right tool for research experiments where ANN index quality is itself
under study: comparing HNSW vs IVFPQ recall-latency tradeoffs, or producing numbers
comparable with BEIR baselines. FAISS is a library, not a service, and can be used in
Pyserini (which builds FAISS indexes for dense retrieval experiments).

**OpenSearch k-NN** is a valid alternative if the architecture requires hybrid BM25 +
dense queries to be served from a single request to one service (OpenSearch), without
application-level fusion. It is the runner-up. Revisit at Phase 6 if the hybrid query
path becomes a performance bottleneck.

**On BGE-M3's sparse and multi-vector outputs:**
- Sparse vectors: best indexed in OpenSearch via its neural sparse search feature;
  alternatively stored as PostgreSQL `real[]` and searched with a custom SQL dot-product
  query (slower but feasible at pilot scale).
- Multi-vector (MaxSim): no service natively supports this; it requires fetching
  candidate token-level vectors and computing MaxSim in Python. This is a Phase 2
  research experiment, not a production feature.

**Main risk:** At very large scale (1 M+ vectors, 1024 dimensions), pgvector HNSW
requires ~4 GB RAM for the index structure alone. At that point, IVFPQ in FAISS is
more memory-efficient. Mitigated by planning an IVFPQ fallback in `src/itihasa/retrieve/dense.py`.

## Decision

> *Owner to record decision and date here.*

## Consequences

- `pgvector` is added as a PostgreSQL extension in `docker-compose.yml`
  (via `pgvector/pgvector` Docker image or as an extension install in the
  standard PostgreSQL image).
- `src/itihasa/retrieve/dense.py` manages the pgvector HNSW index; it also exposes
  a `faiss_index()` function for research experiments that writes a `.faiss` file
  to `results/`.
- Dense embeddings (1024-dim float32) are stored in a `record_embeddings` table with
  columns `(record_id FK, model_name, model_version, vector vector(1024))`.
- Sparse and multi-vector outputs from BGE-M3 are stored as JSONB columns in the
  same table for Phase 2 experiments; production indexing of sparse vectors will be
  revisited after Phase 2 evaluation results are known.
- The pgvector index type (HNSW vs IVFFlat) and parameters (`m`, `ef_construction`)
  are configuration values in `configs/dense.yaml`, not hardcoded.
