"""Article caching functionality for RSS news articles.

This module provides functionality to cache RSS news articles as markdown files
with YAML frontmatter, enabling faster retrieval and reducing API calls.

Key Functions:
- `save_article_to_cache()` - Save an article to disk with YAML frontmatter
- `load_article_from_cache()` - Load an article from disk
- `get_articles_for_symbol()` - Retrieve cached articles for a specific symbol
- `get_recent_articles()` - Retrieve all recent cached articles
- `fetch_and_cache_articles_for_symbol()` - Fetch fresh RSS articles, cache new ones,
  and return all articles for a symbol (ensures up-to-date data)
- `cleanup_old_articles()` - Delete articles older than specified age
- `get_cache_statistics()` - Get cache statistics (count, size, age)
"""

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

import frontmatter
import yaml
from slugify import slugify

from infra.configuration import get_article_cache_root
from infra.telegram_logging_handler import app_logger
from news.rss_parser import CURRENT_REPORT_ARTICLE_LIMIT, get_news


def parse_article_date(date_string: str) -> datetime:
    """Parse article date from either ISO format or RSS format.

    Args:
        date_string: Date string in ISO format or RSS format

    Returns:
        datetime object with timezone

    Raises:
        ValueError: If date string cannot be parsed
    """
    try:
        # Try ISO format first (e.g., '2025-11-01T15:30:45+00:00')
        return datetime.fromisoformat(date_string)
    except (ValueError, AttributeError):
        try:
            # Try RSS format (e.g., 'Sat, 01 Nov 2025 15:30:45 +0000')
            return parsedate_to_datetime(date_string)
        except (ValueError, TypeError, AttributeError) as e:
            msg = f"Cannot parse date: {date_string}"
            raise ValueError(msg) from e


@dataclass
class CachedArticle:
    """Represents a cached news article.

    Attributes:
        source: RSS source name (e.g., 'coindesk', 'decrypt')
        title: Article title
        link: Original article URL
        published: Publication timestamp (ISO 8601 format)
        fetched: Timestamp when article was fetched (ISO 8601 format)
        content: Cleaned or AI-enhanced article content
        symbols: List of cryptocurrency symbols mentioned in the article
        summary: AI-generated article summary
        raw_content: Original scraped article text prior to AI cleanup
        relevance_score: AI-assigned relevance score in range [0, 1]
        is_relevant: Flag indicating if the article should be used for analysis
        processed_at: Timestamp when AI processing occurred (ISO 8601)
        analysis_notes: Additional AI-provided reasoning or metadata
    """

    source: str
    title: str
    link: str
    published: str
    fetched: str
    content: str
    symbols: list[str] = field(default_factory=list)
    summary: str = ""
    raw_content: str | None = None
    relevance_score: float | None = None
    is_relevant: bool = False
    processed_at: str | None = None
    analysis_notes: str = ""


def get_cache_directory() -> Path:
    """Get the cache directory path.

    Returns:
        Path object pointing to the cache directory (news/cache/)
    """
    return get_article_cache_root()


def ensure_cache_directory() -> Path:
    """Ensure the cache directory exists.

    Returns:
        Path object pointing to the cache directory

    Raises:
        ValueError: If the cache root directory is not writable
    """
    cache_root = get_article_cache_root()

    # Check if the cache root directory is writable
    if cache_root.exists() and not os.access(cache_root, os.W_OK):
        msg = f"Cache root directory is not writable: {cache_root}"
        raise ValueError(msg)
    if not cache_root.exists():
        # Try to create the root directory
        try:
            cache_root.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            msg = f"Cannot create cache root directory: {cache_root} - {e}"
            raise ValueError(msg) from e

    return cache_root


def get_article_filename(article: CachedArticle) -> str:
    """Generate a safe filename for a cached article.

    Args:
        article: CachedArticle instance

    Returns:
        Filename in format: source_slugified-title.md
    """
    slug = slugify(article.title, max_length=100)
    return f"{article.source}_{slug}.md"


def save_article_to_cache(article: CachedArticle) -> Path:
    """Save an article to the cache as a markdown file with YAML frontmatter.

    Args:
        article: CachedArticle instance to save

    Returns:
        Path to the saved file
    """
    cache_dir = ensure_cache_directory()
    filename = get_article_filename(article)
    filepath = cache_dir / filename

    # Create frontmatter metadata
    metadata = {
        "source": article.source,
        "title": article.title,
        "link": article.link,
        "published": article.published,
        "fetched": article.fetched,
        "symbols": article.symbols,
        "summary": article.summary,
        "raw_content": article.raw_content,
        "relevance_score": article.relevance_score,
        "is_relevant": article.is_relevant,
        "processed_at": article.processed_at,
        "analysis_notes": article.analysis_notes,
    }

    # Create frontmatter post with content
    post = frontmatter.Post(article.content, **metadata)

    # Write to file
    with filepath.open("w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))

    return filepath


def load_article_from_cache(filepath: Path) -> CachedArticle | None:
    """Load a cached article from a markdown file.

    Args:
        filepath: Path to the cached article file

    Returns:
        CachedArticle instance or None if file doesn't exist or is invalid
    """
    if not filepath.exists():
        return None

    try:
        with filepath.open(encoding="utf-8") as f:
            post = frontmatter.load(f)

        # Extract symbols with proper type handling
        symbols_value = post.get("symbols", [])
        symbols_list = list(symbols_value) if isinstance(symbols_value, list) else []

        summary_value = post.get("summary", "")
        summary = str(summary_value) if isinstance(summary_value, str) else ""

        raw_content_value = post.get("raw_content")
        raw_content = str(raw_content_value) if isinstance(raw_content_value, str) else None

        relevance_value = post.get("relevance_score")
        relevance_score = (
            float(relevance_value) if isinstance(relevance_value, (int, float)) else None
        )

        is_relevant_value = post.get("is_relevant", False)
        is_relevant = bool(is_relevant_value)

        processed_at_value = post.get("processed_at")
        processed_at = str(processed_at_value) if isinstance(processed_at_value, str) else None

        analysis_notes_value = post.get("analysis_notes", "")
        analysis_notes = str(analysis_notes_value) if isinstance(analysis_notes_value, str) else ""

        content_value = post.content if isinstance(post.content, str) else str(post.content)

        return CachedArticle(
            source=str(post.get("source", "")),
            title=str(post.get("title", "")),
            link=str(post.get("link", "")),
            published=str(post.get("published", "")),
            fetched=str(post.get("fetched", "")),
            content=content_value,
            symbols=symbols_list,
            summary=summary,
            raw_content=raw_content,
            relevance_score=relevance_score,
            is_relevant=is_relevant,
            processed_at=processed_at,
            analysis_notes=analysis_notes,
        )
    except (OSError, ValueError, KeyError, yaml.YAMLError):
        return None


def get_cached_articles() -> list[CachedArticle]:
    """Retrieve all cached articles.

    Returns:
        List of CachedArticle instances
    """
    cache_dir = get_cache_directory()

    if not cache_dir.exists():
        return []

    articles = []
    for filepath in cache_dir.glob("*.md"):
        article = load_article_from_cache(filepath)
        if article is not None:
            articles.append(article)

    return articles


def article_exists_in_cache(link: str) -> bool:
    """Check if an article with a specific URL exists in the cache.

    Args:
        link: Article URL to check

    Returns:
        True if article exists in cache, False otherwise
    """
    cached_articles = get_cached_articles()
    return any(article.link == link for article in cached_articles)


def get_articles_for_symbol(
    symbol: str,
    hours: int = 24,
) -> list[CachedArticle]:
    """Retrieve cached articles mentioning a specific cryptocurrency symbol.

    Args:
        symbol: Cryptocurrency symbol to search for (e.g., 'BTC', 'ETH')
        hours: Number of hours to look back. Defaults to 24.

    Returns:
        List of CachedArticle instances that mention the symbol,
        sorted by published date (newest first)
    """
    now = datetime.now(tz=UTC)
    cutoff_time = now - timedelta(hours=hours)

    # Normalize symbol to uppercase for comparison
    symbol_upper = symbol.upper()

    # Collect articles from cache
    articles_with_symbol = []
    all_articles = get_cached_articles()

    for article in all_articles:
        # Check if symbol is in the article's symbol list
        if symbol_upper in [s.upper() for s in article.symbols]:
            # Parse published date and check if within time range
            try:
                published_dt = parse_article_date(article.published)
                if published_dt >= cutoff_time:
                    articles_with_symbol.append(article)
            except (ValueError, AttributeError) as e:
                # If date parsing fails, skip this article
                app_logger.warning(
                    f"Failed to parse date for article '{article.title}': {e!s}",
                )
                continue

    # Sort by published date, newest first
    articles_with_symbol.sort(
        key=lambda a: parse_article_date(a.published),
        reverse=True,
    )

    return articles_with_symbol


def get_recent_articles(hours: int = 24) -> list[CachedArticle]:
    """Retrieve all cached articles from the last N hours.

    Args:
        hours: Number of hours to look back. Defaults to 24.

    Returns:
        List of CachedArticle instances within the time range,
        sorted by published date (newest first)
    """
    now = datetime.now(tz=UTC)
    cutoff_time = now - timedelta(hours=hours)

    # Collect articles from cache
    recent_articles = []
    all_articles = get_cached_articles()

    for article in all_articles:
        # Parse published date and check if within time range
        try:
            published_dt = parse_article_date(article.published)
            if published_dt >= cutoff_time:
                recent_articles.append(article)
        except (ValueError, AttributeError) as e:
            # If date parsing fails, skip this article
            app_logger.warning(
                f"Failed to parse date for article '{article.title}': {e!s}",
            )
            continue

    # Sort by published date, newest first
    recent_articles.sort(
        key=lambda a: parse_article_date(a.published),
        reverse=True,
    )

    return recent_articles


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
    except Exception as e:
        app_logger.warning(f"Error fetching fresh RSS articles: {e!s}")

    # Return all cached articles for the symbol
    return get_articles_for_symbol(symbol, hours)


def cleanup_old_articles(max_age_hours: int = 24) -> int:
    """Delete cached articles older than the specified age.

    Args:
        max_age_hours: Maximum age of articles to keep. Defaults to 24 hours.

    Returns:
        Number of articles deleted
    """
    deleted_count = 0
    cutoff_time = datetime.now(tz=UTC) - timedelta(hours=max_age_hours)

    cache_dir = get_cache_directory()

    # Skip if directory doesn't exist
    if not cache_dir.exists():
        return 0

    # Get all markdown files
    markdown_files = list(cache_dir.glob("*.md"))

    for markdown_file in markdown_files:
        try:
            article = load_article_from_cache(markdown_file)

            # Skip if article failed to load
            if article is None:
                continue

            # Parse published date and check if older than cutoff
            published_dt = parse_article_date(article.published)
            if published_dt < cutoff_time:
                # Delete the markdown file
                markdown_file.unlink()
                deleted_count += 1

        except Exception as e:
            app_logger.warning(f"Error processing {markdown_file}: {e!s}")

    return deleted_count


def get_cache_statistics() -> dict[str, int | float | str]:
    """Get statistics about the article cache.

    Returns:
        Dictionary with cache statistics:
        - total_articles: Number of cached articles
        - total_size_mb: Total disk space used (MB)
        - oldest_article_hours: Age of oldest article (hours)
        - newest_article_hours: Age of newest article (hours)
        - cache_path: Path to cache root directory
    """
    total_articles = 0
    total_size_bytes = 0
    oldest_time: datetime | None = None
    newest_time: datetime | None = None

    # Get cache directory
    cache_dir = get_cache_directory()

    # Skip if directory doesn't exist
    if not cache_dir.exists():
        return {
            "total_articles": 0,
            "total_size_mb": 0.0,
            "oldest_article_hours": 0.0,
            "newest_article_hours": 0.0,
            "cache_path": str(cache_dir),
        }

    # Get all markdown files
    markdown_files = list(cache_dir.glob("*.md"))

    for markdown_file in markdown_files:
        try:
            article = load_article_from_cache(markdown_file)

            # Skip if article failed to load
            if article is None:
                continue

            total_articles += 1

            # Calculate file size
            total_size_bytes += markdown_file.stat().st_size

            # Track oldest/newest
            published_dt = parse_article_date(article.published)
            if oldest_time is None or published_dt < oldest_time:
                oldest_time = published_dt
            if newest_time is None or published_dt > newest_time:
                newest_time = published_dt

        except Exception:
            pass

    # Calculate age in hours
    now = datetime.now(tz=UTC)
    oldest_hours = (now - oldest_time).total_seconds() / 3600 if oldest_time else 0
    newest_hours = (now - newest_time).total_seconds() / 3600 if newest_time else 0

    return {
        "total_articles": total_articles,
        "total_size_mb": round(total_size_bytes / (1024 * 1024), 2),
        "oldest_article_hours": round(oldest_hours, 1),
        "newest_article_hours": round(newest_hours, 1),
        "cache_path": str(cache_dir),
    }
