"""RSS feed parsing and news article extraction."""

import json
import time  # Added for struct_time type checking
from datetime import UTC, datetime, timedelta
from time import mktime

import feedparser
import requests
from bs4 import BeautifulSoup

from infra.configuration import is_article_cache_enabled
from infra.telegram_logging_handler import app_logger
from news.article_cache import (
    CachedArticle,
    article_exists_in_cache,
    get_cached_articles,
    save_article_to_cache,
)


def get_news():
    """Fetch news articles from various cryptocurrency RSS feeds.

    If article caching is enabled, returns cached articles from today.
    Otherwise, fetches fresh articles from RSS feeds.
    """
    # Check if caching is enabled
    if is_article_cache_enabled():
        # Try to get cached articles first
        cached_articles = get_cached_articles()
        if cached_articles:
            # Convert CachedArticle objects to dict format
            articles_dict = [
                {
                    "source": article.source,
                    "title": article.title,
                    "link": article.link,
                    "published": article.published,
                    "content": article.content,
                }
                for article in cached_articles
            ]
            app_logger.info(f"Loaded {len(articles_dict)} articles from cache")
            return json.dumps(articles_dict, indent=2)

    # No cache or cache disabled - fetch from RSS feeds
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
    """Fetch and parse news articles from an RSS feed.

    If article caching is enabled, saves fetched articles to cache.
    """
    try:
        feed = feedparser.parse(feed_url)
        latest_news = []
        current_time = datetime.now(UTC)
        cache_enabled = is_article_cache_enabled()

        for entry in feed.entries:
            # Extract fields with type safety
            entry_link = str(entry.link) if hasattr(entry, "link") else ""
            entry_title = str(entry.title) if hasattr(entry, "title") else ""
            entry_published = str(entry.published) if hasattr(entry, "published") else ""

            # Skip if already cached (when caching is enabled)
            if cache_enabled and article_exists_in_cache(entry_link):
                continue

            # Make published_time timezone-aware by adding UTC timezone
            if hasattr(entry, "published_parsed") and isinstance(
                entry.published_parsed,
                time.struct_time,
            ):
                published_time = datetime.fromtimestamp(mktime(entry.published_parsed), tz=UTC)
            else:
                # Fallback to current time if published_parsed is not valid
                published_time = current_time

            if current_time - published_time <= timedelta(days=1):
                full_content = fetch_full_content(entry_link, class_name)

                article_dict = {
                    "source": source,
                    "title": entry_title,
                    "link": entry_link,
                    "published": entry_published,
                    "content": full_content,
                }
                latest_news.append(article_dict)

                # Save to cache if enabled
                if cache_enabled:
                    cached_article = CachedArticle(
                        source=source,
                        title=entry_title,
                        link=entry_link,
                        published=entry_published,
                        fetched=current_time.isoformat(),
                        content=full_content,
                        symbols=[],  # Will be populated in Phase 3
                    )
                    save_article_to_cache(cached_article)

            max_news_items = 10
            if len(latest_news) >= max_news_items:
                break

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


if __name__ == "__main__":
    pass
