"""LLM-based entity and relationship extraction pipeline with schema validation and fallback."""

import json
import logging
import re
from typing import Literal

from google import genai
from google.genai import types

from api.config import Settings, get_settings
from extraction.prompts import (
    EXTRACTION_FEW_SHOT_EXAMPLES,
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_USER_PROMPT_TEMPLATE,
)
from extraction.schemas import (
    ArticleChunk,
    DisruptionEvent,
    ExtractedEntity,
    ExtractedRelationship,
    ExtractionPayload,
)

logger = logging.getLogger(__name__)


def extract_fallback_rule_based(chunk: ArticleChunk) -> ExtractionPayload:
    """Extract entities, events, and relationships using deterministic rule-based matching."""
    text = chunk.text
    entities: list[ExtractedEntity] = []
    relationships: list[ExtractedRelationship] = []
    events: list[DisruptionEvent] = []

    port_patterns = [
        ("Port of Shanghai", "Port"),
        ("Port of Singapore", "Port"),
        ("Port of Ningbo-Zhoushan", "Port"),
        ("Port of Ningbo", "Port"),
        ("Port of Shenzhen", "Port"),
        ("Port of Busan", "Port"),
        ("Port of Los Angeles", "Port"),
        ("Port of Long Beach", "Port"),
        ("Port of Rotterdam", "Port"),
        ("Port of Antwerp-Bruges", "Port"),
        ("Port of Antwerp", "Port"),
        ("Port of Hamburg", "Port"),
        ("Port of Kaohsiung", "Port"),
        ("Port of Tokyo", "Port"),
        ("Port of Baltimore", "Port"),
        ("Port of Montreal", "Port"),
        ("Panama Canal", "Port"),
    ]

    country_patterns = [
        ("China", "Country"),
        ("Taiwan", "Country"),
        ("United States", "Country"),
        ("South Korea", "Country"),
        ("Japan", "Country"),
        ("Germany", "Country"),
        ("Netherlands", "Country"),
        ("Belgium", "Country"),
        ("Singapore", "Country"),
        ("Vietnam", "Country"),
        ("Malaysia", "Country"),
        ("France", "Country"),
        ("Canada", "Country"),
        ("Indonesia", "Country"),
    ]

    component_patterns = [
        ("DDR5 DRAM", "Component"),
        ("LPDDR5X", "Component"),
        ("microprocessor", "Component"),
        ("microcontroller", "Component"),
        ("power management IC", "Component"),
        ("OLED Panel", "Component"),
        ("display panel", "Component"),
        ("camera sensor", "Component"),
        ("lithium-ion battery cell", "Component"),
        ("battery cell", "Component"),
        ("multilayer PCB", "Component"),
        ("printed circuit board", "Component"),
        ("PCB", "Component"),
    ]

    found_entities: dict[str, str] = {}
    for name, label in port_patterns + country_patterns + component_patterns:
        if re.search(rf"\b{re.escape(name)}\b", text, re.IGNORECASE):
            found_entities[name] = label
            entities.append(ExtractedEntity(label=label, name=name, properties={}))

    event_type: Literal["strike", "storm", "congestion", "embargo", "shortage", "other"] = "other"
    severity: Literal["low", "medium", "high", "critical"] = "medium"

    lower_text = text.lower()
    if "strike" in lower_text or "labor action" in lower_text:
        event_type = "strike"
        severity = "high"
    elif "typhoon" in lower_text or "hurricane" in lower_text or "storm" in lower_text:
        event_type = "storm"
        severity = "high"
    elif "congestion" in lower_text or "bottleneck" in lower_text or "delay" in lower_text:
        event_type = "congestion"
        severity = "medium"
    elif "shortage" in lower_text:
        event_type = "shortage"
        severity = "critical"
    elif "earthquake" in lower_text:
        event_type = "earthquake"
        severity = "critical"

    event_id = f"evt_{abs(hash(chunk.id)) % 100000:05d}"
    matched_event = DisruptionEvent(
        id=event_id,
        event_type=event_type if event_type != "earthquake" else "other",
        description=chunk.title,
        start_date=chunk.published_date,
        severity=severity,
    )
    events.append(matched_event)

    entities.append(
        ExtractedEntity(
            label="Event",
            name=chunk.title,
            properties={"type": event_type, "severity": severity},
        )
    )

    for ent_name, ent_label in found_entities.items():
        relationships.append(
            ExtractedRelationship(
                type="AFFECTS",
                from_name=chunk.title,
                from_label="Event",
                to_name=ent_name,
                to_label=ent_label,
                properties={"confidence": 0.85},
            )
        )
        relationships.append(
            ExtractedRelationship(
                type="MENTIONS",
                from_name=chunk.id,
                from_label="Article",
                to_name=ent_name,
                to_label=ent_label,
                properties={"confidence": 0.90},
            )
        )

    return ExtractionPayload(entities=entities, relationships=relationships, events=events)


def extract_from_chunk_hf(
    chunk: ArticleChunk,
    api_key: str,
    model: str,
) -> ExtractionPayload:
    """Execute LLM structured extraction using Hugging Face Inference API."""
    from generation.hf_client import generate_json_response

    formatted_user_prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(
        title=chunk.title,
        source=chunk.source,
        published_date=chunk.published_date,
        text=chunk.text,
    )
    full_prompt = f"{EXTRACTION_FEW_SHOT_EXAMPLES}\n\n{formatted_user_prompt}"

    payload_data = generate_json_response(
        system_prompt=EXTRACTION_SYSTEM_PROMPT,
        user_message=full_prompt,
        api_key=api_key,
        model=model,
        temperature=0.0,
    )
    if not payload_data or not isinstance(payload_data, dict):
        raise ValueError("Empty or non-dict response from Hugging Face for extraction")

    return ExtractionPayload.model_validate(payload_data)


def extract_from_chunk_gemini(
    chunk: ArticleChunk,
    api_key: str,
    model_name: str = "gemini-2.5-flash",
) -> ExtractionPayload:
    """Execute LLM structured extraction using Google GenAI SDK with JSON schema."""
    client = genai.Client(api_key=api_key)
    formatted_user_prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(
        title=chunk.title,
        source=chunk.source,
        published_date=chunk.published_date,
        text=chunk.text,
    )
    full_prompt = f"{EXTRACTION_FEW_SHOT_EXAMPLES}\n\n{formatted_user_prompt}"

    response = client.models.generate_content(
        model=model_name,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ExtractionPayload,
            system_instruction=EXTRACTION_SYSTEM_PROMPT,
            temperature=0.0,
        ),
    )

    raw_text = response.text or "{}"
    payload_data = json.loads(raw_text)
    return ExtractionPayload.model_validate(payload_data)


def extract_from_chunk(
    chunk: ArticleChunk,
    settings: Settings | None = None,
    max_retries: int = 2,
) -> ExtractionPayload:
    """Run extraction pipeline on article chunk with LLM and automatic fallback handling."""
    cfg = settings or get_settings()

    # 1. Try Hugging Face if configured
    if cfg.hf_api_key and cfg.hf_api_key.strip():
        for attempt in range(max_retries + 1):
            try:
                return extract_from_chunk_hf(chunk, cfg.hf_api_key, cfg.hf_model)
            except Exception as err:
                logger.warning(
                    "HF extraction failed on chunk %s (attempt %d/%d): %s",
                    chunk.id,
                    attempt + 1,
                    max_retries + 1,
                    err,
                )
                if attempt == max_retries:
                    break

    # 2. Try Gemini if configured
    if cfg.gemini_api_key and cfg.gemini_api_key.strip():
        for attempt in range(max_retries + 1):
            try:
                return extract_from_chunk_gemini(chunk, cfg.gemini_api_key)
            except Exception as err:
                logger.warning(
                    "Gemini extraction failed on chunk %s (attempt %d/%d): %s",
                    chunk.id,
                    attempt + 1,
                    max_retries + 1,
                    err,
                )
                if attempt == max_retries:
                    break

    # 3. Deterministic fallback
    return extract_fallback_rule_based(chunk)


def run_extraction_batch(
    chunks: list[ArticleChunk],
    settings: Settings | None = None,
) -> list[tuple[ArticleChunk, ExtractionPayload]]:
    """Execute extraction pipeline over a collection of article chunks."""
    cfg = settings or get_settings()
    results: list[tuple[ArticleChunk, ExtractionPayload]] = []

    for _idx, chunk in enumerate(chunks, start=1):
        payload = extract_from_chunk(chunk, settings=cfg)
        results.append((chunk, payload))

    return results
