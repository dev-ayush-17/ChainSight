"""Unit tests for embedding generation and Neo4j node embedding upserts."""

from unittest.mock import MagicMock

from embedding.embed import (
    compute_deterministic_embedding,
    embed_and_upsert_articles,
    embed_and_upsert_suppliers,
    embed_query,
    embed_texts,
)


def test_compute_deterministic_embedding() -> None:
    """Verify compute_deterministic_embedding returns 384-dimensional unit vector."""
    vec1 = compute_deterministic_embedding("Port of Shanghai container congestion")
    vec2 = compute_deterministic_embedding("Port of Shanghai container congestion")
    vec3 = compute_deterministic_embedding("Red Sea maritime missile attack")

    assert len(vec1) == 384
    assert vec1 == vec2
    assert vec1 != vec3

    norm = sum(x * x for x in vec1)
    assert 0.99 <= norm <= 1.01


def test_embed_texts_and_query() -> None:
    """Verify embed_texts and embed_query return valid vector structures."""
    vectors = embed_texts(["Text A", "Text B"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 384

    query_vec = embed_query("Who supplies CMP-0001?")
    assert len(query_vec) == 384


def test_embed_and_upsert_articles_with_mock() -> None:
    """Verify embed_and_upsert_articles fetches unindexed articles and updates embeddings."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_session.run.side_effect = [
        MagicMock(data=MagicMock(return_value=[{"id": "art_1", "text": "Article content"}])),
        MagicMock(),
    ]

    count = embed_and_upsert_articles(mock_driver)
    assert count == 1
    assert mock_session.run.call_count == 2


def test_embed_and_upsert_suppliers_with_mock() -> None:
    """Verify embed_and_upsert_suppliers generates description embeddings for vendors."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_session.run.side_effect = [
        MagicMock(
            data=MagicMock(
                return_value=[
                    {"id": "SUP-001", "name": "Acme Semi", "tier": 1, "components": ["DRAM"]}
                ]
            )
        ),
        MagicMock(),
    ]

    count = embed_and_upsert_suppliers(mock_driver)
    assert count == 1
    assert mock_session.run.call_count == 2
