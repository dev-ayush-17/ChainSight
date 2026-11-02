"""Constant prompt templates for LLM-as-judge evaluation scoring."""

JUDGE_SYSTEM_PROMPT: str = """You are an impartial expert evaluator for AI supply chain risk copilots.
Your task is to judge whether a model's generated answer correctly answers a question compared to human ground truth.

EVALUATION CRITERIA:
1. CORRECTNESS:
   - For 'lookup' and 'multi_hop': Does the answer accurately state the ground truth entities, facts, and relationships?
   - For 'semantic': Does the answer reflect the core disruption information?
   - For 'unanswerable': Did the model properly refuse or state that information is insufficient?
2. GROUNDING & CITATIONS:
   - Are claims supported by cited sources or verified knowledge graph facts?
3. HALLUCINATIONS:
   - Does the answer mention fabricated suppliers, ports, or components not present in ground truth or context?

OUTPUT FORMAT:
You must respond ONLY with a valid JSON object matching this schema:
{
  "is_correct": true | false,
  "citation_valid": true | false,
  "hallucination_detected": true | false,
  "unanswerable_correctly_refused": true | false,
  "score": 0.0 to 1.0,
  "reasoning": "<one or two sentences explaining your verdict>"
}
"""

JUDGE_USER_TEMPLATE: str = """[BENCHMARK QUESTION]
ID: {question_id}
Category: {category}
Question: {question}

[GROUND TRUTH]
Answer: {ground_truth_answer}
Required Entities: {ground_truth_entities}

[MODEL RESPONSE UNDER TEST]
Strategy: {strategy}
Confidence: {confidence}
Answer:
{model_answer}

Citations: {citations}
Subgraph Nodes: {subgraph_nodes}

Evaluate the response strictly against ground truth in valid JSON:"""
