"""RSS feed parsing and news article extraction."""

import json
import time  # Added for struct_time type checking
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import mktime

import feedparser
import requests
from bs4 import BeautifulSoup

from infra.configuration import is_article_cache_enabled
from infra.sql_connection import connect_to_sql_sqlite
from infra.telegram_logging_handler import app_logger
from news.article_cache import (
    CachedArticle,
    article_exists_in_cache,
    save_article_to_cache,
)
from news.article_processor import ArticleProcessingError, process_article_with_ollama
from news.symbol_detector import detect_symbols_in_text
from source_repository import fetch_symbols


@dataclass(slots=True)
class RSSEntry:
    """Represents a parsed RSS entry from any feed source.

    Used for cross-feed aggregation and sorting before processing.
    """
    source: str
    title: str
    link: str
    published_time: datetime
    published_str: str
    class_name: str
    raw_entry: object


MAX_RELEVANT_ARTICLES = 10


def get_news():
    """Fetch news articles from various cryptocurrency RSS feeds.

    Always fetches from RSS feeds to ensure latest articles are available.
    The fetch_rss_news() method handles caching - it skips articles that
    are already cached and only fetches/caches new ones.

    Returns:
        JSON string of fetched articles (newly cached ones only)
    """
    # Always fetch from RSS feeds - fetch_rss_news() handles duplicate checking
    feeds = {
        "decrypt": {"url": "https://decrypt.co/feed", "class": "post-content"},
        "coindesk": {
            "url": "https://www.coindesk.com/arc/outboundfeeds/rss",
            "class": "document-body",
        },
        "newsBTC": {
            "url": "https://www.newsbtc.com/feed",
            "class": "entry-content",  # Updated from 'content-inner jeg_link_underline'
        },
        "coinJournal": {
            "url": "https://coinjournal.net/feed",
            "class": "post-article-content lg:col-span-8",
        },
        "coinpedia": {
            "url": "https://coinpedia.org/feed",
            "class": "entry-content entry clearfix",
        },
        "ambcrypto": {
            "url": "https://ambcrypto.com/feed/",
            "class": "single-post-main-middle",
        },
    }

    all_news = []
    for source, feed_info in feeds.items():
        all_news.extend(fetch_rss_news(feed_info["url"], source, feed_info["class"]))

    return json.dumps(all_news, indent=2)


def fetch_rss_news(feed_url, source, class_name):
    """Fetch and parse news articles from an RSS feed."""
    try:
        feed = feedparser.parse(feed_url)
        current_time = datetime.now(UTC)
        cache_enabled = is_article_cache_enabled()
        symbols_list = _load_symbols_for_detection(cache_enabled=cache_enabled)

        # First pass: collect up to MAX_RELEVANT_ARTICLES valid entries
        entries_to_process = []
        for entry in feed.entries:
            entry_link, _, _ = _extract_entry_fields(entry)
            if cache_enabled and article_exists_in_cache(entry_link):
                continue

            published_time = _resolve_published_time(entry, current_time)
            if current_time - published_time > timedelta(days=1):
                continue

            entries_to_process.append(entry)
            if len(entries_to_process) >= MAX_RELEVANT_ARTICLES:
                break

        # Second pass: process entries with progress
        latest_news: list[dict[str, object]] = []
        total_to_process = len(entries_to_process)
        for entry_index, entry in enumerate(entries_to_process):
            processed = _process_feed_entry(
                entry=entry,
                source=source,
                class_name=class_name,
                current_time=current_time,
                cache_enabled=cache_enabled,
                symbols_list=symbols_list,
                current_index=entry_index + 1,
                total=total_to_process,
            )

            if processed is None:
                continue

            cached_article, relevant_payload = processed

            if cache_enabled and cached_article is not None:
                save_article_to_cache(cached_article)

            if relevant_payload is not None:
                latest_news.append(relevant_payload)

    except (AttributeError, KeyError, ValueError, TypeError) as e:
        app_logger.error(f"Error fetching news from {feed_url}: {e!s}")
        return []
    else:
        return latest_news


def fetch_full_content(url, class_name):
    """Fetch the full content of a news article from its URL."""
    try:
        response = requests.get(url, timeout=30)
        soup = BeautifulSoup(response.content, "html.parser")

        article = soup.find("div", class_=class_name) or soup.find("article")
        if article:
            article_text = article.get_text()
            return "\n".join(line.strip() for line in article_text.splitlines() if line.strip())
    except (requests.RequestException, AttributeError, ValueError, TypeError) as e:
        app_logger.error(f"Error fetching full content from {url}: {e!s}")
        return "Failed to fetch full content"
    else:
        return "Failed to extract full content"


@dataclass(slots=True)
class ArticleEnrichmentResult:
    """Structured output from the AI enrichment step."""

    summary: str
    cleaned_content: str
    symbols: list[str]
    relevance_score: float | None
    is_relevant: bool
    notes: str


def _parse_rss_entry(
    entry: object,
    source: str,
    class_name: str,
    current_time: datetime,
) -> RSSEntry | None:
    """Parse a raw RSS entry into a normalized RSSEntry object.

    Args:
        entry: Raw feedparser entry object
        source: RSS feed source name (e.g., 'coindesk', 'decrypt')
        class_name: CSS class name for content extraction
        current_time: Current datetime for fallback published time

    Returns:
        RSSEntry object if parsing successful, None if entry is invalid
    """
    try:
        entry_link, entry_title, entry_published = _extract_entry_fields(entry)

        # Validate required fields
        if not entry_link or entry_link == "None" or not entry_title:
            return None

        published_time = _resolve_published_time(entry, current_time)

        return RSSEntry(
            source=source,
            title=entry_title,
            link=entry_link,
            published_time=published_time,
            published_str=entry_published,
            class_name=class_name,
            raw_entry=entry,
        )
    except (AttributeError, KeyError, ValueError, TypeError) as e:
        app_logger.warning(f"Failed to parse RSS entry from {source}: {e!s}")
        return None


def _is_entry_processable(entry: RSSEntry, *, cache_enabled: bool, current_time: datetime) -> bool:
    """Check if an RSS entry should be processed for AI analysis.

    Args:
        entry: RSSEntry object to check
        cache_enabled: Whether article caching is enabled
        current_time: Current datetime for age checking

    Returns:
        True if entry should be processed, False otherwise
    """
    # Skip if already cached
    if cache_enabled and article_exists_in_cache(entry.link):
        return False

    # Skip if older than 24 hours
    return current_time - entry.published_time <= timedelta(days=1)


def _load_symbols_for_detection(*, cache_enabled: bool) -> list:
    if not cache_enabled:
        return []

    try:
        with connect_to_sql_sqlite() as conn:
            return fetch_symbols(conn)
    except (ConnectionError, OSError, ValueError) as exc:
        app_logger.warning(f"Could not fetch symbols for detection: {exc!s}")
        return []


def _process_feed_entry(
    *,
    entry: object,
    source: str,
    class_name: str,
    current_time: datetime,
    cache_enabled: bool,
    symbols_list: list,
    current_index: int,
    total: int,
) -> tuple[CachedArticle | None, dict[str, object] | None] | None:
    entry_link, entry_title, entry_published = _extract_entry_fields(entry)

    if cache_enabled and article_exists_in_cache(entry_link):
        return None

    published_time = _resolve_published_time(entry, current_time)
    if current_time - published_time > timedelta(days=1):
        return None

    full_content = fetch_full_content(entry_link, class_name)
    detected_symbols = _detect_symbols(
        entry_title,
        full_content,
        cache_enabled=cache_enabled,
        symbols_list=symbols_list,
    )

    focus_symbols = [symbol.symbol_name for symbol in symbols_list] if symbols_list else None
    enrichment = _enrich_article_with_ai(
        title=entry_title,
        full_content=full_content,
        focus_symbols=focus_symbols,
        detected_symbols=detected_symbols,
        article_link=entry_link,
        current_index=current_index,
        total=total,
    )

    normalized_symbols = _normalize_symbols(enrichment.symbols or detected_symbols)
    processed_at = current_time.isoformat()

    article_payload = {
        "source": source,
        "title": entry_title,
        "link": entry_link,
        "published": entry_published,
        "content": enrichment.cleaned_content,
        "summary": enrichment.summary,
        "symbols": normalized_symbols,
        "relevance_score": enrichment.relevance_score,
        "is_relevant": enrichment.is_relevant,
        "processed_at": processed_at,
        "analysis_notes": enrichment.notes,
    }

    cached_article = None
    if cache_enabled:
        cached_article = CachedArticle(
            source=source,
            title=entry_title,
            link=entry_link,
            published=entry_published,
            fetched=current_time.isoformat(),
            content=enrichment.cleaned_content,
            symbols=normalized_symbols,
            summary=enrichment.summary,
            raw_content=full_content,
            relevance_score=enrichment.relevance_score,
            is_relevant=enrichment.is_relevant,
            processed_at=processed_at,
            analysis_notes=enrichment.notes,
        )

    relevant_payload = article_payload if enrichment.is_relevant else None

    return cached_article, relevant_payload


def _extract_entry_fields(entry: object) -> tuple[str, str, str]:
    entry_link = str(getattr(entry, "link", ""))
    entry_title = str(getattr(entry, "title", ""))
    entry_published = str(getattr(entry, "published", ""))
    return entry_link, entry_title, entry_published


def _resolve_published_time(entry: object, fallback: datetime) -> datetime:
    published_parsed = getattr(entry, "published_parsed", None)
    if isinstance(published_parsed, time.struct_time):
        return datetime.fromtimestamp(mktime(published_parsed), tz=UTC)
    return fallback


def _detect_symbols(
    title: str,
    content: str,
    *,
    cache_enabled: bool,
    symbols_list: list,
) -> list[str]:
    if not (cache_enabled and symbols_list):
        return []
    article_text = f"{title} {content}"
    return detect_symbols_in_text(article_text, symbols_list)


def _enrich_article_with_ai(
    *,
    title: str,
    full_content: str,
    focus_symbols: list[str] | None,
    detected_symbols: list[str],
    article_link: str,
    current_index: int,
    total: int,
) -> ArticleEnrichmentResult:
    if not full_content or not full_content.strip():
        return ArticleEnrichmentResult(
            summary="",
            cleaned_content=full_content,
            symbols=detected_symbols[:],
            relevance_score=None,
            is_relevant=False,
            notes="",
        )

    app_logger.info(f"🔄 Processing article {current_index}/{total}: {title[:50]}...")
    start_time = time.perf_counter()

    try:
        analysis = process_article_with_ollama(
            title=title,
            raw_content=full_content,
            focus_symbols=focus_symbols,
        )
    except ArticleProcessingError as exc:
        elapsed_time = time.perf_counter() - start_time
        notes = f"processing_error: {exc}"
        app_logger.warning(
            "Ollama processing failed for %s after %.2fs: %s",
            article_link,
            elapsed_time,
            exc,
        )
        return ArticleEnrichmentResult(
            summary="",
            cleaned_content=full_content,
            symbols=detected_symbols[:],
            relevance_score=None,
            is_relevant=True,
            notes=notes,
        )

    resolved_symbols = list(analysis.symbols) if analysis.symbols else detected_symbols[:]
    return ArticleEnrichmentResult(
        summary=analysis.summary,
        cleaned_content=analysis.cleaned_content,
        symbols=resolved_symbols,
        relevance_score=analysis.relevance_score,
        is_relevant=analysis.is_relevant,
        notes=analysis.reasoning,
    )


def _normalize_symbols(symbols: list[str]) -> list[str]:
    normalized = {
        symbol.strip().upper()
        for symbol in symbols
        if isinstance(symbol, str) and symbol.strip()
    }
    return sorted(normalized)


if __name__ == "__main__":
    pass
