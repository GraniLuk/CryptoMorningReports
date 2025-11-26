"""RSS feed parsing and news article extraction."""

import calendar
import json
import time  # Added for struct_time type checking
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import feedparser
import requests
from bs4 import BeautifulSoup

from infra.configuration import is_article_cache_enabled
from infra.sql_connection import connect_to_sql_sqlite
from infra.telegram_logging_handler import app_logger
from news.article_cache import (
    CachedArticle,
    article_exists_in_cache,
    get_articles_for_symbol,
    save_article_to_cache,
)
from news.article_processor import ArticleProcessingError, process_article_with_ollama
from news.constants import CURRENT_REPORT_ARTICLE_LIMIT, NEWS_ARTICLE_LIMIT
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


def _collect_all_rss_entries(*, cache_enabled: bool, current_time: datetime) -> list[RSSEntry]:
    """Collect RSS entries from all feeds without processing them.

    Args:
        cache_enabled: Whether article caching is enabled
        current_time: Current datetime for age filtering

    Returns:
        List of RSSEntry objects from all feeds, sorted by published_time (newest first)
    """
    feeds = {
        "cointelegraph": {
            "url": "https://cointelegraph.com/rss",
            "class": "post-content",
            "required_hashtags": ["bitcoin-price", "price-analysis"],
        },
    }

    all_entries = []
    feed_stats = {}

    for source, feed_info in feeds.items():
        required_hashtags = feed_info.get("required_hashtags")
        feed_entries = _collect_entries_from_feed(
            feed_url=feed_info["url"],
            source=source,
            class_name=feed_info["class"],
            cache_enabled=cache_enabled,
            current_time=current_time,
            required_hashtags=required_hashtags,
        )
        all_entries.extend(feed_entries)
        feed_stats[source] = len(feed_entries)

    # Sort all entries by published time (newest first)
    all_entries.sort(key=lambda entry: entry.published_time, reverse=True)

    total_entries = len(all_entries)
    app_logger.info(
        f"Collected {total_entries} RSS entries from {len(feeds)} feeds: "
        f"{', '.join(f'{source}={count}' for source, count in feed_stats.items())}",
    )

    return all_entries


def _has_required_hashtags(article_link: str, required_hashtags: list[str]) -> bool:
    """Check if article page contains at least one of the required hashtags.

    Args:
        article_link: URL of the article to check
        required_hashtags: List of hashtags to look for
            (e.g., ['bitcoin-price', 'price-analysis'])

    Returns:
        True if article contains at least one required hashtag, False otherwise
    """
    try:
        response = requests.get(article_link, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")

        # Find all links with href containing '/tags/'
        tag_links = soup.find_all("a", href=True)

        # Extract hashtag names from URLs
        # (e.g., '/tags/bitcoin-price' -> 'bitcoin-price')
        article_hashtags = set()
        for link in tag_links:
            href = link.get("href", "")  # type: ignore[union-attr]
            if isinstance(href, str) and "/tags/" in href:
                hashtag = href.split("/tags/")[-1].lower()
                article_hashtags.add(hashtag)

        # Check if any required hashtag is present
        return bool(article_hashtags & set(required_hashtags))

    except (requests.RequestException, AttributeError, ValueError, TypeError) as e:
        app_logger.warning(f"Failed to check hashtags for {article_link}: {e!s}")
        # On error, include the article (fail open rather than fail closed)
        return True


def _collect_entries_from_feed(
    *,
    feed_url: str,
    source: str,
    class_name: str,
    cache_enabled: bool,
    current_time: datetime,
    required_hashtags: list[str] | None = None,
) -> list[RSSEntry]:
    """Collect entries from a single RSS feed.

    Args:
        feed_url: URL of the RSS feed
        source: Source name (e.g., 'coindesk')
        class_name: CSS class for content extraction
        cache_enabled: Whether caching is enabled
        current_time: Current datetime
        required_hashtags: Optional list of hashtags to filter by
            (e.g., ['bitcoin-price', 'price-analysis'])

    Returns:
        List of RSSEntry objects from this feed
    """
    try:
        feed = feedparser.parse(feed_url)
        entries = []

        for entry in feed.entries:
            parsed_entry = _parse_rss_entry(
                entry=entry,
                source=source,
                class_name=class_name,
                current_time=current_time,
            )

            if parsed_entry is None:
                continue

            # Filter out entries that shouldn't be processed
            if not _is_entry_processable(
                entry=parsed_entry,
                cache_enabled=cache_enabled,
                current_time=current_time,
            ):
                continue

            # Filter by hashtags if required (for Cointelegraph)
            if required_hashtags and not _has_required_hashtags(
                article_link=parsed_entry.link,
                required_hashtags=required_hashtags,
            ):
                continue

            entries.append(parsed_entry)

    except (AttributeError, KeyError, ValueError, TypeError) as e:
        app_logger.warning(f"Failed to collect entries from {feed_url}: {e!s}")
        return []
    else:
        return entries


def _process_entries_until_target(
    *,
    entries: list[RSSEntry],
    current_time: datetime,
    cache_enabled: bool,
    symbols_list: list,
    target_relevant: int,
) -> tuple[list[dict[str, object]], int]:
    """Process RSS entries until target number of relevant articles are found.

    Args:
        entries: List of RSSEntry objects to process (sorted by published_time)
        current_time: Current datetime for processing
        cache_enabled: Whether article caching is enabled
        symbols_list: List of symbols for detection
        target_relevant: Target number of relevant articles to find

    Returns:
        Tuple of (relevant_articles, total_processed)
    """
    relevant_articles: list[dict[str, object]] = []
    total_processed = 0
    start_time = datetime.now(UTC)

    for entry in entries:
        total_processed += 1

        # Process this entry
        processed = _process_feed_entry(
            entry=entry.raw_entry,
            source=entry.source,
            class_name=entry.class_name,
            current_time=current_time,
            cache_enabled=cache_enabled,
            symbols_list=symbols_list,
        )

        if processed is None:
            continue

        cached_article, relevant_payload = processed

        # Save to cache if enabled
        if cache_enabled and cached_article is not None:
            save_article_to_cache(cached_article)

        # Add to results if relevant
        if relevant_payload is not None:
            relevant_articles.append(relevant_payload)

            # Log processed article
            elapsed_time = _extract_elapsed_time(relevant_payload)
            human_time = _format_elapsed_time(elapsed_time)
            relevance_score = relevant_payload.get("relevance_score") or 0.0
            is_relevant = relevant_payload.get("is_relevant", False)
            app_logger.info(
                f"✅ {relevant_payload['source']} | {relevant_payload['title']} | "
                f"{human_time} | {len(relevant_articles)}/{target_relevant} relevant | "
                f"relevance: {relevance_score:.2f}, relevant: {is_relevant} | "
                f"{relevant_payload['link']}",
            )

            # Early stopping: we have enough relevant articles
            if len(relevant_articles) >= target_relevant:
                break

    # Final summary logging
    total_time = (datetime.now(UTC) - start_time).total_seconds()
    estimated_saved_time = _estimate_time_saved(total_processed, len(entries), total_time)

    app_logger.info(
        f"✅ Completed: Processed {total_processed}/{len(entries)} articles in {total_time:.1f}s, "
        f"found {len(relevant_articles)}/{target_relevant} relevant "
        f"(saved ~{estimated_saved_time:.1f}s)",
    )

    return relevant_articles, total_processed


def _estimate_time_saved(processed: int, total_available: int, actual_time: float) -> float:
    """Estimate time saved by early stopping.

    Args:
        processed: Number of articles actually processed
        total_available: Total articles available
        actual_time: Time spent processing

    Returns:
        Estimated time that would have been spent processing remaining articles
    """
    if processed == 0:
        return 0.0

    avg_time_per_article = actual_time / processed
    remaining_articles = total_available - processed
    return avg_time_per_article * remaining_articles


def get_news(target_relevant: int | None = None) -> str:
    """Fetch news articles from various cryptocurrency RSS feeds using lazy evaluation.

    Collects all RSS entries from all feeds first, sorts them by published time (newest first),
    then processes entries one-by-one until finding target_relevant relevant articles.
    This optimizes processing by avoiding unnecessary work on older/irrelevant articles.

    Args:
        target_relevant: Number of relevant articles to find. If None, uses NEWS_ARTICLE_LIMIT.

    Returns:
        JSON string containing a list of newly cached relevant articles.
        Each article includes metadata like title, link, published date, and detected symbols.
        Only articles that were processed and cached during this call are returned.
        The returned articles are sorted by relevance and recency.
    """
    if target_relevant is None:
        target_relevant = NEWS_ARTICLE_LIMIT

    start_time = datetime.now(UTC)
    current_time = datetime.now(UTC)
    cache_enabled = is_article_cache_enabled()
    symbols_list = _load_symbols_for_detection(cache_enabled=cache_enabled)

    # Phase 1: Collect all entries from all feeds
    all_entries = _collect_all_rss_entries(
        cache_enabled=cache_enabled,
        current_time=current_time,
    )

    # Phase 2: Process entries in sorted order until we have enough relevant articles
    relevant_articles, total_processed = _process_entries_until_target(
        entries=all_entries,
        current_time=current_time,
        cache_enabled=cache_enabled,
        symbols_list=symbols_list,
        target_relevant=target_relevant,
    )

    # Performance logging
    end_time = datetime.now(UTC)
    total_time = end_time - start_time
    articles_found = len(relevant_articles)

    from infra.telegram_logging_handler import app_logger  # noqa: PLC0415

    app_logger.info(
        f"RSS processing completed: {articles_found}/{target_relevant} target articles found, "
        f"{total_processed} articles processed in {total_time.total_seconds():.1f}s "
        f"(avg: {total_time.total_seconds() / max(total_processed, 1):.1f}s per article)",
    )

    if articles_found < target_relevant:
        app_logger.warning(
            f"RSS processing: Only found {articles_found}/{target_relevant} target articles. "
            f"Consider increasing time window or checking feed availability.",
        )

    return json.dumps(relevant_articles, indent=2)


def fetch_and_cache_articles_for_symbol(
    symbol: str,
    hours: int = 24,
) -> list[CachedArticle]:
    """Fetch fresh RSS articles, cache new ones, and return all articles for a symbol.

    This function ensures the cache is up-to-date by:
    1. Fetching fresh articles from RSS feeds (limited to CURRENT_REPORT_ARTICLE_LIMIT)
    2. Caching any new articles (skips duplicates)
    3. Returning all cached articles for the specified symbol

    Args:
        symbol: Cryptocurrency symbol to search for (e.g., 'BTC', 'ETH')
        hours: Number of hours to look back. Defaults to 24.

    Returns:
        List of CachedArticle instances that mention the symbol,
        sorted by published date (newest first)
    """
    # Fetch fresh articles from RSS feeds (will cache new ones automatically)
    # Use CURRENT_REPORT_ARTICLE_LIMIT for current reports instead of NEWS_ARTICLE_LIMIT
    try:
        get_news(target_relevant=CURRENT_REPORT_ARTICLE_LIMIT)
    except (OSError, ValueError, KeyError) as e:
        app_logger.warning(f"Error fetching fresh RSS articles: {e!s}")

    # Return all cached articles for the symbol
    return get_articles_for_symbol(symbol, hours)


def fetch_rss_news(feed_url, source, class_name):
    """Fetch and parse news articles from an RSS feed.

    DEPRECATED: This function uses the old per-feed processing architecture.
    Use get_news() instead, which provides optimized cross-feed sorting and lazy evaluation.

    This function is kept for backward compatibility with existing tests.
    """
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
            if len(entries_to_process) >= NEWS_ARTICLE_LIMIT:
                break

        # Second pass: process entries with progress
        latest_news: list[dict[str, object]] = []
        for entry in entries_to_process:
            processed = _process_feed_entry(
                entry=entry,
                source=source,
                class_name=class_name,
                current_time=current_time,
                cache_enabled=cache_enabled,
                symbols_list=symbols_list,
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
    elapsed_time: float  # Time in seconds taken to process the article with AI


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
        "elapsed_time": enrichment.elapsed_time,
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
        return datetime.fromtimestamp(calendar.timegm(published_parsed), tz=UTC)
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
) -> ArticleEnrichmentResult:
    if not full_content or not full_content.strip():
        return ArticleEnrichmentResult(
            summary="",
            cleaned_content=full_content,
            symbols=detected_symbols[:],
            relevance_score=None,
            is_relevant=False,
            notes="",
            elapsed_time=0.0,
        )

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
            elapsed_time=elapsed_time,
        )

    resolved_symbols = list(analysis.symbols) if analysis.symbols else detected_symbols[:]
    return ArticleEnrichmentResult(
        summary=analysis.summary,
        cleaned_content=analysis.cleaned_content,
        symbols=resolved_symbols,
        relevance_score=analysis.relevance_score,
        is_relevant=analysis.is_relevant,
        notes=analysis.reasoning,
        elapsed_time=analysis.elapsed_time,
    )


def _normalize_symbols(symbols: list[str]) -> list[str]:
    normalized = {
        symbol.strip().upper() for symbol in symbols if isinstance(symbol, str) and symbol.strip()
    }
    return sorted(normalized)


def _extract_elapsed_time(payload: dict) -> float:
    """Extract and convert elapsed_time from payload safely."""
    elapsed_time_raw = payload.get("elapsed_time", 0.0)
    if isinstance(elapsed_time_raw, (int, float)):
        return float(elapsed_time_raw)
    try:
        return float(elapsed_time_raw)
    except (ValueError, TypeError):
        return 0.0


def _format_elapsed_time(seconds: float) -> str:
    """Format elapsed time in human readable format (e.g., '3m 25s')."""
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    if minutes > 0:
        return f"{minutes}m {remaining_seconds}s"
    return f"{remaining_seconds}s"


if __name__ == "__main__":
    pass
