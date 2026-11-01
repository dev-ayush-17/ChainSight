"""Unit tests for vector search and graph expansion."""

from unittest.mock import MagicMock

from retrieval.vector_search import search_articles_fallback_text, search_articles_vector


def test_search_articles_vector_with_expansion() -> None:
    """Verify search_articles_vector queries index and performs 1-hop expansion."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_session.run.side_effect = [
        # Call 1: Vector search returns 1 article
        MagicMock(
            data=MagicMock(
                return_value=[
                    {
                        "chunk_id": "art_123",
                        "title": "Shanghai Port Congestion",
                        "source": "Lloyds List",
                        "published_date": "2024-09-18",
                        "text": "Typhoon disrupted Port of Shanghai operations.",
                        "score": 0.89,
                        "mentioned_ids": ["PORT-SHA", "CN"],
                    }
                ]
            )
        ),
        # Call 2: Graph expansion returns neighbor nodes
        MagicMock(
            data=MagicMock(
                return_value=[
                    {"neighbor_id": "SUP-001"},
                    {"neighbor_id": "SUP-002"},
                ]
            )
        ),
    ]

    results = search_articles_vector(mock_driver, [0.1] * 384, top_k=5)
    assert len(results) == 1
    assert results[0].chunk_id == "art_123"
    assert results[0].score == 0.89
    assert "PORT-SHA" in results[0].mentioned_node_ids
    assert "SUP-001" in results[0].expanded_node_ids


def test_search_articles_fallback_text() -> None:
    """Verify search_articles_fallback_text retrieves articles matching keyword."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_session.run.return_value.data.return_value = [
        {
            "chunk_id": "art_999",
            "title": "Red Sea Shipping Delays",
            "source": "Financial Times",
            "published_date": "2024-01-15",
            "text": "Missile attacks forced rerouting around Cape of Good Hope.",
            "mentioned_ids": ["PORT-RTM"],
        }
    ]

    results = search_articles_fallback_text(mock_driver, keywords=["Red Sea"], top_k=3)
    assert len(results) == 1
    assert results[0].chunk_id == "art_999"
    assert results[0].score == 1.0
