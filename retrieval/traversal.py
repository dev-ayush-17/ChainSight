"""Parameterized Cypher templates for multi-hop supply chain impact traversal."""

import logging
from pathlib import Path

import pandas as pd
from neo4j import Driver

from retrieval.schemas import TraversalImpactResult

logger = logging.getLogger(__name__)
DATA_DIR = Path("data/raw/synthetic")


def _fallback_port_disruption(port_name: str) -> TraversalImpactResult:
    """Traverse port disruption impact using local synthetic CSV dataset."""
    records: list[dict[str, str | int | float | bool]] = []
    subgraph_nodes: set[str] = set()

    if not DATA_DIR.exists():
        return TraversalImpactResult(
            template_name="port_disruption_impact",
            parameters={"port_name": port_name},
            records=[],
            subgraph_node_ids=[],
            subgraph_edge_ids=[],
        )

    try:
        ports = pd.read_csv(DATA_DIR / "ports.csv")
        ships_via = pd.read_csv(DATA_DIR / "ships_via.csv")
        suppliers = pd.read_csv(DATA_DIR / "suppliers.csv")
        produces = pd.read_csv(DATA_DIR / "produces.csv")
        components = pd.read_csv(DATA_DIR / "components.csv")
        bom = pd.read_csv(DATA_DIR / "bom.csv")
        products = pd.read_csv(DATA_DIR / "products.csv")

        p_mask = ports["name"].str.contains(port_name, case=False, na=False) | (
            ports["id"] == port_name
        )
        matched_ports = ports[p_mask]
        if matched_ports.empty:
            matched_ports = ports.head(1)

        for _, port_row in matched_ports.iterrows():
            port_id = str(port_row["id"])
            p_name = str(port_row["name"])
            subgraph_nodes.add(port_id)

            sv = ships_via[ships_via["port_id"] == port_id]
            for _, sv_row in sv.iterrows():
                sup_id = str(sv_row["supplier_id"])
                sup_match = suppliers[suppliers["id"] == sup_id]
                sup_name = str(sup_match.iloc[0]["name"]) if not sup_match.empty else sup_id
                sup_tier = int(sup_match.iloc[0]["tier"]) if not sup_match.empty else 1
                subgraph_nodes.add(sup_id)

                prod_links = produces[produces["supplier_id"] == sup_id]
                for _, pr_row in prod_links.iterrows():
                    comp_id = str(pr_row["component_id"])
                    comp_match = components[components["id"] == comp_id]
                    comp_name = str(comp_match.iloc[0]["name"]) if not comp_match.empty else comp_id
                    is_sole = (
                        bool(comp_match.iloc[0]["is_sole_sourced"])
                        if not comp_match.empty
                        else False
                    )
                    subgraph_nodes.add(comp_id)

                    bom_links = bom[bom["component_id"] == comp_id]
                    for _, bom_row in bom_links.iterrows():
                        prod_id = str(bom_row["product_id"])
                        is_crit = bool(bom_row.get("is_critical", True))
                        prod_match = products[products["id"] == prod_id]
                        prod_name = (
                            str(prod_match.iloc[0]["name"]) if not prod_match.empty else prod_id
                        )
                        rev = (
                            float(prod_match.iloc[0]["revenue_usd_annual"])
                            if not prod_match.empty
                            else 0.0
                        )
                        subgraph_nodes.add(prod_id)

                        records.append(
                            {
                                "port_id": port_id,
                                "port_name": p_name,
                                "supplier_id": sup_id,
                                "supplier_name": sup_name,
                                "supplier_tier": sup_tier,
                                "component_id": comp_id,
                                "component_name": comp_name,
                                "is_sole_sourced": is_sole,
                                "is_critical": is_crit,
                                "product_id": prod_id,
                                "product_name": prod_name,
                                "annual_revenue_usd": rev,
                            }
                        )
    except Exception as err:
        logger.error("Error in fallback port disruption traversal: %s", err)

    records.sort(key=lambda x: float(x.get("annual_revenue_usd", 0.0)), reverse=True)
    return TraversalImpactResult(
        template_name="port_disruption_impact",
        parameters={"port_name": port_name},
        records=records[:25],
        subgraph_node_ids=sorted(subgraph_nodes),
        subgraph_edge_ids=[],
    )


def _fallback_supplier_disruption(supplier_query: str) -> TraversalImpactResult:
    """Traverse supplier disruption impact using local synthetic CSV dataset."""
    records: list[dict[str, str | int | float | bool]] = []
    subgraph_nodes: set[str] = set()

    if not DATA_DIR.exists():
        return TraversalImpactResult(
            template_name="supplier_disruption_impact",
            parameters={"supplier": supplier_query},
            records=[],
            subgraph_node_ids=[],
            subgraph_edge_ids=[],
        )

    try:
        suppliers = pd.read_csv(DATA_DIR / "suppliers.csv")
        produces = pd.read_csv(DATA_DIR / "produces.csv")
        components = pd.read_csv(DATA_DIR / "components.csv")
        bom = pd.read_csv(DATA_DIR / "bom.csv")
        products = pd.read_csv(DATA_DIR / "products.csv")

        s_mask = (suppliers["id"] == supplier_query) | suppliers["name"].str.contains(
            supplier_query, case=False, na=False
        )
        matched_sups = suppliers[s_mask]
        if matched_sups.empty:
            matched_sups = suppliers.head(1)

        for _, s_row in matched_sups.iterrows():
            sup_id = str(s_row["id"])
            sup_name = str(s_row["name"])
            rel = float(s_row.get("reliability_score", 0.85))
            subgraph_nodes.add(sup_id)

            prod_links = produces[produces["supplier_id"] == sup_id]
            for _, pr_row in prod_links.iterrows():
                comp_id = str(pr_row["component_id"])
                comp_match = components[components["id"] == comp_id]
                comp_name = str(comp_match.iloc[0]["name"]) if not comp_match.empty else comp_id
                is_sole = (
                    bool(comp_match.iloc[0]["is_sole_sourced"]) if not comp_match.empty else False
                )
                subgraph_nodes.add(comp_id)

                bom_links = bom[bom["component_id"] == comp_id]
                for _, b_row in bom_links.iterrows():
                    prod_id = str(b_row["product_id"])
                    prod_match = products[products["id"] == prod_id]
                    prod_name = str(prod_match.iloc[0]["name"]) if not prod_match.empty else prod_id
                    rev = (
                        float(prod_match.iloc[0]["revenue_usd_annual"])
                        if not prod_match.empty
                        else 0.0
                    )
                    subgraph_nodes.add(prod_id)

                    records.append(
                        {
                            "supplier_id": sup_id,
                            "supplier_name": sup_name,
                            "reliability_score": rel,
                            "component_id": comp_id,
                            "component_name": comp_name,
                            "is_sole_sourced": is_sole,
                            "product_id": prod_id,
                            "product_name": prod_name,
                            "product_revenue": rev,
                        }
                    )
    except Exception as err:
        logger.error("Error in fallback supplier disruption traversal: %s", err)

    records.sort(key=lambda x: float(x.get("product_revenue", 0.0)), reverse=True)
    return TraversalImpactResult(
        template_name="supplier_disruption_impact",
        parameters={"supplier": supplier_query},
        records=records[:25],
        subgraph_node_ids=sorted(subgraph_nodes),
        subgraph_edge_ids=[],
    )


def _fallback_country_concentration(country_query: str) -> TraversalImpactResult:
    """Analyze country concentration risk using local synthetic CSV dataset."""
    records: list[dict[str, str | int | float | bool]] = []
    subgraph_nodes: set[str] = set()

    if not DATA_DIR.exists():
        return TraversalImpactResult(
            template_name="country_concentration_risk",
            parameters={"country": country_query},
            records=[],
            subgraph_node_ids=[],
            subgraph_edge_ids=[],
        )

    try:
        countries = pd.read_csv(DATA_DIR / "countries.csv")
        suppliers = pd.read_csv(DATA_DIR / "suppliers.csv")
        produces = pd.read_csv(DATA_DIR / "produces.csv")
        bom = pd.read_csv(DATA_DIR / "bom.csv")
        products = pd.read_csv(DATA_DIR / "products.csv")

        c_mask = (countries["code"] == country_query) | countries["name"].str.contains(
            country_query, case=False, na=False
        )
        matched_countries = countries[c_mask]
        if matched_countries.empty:
            matched_countries = countries.head(1)

        for _, c_row in matched_countries.iterrows():
            c_code = str(c_row["code"])
            c_name = str(c_row["name"])
            c_risk = float(c_row.get("risk_index", 0.5))
            subgraph_nodes.add(c_code)

            sups = suppliers[suppliers["country_code"] == c_code]
            sup_count = len(sups)
            sup_ids = sups["id"].tolist()
            prod_links = produces[produces["supplier_id"].isin(sup_ids)]
            comp_ids = prod_links["component_id"].tolist()
            bom_links = bom[bom["component_id"].isin(comp_ids)]
            prod_ids = bom_links["product_id"].unique().tolist()
            prods = products[products["id"].isin(prod_ids)]
            tot_rev = float(prods["revenue_usd_annual"].sum())

            records.append(
                {
                    "country_code": c_code,
                    "country_name": c_name,
                    "country_risk": c_risk,
                    "supplier_count": sup_count,
                    "exposed_product_count": len(prods),
                    "total_revenue_at_risk": tot_rev,
                }
            )
    except Exception as err:
        logger.error("Error in fallback country concentration traversal: %s", err)

    return TraversalImpactResult(
        template_name="country_concentration_risk",
        parameters={"country": country_query},
        records=records,
        subgraph_node_ids=sorted(subgraph_nodes),
        subgraph_edge_ids=[],
    )


def _fallback_alternative_suppliers(query: str) -> TraversalImpactResult:
    """Find alternative suppliers using local synthetic CSV dataset."""
    records: list[dict[str, str | int | float | bool]] = []
    subgraph_nodes: set[str] = set()

    if not DATA_DIR.exists():
        return TraversalImpactResult(
            template_name="alternative_supplier_finder",
            parameters={"target": query},
            records=[],
            subgraph_node_ids=[],
            subgraph_edge_ids=[],
        )

    try:
        alt_df = pd.read_csv(DATA_DIR / "alternative_suppliers.csv")
        suppliers = pd.read_csv(DATA_DIR / "suppliers.csv")
        components = pd.read_csv(DATA_DIR / "components.csv")

        for _, row in alt_df.iterrows():
            p_id = str(row["primary_supplier_id"])
            a_id = str(row["alt_supplier_id"])
            c_id = str(row["component_id"])
            q_stat = str(row.get("qualification_status", "qualified"))

            # Match on supplier or component
            if (
                query.lower() in p_id.lower()
                or query.lower() in a_id.lower()
                or query.lower() in c_id.lower()
                or query in ["", "alternative", "replace"]
            ):
                p_match = suppliers[suppliers["id"] == p_id]
                p_name = str(p_match.iloc[0]["name"]) if not p_match.empty else p_id
                a_match = suppliers[suppliers["id"] == a_id]
                a_name = str(a_match.iloc[0]["name"]) if not a_match.empty else a_id
                a_country = str(a_match.iloc[0]["country_code"]) if not a_match.empty else "US"
                a_rel = float(a_match.iloc[0]["reliability_score"]) if not a_match.empty else 0.85
                c_match = components[components["id"] == c_id]
                c_name = str(c_match.iloc[0]["name"]) if not c_match.empty else c_id

                subgraph_nodes.add(p_id)
                subgraph_nodes.add(a_id)
                subgraph_nodes.add(c_id)

                records.append(
                    {
                        "primary_supplier_id": p_id,
                        "primary_supplier_name": p_name,
                        "alt_supplier_id": a_id,
                        "alt_supplier_name": a_name,
                        "alt_country": a_country,
                        "alt_reliability": a_rel,
                        "component_id": c_id,
                        "component_name": c_name,
                        "qualification_status": q_stat,
                    }
                )
    except Exception as err:
        logger.error("Error in fallback alternative supplier traversal: %s", err)

    records.sort(key=lambda x: float(x.get("alt_reliability", 0.0)), reverse=True)
    return TraversalImpactResult(
        template_name="alternative_supplier_finder",
        parameters={"target": query},
        records=records[:25],
        subgraph_node_ids=sorted(subgraph_nodes),
        subgraph_edge_ids=[],
    )


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

    try:
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
    except Exception as err:
        logger.warning("Neo4j port disruption query failed (%s); using dataset fallback.", err)
        return _fallback_port_disruption(port_name)


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

    try:
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
    except Exception as err:
        logger.warning("Neo4j supplier query failed (%s); using dataset fallback.", err)
        return _fallback_supplier_disruption(supplier_id_or_name)


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

    try:
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
    except Exception as err:
        logger.warning("Neo4j country query failed (%s); using dataset fallback.", err)
        return _fallback_country_concentration(country_code_or_name)


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

    try:
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
    except Exception as err:
        logger.warning(
            "Neo4j alternative suppliers query failed (%s); using dataset fallback.", err
        )
        return _fallback_alternative_suppliers(supplier_or_component_id)
