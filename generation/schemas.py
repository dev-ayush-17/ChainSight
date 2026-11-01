"""Pydantic schemas for LLM generation structured outputs."""

from typing import Literal

from pydantic import BaseModel, Field

ConfidenceLevel = Literal["high", "medium", "low", "none"]


class LLMGenerationResponse(BaseModel):
    """Structured JSON schema output requested from LLM generation call."""

    answer: str = Field(..., description="Grounded markdown answer text")
    cited_sources: list[str] = Field(
        default_factory=list, description="List of source IDs cited in answer"
    )
    reasoning_summary: str = Field(
        ..., description="Brief one-sentence explanation of the analytical chain"
    )
    confidence: ConfidenceLevel = Field(
        default="medium", description="Confidence assessment in response"
    )
