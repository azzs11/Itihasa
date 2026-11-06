# 005 — Object storage

**Date proposed:** 2026-11-06
**Status:** Accepted — 2026-11-06

## Context

Raw source files (SPARQL responses, Wikipedia HTML, Internet Archive scans, uploaded
manuscripts), BagIt packages, OCR outputs, and versioned corpus snapshots need durable
byte-level storage separate from the relational record store. The object storage is
accessed through a single `StorageBackend` interface so the implementation can be
swapped without changing any other module.

**MinIO is not a viable option.** The community edition stopped publishing binaries
and Docker images in October 2025 and the repository was archived as no longer maintained
in February 2026 (noted as stated by owner; both dates are after the model's August 2025
knowledge cutoff and cannot be independently verified here).

Pilot scale: 2,000–5,000 documents plus cached source responses; full scale:
potentially millions of objects. Compute: a single laptop, no cluster.

## Options

| Option | Licence | Notes |
|--------|---------|-------|
| **Local filesystem + BagIt (RFC 8493)** | RFC (CC) + bagit-python CC0 | Hierarchical directory layout; BagIt manifests record SHA-256 fixity for every file; no service needed |
| **SeaweedFS** | Apache 2.0 | Distributed object store with S3-compatible API; master-volume architecture; single-binary deployable; active development |
| **Garage** | AGPL-3.0 | Lightweight distributed S3-compatible store written in Rust; designed for small self-hosted clusters |

## Literature

- **RFC 8493** (IETF, 2018): The BagIt File Packaging Format. Used by the Library
  of Congress, Internet Archive, and the British Library Endangered Archives Programme
  (which covers the kind of material Itihasa ingests) for digital preservation packaging.
- **Fedora Commons 6** (GLAM sector standard): supports both a local filesystem backend
  and S3-compatible backends. Starts on filesystem; migrates to S3 at scale.
- **Archivematica** (GLAM preservation workflow): uses BagIt as its primary transfer
  package format, writing to local filesystem or cloud storage behind an abstraction.
- SeaweedFS: Weed-FS paper, Weed (2012), plus GitHub star count and issue activity
  indicate production use at multiple companies, though not specifically in GLAM.
- Garage: no peer-reviewed literature found; primary reference is the official
  documentation at garagehq.deuxfleurs.fr.

## Comparison

| Criterion | Filesystem + BagIt | SeaweedFS | Garage |
|-----------|--------------------|-----------|--------|
| Licence | RFC + CC0 | Apache 2.0 | AGPL-3.0 |
| S3-compatible API | No | Yes | Yes |
| Docker service required | No | Yes (master + volume server) | Yes |
| RAM overhead | Near zero | ~200 MB idle | ~50 MB idle |
| Operational complexity | Minimal | Medium | Low |
| Fixity checking | BagIt manifest (SHA-256, built-in) | CRC per object (not BagIt) | Per-object checksums |
| BagIt native | Yes | No (would need a wrapper) | No |
| Heritage / GLAM precedent | Very high (LoC, IA, BL EAP) | None found | None found |
| Pilot scale (5 K docs) | Fully sufficient | Overkill | Overkill |
| Full scale (1 M+ objects) | Filesystem limits apply | Excellent | Good |
| Public deployment concern | None | None | AGPL requires source-sharing if modified and deployed as a network service |
| Switch-away complexity | Implement S3 backend in one module | Implement filesystem backend | Implement filesystem backend |

**On Garage's AGPL-3.0 licence:** if Garage is modified and run as a network service
(i.e. the public demo in Phase 7 uses it), the AGPL requires releasing the modified
Garage source. This is not a concern for internal research use but would create an
obligation if Itihasa is ever deployed as a hosted service. SeaweedFS (Apache 2.0)
does not carry this restriction.

## Recommendation

**Local filesystem + BagIt for Phases 0–3.**

At pilot scale the filesystem is entirely sufficient and BagIt is the standard
preservation packaging format used by the institutions whose data Itihasa ingests.
Adding a network object-store service (SeaweedFS or Garage) for 5,000 documents
brings operational cost with no benefit. The `StorageBackend` interface means
switching to SeaweedFS — if a network API becomes necessary for IIIF image serving
in Phase 3, or if the corpus grows beyond filesystem limits — is a single-module
change that does not touch any connector, normaliser, or retrieval code.

If an S3-compatible API is needed from day one (for example to run a IIIF image
server that requires S3 protocol), **SeaweedFS** is preferred over Garage because
its Apache 2.0 licence carries no deployment obligations.

**Main risk:** Filesystem inode limits and directory-listing speed degrade above
~100,000 objects per directory. Mitigated by a two-level hash-sharded directory
layout (e.g. `objects/ab/cd/<sha256>.bag`) which distributes objects across
65,536 leaf directories.

## Decision

> **Decision:** Filesystem + BagIt packages behind a single `StorageBackend` interface.
> Revisit SeaweedFS in Phase 4 when public uploads begin.
>
> **Date decided:** 2026-11-06

## Consequences

- `src/itihasa/ingest/storage.py` defines the `StorageBackend` abstract interface
  with methods `put(key, data)`, `get(key)`, `exists(key)`, `delete(key)`.
- `src/itihasa/ingest/filesystem.py` implements `FilesystemBackend` using the
  two-level sharded layout. Each stored object is a BagIt bag directory.
- Switching to SeaweedFS later requires writing `SeaweedFSBackend` in one file and
  changing one config value.
- BagIt manifests provide SHA-256 fixity for all stored objects, satisfying
  the fixity requirement in Phase 3.
