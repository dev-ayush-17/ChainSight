"""Unit tests for context assembler merging graph facts, article chunks, and token trimming."""

from retrieval.context_assembler import (
    assemble_context,
    estimate_token_count,
    format_tabular_record,
)
from retrieval.schemas import (
    IntentClassification,
    TraversalImpactResult,
    VectorSearchResult,
)


def test_format_tabular_record() -> None:
    """Format single graph tabular record into a human-readable factual bullet point."""
    rec = {"supplier_id": "SUP-007", "annual_revenue": 1250000.5, "is_critical": True}
    formatted = format_tabular_record(rec)
    assert "Supplier Id: SUP-007" in formatted
    assert "Annual Revenue: 1,250,000.50" in formatted
    assert "Is Critical: True" in formatted


def test_estimate_token_count() -> None:
    """Estimate token count returns positive count."""
    text = "ChainSight is an enterprise Graph RAG supply chain risk copilot."
    tokens = estimate_token_count(text)
    assert tokens > 5


def test_assemble_context_refused_intent() -> None:
    """Assemble context immediately marks refused for unanswerable queries."""
    intent = IntentClassification(
        intent="unanswerable",
        confidence=0.95,
        reasoning="Out of scope query",
        extracted_entities=[],
        disruption_keywords=[],
    )
    assembled = assemble_context("What is the CEO salary?", intent=intent)
    assert assembled.strategy == "refused"
    assert assembled.is_empty is True
    assert len(assembled.structured_facts) == 0
    assert len(assembled.citations) == 0


def test_assemble_context_traversal_and_vector() -> None:
    """Assemble context merges traversal facts and vector search articles."""
    intent = IntentClassification(
        intent="impact_traversal",
        confidence=0.92,
        reasoning="Port disruption",
        extracted_entities=["Port of Shanghai"],
        disruption_keywords=["strike"],
    )
    traversal = TraversalImpactResult(
        template_name="port_disruption_impact",
        parameters={"port_name": "Port of Shanghai"},
        records=[
            {
                "port_name": "Port of Shanghai",
                "supplier_name": "Apex Microelectronics",
                "annual_revenue_usd": 45000000.0,
            }
        ],
        subgraph_node_ids=["port_SHA", "sup_001"],
        subgraph_edge_ids=[],
    )
    vector = [
        VectorSearchResult(
            chunk_id="art_101",
            title="Shanghai Port Congestion Mounts",
            source="Maritime Executive",
            published_date="2025-06-15",
            text="Port terminals in Shanghai face significant vessel backlogs.",
            score=0.88,
            mentioned_node_ids=["port_SHA"],
            expanded_node_ids=["sup_001"],
        )
    ]

    assembled = assemble_context(
        "Port of Shanghai strike impact",
        intent=intent,
        traversal_result=traversal,
        vector_results=vector,
    )

    assert assembled.strategy == "impact_traversal"
    assert assembled.is_empty is False
    assert len(assembled.structured_facts) == 1
    assert "Apex Microelectronics" in assembled.structured_facts[0]
    assert len(assembled.citations) == 1
    assert assembled.citations[0].title == "Shanghai Port Congestion Mounts"
    assert "port_SHA" in assembled.subgraph_node_ids
    assert "sup_001" in assembled.subgraph_node_ids


def test_assemble_context_token_trimming() -> None:
    """Assemble context trims articles when exceeding token budget."""
    intent = IntentClassification(
        intent="semantic",
        confidence=0.80,
        reasoning="Semantic news query",
        extracted_entities=[],
        disruption_keywords=["delays"],
    )
    long_text = "Supply chain disruptions and container terminal delays. " * 300
    vector_results = [
        VectorSearchResult(
            chunk_id=f"art_{i}",
            title=f"Article {i}",
            source="Reuters",
            published_date="2025-01-01",
            text=long_text,
            score=0.85,
            mentioned_node_ids=[],
            expanded_node_ids=[],
        )
        for i in range(10)
    ]

    assembled = assemble_context(
        "Recent shipping disruptions",
        intent=intent,
        vector_results=vector_results,
        max_tokens=400,
    )

    assert assembled.estimated_token_count <= 800
    assert len(assembled.citations) == 10
