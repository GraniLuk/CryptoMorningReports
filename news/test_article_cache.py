"""Tests for article caching functionality.

This module contains comprehensive tests to verify that the article caching
system works correctly, including saving, loading, and retrieving articles.
"""

import shutil
from datetime import UTC, datetime
from pathlib import Path

from news.article_cache import (
    CachedArticle,
    article_exists_in_cache,
    ensure_cache_directory,
    get_article_filename,
    get_cache_directory,
    get_cached_articles,
    load_article_from_cache,
    save_article_to_cache,
)


def test_cache_directory_structure():
    """Test that cache directory is created with correct date structure."""
    test_date = datetime(2025, 1, 15, tzinfo=UTC)
    cache_dir = get_cache_directory(test_date)

    # Verify the path structure
    assert "cache" in str(cache_dir)
    assert "2025-01-15" in str(cache_dir)

    print("✅ Cache directory structure test passed")


def test_ensure_cache_directory():
    """Test that cache directory is created if it doesn't exist."""
    test_date = datetime(2025, 1, 15, tzinfo=UTC)
    cache_dir = ensure_cache_directory(test_date)

    # Verify directory exists
    assert cache_dir.exists()
    assert cache_dir.is_dir()

    # Cleanup
    if cache_dir.exists():
        shutil.rmtree(cache_dir.parent)

    print("✅ Ensure cache directory test passed")


def test_article_filename_generation():
    """Test that article filenames are generated correctly with slugification."""
    article = CachedArticle(
        source="coindesk",
        title="Bitcoin Surges to $100,000 - New All-Time High!",
        link="https://example.com/article",
        published="2025-01-15T10:00:00Z",
        fetched="2025-01-15T10:05:00Z",
        content="Article content here",
        symbols=["BTC"],
    )

    filename = get_article_filename(article)

    # Verify filename format
    assert filename.startswith("coindesk_")
    assert filename.endswith(".md")
    assert "bitcoin" in filename.lower()
    assert "$" not in filename  # Special chars should be removed
    assert " " not in filename  # Spaces should be removed

    print(f"✅ Filename generation test passed: {filename}")


def test_save_and_load_article():
    """Test saving an article to cache and loading it back."""
    test_date = datetime(2025, 1, 15, tzinfo=UTC)

    # Create test article
    original_article = CachedArticle(
        source="decrypt",
        title="Ethereum Completes Major Upgrade",
        link="https://example.com/eth-upgrade",
        published="2025-01-15T12:00:00Z",
        fetched="2025-01-15T12:05:00Z",
        content="Ethereum has successfully completed its latest protocol upgrade...",
        symbols=["ETH"],
    )

    # Save to cache
    filepath = save_article_to_cache(original_article, test_date)

    # Verify file was created
    assert filepath.exists()
    assert filepath.suffix == ".md"

    # Load from cache
    loaded_article = load_article_from_cache(filepath)

    # Verify all fields match
    assert loaded_article is not None
    assert loaded_article.source == original_article.source
    assert loaded_article.title == original_article.title
    assert loaded_article.link == original_article.link
    assert loaded_article.published == original_article.published
    assert loaded_article.fetched == original_article.fetched
    assert loaded_article.content == original_article.content
    assert loaded_article.symbols == original_article.symbols

    # Cleanup
    cache_dir = get_cache_directory(test_date)
    if cache_dir.exists():
        shutil.rmtree(cache_dir.parent)

    print("✅ Save and load article test passed")


def test_get_cached_articles():
    """Test retrieving all cached articles for a specific date."""
    test_date = datetime(2025, 1, 15, tzinfo=UTC)

    # Create multiple test articles
    articles = [
        CachedArticle(
            source="coindesk",
            title="Bitcoin Reaches New Milestone",
            link="https://example.com/btc-1",
            published="2025-01-15T10:00:00Z",
            fetched="2025-01-15T10:05:00Z",
            content="Bitcoin content 1",
            symbols=["BTC"],
        ),
        CachedArticle(
            source="decrypt",
            title="Solana Network Upgrade Announced",
            link="https://example.com/sol-1",
            published="2025-01-15T11:00:00Z",
            fetched="2025-01-15T11:05:00Z",
            content="Solana content 1",
            symbols=["SOL"],
        ),
        CachedArticle(
            source="newsBTC",
            title="Cardano Partnership Revealed",
            link="https://example.com/ada-1",
            published="2025-01-15T12:00:00Z",
            fetched="2025-01-15T12:05:00Z",
            content="Cardano content 1",
            symbols=["ADA"],
        ),
    ]

    # Save all articles
    for article in articles:
        save_article_to_cache(article, test_date)

    # Retrieve cached articles
    cached_articles = get_cached_articles(test_date)

    # Verify we got all articles back
    assert len(cached_articles) == 3

    # Verify they match our originals
    cached_titles = {article.title for article in cached_articles}
    original_titles = {article.title for article in articles}
    assert cached_titles == original_titles

    # Cleanup
    cache_dir = get_cache_directory(test_date)
    if cache_dir.exists():
        shutil.rmtree(cache_dir.parent)

    print(f"✅ Get cached articles test passed ({len(cached_articles)} articles)")


def test_article_exists_in_cache():
    """Test checking if an article exists in the cache."""
    test_date = datetime(2025, 1, 15, tzinfo=UTC)

    article = CachedArticle(
        source="coinJournal",
        title="Polygon Announces New Feature",
        link="https://example.com/matic-feature",
        published="2025-01-15T14:00:00Z",
        fetched="2025-01-15T14:05:00Z",
        content="Polygon content here",
        symbols=["MATIC"],
    )

    # Initially should not exist
    assert not article_exists_in_cache(article.link, test_date)

    # Save article
    save_article_to_cache(article, test_date)

    # Now should exist
    assert article_exists_in_cache(article.link, test_date)

    # Different URL should not exist
    assert not article_exists_in_cache("https://example.com/different-url", test_date)

    # Cleanup
    cache_dir = get_cache_directory(test_date)
    if cache_dir.exists():
        shutil.rmtree(cache_dir.parent)

    print("✅ Article exists in cache test passed")


def test_load_nonexistent_article():
    """Test loading an article that doesn't exist returns None."""
    nonexistent_path = Path("nonexistent_file.md")
    result = load_article_from_cache(nonexistent_path)

    assert result is None

    print("✅ Load nonexistent article test passed")


def test_get_cached_articles_empty():
    """Test retrieving cached articles when cache directory is empty."""
    # Use a date that has no cache
    test_date = datetime(1999, 1, 1, tzinfo=UTC)
    cached_articles = get_cached_articles(test_date)

    assert cached_articles == []

    print("✅ Get cached articles (empty) test passed")


def run_all_tests():
    """Run all article cache tests."""
    print("\n🧪 Running Article Cache Tests\n" + "=" * 50)

    test_cache_directory_structure()
    test_ensure_cache_directory()
    test_article_filename_generation()
    test_save_and_load_article()
    test_get_cached_articles()
    test_article_exists_in_cache()
    test_load_nonexistent_article()
    test_get_cached_articles_empty()

    print("\n" + "=" * 50)
    print("✅ All article cache tests passed!\n")


if __name__ == "__main__":
    run_all_tests()
