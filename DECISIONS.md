# DECISIONS.md — Architectural Decision Log

## ADR-001: Local Neo4j Containerization and Environment Configuration
**Date:** 2026-10-24
**Status:** Accepted

**Context:**
ChainSight requires a Neo4j instance supporting Cypher multi-hop graph queries, full-text search, and vector embeddings (384 dims). We needed to decide between local containerized Neo4j via Docker Compose and Neo4j AuraDB Free.

**Options Considered:**
1. Docker Compose with `neo4j:5.20-community` — fully reproducible, zero cost, local low-latency (<5ms), APOC plugins enabled, no node limits.
2. Neo4j AuraDB Free — cloud hosted, accessible remotely, but has a 200k node / 400k rels limit and requires network connectivity.

**Decision:**
Use Docker Compose with `neo4j:5.20-community` as the default local infrastructure for reproducible development, testing, and CI, while keeping connection credentials configurable via `.env` (Pydantic `Settings`) so the builder can switch seamlessly to an AuraDB URI for live portfolio demonstrations.

**Consequences:**
- Local developers need Docker Desktop running or an active Neo4j instance at `bolt://localhost:7687`.
- Volume mounts allow preloading synthetic CSVs and persistent graph state.
- Ingestion scripts can connect to either local or cloud instances transparently.

---

## ADR-002: Ingestion Pipeline and Strict Pydantic Data Layer
**Date:** 2026-10-24
**Status:** Accepted

**Context:**
Per `AGENTS.md`, all inter-module data transfer must use Pydantic models (no raw dicts), no `Any` types, and Neo4j driver instances must be dependency-injected rather than imported as global singletons. We needed an ingestion architecture that is fast, resilient, and adheres strictly to this contract.

**Options Considered:**
1. Direct Python driver execution with individual `session.run()` per entity row — extremely slow over network/socket.
2. Neo4j `LOAD CSV` Cypher commands directly inside Neo4j — requires server-side file access, bypasses Python-side schema validation, and makes unit testing difficult without an active database.
3. Hybrid client-side Pydantic validation with parameterized `UNWIND $batch` Cypher transactions — parses and strictly validates every record into typed Pydantic models, then converts validated models to dict batches for efficient single-roundtrip database upserts.

**Decision:**
Option 3: Ingestion scripts (`ingestion/load_graph.py`) parse CSVs into strongly-typed Pydantic models from `data/models.py`. Validated models are dumped to batch parameters and executed via `UNWIND $batch AS row MERGE ...` queries. Driver lifecycle is managed explicitly via context manager or dependency injection.

**Consequences:**
- Guarantees schema integrity before any database write occurs.
- Highly performant batch insertion.
- Entire ingestion logic can be unit-tested without requiring a live Neo4j instance.

---
<!-- Copy above template for each new decision -->
