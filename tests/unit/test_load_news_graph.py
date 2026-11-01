"""Unit tests for news graph loading and Cypher batch execution."""

from unittest.mock import MagicMock

from extraction.schemas import (
    ArticleChunk,
    DisruptionEvent,
    ExtractedEntity,
    ExtractedRelationship,
    ExtractionPayload,
)
from ingestion.load_news_graph import (
    ensure_event_constraint,
    ingest_articles_to_neo4j,
    ingest_extracted_events_and_links,
    verify_news_graph,
)


def test_ensure_event_constraint_executes() -> None:
    """Verify ensure_event_constraint runs constraint creation query."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    ensure_event_constraint(mock_driver)
    assert mock_session.run.called
    stmt = mock_session.run.call_args[0][0]
    assert "CONSTRAINT" in stmt
    assert "Event" in stmt


def test_ingest_articles_to_neo4j_executes() -> None:
    """Verify ingest_articles_to_neo4j executes batch queries for articles and next chunks."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    chunks = [
        ArticleChunk(
            id="art_001",
            title="Article 1",
            source="Source 1",
            url="https://example.com/1",
            published_date="2024-10-01",
            chunk_index=0,
            text="Text chunk 1",
            token_count=100,
            previous_chunk_id=None,
        ),
        ArticleChunk(
            id="art_002",
            title="Article 1",
            source="Source 1",
            url="https://example.com/1",
            published_date="2024-10-01",
            chunk_index=1,
            text="Text chunk 2",
            token_count=90,
            previous_chunk_id="art_001",
        ),
    ]

    count = ingest_articles_to_neo4j(mock_driver, chunks)
    assert count == 2
    assert mock_session.run.call_count == 2


def test_ingest_extracted_events_and_links_executes() -> None:
    """Verify batch queries for events, mentions, and affects."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    chunk = ArticleChunk(
        id="art_001",
        title="Article 1",
        source="Source 1",
        url="https://example.com/1",
        published_date="2024-10-01",
        chunk_index=0,
        text="Port of Shanghai strike affects shipping.",
        token_count=50,
        previous_chunk_id=None,
    )

    payload = ExtractionPayload(
        entities=[
            ExtractedEntity(label="Port", name="Port of Shanghai", properties={}),
        ],
        relationships=[
            ExtractedRelationship(
                type="AFFECTS",
                from_name="Strike event",
                from_label="Event",
                to_name="Port of Shanghai",
                to_label="Port",
                confidence=0.9,
            )
        ],
        events=[
            DisruptionEvent(
                id="evt_001",
                event_type="strike",
                description="Strike event",
                start_date="2024-10-01",
                severity="high",
            )
        ],
    )

    stats = ingest_extracted_events_and_links(
        mock_driver,
        [(chunk, payload)],
        supplier_reg={},
        component_reg={},
    )
    assert stats["events"] == 1
    assert stats["mentions"] == 1
    assert stats["affects"] == 1
    assert mock_session.run.call_count == 6


def test_verify_news_graph() -> None:
    """Verify verify_news_graph queries graph counts and returns dictionary."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_res = MagicMock()
    mock_res.single.return_value = {"total": 105}
    mock_session.run.return_value = mock_res
    mock_res.data.return_value = []

    stats = verify_news_graph(mock_driver)
    assert stats["article_count"] == 105
