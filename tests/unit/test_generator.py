"""Unit tests for response generation, hallucination guardrails, and deterministic synthesis."""

from api.models import Citation
from generation.generator import (
    generate_copilot_response,
    synthesize_answer_deterministic,
    verify_hallucinations,
)
from generation.prompts import INSUFFICIENT_INFO_ANSWER, REFUSAL_ANSWER
from retrieval.context_assembler import AssembledContext


def test_synthesize_answer_deterministic_refusal() -> None:
    """Refused context returns refusal statement."""
    context = AssembledContext(
        strategy="refused",
        raw_query="What is the CEO bonus?",
        structured_facts=[],
        citations=[],
        subgraph_node_ids=[],
        subgraph_edge_ids=[],
        formatted_prompt_context="[REFUSED]",
        is_empty=True,
    )
    res = synthesize_answer_deterministic(context)
    assert res.answer == REFUSAL_ANSWER
    assert res.confidence == "none"
    assert len(res.cited_sources) == 0


def test_synthesize_answer_deterministic_empty() -> None:
    """Empty context returns insufficient information statement."""
    context = AssembledContext(
        strategy="lookup",
        raw_query="What is the secret factory code?",
        structured_facts=[],
        citations=[],
        subgraph_node_ids=[],
        subgraph_edge_ids=[],
        formatted_prompt_context="None available.",
        is_empty=True,
    )
    res = synthesize_answer_deterministic(context)
    assert res.answer == INSUFFICIENT_INFO_ANSWER
    assert res.confidence == "none"


def test_synthesize_answer_deterministic_with_facts() -> None:
    """Structured facts produce grounded bulleted assessment."""
    context = AssembledContext(
        strategy="impact_traversal",
        raw_query="Port of Shanghai strike",
        structured_facts=["- [Graph Fact] Supplier: Apex Micro | Exposure: $45M"],
        citations=[
            Citation(
                source_id="source_1",
                title="Port Congestion",
                source="Reuters",
                url="https://example.com",
                date="2025-06-01",
            )
        ],
        subgraph_node_ids=["sup_001", "port_SHA"],
        subgraph_edge_ids=[],
        formatted_prompt_context="Facts",
        is_empty=False,
    )
    res = synthesize_answer_deterministic(context)
    assert "Supply Chain Risk Assessment" in res.answer
    assert "Apex Micro" in res.answer
    assert "[source_1]" in res.answer
    assert res.confidence == "high"


def test_verify_hallucinations_guardrail() -> None:
    """Verify hallucination detection flags ungrounded entity IDs."""
    context = AssembledContext(
        strategy="lookup",
        raw_query="Supplier SUP-007 details",
        structured_facts=["- [Graph Fact] Supplier Id: SUP-007"],
        citations=[],
        subgraph_node_ids=["sup_007"],
        subgraph_edge_ids=[],
        formatted_prompt_context="Supplier Id: SUP-007 located in Taiwan.",
        is_empty=False,
    )

    # Valid answer referencing SUP-007
    assert verify_hallucinations("Supplier SUP-007 is in Taiwan.", context) is True

    # Hallucinated answer referencing ungrounded SUP-999
    assert verify_hallucinations("Supplier SUP-999 is in Brazil.", context) is False


def test_generate_copilot_response_end_to_end() -> None:
    """Generate copilot response builds complete ChatResponse model."""
    context = AssembledContext(
        strategy="impact_traversal",
        raw_query="Disruption at Port of Rotterdam",
        structured_facts=["- [Graph Fact] Supplier: Delta Electronics | Annual Revenue: $12M"],
        citations=[],
        subgraph_node_ids=["sup_010", "port_ROT"],
        subgraph_edge_ids=[],
        formatted_prompt_context="Delta Electronics $12M",
        is_empty=False,
    )
    resp = generate_copilot_response(context)
    assert resp.retrieval_strategy == "impact_traversal"
    assert resp.confidence == "high"
    assert resp.latency_ms >= 0
    assert "Delta Electronics" in resp.answer
    assert "sup_010" in resp.subgraph_node_ids
