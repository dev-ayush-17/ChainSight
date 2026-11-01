"""Unit tests for query intent routing across lookup, traversal, semantic, and unanswerable."""

import pytest

from retrieval.router import classify_intent


@pytest.mark.parametrize(
    "query, expected_intent",
    [
        # --- LOOKUP INTENT ---
        ("Which country is supplier SUP-007 located in?", "lookup"),
        ("Who produces component CMP-0012?", "lookup"),
        ("What is the lead time for supplier SUP-015?", "lookup"),
        ("Show details for Port of Shanghai", "lookup"),
        ("What is the annual revenue of product PRD-001?", "lookup"),
        ("What is the UN_LOCODE for Port of Rotterdam?", "lookup"),
        ("List all components in product PRD-003", "lookup"),
        # --- IMPACT TRAVERSAL INTENT ---
        (
            "Port of Shanghai is disrupted: which products are exposed and revenue risk?",
            "impact_traversal",
        ),
        (
            "A dockworkers strike shut down Port of Rotterdam, which suppliers are impacted?",
            "impact_traversal",
        ),
        (
            "Supplier SUP-005 had a factory shutdown: what products are affected?",
            "impact_traversal",
        ),
        (
            "Find alternative suppliers for component CMP-0005 due to shortage",
            "impact_traversal",
        ),
        (
            "Analyze country concentration risk and total revenue at risk in Taiwan",
            "impact_traversal",
        ),
        (
            "Typhoon disrupted Port of Ningbo, what is our downstream exposure?",
            "impact_traversal",
        ),
        # --- SEMANTIC INTENT ---
        (
            "What recent shipping disruptions and container delays have occurred in Asia?",
            "semantic",
        ),
        (
            "Tell me about global supply chain freight rate trends and maritime bottlenecks",
            "semantic",
        ),
        (
            "Are there any active logistics delays affecting European container terminals?",
            "semantic",
        ),
        # --- UNANSWERABLE INTENT ---
        ("What is the CEO's annual salary and bonus package?", "unanswerable"),
        ("What is the current stock price and market cap of Apple?", "unanswerable"),
        ("What is a delicious recipe for dinner tonight?", "unanswerable"),
        ("Who won the football game yesterday?", "unanswerable"),
        ("", "unanswerable"),
    ],
)
def test_classify_intent_cases(query: str, expected_intent: str) -> None:
    """Verify intent router accurately categorizes benchmark question types."""
    res = classify_intent(query)
    assert res.intent == expected_intent
    assert res.confidence >= 0.70
    assert len(res.reasoning) > 0
