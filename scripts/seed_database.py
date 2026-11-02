"""Automated one-command database seeding for local development and Docker deployment."""

import logging
from pathlib import Path

from api.config import get_settings
from api.dependencies import get_neo4j_driver_from_settings
from data.generate_synthetic import run_generation
from embedding.embed import embed_and_upsert_articles, embed_and_upsert_suppliers
from ingestion.load_graph import ingest_all
from ingestion.load_news_graph import run_news_graph_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def seed_all() -> None:
    """Execute complete end-to-end data generation, ingestion, extraction, and vector embedding."""
    settings = get_settings()
    data_dir = Path("data")
    synth_dir = Path("data/raw/synthetic")
    news_dir = Path("data/raw/news")

    logger.info("=== STEP 1/4: Generating Synthetic Supply Chain Dataset ===")
    run_generation(data_dir)

    with get_neo4j_driver_from_settings(settings) as driver:
        logger.info("=== STEP 2/4: Loading Knowledge Graph into Neo4j ===")
        ingest_all(driver, synth_dir)

        logger.info("=== STEP 3/4: Ingesting News & Extracting Entity Links ===")
        run_news_graph_pipeline(driver, news_dir, synth_dir, settings)

        logger.info("=== STEP 4/4: Generating Dense Vector Embeddings in Neo4j ===")
        art_count = embed_and_upsert_articles(driver)
        sup_count = embed_and_upsert_suppliers(driver)
        logger.info(
            "Vector indexing complete! Upserted %d article vectors and %d supplier vectors.",
            art_count,
            sup_count,
        )

    logger.info("🎉 Database seeding completed successfully! All services ready.")


if __name__ == "__main__":
    seed_all()
