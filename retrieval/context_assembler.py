"""Context assembler merging structured graph facts and news excerpts within token budget."""

from typing import Literal

import tiktoken
from pydantic import BaseModel, Field

from api.models import Citation
from retrieval.schemas import (
    CypherQueryResult,
    IntentClassification,
    TraversalImpactResult,
    VectorSearchResult,
)

StrategyType = Literal["lookup", "impact_traversal", "semantic", "refused"]
MAX_CONTEXT_TOKENS: int = 3000


class AssembledContext(BaseModel):
    """Normalized, deduplicated, and ranked context ready for LLM generation."""

    strategy: StrategyType = Field(..., description="Selected retrieval strategy")
    raw_query: str = Field(..., description="Original user prompt")
    structured_facts: list[str] = Field(
        default_factory=list, description="Ranked factual statements derived from graph"
    )
    citations: list[Citation] = Field(
        default_factory=list, description="Citations corresponding to retrieved passages"
    )
    subgraph_node_ids: list[str] = Field(
        default_factory=list, description="Deduplicated node IDs for UI visualization"
    )
    subgraph_edge_ids: list[str] = Field(
        default_factory=list, description="Deduplicated edge IDs for UI visualization"
    )
    formatted_prompt_context: str = Field(
        ..., description="Final combined string inserted into LLM prompt"
    )
    is_empty: bool = Field(
        default=False, description="Flag set when zero relevant context was retrieved"
    )
    estimated_token_count: int = Field(default=0, ge=0, description="Estimated token count")


def estimate_token_count(text: str) -> int:
    """Estimate token count of string using tiktoken or fast heuristic."""
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # 1 token ~= 4 chars fallback heuristic
        return max(1, len(text) // 4)


def format_tabular_record(record: dict[str, str | int | float | bool]) -> str:
    """Format single graph tabular record into a human-readable factual bullet point."""
    items = []
    for k, v in record.items():
        clean_k = k.replace("_", " ").title()
        if isinstance(v, float):
            items.append(f"{clean_k}: {v:,.2f}")
        else:
            items.append(f"{clean_k}: {v}")
    return " | ".join(items)


def assemble_context(
    query: str,
    intent: IntentClassification,
    traversal_result: TraversalImpactResult | None = None,
    cypher_result: CypherQueryResult | None = None,
    vector_results: list[VectorSearchResult] | None = None,
    max_tokens: int = MAX_CONTEXT_TOKENS,
) -> AssembledContext:
    """Merge, rank, trim, and assemble multi-strategy retrieval data into a structured context."""
    if intent.intent == "unanswerable":
        return AssembledContext(
            strategy="refused",
            raw_query=query,
            structured_facts=[],
            citations=[],
            subgraph_node_ids=[],
            subgraph_edge_ids=[],
            formatted_prompt_context="[REFUSED: Query out of supply chain domain scope.]",
            is_empty=True,
            estimated_token_count=10,
        )

    structured_facts: list[str] = []
    citations: list[Citation] = []
    node_ids: set[str] = set()
    edge_ids: set[str] = set()

    # 1. Process Traversal Results (High Priority Graph Facts)
    if traversal_result and traversal_result.records:
        for rec in traversal_result.records:
            fact_str = format_tabular_record(rec)
            structured_facts.append(f"- [Graph Fact] {fact_str}")
        node_ids.update(traversal_result.subgraph_node_ids)
        edge_ids.update(traversal_result.subgraph_edge_ids)

    # 2. Process Cypher Query Results (Lookup Graph Facts)
    if cypher_result and cypher_result.records:
        for rec in cypher_result.records:
            fact_str = format_tabular_record(rec)
            structured_facts.append(f"- [Graph Fact] {fact_str}")
        node_ids.update(cypher_result.subgraph_node_ids)

    # 3. Process Vector Search Results (Articles & News)
    article_passages: list[str] = []
    if vector_results:
        for idx, res in enumerate(vector_results, start=1):
            source_id = f"source_{idx}"
            snippet = res.text[:300].strip() + ("..." if len(res.text) > 300 else "")
            article_passages.append(
                f'[{source_id}] "{res.title}" ({res.source}, {res.published_date}):\n{snippet}'
            )
            citations.append(
                Citation(
                    source_id=source_id,
                    title=res.title,
                    source=res.source,
                    url=f"https://chainsight.internal/articles/{res.chunk_id}",
                    date=res.published_date,
                )
            )
            node_ids.add(res.chunk_id)
            node_ids.update(res.mentioned_node_ids)
            node_ids.update(res.expanded_node_ids)

    # Check if empty context
    is_empty = (len(structured_facts) == 0) and (len(article_passages) == 0)

    # 4. Map Intent to Strategy Type
    strategy_mapping: dict[str, StrategyType] = {
        "impact_traversal": "impact_traversal",
        "lookup": "lookup",
        "semantic": "semantic",
        "unanswerable": "refused",
    }
    strategy = strategy_mapping.get(intent.intent, "semantic")
    if is_empty:
        strategy = "refused"

    # 5. Build Formatted Context with Budget Trimming
    header_facts = "\n".join(structured_facts) if structured_facts else "None available."
    header_articles = "\n\n".join(article_passages) if article_passages else "None available."

    full_context_str = (
        f"### STRUCTURED GRAPH FACTS (High Priority):\n{header_facts}\n\n"
        f"### DISRUPTION NEWS & ARTICLE EXCERPTS:\n{header_articles}"
    )

    # Token trimming if needed
    token_count = estimate_token_count(full_context_str)
    if token_count > max_tokens:
        # Retain graph facts first, trim article excerpts
        trimmed_articles = []
        running_tokens = estimate_token_count(
            f"### STRUCTURED GRAPH FACTS (High Priority):\n{header_facts}\n\n"
            "### DISRUPTION NEWS & ARTICLE EXCERPTS:\n"
        )
        for passage in article_passages:
            passage_tokens = estimate_token_count(passage)
            if running_tokens + passage_tokens < max_tokens:
                trimmed_articles.append(passage)
                running_tokens += passage_tokens
            else:
                break
        trimmed_article_str = (
            "\n\n".join(trimmed_articles) if trimmed_articles else "Excerpts omitted due to length."
        )
        full_context_str = (
            f"### STRUCTURED GRAPH FACTS (High Priority):\n{header_facts}\n\n"
            f"### DISRUPTION NEWS & ARTICLE EXCERPTS:\n{trimmed_article_str}"
        )
        token_count = estimate_token_count(full_context_str)

    return AssembledContext(
        strategy=strategy,
        raw_query=query,
        structured_facts=structured_facts,
        citations=citations,
        subgraph_node_ids=sorted(node_ids),
        subgraph_edge_ids=sorted(edge_ids),
        formatted_prompt_context=full_context_str,
        is_empty=is_empty,
        estimated_token_count=token_count,
    )
