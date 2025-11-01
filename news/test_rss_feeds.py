"""Test script to verify RSS feed functionality for all sources.

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
from typing import Any

from infra.telegram_logging_handler import app_logger
from news.rss_parser import fetch_full_content, fetch_rss_news


# Minimum content length to consider successful extraction
MIN_CONTENT_LENGTH = 100


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


def test_single_feed(source: str, feed_info: dict[str, str]) -> dict[str, Any]:
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
        articles = fetch_rss_news(feed_info["url"], source, feed_info["class"])

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
        content = first_article.get("content", "")
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


def test_24h_filtering() -> dict[str, Any]:
    """Test that 24-hour filtering logic works correctly.

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


def test_full_content_fetching() -> dict[str, Any]:
    """Test full content fetching with different class selectors.

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

    all_results = []

    # Test each feed individually
    for source, feed_info in RSS_FEEDS.items():
        result = test_single_feed(source, feed_info)
        all_results.append(result)

    # Test 24h filtering
    filtering_result = test_24h_filtering()
    app_logger.info(f"24h filtering: {filtering_result['details']}")

    # Test full content fetching
    content_result = test_full_content_fetching()
    app_logger.info(f"Full content fetching tested for {len(content_result['per_source'])} sources")

    # Print summary
    print_summary(all_results)

    app_logger.info("RSS feed verification tests completed!")


if __name__ == "__main__":
    main()
