# AGENTS.md — AI Coding Assistant Instructions for ChainSight

## Project Context
ChainSight is a Graph RAG supply chain risk copilot. The codebase uses:
- Python 3.11, FastAPI, Streamlit, Neo4j (Bolt), sentence-transformers, Gemini API
- Pydantic for all data models; ruff for formatting/linting
- Custom retrieval layer (no LangChain/LlamaIndex)

## Architecture Rules (Never Violate Without Creating a DECISIONS.md Entry)
1. All inter-module data transfer uses Pydantic models (no raw dicts).
2. Neo4j driver is injected, never imported as a global singleton in modules.
3. LLM is called only in: extraction/pipeline.py, retrieval/cypher_gen.py,
   generation/generator.py, eval/judge.py.
4. No CREATE/MERGE/DELETE Cypher generated at runtime except in ingestion scripts.
5. Prompts are constants in prompts.py files, not inline strings.

## Code Style
- ruff format + lint (run `ruff check . && ruff format .` before committing)
- All functions have type annotations and a one-line docstring
- No `Any` types; no bare `except`

## What AI Should NOT Do
- Do not install new dependencies without discussing trade-offs first
- Do not add LangChain, LlamaIndex, or similar framework abstractions
- Do not modify eval/questions.yaml (ground truth authored by human only)
- Do not change graph schema without a DECISIONS.md entry

## Per-Ticket Checklist (AI must confirm before presenting code)
- [ ] Does the implementation match the ticket scope only?
- [ ] Are all new functions typed and docstrung?
- [ ] Is any new external dependency justified?
- [ ] Does the code pass `ruff check`?
- [ ] Are there unit tests for new logic?
