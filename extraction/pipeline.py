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
        ("lithium battery", "Component"),
        ("aluminum chassis", "Component"),
        ("titanium frame", "Component"),
        ("semiconductor", "Component"),
        ("silicon wafer", "Component"),
        ("resistor", "Component"),
        ("capacitor", "Component"),
    ]

    supplier_patterns = [
        ("TSMC", "Supplier"),
        ("United Microelectronics", "Supplier"),
        ("ASE Technology", "Supplier"),
        ("Samsung", "Supplier"),
        ("Foxconn", "Supplier"),
    ]

    found_names: set[str] = set()

    for pattern, label in port_patterns + country_patterns + component_patterns + supplier_patterns:
        if (
            re.search(r"\b" + re.escape(pattern) + r"\b", text, re.IGNORECASE)
            and pattern not in found_names
        ):
            entities.append(ExtractedEntity(label=label, name=pattern, properties={}))
            found_names.add(pattern)

    event_type: Literal["strike", "storm", "congestion", "embargo", "shortage", "other"] = "other"
    severity: Literal["low", "medium", "high", "critical"] = "medium"

    if re.search(r"\b(strike|walkout|picket|labor dispute)\b", text, re.IGNORECASE):
        event_type = "strike"
        severity = "high"
    elif re.search(r"\b(typhoon|storm|flood|earthquake|blizzard)\b", text, re.IGNORECASE):
        event_type = "storm"
        severity = "critical"
    elif re.search(r"\b(congestion|backlog|delay|queues|bottleneck)\b", text, re.IGNORECASE):
        event_type = "congestion"
        severity = "medium"
    elif re.search(r"\b(shortage|allocation|deficit|yield loss)\b", text, re.IGNORECASE):
        event_type = "shortage"
        severity = "high"
    elif re.search(r"\b(embargo|export control|sanction|restriction)\b", text, re.IGNORECASE):
        event_type = "embargo"
        severity = "high"

    event_desc = f"{event_type.capitalize()} disruption: {chunk.title}"
    event = DisruptionEvent(
        id=f"evt_{chunk.id[:12]}",
        event_type=event_type,
        description=event_desc,
        start_date=chunk.published_date,
        severity=severity,
    )
    events.append(event)

    for ent in entities:
        if ent.label in ["Port", "Supplier", "Country"]:
            relationships.append(
                ExtractedRelationship(
                    type="AFFECTS",
                    from_name=event_desc,
                    from_label="Event",
                    to_name=ent.name,
                    to_label=ent.label,
                    confidence=0.9,
                )
            )

    return ExtractionPayload(entities=entities, relationships=relationships, events=events)


def extract_from_chunk_llm(
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

    if not cfg.gemini_api_key or cfg.gemini_api_key.strip() == "":
        return extract_fallback_rule_based(chunk)

    for attempt in range(max_retries + 1):
        try:
            return extract_from_chunk_llm(chunk, cfg.gemini_api_key)
        except Exception as err:
            logger.warning(
                "LLM extraction failed on chunk %s (attempt %d/%d): %s",
                chunk.id,
                attempt + 1,
                max_retries + 1,
                err,
            )
            if attempt == max_retries:
                logger.info(
                    "Falling back to deterministic rule-based extractor for chunk %s", chunk.id
                )
                return extract_fallback_rule_based(chunk)

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
