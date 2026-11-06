# 001 — Python package name

**Date proposed:** 2026-11-06
**Status:** Proposed — decision pending

## Context

The project needs a single Python package name that is used as the top-level import path
(`import itihasa`), the PyPI package identifier, and the prefix for Docker image names.
It must be a valid Python identifier (PEP 8 snake_case) with no conflicts on PyPI and
no ambiguity for a reader who does not already know the project.

## Options

| Name | Notes |
|------|-------|
| `itihasa` | Matches the project name exactly; clean and unambiguous to import |
| `itihasa_kg` | Makes the knowledge-graph intent explicit but adds length to every import |
| `ihkg` | Short, but opaque to any reader who has not memorised the acronym |
| `heritage` | Too generic; likely conflicts with other packages on PyPI |

## Literature

No specific precedent is needed here. Research software convention is to match the project
name when it is unique: spaCy, gensim, transformers, sentence-transformers. The name
`itihasa` is unique on PyPI as of the date above.

## Comparison

| Criterion | `itihasa` | `itihasa_kg` | `ihkg` | `heritage` |
|-----------|-----------|--------------|--------|------------|
| Import clarity | High | High | Low | Medium |
| PyPI uniqueness | Yes | Yes | Yes | Likely no |
| Length | Short | Medium | Very short | Short |
| Reflects project | Yes | Partially | No | Partially |

## Recommendation

**`itihasa`.** It is the natural choice: same word as the project, no conflicts, clean to import.

**Main risk:** None material. Verify PyPI availability before the first release.

## Decision

> *Owner to record decision and date here.*

## Consequences

- Top-level Python package lives at `src/itihasa/`.
- PyPI package name is `itihasa`.
- Docker images are prefixed `itihasa/` (e.g. `itihasa/api`).
- All sub-packages follow `itihasa.<subpackage>` (e.g. `itihasa.collect.wikidata`).
