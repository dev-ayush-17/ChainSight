"""Pydantic models for evaluation benchmark dataset, judge scoring, and comparative metrics."""

from typing import Literal

from pydantic import BaseModel, Field

from api.models import ChatResponse

SystemType = Literal["graph_rag", "baseline_vector_rag"]
CategoryType = Literal["lookup", "multi_hop", "semantic", "unanswerable"]


class BenchmarkQuestion(BaseModel):
    """Ground truth benchmark question definition."""

    id: str = Field(..., description="Unique question ID (e.g. L001, M001)")
    category: CategoryType = Field(..., description="Benchmark category")
    question: str = Field(..., description="Natural language question text")
    ground_truth_answer: str = Field(..., description="Human-authored ground truth answer")
    ground_truth_entities: list[str] = Field(
        default_factory=list, description="Target entities that must appear in grounded response"
    )
    expected_hop_count: int | None = Field(
        default=None, description="Expected multi-hop graph distance"
    )
    notes: str | None = Field(default=None, description="Analytical context and reasoning notes")


class JudgmentResult(BaseModel):
    """Scoring evaluation returned by LLM-as-judge or deterministic rule evaluator."""

    is_correct: bool = Field(..., description="Whether answer matches ground truth factual claims")
    citation_valid: bool = Field(
        ..., description="Whether response contains valid grounding citations"
    )
    hallucination_detected: bool = Field(
        ..., description="Whether answer introduces fabricated entity IDs"
    )
    unanswerable_correctly_refused: bool = Field(
        ..., description="Whether unanswerable query was properly refused"
    )
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized quality score 0.0 to 1.0")
    reasoning: str = Field(..., description="Evaluation justification from judge")


class BenchmarkEvaluationRow(BaseModel):
    """Single question execution result comparing response against judgment."""

    question_id: str = Field(..., description="ID of evaluated question")
    category: CategoryType = Field(..., description="Evaluation category")
    question: str = Field(..., description="Original user prompt")
    system: SystemType = Field(..., description="System tested: graph_rag or baseline_vector_rag")
    response: ChatResponse = Field(..., description="Generated copilot response")
    judgment: JudgmentResult = Field(..., description="Scored judgment metrics")


class CategoryMetric(BaseModel):
    """Aggregated evaluation metrics for a single question category."""

    category: CategoryType = Field(..., description="Question category")
    count: int = Field(..., description="Total questions in category")
    correctness: float = Field(..., description="Percentage of correct answers (0.0 to 1.0)")
    citation_recall: float = Field(..., description="Percentage of valid citations")
    hallucination_rate: float = Field(..., description="Percentage with hallucinations detected")
    avg_latency_ms: float = Field(..., description="Average response latency in milliseconds")


class BenchmarkSummaryReport(BaseModel):
    """Comprehensive comparative evaluation report across Graph RAG vs Baseline Vector RAG."""

    timestamp: str = Field(..., description="Execution timestamp YYYY-MM-DD HH:MM:SS")
    total_questions: int = Field(..., description="Total benchmark questions evaluated")
    graph_rag_correctness: float = Field(..., description="Overall Graph RAG correctness")
    baseline_rag_correctness: float = Field(
        ..., description="Overall Baseline Vector RAG correctness"
    )
    correctness_delta_percentage_points: float = Field(
        ..., description="Percentage points improvement of Graph RAG over baseline"
    )
    multi_hop_correctness_graph: float = Field(
        ..., description="Graph RAG correctness on multi-hop questions"
    )
    multi_hop_correctness_baseline: float = Field(
        ..., description="Baseline Vector RAG correctness on multi-hop questions"
    )
    multi_hop_delta_percentage_points: float = Field(
        ..., description="Multi-hop percentage points improvement"
    )
    citation_recall_graph: float = Field(..., description="Graph RAG citation recall")
    citation_recall_baseline: float = Field(..., description="Baseline citation recall")
    hallucination_rate_graph: float = Field(..., description="Graph RAG hallucination rate")
    hallucination_rate_baseline: float = Field(..., description="Baseline hallucination rate")
    unanswerable_precision: float = Field(
        ..., description="Refusal precision on unanswerable queries"
    )
    latency_p90_graph_ms: float = Field(..., description="P90 latency for Graph RAG in ms")
    latency_p90_baseline_ms: float = Field(..., description="P90 latency for Baseline RAG in ms")
    category_breakdown_graph: list[CategoryMetric] = Field(
        default_factory=list, description="Per-category metrics for Graph RAG"
    )
    category_breakdown_baseline: list[CategoryMetric] = Field(
        default_factory=list, description="Per-category metrics for Baseline RAG"
    )
