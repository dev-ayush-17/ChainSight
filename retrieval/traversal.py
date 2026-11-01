"""Parameterized Cypher templates for multi-hop supply chain impact traversal."""

from neo4j import Driver

from retrieval.schemas import TraversalImpactResult


def run_port_disruption_impact(driver: Driver, port_name: str) -> TraversalImpactResult:
    """Traverse graph from disrupted port to exposed suppliers, components, and products."""
    cypher = """
    MATCH (port:Port)<-[:SHIPS_VIA]-(s:Supplier)
          -[:PRODUCES]->(c:Component)-[bom:PART_OF]->(p:Product)
    WHERE port.name =~ ('(?i).*' + $port_name + '.*') OR port.id = $port_name
    RETURN port.id AS port_id,
           port.name AS port_name,
           s.id AS supplier_id,
           s.name AS supplier_name,
           s.tier AS supplier_tier,
           c.id AS component_id,
           c.name AS component_name,
           c.is_sole_sourced AS is_sole_sourced,
           bom.is_critical AS is_critical,
           p.id AS product_id,
           p.name AS product_name,
           p.revenue_usd_annual AS annual_revenue_usd
    ORDER BY p.revenue_usd_annual DESC
    """
    records: list[dict[str, str | int | float | bool]] = []
    subgraph_nodes: set[str] = set()

    with driver.session() as session:
        result = session.run(cypher, port_name=port_name)
        for row in result:
            data_row: dict[str, str | int | float | bool] = {
                "port_id": str(row["port_id"]),
                "port_name": str(row["port_name"]),
                "supplier_id": str(row["supplier_id"]),
                "supplier_name": str(row["supplier_name"]),
                "supplier_tier": int(row["supplier_tier"]),
                "component_id": str(row["component_id"]),
                "component_name": str(row["component_name"]),
                "is_sole_sourced": bool(row["is_sole_sourced"]),
                "is_critical": bool(row["is_critical"]),
                "product_id": str(row["product_id"]),
                "product_name": str(row["product_name"]),
                "annual_revenue_usd": float(row["annual_revenue_usd"]),
            }
            records.append(data_row)
            subgraph_nodes.add(str(row["port_id"]))
            subgraph_nodes.add(str(row["supplier_id"]))
            subgraph_nodes.add(str(row["component_id"]))
            subgraph_nodes.add(str(row["product_id"]))

    return TraversalImpactResult(
        template_name="port_disruption_impact",
        parameters={"port_name": port_name},
        records=records,
        subgraph_node_ids=sorted(subgraph_nodes),
        subgraph_edge_ids=[],
    )


def run_supplier_disruption_impact(
    driver: Driver, supplier_id_or_name: str
) -> TraversalImpactResult:
    """Traverse graph from disrupted supplier to impacted components, facilities, and products."""
    cypher = """
    MATCH (s:Supplier)
    WHERE s.id = $query OR s.name =~ ('(?i).*' + $query + '.*')
    OPTIONAL MATCH (s)-[:OPERATES]->(f:Facility)
    OPTIONAL MATCH (s)-[:PRODUCES]->(c:Component)-[bom:PART_OF]->(p:Product)
    RETURN s.id AS supplier_id,
           s.name AS supplier_name,
           s.reliability_score AS reliability_score,
           collect(DISTINCT f.name) AS facilities,
           c.id AS component_id,
           c.name AS component_name,
           c.is_sole_sourced AS is_sole_sourced,
           p.id AS product_id,
           p.name AS product_name,
           p.revenue_usd_annual AS product_revenue
    ORDER BY p.revenue_usd_annual DESC
    """
    records: list[dict[str, str | int | float | bool]] = []
    subgraph_nodes: set[str] = set()

    with driver.session() as session:
        result = session.run(cypher, query=supplier_id_or_name)
        for row in result:
            s_id = str(row["supplier_id"])
            subgraph_nodes.add(s_id)
            c_id = str(row["component_id"]) if row["component_id"] else ""
            p_id = str(row["product_id"]) if row["product_id"] else ""
            if c_id:
                subgraph_nodes.add(c_id)
            if p_id:
                subgraph_nodes.add(p_id)

            records.append(
                {
                    "supplier_id": s_id,
                    "supplier_name": str(row["supplier_name"]),
                    "reliability_score": float(row["reliability_score"] or 0.0),
                    "component_id": c_id,
                    "component_name": str(row["component_name"] or "None"),
                    "is_sole_sourced": bool(row["is_sole_sourced"] or False),
                    "product_id": p_id,
                    "product_name": str(row["product_name"] or "None"),
                    "product_revenue": float(row["product_revenue"] or 0.0),
                }
            )

    return TraversalImpactResult(
        template_name="supplier_disruption_impact",
        parameters={"supplier": supplier_id_or_name},
        records=records,
        subgraph_node_ids=sorted(subgraph_nodes),
        subgraph_edge_ids=[],
    )


def run_country_concentration_risk(
    driver: Driver, country_code_or_name: str
) -> TraversalImpactResult:
    """Analyze geographic concentration of suppliers, products, and revenue in a country."""
    cypher = """
    MATCH (country:Country)<-[:LOCATED_IN]-(s:Supplier)
          -[:PRODUCES]->(c:Component)-[:PART_OF]->(p:Product)
    WHERE country.code = $query OR country.name =~ ('(?i).*' + $query + '.*')
    RETURN country.code AS country_code,
           country.name AS country_name,
           country.risk_index AS country_risk,
           count(DISTINCT s) AS supplier_count,
           collect(DISTINCT s.name) AS suppliers,
           count(DISTINCT p) AS exposed_product_count,
           collect(DISTINCT p.name) AS exposed_products,
           sum(p.revenue_usd_annual) AS total_revenue_at_risk
    """
    records: list[dict[str, str | int | float | bool]] = []
    subgraph_nodes: set[str] = set()

    with driver.session() as session:
        result = session.run(cypher, query=country_code_or_name)
        for row in result:
            c_code = str(row["country_code"])
            subgraph_nodes.add(c_code)
            records.append(
                {
                    "country_code": c_code,
                    "country_name": str(row["country_name"]),
                    "country_risk": float(row["country_risk"] or 0.0),
                    "supplier_count": int(row["supplier_count"]),
                    "exposed_product_count": int(row["exposed_product_count"]),
                    "total_revenue_at_risk": float(row["total_revenue_at_risk"] or 0.0),
                }
            )

    return TraversalImpactResult(
        template_name="country_concentration_risk",
        parameters={"country": country_code_or_name},
        records=records,
        subgraph_node_ids=sorted(subgraph_nodes),
        subgraph_edge_ids=[],
    )


def run_alternative_supplier_finder(
    driver: Driver, supplier_or_component_id: str
) -> TraversalImpactResult:
    """Find qualified alternative suppliers for a disrupted component or vendor."""
    cypher = """
    MATCH (s1:Supplier)-[r:ALTERNATIVE_FOR]->(alt:Supplier)
    MATCH (s1)-[:PRODUCES]->(c:Component {id: r.component_id})
    WHERE s1.id = $query
       OR s1.name =~ ('(?i).*' + $query + '.*')
       OR c.id = $query
       OR c.name =~ ('(?i).*' + $query + '.*')
    RETURN s1.id AS primary_supplier_id,
           s1.name AS primary_supplier_name,
           alt.id AS alt_supplier_id,
           alt.name AS alt_supplier_name,
           alt.country_code AS alt_country,
           alt.reliability_score AS alt_reliability,
           c.id AS component_id,
           c.name AS component_name,
           r.qualification_status AS qualification_status
    ORDER BY alt.reliability_score DESC
    """
    records: list[dict[str, str | int | float | bool]] = []
    subgraph_nodes: set[str] = set()

    with driver.session() as session:
        result = session.run(cypher, query=supplier_or_component_id)
        for row in result:
            p_id = str(row["primary_supplier_id"])
            a_id = str(row["alt_supplier_id"])
            c_id = str(row["component_id"])
            subgraph_nodes.add(p_id)
            subgraph_nodes.add(a_id)
            subgraph_nodes.add(c_id)

            records.append(
                {
                    "primary_supplier_id": p_id,
                    "primary_supplier_name": str(row["primary_supplier_name"]),
                    "alt_supplier_id": a_id,
                    "alt_supplier_name": str(row["alt_supplier_name"]),
                    "alt_country": str(row["alt_country"]),
                    "alt_reliability": float(row["alt_reliability"] or 0.0),
                    "component_id": c_id,
                    "component_name": str(row["component_name"]),
                    "qualification_status": str(row["qualification_status"]),
                }
            )

    return TraversalImpactResult(
        template_name="alternative_supplier_finder",
        parameters={"target": supplier_or_component_id},
        records=records,
        subgraph_node_ids=sorted(subgraph_nodes),
        subgraph_edge_ids=[],
    )
