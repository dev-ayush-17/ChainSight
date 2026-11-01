"""Unit tests for news ingestion, cleaning, and token-based chunking."""

from extraction.schemas import RawArticle
from ingestion.news_ingest import (
    chunk_article_text,
    clean_html_text,
    compute_chunk_id,
    get_curated_disruption_articles,
    matches_supply_chain_keywords,
)


def test_clean_html_text_removes_tags_and_whitespace() -> None:
    """Verify clean_html_text strips HTML tags, scripts, and collapses spaces."""
    raw = "<p>Port of <b>Shanghai</b> is congested.&nbsp; <script>alert(1);</script></p>"
    cleaned = clean_html_text(raw)
    assert cleaned == "Port of Shanghai is congested."


def test_matches_supply_chain_keywords() -> None:
    """Verify matches_supply_chain_keywords identifies disruption terms."""
    assert matches_supply_chain_keywords("Severe port strike delays shipments.")
    assert matches_supply_chain_keywords("Semiconductor shortage affects laptop production.")
    assert not matches_supply_chain_keywords("Celebrity attending red carpet event tonight.")


def test_compute_chunk_id_deterministic() -> None:
    """Verify compute_chunk_id produces identical IDs for identical URL and chunk index."""
    id1 = compute_chunk_id("https://example.com/news/1", 0)
    id2 = compute_chunk_id("https://example.com/news/1", 0)
    id3 = compute_chunk_id("https://example.com/news/1", 1)
    assert id1 == id2
    assert id1.startswith("art_")
    assert id1 != id3


def test_chunk_article_text_creates_valid_chunks() -> None:
    """Verify chunk_article_text produces sequential chunks with previous_chunk_id links."""
    # Create article with ~300 tokens
    content = "The Port of Shanghai is experiencing unprecedented vessel congestion. " * 30
    article = RawArticle(
        title="Shanghai Congestion Alert",
        source="Maritime News",
        url="https://example.com/shanghai-test",
        published_date="2024-09-18",
        content=content,
    )

    chunks = chunk_article_text(article, chunk_size=150, chunk_overlap=30, min_chunk_tokens=40)
    assert len(chunks) >= 2
    assert chunks[0].previous_chunk_id is None
    assert chunks[1].previous_chunk_id == chunks[0].id
    assert all(c.token_count > 0 for c in chunks)


def test_get_curated_disruption_articles_count() -> None:
    """Verify get_curated_disruption_articles returns a substantial corpus."""
    articles = get_curated_disruption_articles()
    assert len(articles) >= 45
    assert any("Strike" in a.title for a in articles)
    assert any("Shanghai" in a.title for a in articles)
