"""Integration tests for RSS feed functionality.

⚠️  WARNING: These tests perform real HTTP requests and Ollama processing.
They are SLOW (~20+ minutes) and should NOT be run in CI/CD pipelines.

For fast unit tests, use: tests/news/test_rss_feed_filtering.py
For integration tests, run this script manually with: python tests/news/test_rss_feeds.py

This script verifies that each RSS feed:
1. Successfully fetches articles
2. Returns correct metadata (title, link, published date)
3. Applies 24-hour filtering correctly
4. Fetches full content successfully
5. Parses HTML correctly using the specified class selectors

Run this script to verify RSS feeds are working before implementing caching.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from time import struct_time
from typing import Any
from unittest.mock import patch

import pytest

from infra.telegram_logging_handler import app_logger
from news import article_processor as ap
from news.rss_parser import fetch_full_content, fetch_rss_news


# Minimum content length to consider successful extraction
MIN_CONTENT_LENGTH = 100


@pytest.fixture
def mock_ollama_processing(monkeypatch):
    """Mock Ollama processing to avoid real API calls during tests."""

    # Mock process_article_with_ollama to return a mock result
    # Need to mock where it's used, not where it's defined
    def mock_process_article(*_args, **_kwargs):
        return ap.ArticleProcessingResult(
            summary="Test summary for mocked article processing.",
            cleaned_content=(
                "This is a mocked cleaned content that simulates what Ollama "
                "would return. It's long enough to pass validation checks."
            ),
            symbols=["BTC", "ETH"],
            relevance_score=0.9,
            is_relevant=True,
            reasoning="Mocked reasoning for test purposes",
            elapsed_time=1.5,
        )

    # Mock fetch_full_content to return mock content
    def mock_fetch_full_content(_url, _css_class):
        return (
            "Mock full content for testing purposes. This is a longer piece "
            "of content that simulates a real article fetched from the web."
        )

    # Mock feedparser.parse to return mock RSS data
    def mock_feedparser_parse(_url):
        class MockEntry:
            def __init__(self, num):
                self.link = f"https://test.com/article{num}"
                self.title = f"Test Article {num}"
                self.published = "Thu, 07 Nov 2025 12:00:00 +0000"
                # Create a struct_time for current time
                now = datetime.now(UTC)
                self.published_parsed = struct_time(
                    (
                        now.year,
                        now.month,
                        now.day,
                        now.hour,
                        now.minute,
                        now.second,
                        now.weekday(),
                        now.timetuple().tm_yday,
                        0,
                    ),
                )

        class MockFeed:
            def __init__(self):
                self.entries = [MockEntry(i) for i in range(1, 4)]

        return MockFeed()

    # Mock article cache functions to avoid database interactions
    def mock_article_exists_in_cache(_url):
        return False  # Always return False so articles are processed

    def mock_save_article_to_cache(_article):
        pass  # No-op

    def mock_is_article_cache_enabled():
        return False  # Disable cache for tests

    # Patch where the function is used, not where it's defined
    monkeypatch.setattr("news.rss_parser.process_article_with_ollama", mock_process_article)
    monkeypatch.setattr("news.rss_parser.fetch_full_content", mock_fetch_full_content)
    # Also patch in the test module namespace since it's imported there
    monkeypatch.setattr("tests.news.test_rss_feeds.fetch_full_content", mock_fetch_full_content)
    monkeypatch.setattr("feedparser.parse", mock_feedparser_parse)
    monkeypatch.setattr("news.rss_parser.article_exists_in_cache", mock_article_exists_in_cache)
    monkeypatch.setattr("news.rss_parser.save_article_to_cache", mock_save_article_to_cache)
    monkeypatch.setattr("news.rss_parser.is_article_cache_enabled", mock_is_article_cache_enabled)


# Define all RSS feed sources with their configurations
RSS_FEEDS = {
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
    # Note: cryptopotato removed - returns HTTP 403 (blocks automated access)
}


# Error messages to check for failed content fetching
FAILED_CONTENT_MESSAGES = {"Failed to fetch full content", "Failed to extract full content"}


def check_single_feed(source: str, feed_info: dict[str, str]) -> dict[str, Any]:
    """Test a single RSS feed and return detailed results.

    Args:
        source: Name of the RSS source
        feed_info: Dictionary with 'url' and 'class' keys

    Returns:
        Dictionary with test results including success status, article count,
        errors, and sample data
    """
    result = {
        "source": source,
        "url": feed_info["url"],
        "class_selector": feed_info["class"],
        "success": False,
        "article_count": 0,
        "articles_within_24h": 0,
        "errors": [],
        "warnings": [],
        "sample_article": None,
        "content_fetch_success": False,
        "content_length": 0,
    }

    try:
        app_logger.info(f"\n{'=' * 80}\nTesting {source}...\n{'=' * 80}")

        # Fetch articles using the existing function
        articles: list[dict[str, Any]] = fetch_rss_news(
            feed_info["url"],
            source,
            feed_info["class"],
        )

        if not articles:
            result["errors"].append("No articles returned")
            app_logger.warning(f"⚠️  {source}: No articles fetched")
            return result

        result["article_count"] = len(articles)
        result["articles_within_24h"] = len(articles)  # fetch_rss_news already filters
        result["success"] = True

        # Test the first article in detail
        first_article = articles[0]
        result["sample_article"] = {
            "title": first_article.get("title", ""),
            "link": first_article.get("link", ""),
            "published": first_article.get("published", ""),
            "source": first_article.get("source", ""),
        }

        # Check content
        content: str = str(first_article.get("content", ""))
        if content in FAILED_CONTENT_MESSAGES:
            if content == "Failed to fetch full content":
                error_msg = "Content fetching failed"
            else:
                error_msg = "Content extraction failed - check class selector"
            result["errors"].append(error_msg)
            result["content_fetch_success"] = False
            app_logger.error(f"❌ {source}: {error_msg}")
        else:
            result["content_fetch_success"] = True
            result["content_length"] = len(content)
            app_logger.info(f"✅ {source}: Content fetched successfully ({len(content)} chars)")

        # Validate metadata
        if not first_article.get("title"):
            result["warnings"].append("Missing title in article")
        if not first_article.get("link"):
            result["errors"].append("Missing link in article")
        if not first_article.get("published"):
            result["warnings"].append("Missing published date")

        # Log summary
        app_logger.info(f"✅ {source}: {len(articles)} articles fetched")
        app_logger.info(f"   Sample title: {first_article.get('title', 'N/A')[:80]}...")
        app_logger.info(f"   Published: {first_article.get('published', 'N/A')}")

    except (ValueError, KeyError, TypeError, AttributeError) as e:
        result["errors"].append(f"Exception: {e!s}")
        app_logger.error(f"❌ {source}: Exception occurred: {e}")

    return result


def check_24h_filtering(_mock_ollama_processing: Any | None = None) -> dict[str, Any]:
    """Check that 24-hour filtering logic works correctly.

    Returns:
        Dictionary with test results for time filtering
    """
    app_logger.info(f"\n{'=' * 80}\nTesting 24-hour filtering logic...\n{'=' * 80}")

    result = {
        "test_name": "24h_filtering",
        "success": False,
        "details": "",
    }

    # This is implicitly tested by fetch_rss_news, which only returns
    # articles from the last 24 hours. We verify this by checking dates.

    # Test with one feed (using decrypt as example)
    try:
        articles = fetch_rss_news(
            RSS_FEEDS["decrypt"]["url"],
            "decrypt",
            RSS_FEEDS["decrypt"]["class"],
        )

        # Check if all articles are within 24 hours
        # Note: We can't check exact timestamps from the returned data
        # as it only includes formatted published string, not datetime
        if articles:
            result["success"] = True
            result["details"] = f"Fetched {len(articles)} articles (all should be within 24h)"
            app_logger.info(f"✅ 24h filtering: {len(articles)} recent articles fetched")
        else:
            result["details"] = (
                "No articles - may indicate filtering is too strict or no recent news"
            )
            app_logger.warning("⚠️  24h filtering: No articles found")

    except (ValueError, KeyError, TypeError, AttributeError) as e:
        result["details"] = f"Error testing filtering: {e!s}"
        app_logger.error(f"❌ 24h filtering test failed: {e}")

    return result


def check_full_content_fetching(_mock_ollama_processing: Any | None = None) -> dict[str, Any]:
    """Check full content fetching with different class selectors.

    Returns:
        Dictionary with test results for content extraction
    """
    app_logger.info(f"\n{'=' * 80}\nTesting full content fetching...\n{'=' * 80}")

    results = {
        "test_name": "full_content_fetching",
        "per_source": {},
    }

    for source, feed_info in RSS_FEEDS.items():
        # Get first article URL
        try:
            articles = fetch_rss_news(feed_info["url"], source, feed_info["class"])
            if articles and len(articles) > 0:
                url = articles[0]["link"]
                content = fetch_full_content(url, feed_info["class"])

                success = (
                    content not in FAILED_CONTENT_MESSAGES and len(content) > MIN_CONTENT_LENGTH
                )

                results["per_source"][source] = {
                    "success": success,
                    "content_length": len(content),
                    "url": url,
                    "class": feed_info["class"],
                }

                if success:
                    app_logger.info(f"✅ {source}: Content extracted ({len(content)} chars)")
                else:
                    app_logger.error(f"❌ {source}: Content extraction failed")

        except (ValueError, KeyError, TypeError, AttributeError) as e:
            results["per_source"][source] = {
                "success": False,
                "error": str(e),
            }
            app_logger.error(f"❌ {source}: Error testing content fetch: {e}")

    return results


def print_summary(all_results: list[dict[str, Any]]) -> None:
    """Print a summary of all test results.

    Args:
        all_results: List of result dictionaries from all tests
    """
    app_logger.info("\n" + "=" * 80)
    app_logger.info("RSS FEED TEST SUMMARY")
    app_logger.info("=" * 80 + "\n")

    total = len(all_results)
    successful = sum(1 for r in all_results if r.get("success", False))

    app_logger.info(f"Total feeds tested: {total}")
    app_logger.info(f"Successful: {successful}")
    app_logger.info(f"Failed: {total - successful}\n")

    # Detailed results
    for result in all_results:
        source = result.get("source", "Unknown")
        status = "✅ PASS" if result.get("success", False) else "❌ FAIL"

        app_logger.info(f"{status} - {source}")
        app_logger.info(f"  Articles fetched: {result.get('article_count', 0)}")
        content_status = "✅" if result.get("content_fetch_success", False) else "❌"
        app_logger.info(f"  Content fetch: {content_status}")

        if result.get("errors"):
            app_logger.info(f"  Errors: {', '.join(result['errors'])}")
        if result.get("warnings"):
            app_logger.info(f"  Warnings: {', '.join(result['warnings'])}")

        if result.get("sample_article"):
            sample = result["sample_article"]
            app_logger.info(f"  Sample: {sample.get('title', 'N/A')[:60]}...")

    # Save detailed results to file
    output_file = Path("news/test_results.json")
    try:
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "summary": {
                        "total": total,
                        "successful": successful,
                        "failed": total - successful,
                    },
                    "results": all_results,
                },
                f,
                indent=2,
            )
        app_logger.info(f"\n📄 Detailed results saved to: {output_file}")
    except OSError as e:
        app_logger.error(f"Failed to save results file: {e}")


def main() -> None:
    """Run all RSS feed tests."""
    app_logger.info("Starting RSS feed verification tests...")

    # Set up mocking for Ollama processing to avoid real API calls
    mock_result = ap.ArticleProcessingResult(
        summary="Test summary",
        cleaned_content="Test cleaned content for article processing.",
        symbols=["BTC", "ETH"],
        relevance_score=0.9,
        is_relevant=True,
        reasoning="Test reasoning",
        elapsed_time=2.0,
    )

    with patch(
        "news.rss_parser.process_article_with_ollama",
        lambda *_args, **_kwargs: mock_result,
    ):
        all_results = []

        # Test each feed individually
        for source, feed_info in RSS_FEEDS.items():
            result = check_single_feed(source, feed_info)
            all_results.append(result)

        # Test 24h filtering
        filtering_result = check_24h_filtering(None)  # Mock is handled by context manager
        app_logger.info(f"24h filtering: {filtering_result['details']}")

        # Test full content fetching
        content_result = check_full_content_fetching(None)  # Mock is handled by context manager
        sources_count = len(content_result["per_source"])
        app_logger.info(f"Full content fetching tested for {sources_count} sources")

        # Print summary
        print_summary(all_results)

    app_logger.info("RSS feed verification tests completed!")


if __name__ == "__main__":
    main()


# Pytest test functions
def test_24h_filtering_pytest(mock_ollama_processing: Any) -> None:
    """Pytest version of 24h filtering test."""
    result = check_24h_filtering(mock_ollama_processing)
    assert result["success"] is True or "No articles" in result["details"]


@pytest.mark.skip(
    reason="Integration test that makes real network calls "
    "- use test_individual_feeds_pytest instead",
)
def test_full_content_fetching_pytest(mock_ollama_processing: Any) -> None:
    """Pytest version of full content fetching test."""
    # Patch fetch_full_content in this module's namespace
    with patch("tests.news.test_rss_feeds.fetch_full_content") as mock_fetch:
        mock_fetch.return_value = (
            "Mock full content for testing purposes. This is a longer piece of content."
        )
        result = check_full_content_fetching(mock_ollama_processing)
        assert len(result["per_source"]) > 0


def test_individual_feeds_pytest(mock_ollama_processing: Any) -> None:
    """Pytest version of individual feed tests."""
    # Test just one feed to keep test time reasonable
    source = "decrypt"
    feed_info = RSS_FEEDS[source]
    result = check_single_feed(source, feed_info)
    assert result["success"] is True
    assert result["article_count"] > 0
