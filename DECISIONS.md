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

## ADR-003: News Ingestion & LLM Extraction Dependencies
**Date:** 2026-10-31
**Status:** Accepted

**Context:**
Week 2 requires real disruption news ingestion (RSS/GDELT), token-based chunking, and schema-constrained LLM entity/relationship extraction. We must choose libraries without introducing heavy monolithic frameworks (e.g. LangChain, LlamaIndex).

**Options Considered:**
1. Custom raw XML parsing + custom token approximation + raw `requests` against LLM REST endpoints.
   - Pros: Zero new third-party dependencies.
   - Cons: Fragile RSS date/encoding parsing across BBC/Reuters; poor token boundary enforcement; reimplementing LLM retry and structured JSON schemas.
2. Lightweight focused libraries: `feedparser` for RSS feeds, `tiktoken` for deterministic 400-token chunks with 50-token overlap, and `google-genai` (official Google SDK) with fallback to REST API.
   - Pros: Minimal surface area, robust RFC-compliant RSS parsing, accurate token counting matching Gemini/OpenAI standard tokenizers, native Pydantic schema validation. Completely avoids LangChain/LlamaIndex abstractions.
   - Cons: Three lightweight packages added to requirements.

**Decision:**
Option 2: Adopt `feedparser`, `tiktoken`, and `google-genai`. Maintain our own custom extraction pipeline, entity resolution, and prompt management in accordance with `AGENTS.md`.

**Consequences:**
- Deterministic chunking and sanitization.
- Clean Pydantic-based structured outputs directly from Gemini 1.5 Flash.
- Fully interview-explainable, custom retrieval architecture remains clean.

---

## ADR-004: Embedding Engine Selection (FastEmbed ONNX vs PyTorch Sentence-Transformers)
**Date:** 2026-11-01
**Status:** Accepted

**Context:**
ChainSight requires generating 384-dimensional dense vector embeddings for `Article` chunk nodes and search queries to support Neo4j's native vector indices (`article_embedding`, `node_desc_embedding`).

**Options Considered:**
1. `sentence-transformers` with PyTorch backend:
   - Pros: Standard HuggingFace library.
   - Cons: Pulls >2GB of PyTorch dependencies and CUDA binaries, slow cold start, heavy footprint for a lightweight local copilot.
2. `fastembed` with ONNX Runtime backend:
   - Pros: Extremely lightweight (<40MB footprint), uses ONNX runtime, generates identical 384-dimensional cosine-normalized embeddings using `sentence-transformers/all-MiniLM-L6-v2` or `BAAI/bge-small-en-v1.5`, 3-5x faster inference, zero torch dependency.
   - Cons: Specialized embedding runner.

**Decision:**
Option 2: Adopt `fastembed` targeting 384-dimensional embeddings compatible with Neo4j vector indexes.

**Consequences:**
- Sub-millisecond local embedding generation.
- Zero massive PyTorch bloat in container and local virtual environment.
- Compatible with Neo4j 384-dim vector index definition from Week 1.

---

## ADR-005: Multi-Strategy Retrieval Layer and Cypher Generation Safety Guardrails
**Date:** 2026-11-01  
**Status:** Accepted  

**Context:**
ChainSight needs to answer multi-hop supply chain questions ("Port X disrupted: exposed products, suppliers, alternatives?"), direct factual lookups, and open-ended disruption news search without relying on heavy agent frameworks. In runtime query generation, arbitrary LLM text-to-Cypher generation presents security risks (potential injection or mutation of graph data) and latency/hallucination vulnerabilities.

**Options Considered:**
1. LLM-only Text-to-Cypher for every query:
   - Pros: Flexible.
   - Cons: High latency, hallucinated property names, security vulnerability if destructive Cypher (`DETACH DELETE`) is generated, prone to schema mismatch.
2. Parameterized Cypher Templates for multi-hop propagation + deterministic regex fallback for lookups + safe read-only Text-to-Cypher:
   - Pros: Guaranteed deterministic 0ms impact traversals for known risk topologies; regex-based immediate resolution for common lookup templates; strict regex safety validator (`validate_cypher_safety`) that rejects mutation keywords (`CREATE`, `MERGE`, `DELETE`, `SET`, `DROP`, `ALTER`); safe schema-constrained LLM fallback.
   - Cons: Requires upfront template and intent routing definition.

**Decision:**
Adopt Option 2: An intent router (`retrieval/router.py`) directs questions across 4 explicit paths:
- `impact_traversal`: Executes parameterized Cypher templates (`retrieval/traversal.py`) with guaranteed multi-hop paths and revenue aggregation.
- `lookup`: Runs safe read-only Text-to-Cypher (`retrieval/cypher_gen.py`) with deterministic pattern matching and AST-level read-only safety guardrails.
- `semantic`: Vector index search with 1-hop Neo4j graph expansion (`retrieval/vector_search.py`).
- `unanswerable`: Immediate refusal guardrail for out-of-scope domain queries.

**Consequences:**
- Zero risk of graph corruption or injection via LLM runtime queries.
- Clean Pydantic inter-module contracts (`retrieval/schemas.py`).
- Complies strictly with all `AGENTS.md` guidelines.

---

## ADR-006: Grounded Generation Architecture, Token Budgeting, and Hallucination Guardrails
**Date:** 2026-11-02  
**Status:** Accepted  

**Context:**
ChainSight's FastAPI backend (`POST /chat`) must assemble heterogeneous retrieved data (graph traversal paths, factual Cypher rows, and article chunks) and synthesize a grounded, citation-backed response within strict token budgets (max 3,000 tokens) without hallucinating ungrounded entity IDs.

**Options Considered:**
1. Unconstrained full-text prompt concatenation without schema validation:
   - Pros: Simple implementation.
   - Cons: Prone to token blowout on long news articles, arbitrary LLM text formatting, hallucination of phantom supplier IDs.
2. Structured Context Assembler + Pydantic Response Schema + Post-generation Hallucination Guardrail:
   - Pros: Prioritizes verified graph facts over news text; enforces 3,000-token ceiling via `tiktoken`; validates structured JSON response (`answer`, `cited_sources`, `confidence`); regex post-verification prevents citing non-existent entity IDs (`SUP-xxx`, `PRD-xxx`); deterministic rule-based fallback guarantees zero-failure offline execution.
   - Cons: Requires explicit schema validation.

**Decision:**
Adopt Option 2: Implement `retrieval/context_assembler.py` and `generation/generator.py` with structured JSON output, citation mapping, and post-generation entity validation.

**Consequences:**
- Deterministic response synthesis for testing and offline environments.
- Strict token budgeting guarantees responses stay well within model context limits.
- Full type safety through Pydantic models.

---

## ADR-007: UI Architecture and Interactive Vis-Network Subgraph Visualization
**Date:** 2026-11-02  
**Status:** Accepted  

**Context:**
The frontend must provide an interactive 2-column copilot dashboard (Chat pane on left, Subgraph visualization on right) that dynamically highlights reasoning subgraphs when answers arrive and allows node property inspection.

**Options Considered:**
1. Heavy external C++ binding graph libraries (`streamlit-agraph` / binary wheels):
   - Pros: Native Streamlit component.
   - Cons: High risk of wheel compilation failure across varied OS platforms (Windows, Linux slim containers), fragile dependency chain.
2. Lightweight, self-contained `vis-network` HTML widget via `st.components.v1.html`:
   - Pros: 100% portable, runs directly in browser iframe via CDN, physics simulation with smooth zoom/pan/drag, zero native compilation overhead, dynamic node color mapping matching PRD schema colors (`#4A90D9` Supplier, `#E67E22` Port, etc.).
   - Cons: Requires custom HTML/JS template string.

**Decision:**
Adopt Option 2: Implement `ui/graph_renderer.py` utilizing `vis-network` rendered via Streamlit HTML components, with full node inspector and example queries sidebar.

**Consequences:**
- Seamless cross-platform execution in local virtualenvs and Docker containers (`ui.Dockerfile`).
- Clean separation between API backend (`http://localhost:8000`) and UI frontend (`http://localhost:8501`).

---
<!-- Copy above template for each new decision -->
