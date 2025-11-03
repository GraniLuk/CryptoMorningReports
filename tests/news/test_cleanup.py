"""Test cleanup and statistics functions for article cache."""

import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from news.article_cache import (
    CachedArticle,
    cleanup_old_articles,
    get_cache_statistics,
    save_article_to_cache,
)


def test_cleanup_and_statistics() -> None:
    """Test cleanup_old_articles and get_cache_statistics functions."""
    # Create test cache directory
    test_cache_root = Path(__file__).parent / "cache"

    # Clean up any existing test cache
    if test_cache_root.exists():
        shutil.rmtree(test_cache_root)

    print("\n=== Testing Cleanup and Statistics Functions ===\n")

    # Create test articles with different ages
    now = datetime.now(tz=UTC)

    # Recent article (2 hours old)
    recent_article = CachedArticle(
        source="test-source",
        title="Recent Article",
        link="https://example.com/recent",
        published=(now - timedelta(hours=2)).isoformat(),
        fetched=now.isoformat(),
        content="Recent content",
        symbols=["BTC"],
    )

    # Old article (26 hours old)
    old_article = CachedArticle(
        source="test-source",
        title="Old Article",
        link="https://example.com/old",
        published=(now - timedelta(hours=26)).isoformat(),
        fetched=now.isoformat(),
        content="Old content",
        symbols=["ETH"],
    )

    # Very old article (50 hours old)
    very_old_article = CachedArticle(
        source="test-source",
        title="Very Old Article",
        link="https://example.com/very-old",
        published=(now - timedelta(hours=50)).isoformat(),
        fetched=now.isoformat(),
        content="Very old content",
        symbols=["BNB"],
    )

    # Save all articles (explicitly using their published dates)
    print("Saving test articles...")
    save_article_to_cache(recent_article, now - timedelta(hours=2))
    save_article_to_cache(old_article, now - timedelta(hours=26))
    save_article_to_cache(very_old_article, now - timedelta(hours=50))
    print("✓ 3 articles saved\n")

    # Get initial statistics
    print("=== Initial Cache Statistics ===")
    stats = get_cache_statistics()
    print(f"Total articles: {stats['total_articles']}")
    print(f"Total size: {stats['total_size_mb']} MB")
    print(f"Oldest article: {stats['oldest_article_hours']:.1f} hours old")
    print(f"Newest article: {stats['newest_article_hours']:.1f} hours old")
    print(f"Cache path: {stats['cache_path']}\n")

    assert stats["total_articles"] == 3, "Should have 3 articles initially"
    assert float(stats["oldest_article_hours"]) > 49, "Oldest should be ~50 hours"
    assert float(stats["newest_article_hours"]) < 3, "Newest should be ~2 hours"

    # Cleanup articles older than 24 hours
    print("=== Cleaning up articles older than 24 hours ===")
    deleted = cleanup_old_articles(max_age_hours=24)
    print(f"✓ Deleted {deleted} articles\n")

    assert deleted == 2, "Should delete 2 old articles"

    # Get statistics after cleanup
    print("=== Cache Statistics After Cleanup ===")
    stats_after = get_cache_statistics()
    print(f"Total articles: {stats_after['total_articles']}")
    print(f"Total size: {stats_after['total_size_mb']} MB")
    print(f"Oldest article: {stats_after['oldest_article_hours']:.1f} hours old")
    print(f"Newest article: {stats_after['newest_article_hours']:.1f} hours old")
    print(f"Cache path: {stats_after['cache_path']}\n")

    assert stats_after["total_articles"] == 1, "Should have 1 article after cleanup"
    assert float(stats_after["oldest_article_hours"]) < 3, "Remaining article should be recent"

    # Cleanup all articles
    print("=== Cleaning up all articles (0 hour retention) ===")
    deleted_all = cleanup_old_articles(max_age_hours=0)
    print(f"✓ Deleted {deleted_all} articles\n")

    assert deleted_all == 1, "Should delete the last article"

    # Final statistics
    print("=== Final Cache Statistics ===")
    final_stats = get_cache_statistics()
    print(f"Total articles: {final_stats['total_articles']}")
    print(f"Total size: {final_stats['total_size_mb']} MB\n")

    assert final_stats["total_articles"] == 0, "Should have 0 articles after full cleanup"
    assert final_stats["total_size_mb"] == 0, "Should have 0 MB after full cleanup"

    print("✅ All tests passed!")

    # Cleanup test cache
    if test_cache_root.exists():
        shutil.rmtree(test_cache_root)
    print("✓ Test cache cleaned up")


if __name__ == "__main__":
    test_cleanup_and_statistics()
