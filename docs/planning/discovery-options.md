# Discovery, ranking and explanation options for Phase 2 evaluation

**Date:** 2026-11-06
**Status:** Candidate options. To be evaluated on Itihasa-Bench (Phase 2) using human
relevance judgements. No implementation decision is made in this document.

---

## Critical constraint: no user-click history

Itihasa has no user-click history, purchase logs or rating data. Recommender systems
that learn from user–item interactions — KGAT, KGIN, LightGCN, NGCF, and similar
graph-neural-network recommenders — require an interaction matrix as their primary
signal. In a new-item cold-start evaluation (arXiv 2403.14377), KGAT and CKE scored
approximately 0 recall while plain Personalized PageRank scored 0.23 recall. These
systems will not be evaluated unless Itihasa later collects real usage logs.

This constraint rules out interaction-learning GNNs. It does not rule out graph neural
networks that learn from the knowledge graph structure alone (e.g. CompGCN, which
encodes relation types without user interactions).

---

## 1. Graph similarity ("more like this", related entities)

### 1.1 Personalized PageRank (PPR)

Random walk with restarts from a seed entity or query. Directly interpretable: the
restart probability anchors the walk to the query. Training-free.

- Implementation: SciPy sparse power iteration (more flexible personalisation vector
  than igraph's built-in PageRank; see decision 007).
- Scale: feasible for millions of edges on a laptop with sparse matrices.
- Reference: cold-start benchmark (arXiv 2403.14377): PPR recall@20 = 0.23 vs ~0
  for interaction-learning baselines.
- Explainability: the walk path from seed to result is the explanation.

### 1.2 SimRank

Structural similarity: two nodes are similar if their neighbours are similar.
Iterable computation; converges in 5–20 rounds in practice.

- Implementation: `igraph.Graph.similarity_simrank()` (C, fast).
- Scale: naive SimRank is O(n²); igraph's implementation uses sparse matrices and
  is feasible for graphs up to ~100,000 nodes.
- Reference: HeritageRec (Rani et al., IEEE ICICACS 2026) used SimRank; this is
  a direct port candidate (one file per commit, with co-author agreement).
- Explainability: shared-neighbour paths are the explanation.

### 1.3 Meta-path similarity (PathSim)

Similarity along semantically meaningful paths defined by domain experts
(e.g. site–dynasty–site, manuscript–language–manuscript, ruler–period–ruler).

- Implementation: Python + igraph or NetworkX (small graphs only); paths defined
  in `configs/graph.yaml`.
- Scale: scales with the number of defined meta-paths; each path is a matrix
  multiplication on the adjacency matrices for each relation type.
- Reference: Sun et al. (2011), "PathSim: Meta path-based top-K similarity search
  in heterogeneous information networks," *PVLDB* 4(11).
- Explainability: each score is directly tied to a named path type.
- Domain cost: good meta-paths require domain knowledge; must be agreed with a
  historian before Phase 2.

### 1.4 Knowledge graph embeddings (RotatE via PyKEEN)

Learned embeddings for entities and relations; ANN search over the embedding space
finds related entities. Training-free at query time (embeddings are pre-trained).

The user-interaction constraint does not apply here: RotatE learns from the KG's
triple structure (head, relation, tail), not from user logs.

- Implementation: PyKEEN (MIT, TU Munich / Fraunhofer IAIS). Train on the graph triples;
  index entity embeddings in pgvector or FAISS.
- **TransE** (Bordes et al. 2013): simpler baseline; assumes relations as translations.
  Fast to train; weaker on symmetric and 1-to-N relations.
- **RotatE** (Sun et al. 2019, arXiv 1902.10197): models each relation as a rotation
  in complex space; handles symmetric, antisymmetric, inverse and composition patterns
  correctly. Recommended over TransE for a heritage KG with diverse relation types.
- **CompGCN** (Vashishth et al. 2020, ICLR): encodes graph structure via graph
  neural network convolutions over the KG (no user interactions). More expressive than
  RotatE but heavier to train; feasible on Colab.
- Reference: Kutt et al. 2026 (arXiv 2602.19711), KG embeddings + HNSW + SPARQL
  filters for a heritage KG, evaluated on expert judgements. Directly comparable to
  our experimental setup.
- Explainability: embedding distance gives a score but no symbolic path; must be
  combined with meta-path templates for user-facing explanations.

**PyKEEN licence:** MIT. GitHub: pykeen/pykeen.
**RotatE approximate model size:** entity embedding matrix is `n_entities × embedding_dim`
floats; at 500,000 entities and dim=256, this is ~500 MB. Feasible on a laptop.

---

## 2. Graph computation library

For PPR and SimRank at pilot scale (Phase 2):

| Library | Licence | PPR | SimRank | Memory (pilot) | Notes |
|---------|---------|-----|---------|----------------|-------|
| igraph | LGPL-2.0+ | Fast (C) | Built-in (`similarity_simrank`) | ~hundreds of MB | Recommended for Phase 2 |
| SciPy sparse | BSD-3-Clause | Fast (sparse `@`) | Manual implementation | ~hundreds of MB | Preferred for PPR (flexible personalisation vector); complement to igraph |

Both libraries are used: igraph for SimRank and shortest paths; SciPy sparse for PPR
(the personalisation vector is more naturally expressed as a sparse vector in SciPy).

---

## 3. Lexical retrieval

### 3.1 BM25

Standard probabilistic term-weighting model. Research baseline using **Pyserini**
(Apache 2.0, University of Waterloo); tuned k1 and b values reported alongside results.

### 3.2 BM25 + RM3

BM25 with Relevance Model 3 pseudo-relevance feedback. Expands the query with terms
from the top-k retrieved documents. Research baseline using **Pyserini** (Lucene
implementation; exact same code as Anserini, cited in dozens of TREC and BEIR papers).
bm25s does not implement RM3.

**Indic tokenisation for both:** Pyserini/Anserini uses Lucene ICU analysis (same
ICU4J library as OpenSearch). Unicode NFC normalization is applied; script-level
word-breaking covers all major Indic scripts. Morphological analysis is not applied
in Phase 2; treated as a future improvement.

---

## 4. Dense retrieval

All models below are tested with pgvector HNSW for the application index and FAISS
for research experiment reproductions.

### 4.1 BGE-M3

**Model:** `BAAI/bge-m3`
**Licence:** MIT (verified on HuggingFace model card as of August 2025)
**Parameters:** 568 M
**Embedding dim:** 1024 (dense); sparse and multi-vector outputs also available
**Languages:** 100+, including Hindi, Bengali, Tamil, Telugu, Gujarati, Marathi,
Kannada, Malayalam, Odia, Punjabi, Sanskrit (reported by BAAI)
**Key property:** single model produces dense, sparse (learned BM25-style), and
multi-vector (ColBERT-style) outputs. Avoids maintaining multiple models.
**Reference:** IndicRAGSuite benchmark (arXiv 2506.01615; after model knowledge cutoff;
cited as stated by owner): BGE-M3 is best on 8 of 13 Indian languages tested.
**Recommended primary model for Phase 2.**

### 4.2 multilingual-e5-large-instruct

**Model:** `intfloat/multilingual-e5-large-instruct`
**Licence:** MIT (verified on HuggingFace model card as of August 2025)
**Parameters:** 560 M
**Embedding dim:** 1024
**Languages:** 100+, including major Indian languages
**Key property:** instruction-following embedding model; query and passage are prefixed
with task instructions, which improves zero-shot retrieval on domain-shifted datasets.
**Reference:** IndicRAGSuite (arXiv 2506.01615; cited as stated by owner): best on
Hindi in the benchmark.
**Comparison model for Phase 2.**

### 4.3 L3Cube-IndicSBERT

**Model:** `l3cube-pune/indic-sentence-similarity-sbert`
**Licence:** CC-BY-4.0 (verified on model card)
**Parameters:** approximately 170 M (BERT-base architecture: 12 layers, hidden size 768,
Indic vocabulary of 197,285 tokens; derived from published config.json)
**Languages:** 11 — Hindi, Marathi, Kannada, Tamil, Telugu, Gujarati, Odia, Punjabi,
Bengali, Malayalam, English (verified on model card; paper: arXiv:2304.11434)
**Key property:** Indic-specific fine-tuning on sentence similarity across 10 Indian
languages and English; supports cross-lingual queries; smaller and faster than BGE-M3.
**Included as:** Indic-specific lightweight alternative.

### 4.4 all-MiniLM-L6-v2

**Model:** `sentence-transformers/all-MiniLM-L6-v2`
**Licence:** Apache 2.0 (verified on HuggingFace model card as of August 2025)
**Parameters:** 22.7 M
**Embedding dim:** 384
**Languages:** Primarily English; limited multilingual capability
**Key property:** Very fast, low memory; the embedding model used in HeritageRec.
**Included as:** HeritageRec baseline only. Expected to perform poorly on Indic-language
queries. Do not use as a production model.

---

## 5. Fusion

### 5.1 Reciprocal Rank Fusion (RRF)

Combines ranked lists from multiple retrieval systems using reciprocal of rank position.
No training required. Formula: `RRF(d) = Σ 1 / (k + rank_i(d))` where k=60 by convention.

- Implementation: Python, 10 lines. No dependencies beyond the ranked lists.
- Reference: Cormack et al. (2009), "Reciprocal rank fusion outperforms Condorcet and
  individual rank learning methods," *SIGIR*.

### 5.2 Learned score fusion

Linear combination of retrieval scores (BM25, dense cosine, PPR, SimRank) learned as
features inside the LambdaMART ranker. No separate fusion step; the ranker learns
optimal weights from labelled queries.

---

## 6. Learning to rank (LTR)

### 6.1 LightGBM LambdaMART (primary candidate)

**Licence:** MIT
**Key property:** Gradient boosting with LambdaMART objective (optimises NDCG directly).
Fast training, interpretable via SHAP feature importance, handles missing features.
Used in production ranking at multiple large search engines.
**Evaluation:** 5-fold cross-validation, split by query (not by document) to prevent
data leakage. With 100 queries and two relevance labels per query, this yields ~20 test
queries per fold — sufficient for significance testing but tight; confidence intervals
must be reported.

### 6.2 XGBoost (rank:ndcg objective)

**Licence:** Apache 2.0
**Key property:** Alternative gradient boosting framework; slightly different bias-variance
tradeoff than LightGBM. Used as a comparison to check whether the LambdaMART results
are framework-sensitive.

### 6.3 CatBoost (YetiRank objective)

**Licence:** Apache 2.0
**Key property:** Handles categorical features (doc_type, language, script) without
one-hot encoding. YetiRank is a listwise LTR objective.

### 6.4 allRank (neural LTR: ListNet, LambdaLoss, NeuralNDCG)

**Licence:** Apache 2.0 (Allegro)
**Key property:** Neural listwise ranking; can model complex feature interactions.
**Condition:** Only feasible if the number of labelled query–document pairs is large
enough (typically 500+ queries for neural LTR to outperform tree-based methods).
With Itihasa-Bench at ~100 queries, allRank is included as an exploratory comparison,
not a primary candidate. Report confidence intervals; do not claim neural superiority
without sufficient data.

---

## 7. Re-ranking

Re-rankers are cross-encoders that re-score a small candidate set (top 100 from first-
stage retrieval) with higher-quality but slower inference.

### 7.1 bge-reranker-v2-m3 (primary candidate)

**Model:** `BAAI/bge-reranker-v2-m3`
**Licence:** MIT (verified on HuggingFace model card as of August 2025)
**Parameters:** 568 M (same backbone as BGE-M3)
**Key property:** Shares the BGE-M3 backbone; natural pairing with BGE-M3 as first-
stage retriever. Multilingual with strong Indic-language coverage.
**Feasibility:** ~2.3 GB GPU RAM or ~6–8 GB CPU RAM for inference. Feasible on Colab.

### 7.2 Qwen3-Reranker-4B

**Model:** `Qwen/Qwen3-Reranker-4B`
**Licence:** Apache-2.0 (verified on model card)
**Parameters:** 4.02 B (36 transformer layers, Qwen3-4B-Base backbone; verified on
model card)
**Context length:** 32,768 tokens
**Languages:** 100+ including major Indian languages (verified on model card)
**Requirements:** Hugging Face Transformers ≥ 4.51.0, or vLLM ≥ 0.8.5 for batched
inference
**Key property:** Instruction-aware cross-encoder reranker; task-specific instructions
improve performance 1–5% over defaults. MTEB-R score: 69.76.
**Included as:** quality ceiling for the reranking ablation. At 4B parameters, CPU
inference is very slow (minutes per query); feasible only on a Colab A100 or T4 GPU.
Not for production use.

### 7.3 mMiniLM cross-encoder (small baseline)

**Model:** likely `cross-encoder/ms-marco-MiniLM-L-6-v2` (English) or a multilingual
MiniLM variant; owner should verify which multilingual variant is appropriate.
**Licence:** Apache 2.0 (verify on HuggingFace model card for the specific variant)
**Parameters:** ~22–66 M depending on variant
**Key property:** Very fast inference; good English baseline. Multilingual capability
limited; included to check whether a small fast model can approach larger rerankers
on primarily English queries in the benchmark.

**Excluded:** jina-reranker-v2 (CC BY-NC licence). Non-commercial licences are not
acceptable in the core system (see project brief, constraint on open licences).

---

## 8. Trust-aware ranking features (research contribution)

These features constitute Itihasa's primary research contribution to the ranking
literature. They are not available in any existing heritage retrieval baseline.

| Feature | Source | Type |
|---------|--------|------|
| OCR confidence | Tesseract / Surya confidence score per page | Float [0, 1] |
| Field extraction confidence | Pydantic validation + NER model confidence | Float [0, 1] |
| Entity-link expert-verified | Boolean flag in `provenance_events` | Boolean |
| Source reliability | Ordinal score assigned per Tier (1 > 2 > upload) | Integer 1–3 |
| BM25 score | First-stage lexical score | Float |
| Dense cosine similarity | BGE-M3 dense vector cosine | Float [0, 1] |
| SimRank score | Graph structural similarity to query entity | Float [0, 1] |
| PPR score | Personalized PageRank from query entities | Float [0, 1] |
| Horn's Index | Shared-entity count normalised by document length | Float |
| Meta-path count | Number of matching meta-paths between query and document entities | Integer |
| Temporal match | Overlap between query period and document EDTF period | Float [0, 1] |
| Spatial match | Distance between query place and document place (km, log-normalised) | Float |
| Document type match | Whether the query type tag matches `doc_type` | Boolean |
| Licence openness | Whether the document can be redistributed (`can_redistribute`) | Boolean |
| Number of verified entities | Count of entities with expert-verified links | Integer |

SHAP TreeExplainer (applied to the LightGBM model) produces per-feature importance
values per query–document pair, used for the SHAP explanation panel in Phase 6.

---

## 9. Explanations

Explanations are shown to users alongside ranked results. They are always symbolic;
no free-form LLM-generated text is used in the core system.

### 9.1 Meta-path sentence templates

A named meta-path maps to a template sentence:
- `site–dynasty–site`: "Both {A} and {B} are associated with the {dynasty} dynasty."
- `manuscript–language–manuscript`: "Both {A} and {B} are written in {language}."
- `ruler–period–document`: "This document mentions {ruler}, who ruled during the
  same period as your query."

Templates are defined in `configs/explanations.yaml` by the domain expert, not
generated automatically.

### 9.2 Evidence pointer

For each linking entity between a retrieved document and the query, the page number
and line number where that entity appears in the document text are recorded in the
`provenance_events` table. The UI shows: "Shah Jahan mentioned on page 4, line 12."

### 9.3 Trust badge

Three levels displayed in the UI:
- Expert-verified: at least one domain expert has confirmed the key entity links.
- Machine-read (high confidence): OCR and extraction confidence above a threshold
  (threshold value is a configuration parameter, not hardcoded).
- Machine-read (uncertain): confidence below threshold; user is advised to verify.

### 9.4 SHAP explanation (Phase 6 panel)

A bar chart showing which features increased or decreased the document's rank relative
to the median score. Generated by `shap.TreeExplainer` on the LightGBM model.

**Fidelity check:** for each explanation shown, verify that removing the explained
feature or path from the ranking model reduces the document's score. Fidelity is
computed as the fraction of explanations where this holds. Report alongside the user
study results.

**Reference:** Frej et al. 2024 (arXiv 2406.07420), graph reasoning paths for
explainable cold-start recommendation. Used as the methodological reference for
path-based explanation generation and fidelity evaluation.

---

## 10. Phase 2 experiment plan

The following systems are run on Itihasa-Bench (~100 queries, pooled human judgements
from two annotators, weighted kappa reported). Every run is logged with the git commit
hash, Pyserini version, model name and version, and configuration file path.

| System | Type | Key components |
|--------|------|----------------|
| BM25 | Lexical | Pyserini, Lucene ICU analysis |
| BM25 + RM3 | Lexical + PRF | Pyserini |
| BGE-M3 dense | Dense | BAAI/bge-m3, pgvector HNSW |
| multilingual-e5-large-instruct | Dense | intfloat/multilingual-e5-large-instruct, pgvector HNSW |
| PPR | Graph | SciPy sparse power iteration from query entities |
| SimRank | Graph | igraph `similarity_simrank` |
| RotatE (PyKEEN) | KG embedding | RotatE, pgvector ANN |
| RRF (all above) | Fusion | Reciprocal rank fusion over all 7 systems |
| LambdaMART (all features) | LTR | LightGBM, all features in section 8 |
| LambdaMART + bge-reranker-v2-m3 | LTR + reranker | LambdaMART top 100, then reranker |

**Metrics:** NDCG@10 (primary), P@5, MAP, Recall@100.
**Significance:** paired two-sided t-test against the best single method;
Bonferroni correction for multiple comparisons; 95% confidence intervals reported.
**Number of queries:** stated explicitly in every reported table.
**Folds:** 5-fold cross-validation, split by query ID (not by document).

**Comparison model for the paper:** IndicRAGSuite (arXiv 2506.01615) reports results
on retrieval over Indian-language content; Itihasa-Bench covers heritage documents
specifically (manuscripts, objects, archival records), so direct numeric comparison
is not valid. Use IndicRAGSuite as a reference for model selection, not as a competing
result.
