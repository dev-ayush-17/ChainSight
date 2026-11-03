"""Pydantic request and response models for the ChainSight REST API."""

from typing import Literal

from pydantic import BaseModel, Field

ConfidenceType = Literal["high", "medium", "low", "none"]
StrategyType = Literal["lookup", "impact_traversal", "semantic", "refused"]


class ChatRequest(BaseModel):
    """User chat request payload."""

    question: str = Field(..., min_length=1, description="Natural language supply chain question")
    session_id: str | None = Field(default=None, description="Optional conversational session ID")


class Citation(BaseModel):
    """Source reference for factual claims in the copilot response."""

    source_id: str = Field(..., description="Unique source or chunk identifier")
    title: str = Field(..., description="Article title or knowledge graph source name")
    source: str = Field(..., description="Publication name or graph repository")
    url: str = Field(..., description="Web URL or internal reference URI")
    date: str = Field(..., description="Publication date formatted as YYYY-MM-DD")


class ChatResponse(BaseModel):
    """Grounding-backed copilot response with citations and subgraph IDs."""

    answer: str = Field(..., description="Synthesized analytical answer")
    citations: list[Citation] = Field(
        default_factory=list, description="List of verified cited sources"
    )
    subgraph_node_ids: list[str] = Field(
        default_factory=list, description="IDs of nodes supporting the reasoning subgraph"
    )
    subgraph_edge_ids: list[str] = Field(
        default_factory=list, description="IDs of edges traversed in the reasoning subgraph"
    )
    retrieval_strategy: StrategyType = Field(
        ..., description="Retrieval strategy selected by router"
    )
    confidence: ConfidenceType = Field(..., description="Analytical confidence level in the answer")
    latency_ms: int = Field(default=0, ge=0, description="End-to-end pipeline latency in ms")


class GraphNode(BaseModel):
    """Knowledge graph node entity formatted for UI rendering."""

    id: str = Field(..., description="Unique entity ID in graph")
    label: str = Field(..., description="Primary Neo4j node label")
    name: str = Field(..., description="Human-readable entity name")
    properties: dict[str, str | int | float | bool | list[str]] = Field(
        default_factory=dict, description="Node key-value attributes"
    )


class GraphEdge(BaseModel):
    """Knowledge graph relationship connecting two nodes."""

    id: str = Field(..., description="Unique edge identifier or hash")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: str = Field(..., description="Neo4j relationship type")
    properties: dict[str, str | int | float | bool] = Field(
        default_factory=dict, description="Edge properties"
    )


class GraphResponse(BaseModel):
    """Subgraph visualization payload containing nodes and connecting edges."""

    nodes: list[GraphNode] = Field(default_factory=list, description="List of graph nodes")
    edges: list[GraphEdge] = Field(default_factory=list, description="List of graph edges")


class HealthResponse(BaseModel):
    """System health check status for database and LLM service."""

    status: str = Field(..., description="Overall service status (e.g. 'ok')")
    neo4j: str = Field(..., description="Neo4j connectivity status")
    llm: str = Field(..., description="LLM service availability status")


class SchemaResponse(BaseModel):
    """Graph schema metadata and label color configuration for UI visualization."""

    node_labels: list[str] = Field(default_factory=list, description="Available node labels")
    relationship_types: list[str] = Field(
        default_factory=list, description="Available relationship types"
    )
    label_colors: dict[str, str] = Field(
        default_factory=dict, description="Hex color mapping for each node label"
    )


class KpiResponse(BaseModel):
    """Supply chain KPI dashboard metrics derived from the knowledge graph."""

    total_revenue_at_risk: float = Field(
        default=0.0, description="Sum of annual revenue across all exposed products (USD)"
    )
    sole_sourced_components: int = Field(
        default=0, description="Count of components with a single supplier (highest risk)"
    )
    high_risk_suppliers: int = Field(
        default=0, description="Suppliers located in countries with risk_index > 0.6"
    )
    active_disruption_events: int = Field(
        default=0, description="Count of currently active disruption events in the graph"
    )
    avg_supplier_reliability: float = Field(
        default=0.0, description="Average supplier reliability score (0.0–1.0)"
    )
    node_counts: dict[str, int] = Field(
        default_factory=dict, description="Count of nodes per Neo4j label"
    )


class BenchmarkMetricItem(BaseModel):
    """Comparison metric item between Graph RAG and Baseline Vector RAG."""

    name: str = Field(..., description="Metric display name")
    target: str = Field(..., description="Target threshold from PRD")
    graph_rag: str = Field(..., description="Graph RAG measured score")
    baseline_vector: str = Field(..., description="Baseline Vector RAG measured score")
    delta: str = Field(..., description="Improvement delta percentage points")
    is_positive: bool = Field(default=True, description="Whether higher is better")
    description: str = Field(..., description="Qualitative evaluation notes")


class EfficiencyComparison(BaseModel):
    """Operational and latency comparison between Graph RAG and Vector RAG."""

    metric: str = Field(..., description="Efficiency dimension")
    graph_rag: str = Field(..., description="Graph RAG capability")
    baseline_vector: str = Field(..., description="Vector RAG capability")
    impact: str = Field(..., description="Business and performance impact")


class QueryComparison(BaseModel):
    """Side-by-side example comparing Graph RAG vs Vector RAG on a specific question."""

    id: str = Field(..., description="Benchmark question ID")
    category: str = Field(..., description="Question category")
    question: str = Field(..., description="Natural language question")
    ground_truth: str = Field(..., description="Human-authored ground truth")
    graph_rag_answer: str = Field(..., description="Response generated by Graph RAG")
    graph_rag_hops: int = Field(default=0, description="Number of graph hops traversed")
    graph_rag_status: str = Field(..., description="Correct or Incorrect")
    vector_rag_answer: str = Field(..., description="Response generated by Vector RAG")
    vector_rag_status: str = Field(..., description="Correct or Incorrect")
    why_graph_won: str = Field(..., description="Architectural reason for the difference")


class BenchmarkResponse(BaseModel):
    """Full benchmark evaluation dataset comparing Graph RAG with normal RAG."""

    summary_metrics: list[BenchmarkMetricItem] = Field(default_factory=list)
    efficiencies: list[EfficiencyComparison] = Field(default_factory=list)
    category_scores: dict[str, dict[str, float]] = Field(default_factory=dict)
    sample_comparisons: list[QueryComparison] = Field(default_factory=list)
