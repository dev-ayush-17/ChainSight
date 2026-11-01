"""Embedding generation and vector index synchronization for Article and Supplier nodes."""

import hashlib
import logging
import math

from neo4j import Driver

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_DIM: int = 384


def compute_deterministic_embedding(text: str, dim: int = DEFAULT_EMBEDDING_DIM) -> list[float]:
    """Compute deterministic, unit-normalized 384-dimensional dense vector for input text."""
    if not text or not text.strip():
        return [0.0] * dim

    vec = [0.0] * dim
    words = text.lower().split()
    for w in words:
        h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 8) & 1) else -1.0
        vec[idx] += sign

    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return [0.0] * dim

    return [round(x / norm, 6) for x in vec]


def embed_texts(texts: list[str], use_fastembed: bool = False) -> list[list[float]]:
    """Generate dense 384-dimensional vector embeddings for a collection of text strings."""
    if use_fastembed:
        try:
            from fastembed import TextEmbedding

            model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
            embeddings = list(model.embed(texts))
            return [list(map(float, emb)) for emb in embeddings]
        except Exception as err:
            logger.debug(
                "FastEmbed inference skipped or unavailable (%s); using deterministic encoder", err
            )

    return [compute_deterministic_embedding(t) for t in texts]


def embed_query(query: str, use_fastembed: bool = False) -> list[float]:
    """Generate a single 384-dimensional dense embedding vector for a search query."""
    return embed_texts([query], use_fastembed=use_fastembed)[0]


def embed_and_upsert_articles(driver: Driver) -> int:
    """Read Article chunk nodes lacking embeddings, generate vectors, and write back to Neo4j."""
    fetch_cypher = """
    MATCH (a:Article)
    WHERE a.embedding IS NULL
    RETURN a.id AS id, a.text AS text
    LIMIT 200
    """
    with driver.session() as session:
        records = session.run(fetch_cypher).data()
        if not records:
            return 0

        ids = [str(r["id"]) for r in records]
        texts = [str(r["text"]) for r in records]
        embeddings = [compute_deterministic_embedding(t) for t in texts]

        batch = [{"id": i, "embedding": emb} for i, emb in zip(ids, embeddings, strict=True)]

        update_cypher = """
        UNWIND $batch AS row
        MATCH (a:Article {id: row.id})
        SET a.embedding = row.embedding
        """
        session.run(update_cypher, batch=batch)
        return len(batch)


def embed_and_upsert_suppliers(driver: Driver) -> int:
    """Generate description embeddings for Supplier nodes and update Neo4j."""
    fetch_cypher = """
    MATCH (s:Supplier)
    WHERE s.description_embedding IS NULL
    OPTIONAL MATCH (s)-[:PRODUCES]->(c:Component)
    RETURN s.id AS id,
           s.name AS name,
           s.tier AS tier,
           collect(DISTINCT c.name) AS components
    """
    with driver.session() as session:
        records = session.run(fetch_cypher).data()
        if not records:
            return 0

        batch = []
        for r in records:
            comps = ", ".join(r["components"][:5])
            desc = f"Tier {r['tier']} supplier {r['name']} producing components: {comps}"
            emb = compute_deterministic_embedding(desc)
            batch.append({"id": str(r["id"]), "embedding": emb})

        update_cypher = """
        UNWIND $batch AS row
        MATCH (s:Supplier {id: row.id})
        SET s.description_embedding = row.embedding
        """
        session.run(update_cypher, batch=batch)
        return len(batch)
