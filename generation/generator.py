"""Grounded response generator with hallucination guardrails and multi-LLM fallback support."""

import json
import logging
import re
import time

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


def _format_executive_briefing(
    raw_query: str,
    facts: list[str],
    citations: list[Citation],
) -> str:
    """Format structured graph facts into an executive-level risk briefing."""
    parsed_records: list[dict[str, str]] = []
    for f in facts:
        clean = f.replace("- [Graph Fact] ", "").strip()
        rec: dict[str, str] = {}
        for part in clean.split(" | "):
            if ":" in part:
                k, v = part.split(":", 1)
                rec[k.strip().lower()] = v.strip()
        if rec:
            parsed_records.append(rec)

    # Extract key entities from parsed records
    products: dict[str, float] = {}
    product_critical_cmps: dict[str, set[str]] = {}
    critical_cmps: set[str] = set()
    sole_sourced_cmps: set[str] = set()
    suppliers: set[str] = set()
    ports: set[str] = set()

    for r in parsed_records:
        prd = r.get("product name") or r.get("product id")
        rev_str = r.get("annual revenue usd") or r.get("revenue") or r.get("exposure")
        cmp_name = r.get("component name") or r.get("component id")
        sup_name = r.get("supplier name") or r.get("supplier id")
        port_name = r.get("port name") or r.get("port id")

        if prd:
            if prd not in products:
                rev_val = 0.0
                if rev_str:
                    try:
                        clean_rev = rev_str.replace("$", "").replace(",", "").replace("M", "000000")
                        rev_val = float(clean_rev)
                    except ValueError:
                        rev_val = 0.0
                products[prd] = rev_val
                product_critical_cmps[prd] = set()

            if cmp_name and (r.get("is critical") == "True" or r.get("is_critical") == "True"):
                product_critical_cmps[prd].add(cmp_name)

        if cmp_name:
            if r.get("is critical") == "True" or r.get("is_critical") == "True":
                critical_cmps.add(cmp_name)
            if r.get("is sole sourced") == "True" or r.get("is_sole_sourced") == "True":
                sole_sourced_cmps.add(cmp_name)

        if sup_name:
            suppliers.add(sup_name)
        if port_name:
            ports.add(port_name)

    citation_suffix = ""
    if citations:
        citation_refs = ", ".join(f"[{c.source_id}]" for c in citations)
        citation_suffix = f"\n\n**Corroborating Disruption News:** Sourced via {citation_refs}."

    if products:
        total_rev = sum(products.values())
        if ports:
            disruption_focus = next(iter(ports))
        elif suppliers:
            disruption_focus = next(iter(suppliers))
        else:
            disruption_focus = "Identified Node"

        rev_formatted = f"${total_rev:,.2f}" if total_rev > 0 else "Substantial Portfolio Exposure"
        crit_str = (
            ", ".join(sorted(critical_cmps))
            if critical_cmps
            else "No single critical components flagged."
        )
        sole_str = (
            ", ".join(sorted(sole_sourced_cmps))
            if sole_sourced_cmps
            else "All components have secondary sourcing registered."
        )
        sup_str = ", ".join(sorted(suppliers)) if suppliers else "Direct facility linkages."

        lines = [
            "### Supply Chain Risk Assessment: Disruption Impact Analysis\n",
            (
                f"**Executive Summary:** Disruption at **{disruption_focus}** directly exposes "
                f"**{len(products)}** downstream product lines with cumulative revenue of "
                f"**{rev_formatted}** across **{len(suppliers)}** supplier dependencies.\n"
            ),
            "#### 📊 Revenue Exposure by Product Family",
            "| Impacted Product | Annual Revenue | Critical Component Exposure |",
            "|---|---|---|",
        ]
        for prd, rev in sorted(products.items(), key=lambda x: x[1], reverse=True):
            cmps = ", ".join(sorted(product_critical_cmps.get(prd, []))) or "Standard BOM"
            lines.append(f"| {prd} | ${rev:,.2f} | {cmps} |")

        lines.extend(
            [
                "\n#### ⚠️ Critical Bottlenecks & Exposure Findings",
                f"- **High-Risk Components:** {crit_str}",
                f"- **Sole-Sourced Vulnerabilities:** {sole_str}",
                f"- **Impacted Suppliers:** {sup_str}",
                "\n#### 🔄 Recommended Strategic Action Items",
                "1. **Safety Stock Buffer:** Allocate 30-day reserves for critical parts.",
                "2. **Alternative Port Logistics:** Route freight through alternate ports.",
                "3. **Vendor Auditing:** Initiate priority status checks with primary suppliers.",
                "4. **Second-Source Sourcing:** Fast-track qualification of alternate vendors.",
                "5. **Customer Notification:** Proactively inform customers of potential delays.",
            ]
        )
        return "\n".join(lines) + citation_suffix

    # Check for alternative supplier facts
    if any("alt supplier" in r or "alternative" in str(r) for r in parsed_records):
        lines = [
            "### Supply Chain Risk Assessment: Alternative Sourcing\n",
            "**Executive Summary:** Qualified alternative suppliers for component shortage:\n",
            "| Component | Qualified Alternative Supplier | Lead Time | Country |",
            "|---|---|---|---|",
        ]
        for r in parsed_records:
            cmp_v = r.get("component name") or r.get("component id") or "Component"
            alt_s = r.get("alt supplier name") or r.get("supplier name") or "Supplier"
            lt = r.get("lead time days") or r.get("lead time") or "Standard"
            country = r.get("country") or "Global"
            lines.append(f"| {cmp_v} | {alt_s} | {lt} | {country} |")
        lines.extend(
            [
                "\n#### 🔄 Recommendation",
                "Begin preliminary purchase order validation with verified secondary suppliers.",
            ]
        )
        return "\n".join(lines) + citation_suffix

    # Standard fallback with structured markdown bullet presentation
    bullet_points = "\n".join(facts)
    return (
        f"### Supply Chain Risk Assessment\n\n"
        f"Based on grounded knowledge graph traversal for **'{raw_query}'**, "
        f"the following entities and risk exposure metrics were identified:\n\n"
        f"{bullet_points}{citation_suffix}"
    )


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

    summary = _format_executive_briefing(
        raw_query=assembled_context.raw_query,
        facts=assembled_context.structured_facts,
        citations=assembled_context.citations,
    )
    cited_ids = [c.source_id for c in assembled_context.citations]
    strategy = assembled_context.strategy
    confidence = "high" if strategy in ["impact_traversal", "lookup"] else "medium"
    fact_count = len(assembled_context.structured_facts)

    return LLMGenerationResponse(
        answer=summary,
        cited_sources=cited_ids,
        reasoning_summary=f"Direct multi-hop traversal with {fact_count} graph facts.",
        confidence=confidence,
    )


def generate_answer_hf(
    assembled_context: AssembledContext,
    api_key: str,
    model: str,
) -> LLMGenerationResponse:
    """Call HuggingFace Inference API to produce structured grounded analytical response."""
    from generation.hf_client import generate_json_response

    user_message = USER_GENERATION_TEMPLATE.format(
        query=assembled_context.raw_query,
        context=assembled_context.formatted_prompt_context,
    )

    data = generate_json_response(
        system_prompt=SYSTEM_GENERATOR_PROMPT,
        user_message=user_message,
        api_key=api_key,
        model=model,
        temperature=0.1,
    )

    if not data:
        return synthesize_answer_deterministic(assembled_context)

    try:
        return LLMGenerationResponse(
            answer=str(data.get("answer", INSUFFICIENT_INFO_ANSWER)),
            cited_sources=[str(s) for s in data.get("cited_sources", [])],
            reasoning_summary=str(data.get("reasoning_summary", "")),
            confidence=data.get("confidence", "medium"),  # type: ignore[arg-type]
        )
    except Exception as e:
        logger.warning("Failed to parse HF response into LLMGenerationResponse: %s", e)
        return synthesize_answer_deterministic(assembled_context)


def generate_answer_gemini(
    assembled_context: AssembledContext,
    api_key: str,
    model_name: str = "gemini-2.5-flash",
) -> LLMGenerationResponse:
    """Call Google Gemini model to produce structured grounded analytical response."""
    from google import genai
    from google.genai import types

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
    """Verify that named IDs mentioned in answer exist in context."""
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
    """Generate final grounded ChatResponse with citations, confidence, and latency.

    LLM priority: HuggingFace (if HF_API_KEY set) → Gemini (if GEMINI_API_KEY set)
    → deterministic rule-based synthesis (always available).
    """
    t0 = start_time if start_time is not None else time.perf_counter()
    cfg = settings or get_settings()

    # Short-circuit for refused queries
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

    # Short-circuit for empty context
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

    # Attempt LLM generation — HF first, then Gemini, then deterministic
    gen_result: LLMGenerationResponse | None = None

    if cfg.hf_api_key and cfg.hf_api_key.strip():
        try:
            gen_result = generate_answer_hf(assembled_context, cfg.hf_api_key, cfg.hf_model)
            logger.info("Generated answer via HuggingFace model: %s", cfg.hf_model)
        except Exception as err:
            logger.warning("HuggingFace generation failed (%s); trying next fallback.", err)

    if gen_result is None and cfg.gemini_api_key and cfg.gemini_api_key.strip():
        try:
            gen_result = generate_answer_gemini(assembled_context, cfg.gemini_api_key)
            logger.info("Generated answer via Gemini.")
        except Exception as err:
            logger.warning(
                "Gemini generation failed (%s); falling back to deterministic synthesis.", err
            )

    if gen_result is None:
        gen_result = synthesize_answer_deterministic(assembled_context)
        logger.info("Using deterministic synthesis (no LLM configured).")

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
