"""Load processed news articles, extracted disruption events, and entity linkages into Neo4j."""

import json
from pathlib import Path

from neo4j import Driver

from api.config import Settings, get_settings
from api.dependencies import get_neo4j_driver_from_settings
from extraction.entity_resolve import resolve_entity
from extraction.pipeline import run_extraction_batch
from extraction.schemas import ArticleChunk, ExtractionPayload, ResolvedEntityReference
from ingestion.news_ingest import run_news_ingestion


def ensure_event_constraint(driver: Driver) -> None:
    """Ensure uniqueness constraint exists for Event nodes."""
    with driver.session() as session:
        session.run("CREATE CONSTRAINT event_id IF NOT EXISTS FOR (e:Event) REQUIRE e.id IS UNIQUE")


def load_supplier_and_component_registries(data_dir: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Load supplier and component lookup registries from synthetic CSVs."""
    import csv

    supplier_reg: dict[str, str] = {}
    component_reg: dict[str, str] = {}

    supp_file = data_dir / "suppliers.csv"
    if supp_file.exists():
        with open(supp_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                supplier_reg[row["name"]] = row["id"]

    comp_file = data_dir / "components.csv"
    if comp_file.exists():
        with open(comp_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                component_reg[row["name"]] = row["id"]

    return supplier_reg, component_reg


def ingest_articles_to_neo4j(driver: Driver, chunks: list[ArticleChunk]) -> int:
    """Upsert Article chunk nodes and NEXT_CHUNK sequence relationships into Neo4j."""
    chunk_dicts = [c.model_dump() for c in chunks]

    cypher_articles = """
    UNWIND $batch AS row
    MERGE (a:Article {id: row.id})
    SET a.title = row.title,
        a.source = row.source,
        a.url = row.url,
        a.published_date = row.published_date,
        a.chunk_index = toInteger(row.chunk_index),
        a.text = row.text,
        a.token_count = toInteger(row.token_count)
    """

    cypher_next_chunk = """
    UNWIND $batch AS row
    WITH row WHERE row.previous_chunk_id IS NOT NULL
    MATCH (prev:Article {id: row.previous_chunk_id})
    MATCH (curr:Article {id: row.id})
    MERGE (prev)-[:NEXT_CHUNK]->(curr)
    """

    with driver.session() as session:
        session.run(cypher_articles, batch=chunk_dicts)
        session.run(cypher_next_chunk, batch=chunk_dicts)

    return len(chunks)


def ingest_extracted_events_and_links(
    driver: Driver,
    extracted_records: list[tuple[ArticleChunk, ExtractionPayload]],
    supplier_reg: dict[str, str],
    component_reg: dict[str, str],
) -> dict[str, int]:
    """Upsert Event nodes, MENTIONS edges, and AFFECTS edges into Neo4j."""
    events_batch: list[dict[str, str]] = []
    mentions_batch: list[dict[str, str | float]] = []
    affects_batch: list[dict[str, str | float]] = []

    for chunk, payload in extracted_records:
        # 1. Events
        for ev in payload.events:
            events_batch.append(
                {
                    "id": ev.id,
                    "event_type": ev.event_type,
                    "description": ev.description,
                    "start_date": ev.start_date or chunk.published_date,
                    "severity": ev.severity,
                    "article_id": chunk.id,
                }
            )

        # 2. Resolved Entities & MENTIONS edges
        resolved_entities: list[ResolvedEntityReference] = []
        for ent in payload.entities:
            res = resolve_entity(
                ent,
                supplier_registry=supplier_reg,
                component_registry=component_reg,
            )
            resolved_entities.append(res)
            mentions_batch.append(
                {
                    "article_id": chunk.id,
                    "target_id": res.target_id,
                    "target_name": res.target_name,
                    "target_label": res.target_label,
                    "confidence": res.confidence,
                }
            )

        # 3. AFFECTS relationships from Events to Port/Supplier/Country
        for rel in payload.relationships:
            if rel.type == "AFFECTS":
                for ev in payload.events:
                    # Find matched target entity
                    for res in resolved_entities:
                        if (
                            res.original_name.lower() in rel.to_name.lower()
                            or rel.to_name.lower() in res.original_name.lower()
                        ):
                            affects_batch.append(
                                {
                                    "event_id": ev.id,
                                    "target_id": res.target_id,
                                    "target_label": res.target_label,
                                    "confidence": rel.confidence,
                                }
                            )

    cypher_events = """
    UNWIND $batch AS row
    MERGE (e:Event {id: row.id})
    SET e.type = row.event_type,
        e.description = row.description,
        e.start_date = row.start_date,
        e.severity = row.severity,
        e.status = 'active'
    WITH e, row
    MATCH (a:Article {id: row.article_id})
    MERGE (a)-[:MENTIONS {confidence: 1.0}]->(e)
    """

    cypher_mentions_ports = """
    UNWIND $batch AS row
    WITH row WHERE row.target_label = 'Port'
    MATCH (a:Article {id: row.article_id})
    MATCH (p:Port) WHERE p.id = row.target_id OR p.name = row.target_name
    MERGE (a)-[r:MENTIONS]->(p)
    SET r.confidence = toFloat(row.confidence)
    """

    cypher_mentions_countries = """
    UNWIND $batch AS row
    WITH row WHERE row.target_label = 'Country'
    MATCH (a:Article {id: row.article_id})
    MATCH (c:Country) WHERE c.code = row.target_id OR c.name = row.target_name
    MERGE (a)-[r:MENTIONS]->(c)
    SET r.confidence = toFloat(row.confidence)
    """

    cypher_mentions_suppliers = """
    UNWIND $batch AS row
    WITH row WHERE row.target_label = 'Supplier'
    MATCH (a:Article {id: row.article_id})
    MATCH (s:Supplier) WHERE s.id = row.target_id OR s.name = row.target_name
    MERGE (a)-[r:MENTIONS]->(s)
    SET r.confidence = toFloat(row.confidence)
    """

    cypher_mentions_components = """
    UNWIND $batch AS row
    WITH row WHERE row.target_label = 'Component'
    MATCH (a:Article {id: row.article_id})
    MATCH (c:Component) WHERE c.id = row.target_id OR c.name = row.target_name
    MERGE (a)-[r:MENTIONS]->(c)
    SET r.confidence = toFloat(row.confidence)
    """

    cypher_affects = """
    UNWIND $batch AS row
    MATCH (e:Event {id: row.event_id})
    MATCH (target) WHERE target.id = row.target_id OR target.code = row.target_id
    MERGE (e)-[r:AFFECTS]->(target)
    SET r.confidence = toFloat(row.confidence)
    """

    with driver.session() as session:
        session.run(cypher_events, batch=events_batch)
        session.run(cypher_mentions_ports, batch=mentions_batch)
        session.run(cypher_mentions_countries, batch=mentions_batch)
        session.run(cypher_mentions_suppliers, batch=mentions_batch)
        session.run(cypher_mentions_components, batch=mentions_batch)
        session.run(cypher_affects, batch=affects_batch)

    return {
        "events": len(events_batch),
        "mentions": len(mentions_batch),
        "affects": len(affects_batch),
    }


def verify_news_graph(driver: Driver) -> dict[str, int]:
    """Execute verification Cypher queries checking article and entity linkage counts."""
    stats: dict[str, int] = {}
    with driver.session() as session:
        # 1. Total articles
        res = session.run("MATCH (a:Article) RETURN count(a) AS total").single()
        stats["article_count"] = int(res["total"]) if res else 0

        # 2. Total events
        res = session.run("MATCH (e:Event) RETURN count(e) AS total").single()
        stats["event_count"] = int(res["total"]) if res else 0

        # 3. Total MENTIONS relationships
        res = session.run("MATCH ()-[r:MENTIONS]->() RETURN count(r) AS total").single()
        stats["mentions_count"] = int(res["total"]) if res else 0

        # 4. Total AFFECTS relationships
        res = session.run("MATCH ()-[r:AFFECTS]->() RETURN count(r) AS total").single()
        stats["affects_count"] = int(res["total"]) if res else 0

        # 5. Total NEXT_CHUNK relationships
        res = session.run("MATCH ()-[r:NEXT_CHUNK]->() RETURN count(r) AS total").single()
        stats["next_chunk_count"] = int(res["total"]) if res else 0

        # Spot-check sample article mentions
        sample_query = """
        MATCH (a:Article)-[:MENTIONS]->(n)
        RETURN a.title AS article,
               labels(n)[0] AS entity_type,
               coalesce(n.name, n.description) AS entity_name
        LIMIT 5
        """
        samples = session.run(sample_query).data()
        print("\n--- Spot-Check 5 Article Entity Linkages ---")
        for s in samples:
            print(f"  Article: {s['article'][:40]}... -> [{s['entity_type']}] {s['entity_name']}")

    return stats


def run_news_graph_pipeline(
    driver: Driver,
    news_dir: Path,
    synthetic_data_dir: Path,
    settings: Settings | None = None,
) -> dict[str, int]:
    """Execute complete end-to-end news ingestion, extraction, and graph loading pipeline."""
    cfg = settings or get_settings()

    print("Ensuring Event constraints...")
    ensure_event_constraint(driver)

    print("Step 1: Ingesting news articles into token chunks...")
    chunks_file = news_dir / "article_chunks.json"
    if chunks_file.exists():
        with open(chunks_file, encoding="utf-8") as f:
            data = json.load(f)
            chunks = [ArticleChunk.model_validate(item) for item in data]
    else:
        chunks = run_news_ingestion(news_dir)

    print(f"Loaded {len(chunks)} article chunks.")

    print("Step 2: Ingesting Article nodes and NEXT_CHUNK edges...")
    ingest_articles_to_neo4j(driver, chunks)

    print("Step 3: Loading entity resolution registries...")
    supplier_reg, component_reg = load_supplier_and_component_registries(synthetic_data_dir)

    print("Step 4: Running LLM/rule-based extraction pipeline...")
    extracted_records = run_extraction_batch(chunks, settings=cfg)
    print(f"Extracted features from {len(extracted_records)} chunks.")

    print("Step 5: Loading Events, MENTIONS, and AFFECTS edges into Neo4j...")
    link_stats = ingest_extracted_events_and_links(
        driver,
        extracted_records,
        supplier_reg,
        component_reg,
    )
    ev_c = link_stats["events"]
    men_c = link_stats["mentions"]
    aff_c = link_stats["affects"]
    print(f"Loaded {ev_c} events, {men_c} mentions, {aff_c} affects.")

    print("Step 6: Verifying news graph counts...")
    stats = verify_news_graph(driver)
    print("\nVerified News Graph Statistics:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    return stats


if __name__ == "__main__":
    app_settings = get_settings()
    news_path = Path("data/raw/news")
    synth_path = Path("data/raw/synthetic")

    with get_neo4j_driver_from_settings(app_settings) as n4j_driver:
        run_news_graph_pipeline(n4j_driver, news_path, synth_path, app_settings)
