"""Tests for article caching functionality.

This module contains comprehensive tests to verify that the article caching
system works correctly, including saving, loading, and retrieving articles.
"""

import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

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

    # Verify the path structure - should end with the date directory
    assert str(cache_dir).endswith("2025-01-15")
    assert "2025-01-15" in str(cache_dir)

    print("✅ Cache directory structure test passed")


def test_ensure_cache_directory():
    """Test that cache directory is created if it doesn't exist."""
    test_date = datetime(2025, 1, 15, tzinfo=UTC)
    cache_dir = ensure_cache_directory(test_date)

    # Verify directory exists
    assert cache_dir.exists()
    assert cache_dir.is_dir()

    # Cleanup - only remove the specific date directory, not the entire cache root
    if cache_dir.exists():
        shutil.rmtree(cache_dir)

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

    # Cleanup - only remove the specific date directory
    cache_dir = get_cache_directory(test_date)
    if cache_dir.exists():
        shutil.rmtree(cache_dir)

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

    # Cleanup - only remove the specific date directory
    cache_dir = get_cache_directory(test_date)
    if cache_dir.exists():
        shutil.rmtree(cache_dir)

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

    # Cleanup - only remove the specific date directory
    cache_dir = get_cache_directory(test_date)
    if cache_dir.exists():
        shutil.rmtree(cache_dir)

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


def test_get_cache_directory_defaults_to_local_cache():
    """Test that get_cache_directory defaults to news/cache when ARTICLE_CACHE_ROOT is not set."""
    # Ensure ARTICLE_CACHE_ROOT is not set
    original_env = os.environ.get("ARTICLE_CACHE_ROOT")
    if "ARTICLE_CACHE_ROOT" in os.environ:
        del os.environ["ARTICLE_CACHE_ROOT"]

    try:
        test_date = datetime(2025, 1, 15, tzinfo=UTC)
        cache_dir = get_cache_directory(test_date)

        # Verify the path ends with news/cache/YYYY-MM-DD
        expected_suffix = Path("news") / "cache" / "2025-01-15"
        assert str(cache_dir).endswith(str(expected_suffix))

        print("✅ Default cache directory test passed")
    finally:
        # Restore original environment
        if original_env is not None:
            os.environ["ARTICLE_CACHE_ROOT"] = original_env


def test_get_cache_directory_respects_env_override():
    """Test that get_cache_directory respects ARTICLE_CACHE_ROOT environment variable."""
    # Set up temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_cache_root = Path(temp_dir) / "custom_cache"

        # Set environment variable
        original_env = os.environ.get("ARTICLE_CACHE_ROOT")
        os.environ["ARTICLE_CACHE_ROOT"] = str(temp_cache_root)

        try:
            test_date = datetime(2025, 1, 15, tzinfo=UTC)
            cache_dir = get_cache_directory(test_date)

            # Verify the path uses the custom root
            expected_path = temp_cache_root / "2025-01-15"
            assert cache_dir == expected_path

            print("✅ Environment override cache directory test passed")
        finally:
            # Restore original environment
            if original_env is not None:
                os.environ["ARTICLE_CACHE_ROOT"] = original_env
            else:
                del os.environ["ARTICLE_CACHE_ROOT"]


def test_ensure_cache_directory_with_custom_root():
    """Test that ensure_cache_directory works with custom ARTICLE_CACHE_ROOT."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_cache_root = Path(temp_dir) / "custom_cache"

        # Set environment variable
        original_env = os.environ.get("ARTICLE_CACHE_ROOT")
        os.environ["ARTICLE_CACHE_ROOT"] = str(temp_cache_root)

        try:
            test_date = datetime(2025, 1, 15, tzinfo=UTC)
            cache_dir = ensure_cache_directory(test_date)

            # Verify directory was created
            assert cache_dir.exists()
            assert cache_dir.is_dir()

            # Verify the custom root was used
            expected_path = temp_cache_root / "2025-01-15"
            assert cache_dir == expected_path

            print("✅ Custom root cache directory creation test passed")
        finally:
            # Restore original environment
            if original_env is not None:
                os.environ["ARTICLE_CACHE_ROOT"] = original_env
            else:
                del os.environ["ARTICLE_CACHE_ROOT"]


def test_ensure_cache_directory_unwritable_root():
    """Test that ensure_cache_directory raises ValueError for unwritable root directory."""
    # Skip on Windows as chmod doesn't work the same way
    if sys.platform == "win32":
        print("✅ Unwritable root directory test skipped on Windows")
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_cache_root = Path(temp_dir) / "unwritable_cache"

        # Create the directory and make it unwritable
        temp_cache_root.mkdir(parents=True, exist_ok=True)
        temp_cache_root.chmod(0o444)  # Read-only

        # Set environment variable
        original_env = os.environ.get("ARTICLE_CACHE_ROOT")
        os.environ["ARTICLE_CACHE_ROOT"] = str(temp_cache_root)

        try:
            test_date = datetime(2025, 1, 15, tzinfo=UTC)

            # Should raise ValueError for unwritable directory
            with pytest.raises(ValueError, match=r"not writable"):
                ensure_cache_directory(test_date)

            print("✅ Unwritable root directory test passed")
        finally:
            # Restore permissions for cleanup
            temp_cache_root.chmod(0o755)

            # Restore original environment
            if original_env is not None:
                os.environ["ARTICLE_CACHE_ROOT"] = original_env
            else:
                del os.environ["ARTICLE_CACHE_ROOT"]


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
    test_get_cache_directory_defaults_to_local_cache()
    test_get_cache_directory_respects_env_override()
    test_ensure_cache_directory_with_custom_root()
    test_ensure_cache_directory_unwritable_root()

    print("\n" + "=" * 50)
    print("✅ All article cache tests passed!\n")


if __name__ == "__main__":
    run_all_tests()
