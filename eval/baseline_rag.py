"""Baseline pure vector RAG system without graph traversal or structured data."""

import time

from neo4j import Driver

from api.config import Settings, get_settings
from api.models import ChatResponse, Citation
from embedding.embed import embed_query
from generation.generator import generate_copilot_response
from retrieval.context_assembler import AssembledContext
from retrieval.router import find_disruption_keywords
from retrieval.schemas import VectorSearchResult
from retrieval.vector_search import search_articles_fallback_text, search_articles_vector


def retrieve_baseline_chunks(
    driver: Driver,
    query: str,
    top_k: int = 5,
) -> list[VectorSearchResult]:
    """Retrieve top-K article chunks via vector search without graph expansion."""
    try:
        q_vec = embed_query(query)
        raw_results = search_articles_vector(driver, q_vec, top_k=top_k)
    except Exception:
        raw_results = []

    if not raw_results:
        keywords = find_disruption_keywords(query) or ["disruption", "shipping", "port", "supply"]
        raw_results = search_articles_fallback_text(driver, keywords=keywords, top_k=top_k)

    # Enforce pure vector baseline: strip all expanded graph entities
    baseline_results: list[VectorSearchResult] = []
    for r in raw_results:
        baseline_results.append(
            VectorSearchResult(
                chunk_id=r.chunk_id,
                title=r.title,
                source=r.source,
                published_date=r.published_date,
                text=r.text,
                score=r.score,
                mentioned_node_ids=[],
                expanded_node_ids=[],
            )
        )
    return baseline_results


def query_baseline_rag(
    driver: Driver,
    question: str,
    settings: Settings | None = None,
    top_k: int = 5,
) -> ChatResponse:
    """Execute baseline vector RAG query without graph traversal or Cypher lookups."""
    t0 = time.perf_counter()
    cfg = settings or get_settings()

    # 1. Retrieve article chunks without any graph expansion
    chunk_results = retrieve_baseline_chunks(driver, question, top_k=top_k)

    # 2. Build citations and formatted context string purely from text chunks
    citations: list[Citation] = []
    text_passages: list[str] = []

    for idx, chunk in enumerate(chunk_results, start=1):
        source_id = f"source_{idx}"
        snippet = chunk.text[:300].strip() + ("..." if len(chunk.text) > 300 else "")
        text_passages.append(
            f'[{source_id}] "{chunk.title}" ({chunk.source}, {chunk.published_date}):\n{snippet}'
        )
        citations.append(
            Citation(
                source_id=source_id,
                title=chunk.title,
                source=chunk.source,
                url=f"https://chainsight.internal/articles/{chunk.chunk_id}",
                date=chunk.published_date,
            )
        )

    context_str = (
        "### DISRUPTION NEWS & ARTICLE EXCERPTS:\n" + "\n\n".join(text_passages)
        if text_passages
        else "None available."
    )

    # 3. Assemble pure vector context (zero structured graph facts, zero subgraph IDs)
    assembled = AssembledContext(
        strategy="semantic",
        raw_query=question,
        structured_facts=[],
        citations=citations,
        subgraph_node_ids=[],
        subgraph_edge_ids=[],
        formatted_prompt_context=context_str,
        is_empty=len(chunk_results) == 0,
    )

    # 4. Generate response via standardized generator
    return generate_copilot_response(assembled, settings=cfg, start_time=t0)
