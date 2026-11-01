"""Pydantic schemas for news articles, LLM extraction output, and entity resolution."""

from typing import Literal

from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    """Extracted domain entity constrained to schema labels."""

    label: Literal["Port", "Supplier", "Event", "Country", "Component", "Product"] = Field(
        ..., description="Permitted entity label"
    )
    name: str = Field(..., description="Canonical name or identifier mentioned in the text")
    properties: dict[str, str | float | int | bool] = Field(
        default_factory=dict, description="Key-value properties of the entity"
    )


class ExtractedRelationship(BaseModel):
    """Extracted relationship connecting two domain entities."""

    type: Literal["AFFECTS", "MENTIONS", "SHIPS_VIA", "LOCATED_IN"] = Field(
        ..., description="Permitted relationship type"
    )
    from_name: str = Field(..., description="Name of the source entity")
    from_label: str = Field(..., description="Label of the source entity")
    to_name: str = Field(..., description="Name of the target entity")
    to_label: str = Field(..., description="Label of the target entity")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0"
    )


class DisruptionEvent(BaseModel):
    """Specific supply chain disruption event extracted from an article."""

    id: str = Field(default="auto", description="Unique event identifier")
    event_type: Literal["strike", "storm", "congestion", "embargo", "shortage", "other"] = Field(
        ..., description="Category of disruption event"
    )
    description: str = Field(..., description="Detailed description of the disruption")
    start_date: str | None = Field(
        default=None, description="Start date in ISO YYYY-MM-DD format or null"
    )
    severity: Literal["low", "medium", "high", "critical"] = Field(
        default="medium", description="Estimated disruption severity"
    )


class ExtractionPayload(BaseModel):
    """Structured output expected from LLM extraction step."""

    entities: list[ExtractedEntity] = Field(
        default_factory=list, description="List of recognized entities"
    )
    relationships: list[ExtractedRelationship] = Field(
        default_factory=list, description="List of recognized relationships"
    )
    events: list[DisruptionEvent] = Field(
        default_factory=list, description="List of distinct disruption events"
    )


class RawArticle(BaseModel):
    """Raw article fetched from RSS feed or news dataset."""

    title: str = Field(..., description="Article headline")
    source: str = Field(..., description="News organization or feed source")
    url: str = Field(..., description="Canonical article URL")
    published_date: str = Field(..., description="Publication date formatted as YYYY-MM-DD")
    content: str = Field(..., description="Cleaned full text of article")


class ArticleChunk(BaseModel):
    """Deterministic token chunk of an article for storage in graph and embedding."""

    id: str = Field(..., description="Deterministic chunk ID (hash of url + chunk_index)")
    title: str = Field(..., description="Article headline")
    source: str = Field(..., description="News source name")
    url: str = Field(..., description="Article URL")
    published_date: str = Field(..., description="Publication date YYYY-MM-DD")
    chunk_index: int = Field(..., ge=0, description="Sequential chunk index for article")
    text: str = Field(..., description="Text content of the chunk")
    token_count: int = Field(..., ge=0, description="Number of tokens in chunk")
    previous_chunk_id: str | None = Field(
        default=None, description="ID of preceding chunk for NEXT_CHUNK graph linking"
    )


class ResolvedEntityReference(BaseModel):
    """Resolved entity node reference mapped to existing graph entity."""

    original_name: str = Field(..., description="Original name extracted from article")
    target_id: str = Field(..., description="Matched node id or un_locode in graph")
    target_name: str = Field(..., description="Canonical graph node name")
    target_label: str = Field(..., description="Canonical graph node label")
    resolution_method: Literal["exact", "fuzzy", "embedding", "new"] = Field(
        ..., description="Resolution strategy that produced match"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Match confidence")
