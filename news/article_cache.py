"""Article caching functionality for RSS news articles.

This module provides functionality to cache RSS news articles as markdown files
with YAML frontmatter, enabling faster retrieval and reducing API calls.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import frontmatter  # type: ignore[import-untyped]
from slugify import slugify  # type: ignore[import-untyped]


@dataclass
class CachedArticle:
    """Represents a cached news article.

    Attributes:
        source: RSS source name (e.g., 'coindesk', 'decrypt')
        title: Article title
        link: Original article URL
        published: Publication timestamp (ISO 8601 format)
        fetched: Timestamp when article was fetched (ISO 8601 format)
        content: Full article content (HTML or text)
        symbols: List of cryptocurrency symbols mentioned in the article
    """

    source: str
    title: str
    link: str
    published: str
    fetched: str
    content: str
    symbols: list[str] = field(default_factory=list)


def get_cache_directory(date: datetime | None = None) -> Path:
    """Get the cache directory path for a specific date.

    Args:
        date: Date for the cache directory. Defaults to today.

    Returns:
        Path object pointing to the cache directory (news/cache/YYYY-MM-DD/)
    """
    if date is None:
        date = datetime.now(tz=UTC)

    cache_root = Path(__file__).parent / "cache"
    return cache_root / date.strftime("%Y-%m-%d")


def ensure_cache_directory(date: datetime | None = None) -> Path:
    """Ensure the cache directory exists for a specific date.

    Args:
        date: Date for the cache directory. Defaults to today.

    Returns:
        Path object pointing to the created cache directory
    """
    cache_dir = get_cache_directory(date)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_article_filename(article: CachedArticle) -> str:
    """Generate a safe filename for a cached article.

    Args:
        article: CachedArticle instance

    Returns:
        Filename in format: source_slugified-title.md
    """
    slug = slugify(article.title, max_length=100)
    return f"{article.source}_{slug}.md"


def save_article_to_cache(article: CachedArticle, date: datetime | None = None) -> Path:
    """Save an article to the cache as a markdown file with YAML frontmatter.

    Args:
        article: CachedArticle instance to save
        date: Date for the cache directory. Defaults to today.

    Returns:
        Path to the saved file
    """
    cache_dir = ensure_cache_directory(date)
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

        return CachedArticle(
            source=post.get("source", ""),
            title=post.get("title", ""),
            link=post.get("link", ""),
            published=post.get("published", ""),
            fetched=post.get("fetched", ""),
            content=post.content,
            symbols=post.get("symbols", []),
        )
    except (OSError, ValueError, KeyError):
        return None


def get_cached_articles(date: datetime | None = None) -> list[CachedArticle]:
    """Retrieve all cached articles for a specific date.

    Args:
        date: Date to retrieve articles for. Defaults to today.

    Returns:
        List of CachedArticle instances
    """
    cache_dir = get_cache_directory(date)

    if not cache_dir.exists():
        return []

    articles = []
    for filepath in cache_dir.glob("*.md"):
        article = load_article_from_cache(filepath)
        if article is not None:
            articles.append(article)

    return articles


def article_exists_in_cache(link: str, date: datetime | None = None) -> bool:
    """Check if an article with a specific URL exists in the cache.

    Args:
        link: Article URL to check
        date: Date to check in. Defaults to today.

    Returns:
        True if article exists in cache, False otherwise
    """
    cached_articles = get_cached_articles(date)
    return any(article.link == link for article in cached_articles)
