"""News ingestion, cleaning, deduplication, and token-based chunking pipeline."""

import contextlib
import hashlib
import html
import re
from datetime import datetime
from pathlib import Path

import feedparser
import tiktoken

from data.news_corpus import get_benchmark_news_articles
from extraction.schemas import ArticleChunk, RawArticle

SUPPLY_CHAIN_KEYWORDS: list[str] = [
    "port strike",
    "shipping disruption",
    "semiconductor shortage",
    "supply chain",
    "logistics delay",
    "trade embargo",
    "dockworkers",
    "freight rates",
    "port congestion",
    "panama canal",
    "red sea",
    "shanghai port",
    "container shortage",
    "component shortage",
    "labor strike",
    "export control",
]

DEFAULT_RSS_FEEDS: list[tuple[str, str]] = [
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    (
        "Reuters Business",
        "https://news.google.com/rss/search?q=port+supply+chain+shipping+strike&hl=en-US&gl=US&ceid=US:en",
    ),
    ("Supply Chain Brain", "https://www.supplychainbrain.com/rss/articles"),
]


def clean_html_text(raw_html: str) -> str:
    """Strip HTML markup, unescape entities, and normalize whitespace."""
    if not raw_html:
        return ""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def matches_supply_chain_keywords(text: str) -> bool:
    """Determine whether text mentions key supply chain disruption terms."""
    lowered = text.lower()
    return any(keyword in lowered for keyword in SUPPLY_CHAIN_KEYWORDS)


def compute_chunk_id(url: str, chunk_index: int) -> str:
    """Generate deterministic SHA-256 derived identifier for article chunk."""
    content_key = f"{url.strip()}::{chunk_index}".encode()
    return f"art_{hashlib.sha256(content_key).hexdigest()[:16]}"


def chunk_article_text(
    article: RawArticle,
    chunk_size: int = 400,
    chunk_overlap: int = 50,
    min_chunk_tokens: int = 100,
) -> list[ArticleChunk]:
    """Segment raw article content into deterministic overlapping token chunks."""
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(article.content)

    if len(tokens) < min_chunk_tokens:
        if len(tokens) >= 40:
            chunk_id = compute_chunk_id(article.url, 0)
            return [
                ArticleChunk(
                    id=chunk_id,
                    title=article.title,
                    source=article.source,
                    url=article.url,
                    published_date=article.published_date,
                    chunk_index=0,
                    text=article.content,
                    token_count=len(tokens),
                    previous_chunk_id=None,
                )
            ]
        return []

    chunks: list[ArticleChunk] = []
    step = chunk_size - chunk_overlap
    prev_chunk_id: str | None = None

    for chunk_idx, i in enumerate(range(0, len(tokens), step)):
        chunk_token_slice = tokens[i : i + chunk_size]
        if len(chunk_token_slice) < min_chunk_tokens and chunks:
            break

        chunk_text = encoding.decode(chunk_token_slice).strip()
        chunk_id = compute_chunk_id(article.url, chunk_idx)
        chunk = ArticleChunk(
            id=chunk_id,
            title=article.title,
            source=article.source,
            url=article.url,
            published_date=article.published_date,
            chunk_index=chunk_idx,
            text=chunk_text,
            token_count=len(chunk_token_slice),
            previous_chunk_id=prev_chunk_id,
        )
        chunks.append(chunk)
        prev_chunk_id = chunk_id

    return chunks


def fetch_rss_articles(feed_urls: list[tuple[str, str]] | None = None) -> list[RawArticle]:
    """Fetch and parse live RSS feeds, filtering for supply chain articles."""
    feeds = feed_urls or DEFAULT_RSS_FEEDS
    articles: list[RawArticle] = []

    for source_name, feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries:
                title = clean_html_text(getattr(entry, "title", ""))
                summary = clean_html_text(getattr(entry, "summary", ""))
                link = getattr(entry, "link", "")

                full_text = f"{title}. {summary}".strip()
                if not matches_supply_chain_keywords(full_text):
                    continue

                pub_date = datetime.now().strftime("%Y-%m-%d")
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    with contextlib.suppress(Exception):
                        pub_date = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d")

                articles.append(
                    RawArticle(
                        title=title,
                        source=source_name,
                        url=link
                        or f"https://chainsight.internal/article/{hashlib.md5(title.encode()).hexdigest()[:8]}",
                        published_date=pub_date,
                        content=full_text,
                    )
                )
        except Exception:
            continue

    return articles


def get_curated_disruption_articles() -> list[RawArticle]:
    """Return pre-curated authentic supply chain disruption articles as reference fallback."""
    return get_benchmark_news_articles()


def run_news_ingestion(
    output_dir: Path,
    fetch_live_rss: bool = True,
    chunk_size: int = 250,
    chunk_overlap: int = 40,
    min_chunk_tokens: int = 50,
) -> list[ArticleChunk]:
    """Execute news collection, cleaning, deduplication, chunking, and persist to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    articles_map: dict[str, RawArticle] = {}

    # 1. Curated baseline supply chain disruption articles
    curated = get_curated_disruption_articles()
    for art in curated:
        articles_map[art.url] = art

    # 2. Live RSS feeds if requested
    if fetch_live_rss:
        try:
            rss_articles = fetch_rss_articles()
            for art in rss_articles:
                if art.url not in articles_map:
                    articles_map[art.url] = art
        except Exception:
            pass

    # 3. Chunk all articles
    all_chunks: list[ArticleChunk] = []
    seen_chunk_ids: set[str] = set()

    for article in articles_map.values():
        chunks = chunk_article_text(
            article=article,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_tokens=min_chunk_tokens,
        )
        for c in chunks:
            if c.id not in seen_chunk_ids:
                seen_chunk_ids.add(c.id)
                all_chunks.append(c)

    # 4. Save to JSON file
    out_file = output_dir / "article_chunks.json"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("[" + ",\n".join(c.model_dump_json() for c in all_chunks) + "]\n")

    return all_chunks


if __name__ == "__main__":
    chunks = run_news_ingestion(Path("data/raw/news"))
    msg = f"News ingestion complete: {len(chunks)} chunks saved."
    print(msg)
