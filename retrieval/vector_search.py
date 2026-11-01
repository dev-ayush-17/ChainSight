"""Vector similarity search over Article chunks with 1-hop graph neighborhood expansion."""

from neo4j import Driver

from retrieval.schemas import VectorSearchResult


def search_articles_vector(
    driver: Driver,
    query_vector: list[float],
    top_k: int = 5,
    min_score: float = 0.50,
) -> list[VectorSearchResult]:
    """Search Article vector index and expand 1-hop neighborhood of mentioned entities."""
    cypher_vector_search = """
    CALL db.index.vector.queryNodes('article_embedding', $top_k, $query_vector)
    YIELD node AS article, score
    WHERE score >= $min_score
    OPTIONAL MATCH (article)-[:MENTIONS]->(entity)
    RETURN article.id AS chunk_id,
           article.title AS title,
           article.source AS source,
           article.published_date AS published_date,
           article.text AS text,
           score,
           collect(DISTINCT coalesce(entity.id, entity.code, entity.name)) AS mentioned_ids
    ORDER BY score DESC
    """
    results: list[VectorSearchResult] = []

    with driver.session() as session:
        try:
            records = session.run(
                cypher_vector_search,
                top_k=top_k,
                query_vector=query_vector,
                min_score=min_score,
            ).data()
        except Exception:
            # Fallback if vector index is not yet indexed in local development
            records = []

        for row in records:
            mentioned = [str(x) for x in row["mentioned_ids"] if x]
            # Expand 1-hop neighborhood for mentioned entities
            expanded_ids: list[str] = []
            if mentioned:
                cypher_expand = """
                UNWIND $node_ids AS nid
                MATCH (n) WHERE n.id = nid OR n.code = nid
                MATCH (n)-[r]-(neighbor)
                RETURN DISTINCT coalesce(neighbor.id, neighbor.code, neighbor.name) AS neighbor_id
                LIMIT 20
                """
                exp_res = session.run(cypher_expand, node_ids=mentioned).data()
                expanded_ids = [str(r["neighbor_id"]) for r in exp_res if r["neighbor_id"]]

            results.append(
                VectorSearchResult(
                    chunk_id=str(row["chunk_id"]),
                    title=str(row["title"]),
                    source=str(row["source"]),
                    published_date=str(row["published_date"]),
                    text=str(row["text"]),
                    score=float(row["score"]),
                    mentioned_node_ids=mentioned,
                    expanded_node_ids=expanded_ids,
                )
            )

    return results


def search_articles_fallback_text(
    driver: Driver,
    keywords: list[str],
    top_k: int = 5,
) -> list[VectorSearchResult]:
    """Search articles using full-text or substring matching as fallback when vector offline."""
    if not keywords:
        cypher = """
        MATCH (a:Article)
        OPTIONAL MATCH (a)-[:MENTIONS]->(entity)
        RETURN a.id AS chunk_id, a.title AS title, a.source AS source,
               a.published_date AS published_date, a.text AS text,
               collect(DISTINCT coalesce(entity.id, entity.code, entity.name)) AS mentioned_ids
        LIMIT $top_k
        """
        params = {"top_k": top_k}
    else:
        cypher = """
        MATCH (a:Article)
        WHERE any(kw IN $keywords WHERE toLower(a.text) CONTAINS toLower(kw))
        OPTIONAL MATCH (a)-[:MENTIONS]->(entity)
        RETURN a.id AS chunk_id, a.title AS title, a.source AS source,
               a.published_date AS published_date, a.text AS text,
               collect(DISTINCT coalesce(entity.id, entity.code, entity.name)) AS mentioned_ids
        LIMIT $top_k
        """
        params = {"keywords": keywords, "top_k": top_k}

    results: list[VectorSearchResult] = []
    with driver.session() as session:
        records = session.run(cypher, **params).data()
        for idx, row in enumerate(records):
            mentioned = [str(x) for x in row["mentioned_ids"] if x]
            results.append(
                VectorSearchResult(
                    chunk_id=str(row["chunk_id"]),
                    title=str(row["title"]),
                    source=str(row["source"]),
                    published_date=str(row["published_date"]),
                    text=str(row["text"]),
                    score=round(1.0 - (idx * 0.05), 2),
                    mentioned_node_ids=mentioned,
                    expanded_node_ids=[],
                )
            )
    return results
