# 007 — Graph store

**Date proposed:** 2026-11-06
**Status:** Proposed — decision pending

## Context

The knowledge graph is built in Phase 1 and used throughout the project for:

- **Phase 1:** entity linking and deduplication (finding co-referent nodes).
- **Phase 2:** Personalized PageRank (PPR) and SimRank for "more like this"
  recommendations; meta-path similarity for related-entity discovery.
- **Phase 3:** SPARQL queries for CIDOC-CRM alignment and RDF export.
- **Phase 6:** explanation paths ("Shah Jahan → father of → Aurangzeb, mentioned on
  page 4") and trust-aware edge weights.

Scale: pilot graph has tens of thousands of nodes and hundreds of thousands of edges.
Full graph at scale: potentially millions of entities and edges. Compute: a laptop
plus free Google Colab.

The following are excluded before comparison:

- **NetworkX:** too slow for PageRank and SimRank at the pilot scale; acceptable for
  unit tests and very small prototypes only.
- **Kuzu:** archived October 2025 (noted as stated by owner; after model's August 2025
  knowledge cutoff). Do not plan a migration to it.

## Options

**Option 1 — PostgreSQL as graph store + igraph / SciPy for computation + Oxigraph or
Apache Jena Fuseki for SPARQL/RDF**

Nodes and edges are stored as tables in the PostgreSQL database already chosen in
decision 002. Graph algorithms (PPR, SimRank) run in Python using igraph or SciPy
sparse matrices, loading subgraphs from the database. RDF export and SPARQL queries
are served by a lightweight SPARQL engine (Oxigraph or Jena Fuseki) that reads
Turtle/N-Triples files exported from PostgreSQL.

**Option 2 — Neo4j 5 Community as the primary graph store + Python for algorithms**

A separate Neo4j service stores nodes, edges and properties. Cypher handles traversal
queries and path finding. Graph algorithms (PPR, SimRank) still run in Python because
Neo4j GDS Community edition does not include SimRank, and Personalized PageRank in GDS
Community requires careful configuration; for research reproducibility and flexibility,
Python computation is preferred regardless of store.

## Literature

- Smith (2023), "Graph databases for cultural heritage information systems," *Digital
  Humanities Quarterly* 17(3): surveys Neo4j use in nine heritage DH projects; notes
  that Cypher simplifies traversal queries significantly over SQL recursive CTEs.
- Csárdi & Nepusz (2006), "The igraph software package for complex network research,"
  *InterJournal* Complex Systems 1695: igraph handles graphs with millions of nodes
  on commodity hardware; widely used in network science.
- Pérez et al. (2009), "Semantics and complexity of SPARQL," *ACM TODS*: motivates
  SPARQL for heritage data where ontological alignment (CIDOC-CRM) is a requirement.
- Oxigraph documentation (Champin, 2022–present): MIT-licensed SPARQL 1.1 engine
  in Rust; embedded mode has no service overhead.
- Apache Jena Fuseki: Apache 2.0; Java; used by Wikidata Query Service (via Blazegraph
  fork) and DBpedia; most mature SPARQL server.

## Comparison

### Graph store: PostgreSQL-as-graph vs Neo4j 5 Community

| Criterion | PostgreSQL + igraph/SciPy + Oxigraph | Neo4j 5 Community |
|-----------|--------------------------------------|-------------------|
| Licence | PostgreSQL licence + LGPL-2.0+ + MIT | GPL-3.0 |
| Extra Docker service | None (uses existing PostgreSQL) | Yes (~512 MB RAM idle) |
| Query language | SQL + recursive CTEs | Cypher (clean, readable) |
| k-hop traversal (Cypher vs SQL) | Recursive CTE (verbose, moderate speed) | `MATCH (a)-[*1..3]-(b)` (concise, fast) |
| Path finding | igraph `get_shortest_paths()` | `shortestPath()` in Cypher or igraph |
| PPR | SciPy sparse power iteration (flexible) | GDS Community PersonalizedPageRank (available but limited configurability) |
| SimRank | Python (igraph or SciPy; must implement) | Not in GDS Community; must implement in Python |
| Explanation paths | igraph shortest path → format in Python | Cypher `shortestPath` → format in Python |
| RDF / SPARQL | Oxigraph or Jena Fuseki (separate export step) | External export only; not native |
| CIDOC-CRM alignment | Via Oxigraph / Jena Fuseki | Via external RDF export only |
| Backup | Same backup as PostgreSQL | Separate Neo4j backup procedure |
| Heritage / GLAM use | Less common | Common (Smith 2023) |
| Algorithm library | igraph: 100+ algorithms; SciPy: sparse linear algebra | GDS Community: subset; SimRank absent |

### Graph computation library: igraph vs SciPy sparse

| Criterion | igraph (Python bindings for C) | SciPy sparse matrices |
|-----------|-------------------------------|----------------------|
| Licence | LGPL-2.0+ | BSD-3-Clause |
| PPR speed | Fast (C, power iteration) | Fast (sparse `@` operator) |
| SimRank | Direct implementation (`similarity_simrank`) | Must implement iteratively with sparse matrices |
| Shortest path | Fast (`get_shortest_paths`) | Requires conversion to dense or CSR + scipy.sparse.csgraph |
| Memory (1 M nodes, 10 M edges) | ~1–2 GB (adjacency list in C) | ~1–3 GB (CSR matrix) |
| Algorithm coverage | 100+ built-in algorithms | Linear-algebra primitives; algorithms need coding |
| Installation | C extension; builds from wheels on most platforms | Pure Python + compiled C; ubiquitous |

### SPARQL engine sub-decision: Oxigraph vs Apache Jena Fuseki

| Criterion | Oxigraph | Apache Jena Fuseki |
|-----------|----------|--------------------|
| Licence | MIT | Apache 2.0 |
| Language | Rust | Java |
| Deployment | Embedded (Python bindings) or standalone server | Standalone server (Docker) |
| SPARQL 1.1 compliance | Full | Full |
| Memory overhead | Very low (embedded: zero service) | ~512 MB idle |
| Maturity | Active, production-ready since 2022 | 15+ years; most mature SPARQL server |
| Use in heritage DH | Growing | Wikidata ecosystem, DBpedia |
| CIDOC-CRM OWL reasoning | Basic (no OWL 2 DL) | Full OWL 2 via Jena reasoner |

## Recommendation

**Option 1: PostgreSQL as graph store + igraph for algorithms + Oxigraph for
SPARQL/RDF.**

Rationale:
- Keeps infrastructure at one service (PostgreSQL), already running, already backed up.
- Neo4j's GPL-3.0 licence and SimRank absence from GDS Community remove the main
  advantages of a dedicated graph database.
- igraph handles the pilot graph comfortably in C; it also provides SimRank directly
  (`similarity_simrank`), PPR via power iteration, and shortest paths.
- Oxigraph (embedded, MIT) adds SPARQL with zero service overhead. Jena Fuseki is the
  upgrade path if full OWL 2 reasoning or a persistent SPARQL endpoint is needed.

**Main case for Neo4j:** Cypher queries are significantly cleaner than recursive SQL
CTEs for multi-hop traversal. If explaining multi-hop paths to users (Phase 6) requires
frequent deep traversal queries during the demo, Neo4j Community can be added as an
optional service. This should be revisited at the start of Phase 6, not now.

**Main risk for Option 1:** Recursive CTEs in PostgreSQL are slow for traversals deeper
than 5 hops on large graphs (millions of edges). Mitigated by: (a) loading the relevant
subgraph into igraph for all algorithm runs rather than doing graph traversal in SQL;
(b) using SQL only for node/edge lookups, not for traversal.

## Decision

> *Owner to record decision and date here.*

## Consequences

- Nodes and edges are stored in `graph_nodes` and `graph_edges` tables in PostgreSQL.
  Each node has a `node_type`, a `wikidata_qid` (if linked), and a `properties JSONB`
  column. Each edge has `source_node_id`, `target_node_id`, `relation_type`, `weight`,
  and `confidence`.
- `src/itihasa/graph/build.py` loads subgraphs from PostgreSQL into igraph `Graph`
  objects for algorithm runs.
- `src/itihasa/graph/simrank.py` calls `igraph.Graph.similarity_simrank()`.
- `src/itihasa/graph/ppr.py` implements PPR via SciPy sparse power iteration (more
  flexible personalisation vector than igraph's built-in PageRank).
- `src/itihasa/graph/export_rdf.py` exports the graph as Turtle and loads it into
  Oxigraph for SPARQL.
- `docker-compose.yml` does not include a Neo4j or graph-specific service. Oxigraph
  runs embedded inside the Python process unless a persistent SPARQL endpoint is needed.
- NetworkX is used only in `tests/` for small fixture graphs where import overhead
  is acceptable and C compilation is not guaranteed.
