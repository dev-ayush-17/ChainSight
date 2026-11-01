"""LLM-based Text-to-Cypher generation with strict read-only safety guardrails and execution."""

import logging
import re

from google import genai
from google.genai import types
from neo4j import Driver

from api.config import Settings, get_settings
from retrieval.prompts import (
    TEXT_TO_CYPHER_FEW_SHOTS,
    TEXT_TO_CYPHER_SYSTEM_PROMPT,
    TEXT_TO_CYPHER_USER_TEMPLATE,
)
from retrieval.schemas import CypherQueryResult

logger = logging.getLogger(__name__)

FORBIDDEN_CYPHER_KEYWORDS: list[str] = [
    r"\bCREATE\b",
    r"\bMERGE\b",
    r"\bDELETE\b",
    r"\bSET\b",
    r"\bREMOVE\b",
    r"\bDROP\b",
    r"\bALTER\b",
    r"\bDETACH\b",
    r"\bCALL\s+dbms\b",
    r"\bCALL\s+apoc\.import\b",
    r"\bCALL\s+apoc\.export\b",
]


def validate_cypher_safety(cypher: str) -> tuple[bool, str | None]:
    """Verify that Cypher query is strictly read-only and free of destructive statements."""
    cleaned = cypher.strip()
    if not cleaned:
        return False, "Empty Cypher query"

    for pattern in FORBIDDEN_CYPHER_KEYWORDS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            return False, f"Prohibited modification keyword detected: {pattern}"

    upper_cleaned = cleaned.upper()
    if not (upper_cleaned.startswith("MATCH") or upper_cleaned.startswith("OPTIONAL MATCH")):
        return False, "Query must start with MATCH or OPTIONAL MATCH"

    if "RETURN" not in upper_cleaned:
        return False, "Query must contain a RETURN clause"

    return True, None


def generate_cypher_fallback(query: str) -> str:
    """Generate deterministic Cypher query from regex pattern matching for lookup queries."""
    # Pattern 1: Supplier Country Lookup: "Which country is supplier SUP-007 located in?"
    sup_match = re.search(r"\b(SUP-\d{3})\b", query, re.IGNORECASE)
    if sup_match and ("country" in query.lower() or "located" in query.lower()):
        sid = sup_match.group(1).upper()
        return (
            f"MATCH (s:Supplier {{id: '{sid}'}})-[:LOCATED_IN]->(c:Country) "
            "RETURN s.id AS supplier_id, s.name AS supplier_name, c.name AS country, "
            "c.code AS country_code "
            "LIMIT 5"
        )

    # Pattern 2: Component Producer Lookup: "Who produces component CMP-0012?"
    cmp_match = re.search(r"\b(CMP-\d{4})\b", query, re.IGNORECASE)
    if cmp_match:
        cid = cmp_match.group(1).upper()
        return (
            f"MATCH (s:Supplier)-[:PRODUCES]->(c:Component {{id: '{cid}'}}) "
            "RETURN s.id AS supplier_id, s.name AS supplier_name, s.tier AS tier, "
            "c.id AS component_id, c.name AS component_name "
            "LIMIT 10"
        )

    # Pattern 3: Product BOM Lookup: "What are the components of product PRD-001?"
    prd_match = re.search(r"\b(PRD-\d{3})\b", query, re.IGNORECASE)
    if prd_match:
        pid = prd_match.group(1).upper()
        return (
            f"MATCH (c:Component)-[r:PART_OF]->(p:Product {{id: '{pid}'}}) "
            "RETURN c.id AS component_id, c.name AS component_name, c.category AS category, "
            "r.quantity AS quantity, r.is_critical AS is_critical "
            "LIMIT 25"
        )

    # Pattern 4: Port Details: "Show details for Port of Shanghai"
    for port in [
        "shanghai",
        "singapore",
        "rotterdam",
        "ningbo",
        "busan",
        "los angeles",
        "long beach",
        "antwerp",
        "hamburg",
        "kaohsiung",
        "tokyo",
    ]:
        if port in query.lower():
            return (
                f"MATCH (p:Port) WHERE p.name =~ '(?i).*{port}.*' "
                "RETURN p.id AS port_id, p.name AS port_name, p.un_locode AS un_locode, "
                "p.throughput_teu_annual AS throughput "
                "LIMIT 5"
            )

    # Generic lookup fallback
    return (
        "MATCH (s:Supplier)-[:PRODUCES]->(c:Component)-[:PART_OF]->(p:Product) "
        "RETURN s.name AS supplier, c.name AS component, p.name AS product "
        "LIMIT 10"
    )


def generate_cypher_llm(
    query: str,
    api_key: str,
    model_name: str = "gemini-2.5-flash",
) -> str:
    """Generate Cypher query using Google GenAI SDK."""
    client = genai.Client(api_key=api_key)
    full_prompt = (
        f"{TEXT_TO_CYPHER_FEW_SHOTS}\n\n{TEXT_TO_CYPHER_USER_TEMPLATE.format(query=query)}"
    )

    response = client.models.generate_content(
        model=model_name,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            system_instruction=TEXT_TO_CYPHER_SYSTEM_PROMPT,
            temperature=0.0,
        ),
    )

    raw = response.text or ""
    # Strip any markdown code formatting
    cleaned = re.sub(r"```(cypher)?", "", raw).strip()
    return cleaned


def execute_text_to_cypher(
    driver: Driver,
    query: str,
    settings: Settings | None = None,
) -> CypherQueryResult:
    """Generate, validate, and execute read-only Cypher query against Neo4j driver."""
    cfg = settings or get_settings()

    cypher: str = ""
    if cfg.gemini_api_key and cfg.gemini_api_key.strip():
        try:
            cypher = generate_cypher_llm(query, cfg.gemini_api_key)
        except Exception as err:
            logger.warning("LLM Cypher generation failed (%s); using fallback pattern mapper", err)
            cypher = generate_cypher_fallback(query)
    else:
        cypher = generate_cypher_fallback(query)

    is_safe, error_msg = validate_cypher_safety(cypher)
    if not is_safe:
        return CypherQueryResult(
            generated_cypher=cypher,
            is_safe=False,
            records=[],
            subgraph_node_ids=[],
            error_message=error_msg,
        )

    records: list[dict[str, str | int | float | bool]] = []
    subgraph_nodes: set[str] = set()

    with driver.session() as session:
        try:
            result = session.run(cypher).data()
            for row in result:
                clean_row: dict[str, str | int | float | bool] = {}
                for k, v in row.items():
                    if isinstance(v, (str, int, float, bool)):
                        clean_row[k] = v
                        if any(id_key in k.lower() for id_key in ["id", "code", "sku"]):
                            subgraph_nodes.add(str(v))
                    elif v is not None:
                        clean_row[k] = str(v)
                records.append(clean_row)
        except Exception as err:
            return CypherQueryResult(
                generated_cypher=cypher,
                is_safe=True,
                records=[],
                subgraph_node_ids=[],
                error_message=str(err),
            )

    return CypherQueryResult(
        generated_cypher=cypher,
        is_safe=True,
        records=records,
        subgraph_node_ids=sorted(subgraph_nodes),
        error_message=None,
    )
