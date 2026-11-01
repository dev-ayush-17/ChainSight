"""Unit tests for Text-to-Cypher generation and safety validation."""

from unittest.mock import MagicMock

from retrieval.cypher_gen import (
    execute_text_to_cypher,
    generate_cypher_fallback,
    validate_cypher_safety,
)


def test_validate_cypher_safety_allows_read_only() -> None:
    """Verify validate_cypher_safety accepts legitimate read-only queries."""
    safe_query = "MATCH (s:Supplier)-[:PRODUCES]->(c:Component) RETURN s.name, c.name LIMIT 10"
    is_safe, error = validate_cypher_safety(safe_query)
    assert is_safe is True
    assert error is None


def test_validate_cypher_safety_rejects_destructive_ops() -> None:
    """Verify validate_cypher_safety blocks destructive mutation statements."""
    forbidden_queries = [
        "MATCH (s:Supplier) DELETE s",
        "MATCH (s:Supplier) SET s.name = 'Hacked'",
        "CREATE (s:Supplier {name: 'Evil Corp'})",
        "MERGE (s:Supplier {id: '123'})",
        "DROP CONSTRAINT supplier_id",
        "MATCH (s:Supplier) REMOVE s.tier",
    ]
    for q in forbidden_queries:
        is_safe, error = validate_cypher_safety(q)
        assert is_safe is False
        assert error is not None


def test_generate_cypher_fallback_patterns() -> None:
    """Verify generate_cypher_fallback maps standard lookup queries to valid Cypher."""
    # Supplier country lookup
    q1 = "Which country is supplier SUP-007 located in?"
    c1 = generate_cypher_fallback(q1)
    assert "MATCH" in c1
    assert "SUP-007" in c1
    assert "RETURN" in c1

    # Component producer lookup
    q2 = "Who produces component CMP-0012?"
    c2 = generate_cypher_fallback(q2)
    assert "MATCH" in c2
    assert "CMP-0012" in c2

    # Product BOM lookup
    q3 = "What are the components of product PRD-001?"
    c3 = generate_cypher_fallback(q3)
    assert "PRD-001" in c3
    assert "PART_OF" in c3


def test_execute_text_to_cypher_executes_safely() -> None:
    """Verify execute_text_to_cypher returns validated CypherQueryResult."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_session.run.return_value.data.return_value = [
        {"supplier_id": "SUP-007", "supplier_name": "Foxconn Precision", "country": "Taiwan"}
    ]

    res = execute_text_to_cypher(mock_driver, "Which country is supplier SUP-007 located in?")
    assert res.is_safe is True
    assert len(res.records) == 1
    assert res.records[0]["supplier_id"] == "SUP-007"
    assert "SUP-007" in res.subgraph_node_ids
