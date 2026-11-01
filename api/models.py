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
