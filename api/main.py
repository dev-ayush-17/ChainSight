"""FastAPI application entrypoint exposing chat, graph, schema, and health endpoints."""

import logging
import time

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from neo4j import Driver

from api.config import Settings
from api.dependencies import get_app_settings, get_driver
from api.models import (
    ChatRequest,
    ChatResponse,
    GraphEdge,
    GraphNode,
    GraphResponse,
    HealthResponse,
    SchemaResponse,
)
from generation.generator import generate_copilot_response
from retrieval.context_assembler import assemble_context
from retrieval.cypher_gen import execute_text_to_cypher
from retrieval.router import classify_intent
from retrieval.traversal import (
    run_alternative_supplier_finder,
    run_country_concentration_risk,
    run_port_disruption_impact,
    run_supplier_disruption_impact,
)
from retrieval.vector_search import (
    search_articles_fallback_text,
    search_articles_vector,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="ChainSight API",
    description="Enterprise Graph RAG supply chain risk copilot backend",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SCHEMA_NODE_LABELS: list[str] = [
    "Supplier",
    "Facility",
    "Component",
    "Product",
    "Port",
    "Country",
    "Customer",
    "Event",
    "Article",
]

SCHEMA_RELATIONSHIPS: list[str] = [
    "OPERATES",
    "PRODUCES",
    "PART_OF",
    "SHIPS_VIA",
    "LOCATED_IN",
    "AFFECTS",
    "MENTIONS",
    "ALTERNATIVE_FOR",
]

SCHEMA_COLORS: dict[str, str] = {
    "Supplier": "#4A90D9",
    "Port": "#E67E22",
    "Component": "#27AE60",
    "Product": "#8E44AD",
    "Country": "#C0392B",
    "Event": "#E74C3C",
    "Article": "#95A5A6",
    "Customer": "#F39C12",
    "Facility": "#16A085",
}


@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
def health_check(
    driver: Driver = Depends(get_driver),
    settings: Settings = Depends(get_app_settings),
) -> HealthResponse:
    """Check connectivity to Neo4j database and LLM API availability."""
    neo4j_status = "error"
    try:
        driver.verify_connectivity()
        neo4j_status = "connected"
    except Exception:
        neo4j_status = "error"

    llm_status = "configured" if settings.gemini_api_key else "not_configured"

    return HealthResponse(
        status="ok" if neo4j_status == "connected" else "degraded",
        neo4j=neo4j_status,
        llm=llm_status,
    )


@app.get("/schema", response_model=SchemaResponse, tags=["Metadata"])
def get_graph_schema() -> SchemaResponse:
    """Return graph schema node labels, relationship types, and visual colors."""
    return SchemaResponse(
        node_labels=SCHEMA_NODE_LABELS,
        relationship_types=SCHEMA_RELATIONSHIPS,
        label_colors=SCHEMA_COLORS,
    )


@app.post("/chat", response_model=ChatResponse, tags=["Copilot"])
def chat_copilot(
    request: ChatRequest,
    driver: Driver = Depends(get_driver),
    settings: Settings = Depends(get_app_settings),
) -> ChatResponse:
    """Execute end-to-end Graph RAG copilot pipeline for user question."""
    t0 = time.perf_counter()
    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question cannot be empty.",
        )

    # 1. Intent Classification
    intent = classify_intent(question)

    traversal_res = None
    cypher_res = None
    vector_res = None

    # 2. Strategy Execution
    try:
        if intent.intent == "impact_traversal":
            norm_q = question.lower()
            entity = intent.extracted_entities[0] if intent.extracted_entities else question

            if "alternative" in norm_q or "replace" in norm_q or "shortage" in norm_q:
                traversal_res = run_alternative_supplier_finder(driver, entity)
            elif "country" in norm_q or "concentration" in norm_q:
                traversal_res = run_country_concentration_risk(driver, entity)
            elif "port" in norm_q or "terminal" in norm_q or "dock" in norm_q:
                traversal_res = run_port_disruption_impact(driver, entity)
            else:
                traversal_res = run_supplier_disruption_impact(driver, entity)

        elif intent.intent == "lookup":
            cypher_res = execute_text_to_cypher(driver, question, settings=settings)

        elif intent.intent == "semantic":
            try:
                vector_res = search_articles_vector(driver, question, top_k=5)
            except Exception:
                vector_res = search_articles_fallback_text(
                    driver, intent.disruption_keywords or ["disruption", "shipping"], top_k=5
                )
    except Exception as err:
        logger.error("Error executing retrieval strategy for query '%s': %s", question, err)

    # 3. Context Assembly
    assembled = assemble_context(
        query=question,
        intent=intent,
        traversal_result=traversal_res,
        cypher_result=cypher_res,
        vector_results=vector_res,
    )

    # 4. Answer Generation with Guardrails
    return generate_copilot_response(assembled, settings=settings, start_time=t0)


@app.get("/graph", response_model=GraphResponse, tags=["Visualization"])
def get_subgraph(
    node_ids: str | None = None,
    edge_ids: str | None = None,
    driver: Driver = Depends(get_driver),
) -> GraphResponse:
    """Fetch nodes and connecting edges for subgraph visualization."""
    if not node_ids:
        return GraphResponse(nodes=[], edges=[])

    target_ids = [nid.strip() for nid in node_ids.split(",") if nid.strip()]
    if not target_ids:
        return GraphResponse(nodes=[], edges=[])

    cypher = """
    MATCH (n)
    WHERE n.id IN $node_ids OR n.name IN $node_ids
    OPTIONAL MATCH (n)-[r]->(m)
    WHERE m.id IN $node_ids OR m.name IN $node_ids
    RETURN n.id AS source_id,
           labels(n) AS source_labels,
           n.name AS source_name,
           properties(n) AS source_props,
           type(r) AS rel_type,
           properties(r) AS rel_props,
           m.id AS target_id,
           labels(m) AS target_labels,
           m.name AS target_name,
           properties(m) AS target_props
    """

    nodes_map: dict[str, GraphNode] = {}
    edges_list: list[GraphEdge] = []

    try:
        with driver.session() as session:
            result = session.run(cypher, node_ids=target_ids)
            for record in result:
                s_id = str(record.get("source_id") or "")
                s_labels = record.get("source_labels") or ["Entity"]
                s_name = str(record.get("source_name") or s_id)
                s_props = dict(record.get("source_props") or {})

                if s_id and s_id not in nodes_map:
                    nodes_map[s_id] = GraphNode(
                        id=s_id,
                        label=s_labels[0] if s_labels else "Entity",
                        name=s_name,
                        properties=s_props,
                    )

                t_id = record.get("target_id")
                if t_id:
                    t_id_str = str(t_id)
                    t_labels = record.get("target_labels") or ["Entity"]
                    t_name = str(record.get("target_name") or t_id_str)
                    t_props = dict(record.get("target_props") or {})

                    if t_id_str not in nodes_map:
                        nodes_map[t_id_str] = GraphNode(
                            id=t_id_str,
                            label=t_labels[0] if t_labels else "Entity",
                            name=t_name,
                            properties=t_props,
                        )

                    rel_type = str(record.get("rel_type") or "CONNECTED_TO")
                    edge_key = f"{s_id}-{rel_type}->{t_id_str}"
                    edges_list.append(
                        GraphEdge(
                            id=edge_key,
                            source=s_id,
                            target=t_id_str,
                            type=rel_type,
                            properties=dict(record.get("rel_props") or {}),
                        )
                    )
    except Exception as err:
        logger.error("Failed to fetch graph nodes for %s: %s", target_ids, err)

    return GraphResponse(nodes=list(nodes_map.values()), edges=edges_list)
