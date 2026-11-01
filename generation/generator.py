"""Grounded response generator with hallucination guardrails and fallback synthesis."""

import json
import logging
import re
import time

from google import genai
from google.genai import types

from api.config import Settings, get_settings
from api.models import ChatResponse, Citation
from generation.prompts import (
    INSUFFICIENT_INFO_ANSWER,
    REFUSAL_ANSWER,
    SYSTEM_GENERATOR_PROMPT,
    USER_GENERATION_TEMPLATE,
)
from generation.schemas import LLMGenerationResponse
from retrieval.context_assembler import AssembledContext

logger = logging.getLogger(__name__)


def synthesize_answer_deterministic(assembled_context: AssembledContext) -> LLMGenerationResponse:
    """Synthesize grounded analytical response deterministically from structured context."""
    if assembled_context.strategy == "refused":
        return LLMGenerationResponse(
            answer=REFUSAL_ANSWER,
            cited_sources=[],
            reasoning_summary="Question falls outside supply chain domain scope.",
            confidence="none",
        )

    if assembled_context.is_empty or not assembled_context.structured_facts:
        if assembled_context.citations:
            # We have article passages
            citations_text = ", ".join(f"[{c.source_id}]" for c in assembled_context.citations)
            cited_ids = [c.source_id for c in assembled_context.citations]
            first_c = assembled_context.citations[0]
            ans = (
                f"Based on recent news reporting {citations_text}, active disruptions have been "
                f"identified in related maritime corridors (reported by {first_c.source} on "
                f"{first_c.date}). Details are highlighted in the source documentation."
            )
            return LLMGenerationResponse(
                answer=ans,
                cited_sources=cited_ids,
                reasoning_summary="Answer synthesized from retrieved article chunks.",
                confidence="medium",
            )
        return LLMGenerationResponse(
            answer=INSUFFICIENT_INFO_ANSWER,
            cited_sources=[],
            reasoning_summary="No relevant graph entities or news records found in knowledge base.",
            confidence="none",
        )

    # We have structured graph facts
    bullet_points = "\n".join(assembled_context.structured_facts)
    cited_ids = [c.source_id for c in assembled_context.citations]
    citation_suffix = ""
    if cited_ids:
        citation_refs = ", ".join(f"[{cid}]" for cid in cited_ids)
        citation_suffix = (
            f"\n\n**Corroborating Disruption News:** Cross-referenced with {citation_refs}."
        )

    summary = (
        f"### Supply Chain Risk Assessment\n\n"
        f"Based on grounded knowledge graph traversal for **'{assembled_context.raw_query}'**, "
        f"the following entities and risk exposure metrics were identified:\n\n"
        f"{bullet_points}{citation_suffix}"
    )

    strategy = assembled_context.strategy
    confidence = "high" if strategy in ["impact_traversal", "lookup"] else "medium"
    fact_count = len(assembled_context.structured_facts)

    return LLMGenerationResponse(
        answer=summary,
        cited_sources=cited_ids,
        reasoning_summary=f"Direct multi-hop traversal with {fact_count} graph facts.",
        confidence=confidence,
    )


def generate_answer_llm(
    assembled_context: AssembledContext,
    api_key: str,
    model_name: str = "gemini-2.5-flash",
) -> LLMGenerationResponse:
    """Call Google Gemini model to produce structured grounded analytical response."""
    client = genai.Client(api_key=api_key)
    prompt = USER_GENERATION_TEMPLATE.format(
        query=assembled_context.raw_query,
        context=assembled_context.formatted_prompt_context,
    )

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=LLMGenerationResponse,
            system_instruction=SYSTEM_GENERATOR_PROMPT,
            temperature=0.1,
        ),
    )

    raw_text = response.text or "{}"
    data = json.loads(raw_text)
    return LLMGenerationResponse.model_validate(data)


def verify_hallucinations(answer: str, assembled_context: AssembledContext) -> bool:
    """Verify that named IDs mentioned in answer (e.g. SUP-xxx, PRD-xxx) exist in context."""
    id_pattern = re.compile(r"\b(SUP-\d{3}|CMP-\d{4}|PRD-\d{3}|FAC-\d{3})\b", re.IGNORECASE)
    answer_ids = set(id_pattern.findall(answer.upper()))
    if not answer_ids:
        return True

    context_str = assembled_context.formatted_prompt_context.upper()
    query_str = assembled_context.raw_query.upper()

    for entity_id in answer_ids:
        if entity_id not in context_str and entity_id not in query_str:
            logger.warning("Hallucination guardrail flagged ungrounded ID in answer: %s", entity_id)
            return False
    return True


def generate_copilot_response(
    assembled_context: AssembledContext,
    settings: Settings | None = None,
    start_time: float | None = None,
) -> ChatResponse:
    """Generate final grounded ChatResponse with citations, confidence, and latency."""
    t0 = start_time if start_time is not None else time.perf_counter()
    cfg = settings or get_settings()

    # Refused queries
    if assembled_context.strategy == "refused":
        latency = int((time.perf_counter() - t0) * 1000)
        return ChatResponse(
            answer=REFUSAL_ANSWER,
            citations=[],
            subgraph_node_ids=[],
            subgraph_edge_ids=[],
            retrieval_strategy="refused",
            confidence="none",
            latency_ms=latency,
        )

    # Empty context
    if assembled_context.is_empty:
        latency = int((time.perf_counter() - t0) * 1000)
        return ChatResponse(
            answer=INSUFFICIENT_INFO_ANSWER,
            citations=[],
            subgraph_node_ids=[],
            subgraph_edge_ids=[],
            retrieval_strategy=assembled_context.strategy,
            confidence="none",
            latency_ms=latency,
        )

    # Attempt LLM generation if configured, otherwise use deterministic synthesis
    gen_result: LLMGenerationResponse | None = None
    if cfg.gemini_api_key and cfg.gemini_api_key.strip():
        try:
            gen_result = generate_answer_llm(assembled_context, cfg.gemini_api_key)
        except Exception as err:
            logger.warning(
                "LLM generation call failed (%s); falling back to rule-based synthesis.", err
            )

    if gen_result is None:
        gen_result = synthesize_answer_deterministic(assembled_context)

    # Apply Hallucination Verification Guardrail
    if not verify_hallucinations(gen_result.answer, assembled_context):
        gen_result = synthesize_answer_deterministic(assembled_context)
        gen_result.confidence = "low"

    # Filter citations to those cited or relevant
    used_citations: list[Citation] = []
    if assembled_context.citations:
        if gen_result.cited_sources:
            cited_set = set(gen_result.cited_sources)
            used_citations = [c for c in assembled_context.citations if c.source_id in cited_set]
        if not used_citations:
            used_citations = assembled_context.citations

    latency = int((time.perf_counter() - t0) * 1000)

    return ChatResponse(
        answer=gen_result.answer,
        citations=used_citations,
        subgraph_node_ids=assembled_context.subgraph_node_ids,
        subgraph_edge_ids=assembled_context.subgraph_edge_ids,
        retrieval_strategy=assembled_context.strategy,
        confidence=gen_result.confidence,
        latency_ms=latency,
    )
