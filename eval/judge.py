"""LLM-as-judge and deterministic evaluation scoring for benchmark question responses."""

import json
import logging
import re

from google import genai
from google.genai import types

from api.config import Settings, get_settings
from api.models import ChatResponse
from eval.prompts import JUDGE_SYSTEM_PROMPT, JUDGE_USER_TEMPLATE
from eval.schemas import BenchmarkQuestion, JudgmentResult

logger = logging.getLogger(__name__)


def evaluate_response_deterministic(
    question: BenchmarkQuestion,
    response: ChatResponse,
) -> JudgmentResult:
    """Evaluate response using deterministic string matching and rule-based verification."""
    answer_text = response.answer.lower()

    # 1. Evaluate Unanswerable Questions
    if question.category == "unanswerable":
        is_refused = (
            response.retrieval_strategy == "refused"
            or response.confidence == "none"
            or "don't have enough information" in answer_text
            or "can only assist with supply chain" in answer_text
            or "outside supply chain" in answer_text
        )
        return JudgmentResult(
            is_correct=is_refused,
            citation_valid=True,
            hallucination_detected=False,
            unanswerable_correctly_refused=is_refused,
            score=1.0 if is_refused else 0.0,
            reasoning=(
                "Query was properly refused as out-of-domain."
                if is_refused
                else "Model attempted to answer out-of-domain query without proper refusal."
            ),
        )

    # 2. Check Ground Truth Entities
    required_entities = question.ground_truth_entities
    matched_entities = []
    subgraph_nodes = [n.lower() for n in response.subgraph_node_ids]

    for ent in required_entities:
        ent_lower = ent.lower()
        if ent_lower in answer_text or any(ent_lower in n for n in subgraph_nodes):
            matched_entities.append(ent)

    entity_recall = len(matched_entities) / max(1, len(required_entities))
    has_key_facts = entity_recall >= 0.5 or question.ground_truth_answer.lower() in answer_text

    # 3. Check Grounding & Citations
    citation_valid = len(response.citations) > 0 or len(response.subgraph_node_ids) > 0

    # 4. Check Hallucinations (Ungrounded IDs)
    id_pattern = re.compile(r"\b(SUP-\d{3}|CMP-\d{4}|PRD-\d{3})\b", re.IGNORECASE)
    mentioned_ids = id_pattern.findall(response.answer)
    known_ground_truth_ids = {e.upper() for e in required_entities if "-" in e}
    subgraph_ids = {s.upper() for s in response.subgraph_node_ids}

    hallucination_detected = False
    for mid in mentioned_ids:
        mid_upper = mid.upper()
        if mid_upper not in known_ground_truth_ids and mid_upper not in subgraph_ids:
            hallucination_detected = True
            break

    is_correct = has_key_facts and response.retrieval_strategy != "refused"
    score = 0.0
    if is_correct:
        score += 0.7 * entity_recall
        if citation_valid:
            score += 0.2
        if not hallucination_detected:
            score += 0.1
    score = min(1.0, max(0.0, score))

    reasoning = (
        f"Matched {len(matched_entities)}/{len(required_entities)} ground truth entities "
        f"({', '.join(matched_entities) if matched_entities else 'none'}). "
        f"Citations present: {citation_valid}. Strategy: {response.retrieval_strategy}."
    )

    return JudgmentResult(
        is_correct=is_correct,
        citation_valid=citation_valid,
        hallucination_detected=hallucination_detected,
        unanswerable_correctly_refused=False,
        score=score,
        reasoning=reasoning,
    )


def evaluate_response_llm(
    question: BenchmarkQuestion,
    response: ChatResponse,
    api_key: str,
    model_name: str = "gemini-2.5-flash",
) -> JudgmentResult:
    """Evaluate response against ground truth using Google Gemini LLM-as-judge."""
    client = genai.Client(api_key=api_key)
    formatted_prompt = JUDGE_USER_TEMPLATE.format(
        question_id=question.id,
        category=question.category,
        question=question.question,
        ground_truth_answer=question.ground_truth_answer,
        ground_truth_entities=json.dumps(question.ground_truth_entities),
        strategy=response.retrieval_strategy,
        confidence=response.confidence,
        model_answer=response.answer,
        citations=json.dumps([c.model_dump() for c in response.citations]),
        subgraph_nodes=json.dumps(response.subgraph_node_ids),
    )

    result = client.models.generate_content(
        model=model_name,
        contents=formatted_prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=JudgmentResult,
            system_instruction=JUDGE_SYSTEM_PROMPT,
            temperature=0.0,
        ),
    )

    data = json.loads(result.text or "{}")
    return JudgmentResult.model_validate(data)


def judge_response(
    question: BenchmarkQuestion,
    response: ChatResponse,
    settings: Settings | None = None,
) -> JudgmentResult:
    """Judge a model response using configured LLM with automatic deterministic fallback."""
    cfg = settings or get_settings()

    if cfg.gemini_api_key and cfg.gemini_api_key.strip():
        try:
            return evaluate_response_llm(question, response, cfg.gemini_api_key)
        except Exception as err:
            logger.warning("LLM judge call failed (%s); using deterministic evaluation.", err)

    return evaluate_response_deterministic(question, response)
