"""Unit tests for extraction schemas and extraction pipeline logic."""

from extraction.pipeline import extract_fallback_rule_based
from extraction.schemas import (
    ArticleChunk,
    DisruptionEvent,
    ExtractedEntity,
    ExtractedRelationship,
    ExtractionPayload,
)


def test_extraction_payload_validation() -> None:
    """Verify ExtractionPayload validates proper entities and events."""
    payload = ExtractionPayload(
        entities=[
            ExtractedEntity(label="Port", name="Port of Shanghai", properties={}),
            ExtractedEntity(label="Country", name="China", properties={}),
        ],
        relationships=[
            ExtractedRelationship(
                type="LOCATED_IN",
                from_name="Port of Shanghai",
                from_label="Port",
                to_name="China",
                to_label="Country",
                confidence=1.0,
            )
        ],
        events=[
            DisruptionEvent(
                id="evt_001",
                event_type="strike",
                description="Dockworkers strike at Port of Shanghai",
                start_date="2024-10-01",
                severity="high",
            )
        ],
    )
    assert len(payload.entities) == 2
    assert payload.events[0].event_type == "strike"
    assert payload.relationships[0].type == "LOCATED_IN"


def test_extract_fallback_rule_based() -> None:
    """Verify extract_fallback_rule_based parses entities and disruption events from text."""
    chunk = ArticleChunk(
        id="art_test_123",
        title="Dockworkers Strike Halts Port of Shanghai",
        source="Reuters Maritime",
        url="https://example.com/strike-shanghai",
        published_date="2024-10-01",
        chunk_index=0,
        text=(
            "A nationwide labor strike at the Port of Shanghai in China has halted "
            "exports of DDR5 DRAM memory components."
        ),
        token_count=25,
        previous_chunk_id=None,
    )

    payload = extract_fallback_rule_based(chunk)
    assert len(payload.entities) >= 2
    entity_names = {e.name for e in payload.entities}
    assert "Port of Shanghai" in entity_names
    assert "China" in entity_names

    assert len(payload.events) == 1
    assert payload.events[0].event_type == "strike"
    assert payload.events[0].severity == "high"
