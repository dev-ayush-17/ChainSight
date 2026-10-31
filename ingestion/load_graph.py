"""Ingestion pipeline to load synthetic supply chain data and establish schema in Neo4j."""

import csv
from pathlib import Path

from neo4j import Driver

from api.config import get_settings
from api.dependencies import get_neo4j_driver_from_settings
from data.models import (
    Component,
    ComponentPartOfProduct,
    Country,
    Customer,
    Facility,
    FacilityShipsToCustomer,
    Port,
    Product,
    Supplier,
    SupplierAlternativeFor,
    SupplierOperatesFacility,
    SupplierProducesComponent,
    SupplierShipsViaPort,
)


def create_constraints_and_indexes(driver: Driver) -> None:
    """Create uniqueness constraints, full-text index, and vector indexes in Neo4j."""
    constraint_statements = [
        "CREATE CONSTRAINT supplier_id IF NOT EXISTS FOR (s:Supplier) REQUIRE s.id IS UNIQUE",
        "CREATE CONSTRAINT component_id IF NOT EXISTS FOR (c:Component) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT port_unlocode IF NOT EXISTS FOR (p:Port) REQUIRE p.un_locode IS UNIQUE",
        "CREATE CONSTRAINT port_id IF NOT EXISTS FOR (p:Port) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT article_id IF NOT EXISTS FOR (a:Article) REQUIRE a.id IS UNIQUE",
        "CREATE CONSTRAINT country_code IF NOT EXISTS FOR (c:Country) REQUIRE c.code IS UNIQUE",
        "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT facility_id IF NOT EXISTS FOR (f:Facility) REQUIRE f.id IS UNIQUE",
    ]

    index_statements = [
        """
        CREATE FULLTEXT INDEX entity_name_ft IF NOT EXISTS
        FOR (n:Supplier|Port|Component|Product|Country|Customer)
        ON EACH [n.name]
        """,
        """
        CREATE VECTOR INDEX article_embedding IF NOT EXISTS
        FOR (a:Article) ON (a.embedding)
        OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}}
        """,
        """
        CREATE VECTOR INDEX node_desc_embedding IF NOT EXISTS
        FOR (n:Supplier) ON (n.description_embedding)
        OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}}
        """,
    ]

    with driver.session() as session:
        for stmt in constraint_statements:
            session.run(stmt)
        for stmt in index_statements:
            session.run(stmt)


def load_countries(driver: Driver, data_dir: Path) -> int:
    """Load Country nodes from CSV into Neo4j."""
    csv_path = data_dir / "countries.csv"
    countries: list[Country] = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            countries.append(
                Country(
                    code=row["code"],
                    name=row["name"],
                    region=row["region"],
                    risk_index=float(row["risk_index"]),
                )
            )

    cypher = """
    UNWIND $batch AS row
    MERGE (c:Country {code: row.code})
    SET c.name = row.name,
        c.region = row.region,
        c.risk_index = toFloat(row.risk_index)
    """
    with driver.session() as session:
        session.run(cypher, batch=[c.model_dump() for c in countries])
    return len(countries)


def load_ports(driver: Driver, data_dir: Path) -> int:
    """Load Port nodes and LOCATED_IN edges from CSV into Neo4j."""
    csv_path = data_dir / "ports.csv"
    ports: list[Port] = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ports.append(
                Port(
                    id=row["id"],
                    name=row["name"],
                    country_code=row["country_code"],
                    un_locode=row["un_locode"],
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                    throughput_teu_annual=int(row["throughput_teu_annual"]),
                )
            )

    cypher = """
    UNWIND $batch AS row
    MERGE (p:Port {id: row.id})
    SET p.name = row.name,
        p.un_locode = row.un_locode,
        p.country_code = row.country_code,
        p.lat = toFloat(row.lat),
        p.lon = toFloat(row.lon),
        p.throughput_teu_annual = toInteger(row.throughput_teu_annual)
    WITH p, row
    MATCH (c:Country {code: row.country_code})
    MERGE (p)-[:LOCATED_IN]->(c)
    """
    with driver.session() as session:
        session.run(cypher, batch=[p.model_dump() for p in ports])
    return len(ports)


def load_suppliers(driver: Driver, data_dir: Path) -> int:
    """Load Supplier nodes and LOCATED_IN edges from CSV into Neo4j."""
    csv_path = data_dir / "suppliers.csv"
    suppliers: list[Supplier] = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            suppliers.append(
                Supplier(
                    id=row["id"],
                    name=row["name"],
                    country_code=row["country_code"],
                    reliability_score=float(row["reliability_score"]),
                    lead_time_days=int(row["lead_time_days"]),
                    tier=int(row["tier"]),
                )
            )

    cypher = """
    UNWIND $batch AS row
    MERGE (s:Supplier {id: row.id})
    SET s.name = row.name,
        s.country_code = row.country_code,
        s.reliability_score = toFloat(row.reliability_score),
        s.lead_time_days = toInteger(row.lead_time_days),
        s.tier = toInteger(row.tier)
    WITH s, row
    MATCH (c:Country {code: row.country_code})
    MERGE (s)-[:LOCATED_IN]->(c)
    """
    with driver.session() as session:
        session.run(cypher, batch=[s.model_dump() for s in suppliers])
    return len(suppliers)


def load_facilities(driver: Driver, data_dir: Path) -> int:
    """Load Facility nodes and LOCATED_IN edges from CSV into Neo4j."""
    csv_path = data_dir / "facilities.csv"
    facilities: list[Facility] = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            facilities.append(
                Facility(
                    id=row["id"],
                    name=row["name"],
                    supplier_id=row["supplier_id"],
                    country_code=row["country_code"],
                    facility_type=row["facility_type"],
                    capacity_units=int(row["capacity_units"]),
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                )
            )

    cypher = """
    UNWIND $batch AS row
    MERGE (f:Facility {id: row.id})
    SET f.name = row.name,
        f.supplier_id = row.supplier_id,
        f.country_code = row.country_code,
        f.type = row.facility_type,
        f.capacity_units = toInteger(row.capacity_units),
        f.lat = toFloat(row.lat),
        f.lon = toFloat(row.lon)
    WITH f, row
    MATCH (c:Country {code: row.country_code})
    MERGE (f)-[:LOCATED_IN]->(c)
    """
    with driver.session() as session:
        session.run(cypher, batch=[f.model_dump() for f in facilities])
    return len(facilities)


def load_components(driver: Driver, data_dir: Path) -> int:
    """Load Component nodes from CSV into Neo4j."""
    csv_path = data_dir / "components.csv"
    components: list[Component] = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            components.append(
                Component(
                    id=row["id"],
                    name=row["name"],
                    category=row["category"],
                    unit_cost_usd=float(row["unit_cost_usd"]),
                    lead_time_days=int(row["lead_time_days"]),
                    is_sole_sourced=row["is_sole_sourced"].lower() == "true",
                )
            )

    cypher = """
    UNWIND $batch AS row
    MERGE (c:Component {id: row.id})
    SET c.name = row.name,
        c.category = row.category,
        c.unit_cost_usd = toFloat(row.unit_cost_usd),
        c.lead_time_days = toInteger(row.lead_time_days),
        c.is_sole_sourced = toBoolean(row.is_sole_sourced)
    """
    with driver.session() as session:
        session.run(cypher, batch=[c.model_dump() for c in components])
    return len(components)


def load_products(driver: Driver, data_dir: Path) -> int:
    """Load Product nodes from CSV into Neo4j."""
    csv_path = data_dir / "products.csv"
    products: list[Product] = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append(
                Product(
                    id=row["id"],
                    name=row["name"],
                    sku=row["sku"],
                    family=row["family"],
                    revenue_usd_annual=float(row["revenue_usd_annual"]),
                    margin_pct=float(row["margin_pct"]),
                )
            )

    cypher = """
    UNWIND $batch AS row
    MERGE (p:Product {id: row.id})
    SET p.name = row.name,
        p.sku = row.sku,
        p.family = row.family,
        p.revenue_usd_annual = toFloat(row.revenue_usd_annual),
        p.margin_pct = toFloat(row.margin_pct)
    """
    with driver.session() as session:
        session.run(cypher, batch=[p.model_dump() for p in products])
    return len(products)


def load_customers(driver: Driver, data_dir: Path) -> int:
    """Load Customer nodes and LOCATED_IN edges from CSV into Neo4j."""
    csv_path = data_dir / "customers.csv"
    customers: list[Customer] = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            customers.append(
                Customer(
                    id=row["id"],
                    name=row["name"],
                    country_code=row["country_code"],
                    annual_revenue_usd=float(row["annual_revenue_usd"]),
                    segment=row["segment"],
                )
            )

    cypher = """
    UNWIND $batch AS row
    MERGE (c:Customer {id: row.id})
    SET c.name = row.name,
        c.country_code = row.country_code,
        c.annual_revenue_usd = toFloat(row.annual_revenue_usd),
        c.segment = row.segment
    WITH c, row
    MATCH (country:Country {code: row.country_code})
    MERGE (c)-[:LOCATED_IN]->(country)
    """
    with driver.session() as session:
        session.run(cypher, batch=[c.model_dump() for c in customers])
    return len(customers)


def load_relationships(driver: Driver, data_dir: Path) -> dict[str, int]:
    """Load OPERATES, PRODUCES, PART_OF, SHIPS_VIA, ALTERNATIVE_FOR, and SHIPS_TO edges."""
    counts: dict[str, int] = {}

    # 1. OPERATES (Supplier -> Facility)
    operates: list[SupplierOperatesFacility] = []
    with open(data_dir / "operates.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            operates.append(
                SupplierOperatesFacility(
                    supplier_id=row["supplier_id"],
                    facility_id=row["facility_id"],
                    since_year=int(row["since_year"]),
                )
            )
    cypher_operates = """
    UNWIND $batch AS row
    MATCH (s:Supplier {id: row.supplier_id})
    MATCH (f:Facility {id: row.facility_id})
    MERGE (s)-[r:OPERATES]->(f)
    SET r.since_year = toInteger(row.since_year)
    """
    with driver.session() as session:
        session.run(cypher_operates, batch=[o.model_dump() for o in operates])
    counts["OPERATES"] = len(operates)

    # 2. PRODUCES (Supplier -> Component)
    produces: list[SupplierProducesComponent] = []
    with open(data_dir / "produces.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            produces.append(
                SupplierProducesComponent(
                    supplier_id=row["supplier_id"],
                    component_id=row["component_id"],
                    annual_volume=int(row["annual_volume"]),
                    is_primary=row["is_primary"].lower() == "true",
                )
            )
    cypher_produces = """
    UNWIND $batch AS row
    MATCH (s:Supplier {id: row.supplier_id})
    MATCH (c:Component {id: row.component_id})
    MERGE (s)-[r:PRODUCES]->(c)
    SET r.annual_volume = toInteger(row.annual_volume),
        r.is_primary = toBoolean(row.is_primary)
    """
    with driver.session() as session:
        session.run(cypher_produces, batch=[p.model_dump() for p in produces])
    counts["PRODUCES"] = len(produces)

    # 3. PART_OF (Component -> Product / BOM)
    bom: list[ComponentPartOfProduct] = []
    with open(data_dir / "bom.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bom.append(
                ComponentPartOfProduct(
                    component_id=row["component_id"],
                    product_id=row["product_id"],
                    quantity=int(row["quantity"]),
                    is_critical=row["is_critical"].lower() == "true",
                )
            )
    cypher_bom = """
    UNWIND $batch AS row
    MATCH (c:Component {id: row.component_id})
    MATCH (p:Product {id: row.product_id})
    MERGE (c)-[r:PART_OF]->(p)
    SET r.quantity = toInteger(row.quantity),
        r.is_critical = toBoolean(row.is_critical)
    """
    with driver.session() as session:
        session.run(cypher_bom, batch=[b.model_dump() for b in bom])
    counts["PART_OF"] = len(bom)

    # 4. SHIPS_VIA (Supplier -> Port)
    ships_via: list[SupplierShipsViaPort] = []
    with open(data_dir / "ships_via.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ships_via.append(
                SupplierShipsViaPort(
                    supplier_id=row["supplier_id"],
                    port_id=row["port_id"],
                    primary=row["primary"].lower() == "true",
                    avg_transit_days=int(row["avg_transit_days"]),
                )
            )
    cypher_ships_via = """
    UNWIND $batch AS row
    MATCH (s:Supplier {id: row.supplier_id})
    MATCH (port:Port {id: row.port_id})
    MERGE (s)-[r:SHIPS_VIA]->(port)
    SET r.primary = toBoolean(row.primary),
        r.avg_transit_days = toInteger(row.avg_transit_days)
    """
    with driver.session() as session:
        session.run(cypher_ships_via, batch=[sv.model_dump() for sv in ships_via])
    counts["SHIPS_VIA"] = len(ships_via)

    # 5. ALTERNATIVE_FOR (Supplier -> Supplier)
    alternatives: list[SupplierAlternativeFor] = []
    with open(data_dir / "alternative_suppliers.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            alternatives.append(
                SupplierAlternativeFor(
                    supplier_id=row["supplier_id"],
                    alternative_supplier_id=row["alternative_supplier_id"],
                    component_id=row["component_id"],
                    qualification_status=row["qualification_status"],
                )
            )
    cypher_alt = """
    UNWIND $batch AS row
    MATCH (s1:Supplier {id: row.supplier_id})
    MATCH (s2:Supplier {id: row.alternative_supplier_id})
    MERGE (s1)-[r:ALTERNATIVE_FOR]->(s2)
    SET r.component_id = row.component_id,
        r.qualification_status = row.qualification_status
    """
    with driver.session() as session:
        session.run(cypher_alt, batch=[a.model_dump() for a in alternatives])
    counts["ALTERNATIVE_FOR"] = len(alternatives)

    # 6. SHIPS_TO (Facility -> Customer)
    shipments: list[FacilityShipsToCustomer] = []
    with open(data_dir / "shipments.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            shipments.append(
                FacilityShipsToCustomer(
                    facility_id=row["facility_id"],
                    customer_id=row["customer_id"],
                    annual_volume_units=int(row["annual_volume_units"]),
                )
            )
    cypher_ships_to = """
    UNWIND $batch AS row
    MATCH (f:Facility {id: row.facility_id})
    MATCH (cust:Customer {id: row.customer_id})
    MERGE (f)-[r:SHIPS_TO]->(cust)
    SET r.annual_volume_units = toInteger(row.annual_volume_units)
    """
    with driver.session() as session:
        session.run(cypher_ships_to, batch=[sh.model_dump() for sh in shipments])
    counts["SHIPS_TO"] = len(shipments)

    return counts


def get_graph_summary(driver: Driver) -> dict[str, int]:
    """Query Neo4j and return total counts of nodes and relationships."""
    summary: dict[str, int] = {}
    with driver.session() as session:
        node_res = session.run("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count")
        for record in node_res:
            label = record["label"] or "Unknown"
            summary[f"Node:{label}"] = int(record["count"])

        rel_res = session.run("MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count")
        for record in rel_res:
            rtype = record["type"] or "Unknown"
            summary[f"Rel:{rtype}"] = int(record["count"])
    return summary


def run_verification_queries(driver: Driver) -> None:
    """Execute sample Cypher queries from PRD §5.4 to verify graph traversals."""
    with driver.session() as session:
        print("\n--- Verifying Q1: Disrupted Port -> Exposed Products ---")
        q1 = """
        MATCH (port:Port {name: 'Port of Shanghai'})<-[:SHIPS_VIA]-(s:Supplier)
              -[:PRODUCES]->(c:Component)
              -[:PART_OF]->(p:Product)
        RETURN port.name AS port, s.name AS supplier,
               c.name AS component, p.name AS product, p.revenue_usd_annual AS revenue
        ORDER BY revenue DESC LIMIT 5
        """
        records = session.run(q1).data()
        for r in records:
            p_rev = r["revenue"]
            print(
                f"  Port: {r['port']} | Supplier: {r['supplier']} | "
                f"Component: {r['component']} | Product: {r['product']} ($ {p_rev:,.0f})"
            )

        print("\n--- Verifying Q2: Alternative Suppliers for Disrupted Component ---")
        q2 = """
        MATCH (s1:Supplier)-[r:ALTERNATIVE_FOR]->(s2:Supplier)
        MATCH (s1)-[:PRODUCES]->(c:Component {id: r.component_id})
        RETURN s1.name AS primary_supplier, s2.name AS alt_supplier,
               c.name AS component, r.qualification_status AS status
        LIMIT 3
        """
        records = session.run(q2).data()
        for r in records:
            print(
                f"  Primary: {r['primary_supplier']} -> Alt: {r['alt_supplier']} | "
                f"Component: {r['component']} ({r['status']})"
            )

        print("\n--- Verifying Q3: Sole-sourced Components in High-Risk Countries ---")
        q3 = """
        MATCH (s:Supplier)-[:PRODUCES]->(c:Component {is_sole_sourced: true})
              -[:PART_OF]->(p:Product)
        MATCH (s)-[:LOCATED_IN]->(country:Country)
        WHERE country.risk_index > 0.60
        RETURN DISTINCT c.name AS component, s.name AS supplier,
               country.name AS country, country.risk_index AS risk, p.name AS product
        LIMIT 5
        """
        records = session.run(q3).data()
        for r in records:
            print(
                f"  Component: {r['component']} (Sole-sourced) | "
                f"Supplier: {r['supplier']} in {r['country']} (Risk {r['risk']}) | "
                f"Product: {r['product']}"
            )


def ingest_all(driver: Driver, data_dir: Path) -> dict[str, int]:
    """Execute complete ingestion pipeline: constraints, nodes, edges, and verify."""
    print("Creating constraints and indexes...")
    create_constraints_and_indexes(driver)

    print("Loading nodes...")
    c_count = load_countries(driver, data_dir)
    p_count = load_ports(driver, data_dir)
    s_count = load_suppliers(driver, data_dir)
    f_count = load_facilities(driver, data_dir)
    cmp_count = load_components(driver, data_dir)
    prd_count = load_products(driver, data_dir)
    cust_count = load_customers(driver, data_dir)

    print(
        f"Loaded {c_count} countries, {p_count} ports, {s_count} suppliers, "
        f"{f_count} facilities, {cmp_count} components, {prd_count} products, "
        f"{cust_count} customers."
    )

    print("Loading relationships...")
    rel_counts = load_relationships(driver, data_dir)
    for rtype, count in rel_counts.items():
        print(f"  Loaded {count} {rtype} relationships.")

    summary = get_graph_summary(driver)
    print("\nNeo4j Knowledge Graph Summary:")
    for key, val in summary.items():
        print(f"  {key}: {val}")

    print("\nRunning verification queries...")
    run_verification_queries(driver)
    return summary


if __name__ == "__main__":
    settings = get_settings()
    data_path = Path("data/raw/synthetic")
    with get_neo4j_driver_from_settings(settings) as neo4j_driver:
        ingest_all(neo4j_driver, data_path)
