"""Unit tests for evaluation benchmark questions loader, baseline RAG, and judge scoring."""

from unittest.mock import MagicMock

from api.models import ChatResponse, Citation
from eval.baseline_rag import query_baseline_rag
from eval.judge import evaluate_response_deterministic
from eval.run_eval import (
    build_summary_report,
    load_benchmark_questions,
    render_markdown_summary,
)
from eval.schemas import (
    BenchmarkEvaluationRow,
    BenchmarkQuestion,
    JudgmentResult,
)


def test_load_benchmark_questions_count_and_distribution() -> None:
    """Verify benchmark questions YAML contains 30 questions matching category distribution."""
    questions = load_benchmark_questions("eval/questions.yaml")
    assert len(questions) == 30

    cat_counts = {}
    for q in questions:
        cat_counts[q.category] = cat_counts.get(q.category, 0) + 1

    assert cat_counts["lookup"] == 8
    assert cat_counts["multi_hop"] == 12
    assert cat_counts["semantic"] == 6
    assert cat_counts["unanswerable"] == 4


def test_evaluate_response_deterministic_unanswerable() -> None:
    """Judge correctly scores proper refusal on unanswerable question."""
    q = BenchmarkQuestion(
        id="U001",
        category="unanswerable",
        question="What is the CEO salary?",
        ground_truth_answer="Refused",
        ground_truth_entities=[],
    )
    resp = ChatResponse(
        answer="I can only assist with supply chain risk analysis.",
        citations=[],
        subgraph_node_ids=[],
        subgraph_edge_ids=[],
        retrieval_strategy="refused",
        confidence="none",
        latency_ms=10,
    )

    judgment = evaluate_response_deterministic(q, resp)
    assert judgment.is_correct is True
    assert judgment.unanswerable_correctly_refused is True
    assert judgment.score == 1.0


def test_evaluate_response_deterministic_entities_matching() -> None:
    """Judge matches ground truth entities and computes normalized score."""
    q = BenchmarkQuestion(
        id="L001",
        category="lookup",
        question="Which country is supplier SUP-007 located in?",
        ground_truth_answer="Taiwan",
        ground_truth_entities=["SUP-007", "Taiwan"],
    )
    resp = ChatResponse(
        answer="Supplier SUP-007 is based in Taiwan (TW).",
        citations=[
            Citation(
                source_id="source_1",
                title="Suppliers",
                source="Knowledge Graph",
                url="#",
                date="2025-01-01",
            )
        ],
        subgraph_node_ids=["sup_007", "c_TWN"],
        subgraph_edge_ids=[],
        retrieval_strategy="lookup",
        confidence="high",
        latency_ms=25,
    )

    judgment = evaluate_response_deterministic(q, resp)
    assert judgment.is_correct is True
    assert judgment.score > 0.8
    assert judgment.citation_valid is True
    assert judgment.hallucination_detected is False


def test_query_baseline_rag_with_mock_driver() -> None:
    """Baseline vector RAG executes query and returns pure vector response."""
    driver = MagicMock()
    session_mock = MagicMock()
    driver.session.return_value.__enter__.return_value = session_mock
    session_mock.run.return_value.data.return_value = [
        {
            "chunk_id": "art_101",
            "title": "Asian Maritime Bottlenecks",
            "source": "Maritime News",
            "published_date": "2025-06-01",
            "text": "Port of Shanghai reports delays.",
            "score": 0.85,
            "mentioned_ids": [],
        }
    ]

    resp = query_baseline_rag(driver, "Port of Shanghai delays")
    assert resp.retrieval_strategy == "semantic"
    assert len(resp.subgraph_node_ids) == 0
    assert len(resp.subgraph_edge_ids) == 0
    assert len(resp.citations) == 1


def test_build_summary_report_and_render_markdown() -> None:
    """Build summary report aggregates metrics and computes positive multi-hop delta."""
    resp_correct = ChatResponse(
        answer="Grounded answer with Taiwan and SUP-007.",
        citations=[
            Citation(
                source_id="s1",
                title="Doc",
                source="Source",
                url="#",
                date="2025-01-01",
            )
        ],
        subgraph_node_ids=["SUP-007"],
        subgraph_edge_ids=[],
        retrieval_strategy="impact_traversal",
        confidence="high",
        latency_ms=50,
    )
    resp_incorrect = ChatResponse(
        answer="I don't have enough information.",
        citations=[],
        subgraph_node_ids=[],
        subgraph_edge_ids=[],
        retrieval_strategy="refused",
        confidence="none",
        latency_ms=40,
    )

    j_correct = JudgmentResult(
        is_correct=True,
        citation_valid=True,
        hallucination_detected=False,
        unanswerable_correctly_refused=False,
        score=0.95,
        reasoning="Accurate",
    )
    j_incorrect = JudgmentResult(
        is_correct=False,
        citation_valid=False,
        hallucination_detected=False,
        unanswerable_correctly_refused=False,
        score=0.0,
        reasoning="Failed to traverse",
    )

    g_rows = [
        BenchmarkEvaluationRow(
            question_id="M001",
            category="multi_hop",
            question="Port strike impact?",
            system="graph_rag",
            response=resp_correct,
            judgment=j_correct,
        )
    ]
    b_rows = [
        BenchmarkEvaluationRow(
            question_id="M001",
            category="multi_hop",
            question="Port strike impact?",
            system="baseline_vector_rag",
            response=resp_incorrect,
            judgment=j_incorrect,
        )
    ]

    report = build_summary_report(g_rows, b_rows)
    assert report.graph_rag_correctness == 1.0
    assert report.baseline_rag_correctness == 0.0
    assert report.multi_hop_delta_percentage_points == 100.0

    markdown = render_markdown_summary(report)
    assert "# ChainSight Benchmark Evaluation Report" in markdown
    assert "Multi-Hop Correctness" in markdown
    assert "+100.0pp" in markdown
