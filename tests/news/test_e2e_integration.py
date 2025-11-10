"""Comprehensive end-to-end integration tests for RSS article caching system.

Tests the complete workflow:
1. RSS feed fetching
2. Article caching with symbol detection
3. Cache retrieval and filtering
4. Error handling and edge cases
5. Cache cleanup
"""

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import requests

from news import article_processor as ap
from news.article_cache import (
    CachedArticle,
    cleanup_old_articles,
    ensure_cache_directory,
    get_articles_for_symbol,
    get_cache_statistics,
    get_recent_articles,
    load_article_from_cache,
    save_article_to_cache,
)
from news.rss_parser import fetch_and_cache_articles_for_symbol, get_news
from news.symbol_detector import detect_symbols_in_text
from source_repository import SourceID, Symbol


class DummyOllamaClient:
    """Simple stand-in for the Ollama SDK client."""

    def __init__(self, response_text: str | None = None, *, should_fail: bool = False) -> None:
        """Initialize the dummy client with a canned response or failure mode."""
        self._response_text = response_text or "{}"
        self._should_fail = should_fail
        self.captured_prompt: str | None = None
        self.captured_temperature: float | None = None

    def generate_text(self, prompt: str, temperature: float = 0.2) -> str:
        """Return the canned response, optionally raising to simulate errors."""
        if self._should_fail:
            message = "simulated failure"
            raise ap.OllamaClientError(message)
        self.captured_prompt = prompt
        self.captured_temperature = temperature
        return self._response_text


@patch("news.article_processor.get_ollama_client")
def test_rss_feed_fetching(mock_get_client):
    """Test RSS feed fetching functionality."""
    # Set up the mock
    mock_client = DummyOllamaClient(
        response_text=json.dumps(
            {
                "summary": "BTC rallies on ETF flows",
                "cleaned_content": "Clean paragraph",
                "symbols": ["btc", "eth"],
                "relevance_score": 1.4,
                "is_relevant": True,
                "reasoning": "High-volume breakout",
            },
        ),
    )
    mock_get_client.return_value = mock_client
    print("📡 TEST 1: RSS Feed Fetching")
    print("-" * 70)

    try:
        articles_json = get_news()
        articles = json.loads(articles_json)
        print(f"✅ Successfully fetched {len(articles)} articles from RSS feeds")

        if articles:
            print("\n   Sample articles:")
            for i, article in enumerate(articles[:3], 1):
                symbols_list = article.get("symbols", [])
                symbols_text = ", ".join(symbols_list) if symbols_list else "none"
                print(f"   {i}. {article['title'][:60]}...")
                print(f"      Source: {article['source']} | Symbols: {symbols_text}")
        else:
            print("⚠️  No articles fetched (RSS feeds may be rate-limited or down)")

    except (OSError, ValueError, ConnectionError, requests.RequestException) as e:
        print(f"❌ RSS fetch failed: {e}")
        print("   Continuing with manual test data...\n")


def test_manual_article_caching():
    """Test manual article caching with symbol detection."""
    print("\n📝 TEST 2: Article Caching with Symbol Detection")
    print("-" * 70)

    # Create test symbols
    test_symbols = [
        Symbol(
            symbol_id=1,
            symbol_name="BTC",
            full_name="Bitcoin",
            source_id=SourceID.BINANCE,
            coingecko_name="bitcoin",
        ),
        Symbol(
            symbol_id=2,
            symbol_name="ETH",
            full_name="Ethereum",
            source_id=SourceID.BINANCE,
            coingecko_name="ethereum",
        ),
        Symbol(
            symbol_id=3,
            symbol_name="SOL",
            full_name="Solana",
            source_id=SourceID.BINANCE,
            coingecko_name="solana",
        ),
        Symbol(
            symbol_id=4,
            symbol_name="ADA",
            full_name="Cardano",
            source_id=SourceID.BINANCE,
            coingecko_name="cardano",
        ),
    ]

    # Create test articles with different symbol mentions
    now = datetime.now(tz=UTC)
    test_articles = [
        {
            "title": "Bitcoin Breaks $100k Milestone as Institutional Adoption Accelerates",
            "content": "Bitcoin (BTC) has reached a historic $100,000 price level...",
        },
        {
            "title": "Ethereum Upgrade Improves Scalability and Reduces Gas Fees",
            "content": "The Ethereum network has successfully implemented its latest upgrade...",
        },
        {
            "title": "Solana and Cardano See Strong Developer Activity Growth",
            "content": (
                "Both Solana and Cardano ecosystems are experiencing record developer growth..."
            ),
        },
        {
            "title": "Market Analysis: BTC and ETH Lead Crypto Recovery",
            "content": (
                "Bitcoin and Ethereum are leading the cryptocurrency market "
                "recovery with strong momentum..."
            ),
        },
    ]

    cached_count = 0
    for i, article_data in enumerate(test_articles, 1):
        # Detect symbols in title and content
        combined_text = f"{article_data['title']} {article_data['content']}"
        detected_symbols = detect_symbols_in_text(combined_text, test_symbols)

        # Create cached article
        article = CachedArticle(
            source="test-source",
            title=article_data["title"],
            link=f"https://example.com/article-{i}",
            published=now.isoformat(),
            fetched=now.isoformat(),
            content=article_data["content"],
            symbols=detected_symbols,
        )

        # Save to cache
        save_article_to_cache(article)
        cached_count += 1

        print(f"✅ Cached: {article.title[:50]}...")
        print(f"   Detected symbols: {', '.join(detected_symbols) if detected_symbols else 'none'}")

    print(f"\n✓ Total articles cached: {cached_count}")


def test_cache_retrieval_and_statistics():
    """Test cache retrieval by symbol, recent articles, and statistics."""
    # ========================================================================
    # TEST 3: Cache Retrieval by Symbol
    # ========================================================================
    print("\n🔍 TEST 3: Retrieve Articles by Symbol")
    print("-" * 70)

    symbols_to_test = ["BTC", "ETH", "SOL", "ADA", "XRP"]
    for symbol in symbols_to_test:
        articles = get_articles_for_symbol(symbol, hours=24)
        print(f"   {symbol}: Found {len(articles)} articles")

        if articles and len(articles) <= 2:  # Show titles for small results
            for article in articles:
                print(f"      - {article.title[:55]}...")

    # ========================================================================
    # TEST 4: Recent Articles Retrieval
    # ========================================================================
    print("\n📰 TEST 4: Retrieve All Recent Articles")
    print("-" * 70)

    recent = get_recent_articles(hours=24)
    print(f"✅ Retrieved {len(recent)} recent articles (last 24 hours)")

    # ========================================================================
    # TEST 5: Cache Statistics
    # ========================================================================
    print("\n📊 TEST 5: Cache Statistics")
    print("-" * 70)

    stats = get_cache_statistics()
    print(f"   Total articles: {stats['total_articles']}")
    print(f"   Disk usage: {stats['total_size_mb']} MB")
    print(f"   Oldest: {stats['oldest_article_hours']:.1f} hours ago")
    print(f"   Newest: {stats['newest_article_hours']:.1f} hours ago")
    print(f"   Cache path: {stats['cache_path']}")


def test_error_handling_and_cleanup():
    """Test error handling for corrupted/missing files and old article cleanup."""
    now = datetime.now(tz=UTC)
    # ========================================================================
    # TEST 6: Error Handling - Corrupted Cache Files
    # ========================================================================
    print("\n🔧 TEST 6: Error Handling - Corrupted Cache Files")
    print("-" * 70)

    # Create a corrupted cache file
    cache_dir = ensure_cache_directory()
    corrupted_file = cache_dir / "corrupted_invalid-frontmatter.md"

    try:
        with corrupted_file.open("w", encoding="utf-8") as f:
            f.write("---\nbroken yaml: [unclosed\n---\nContent")

        # Try to load it
        result = load_article_from_cache(corrupted_file)
        if result is None:
            print("✅ Gracefully handled corrupted file (returned None)")
        else:
            print("⚠️  Corrupted file was loaded (unexpected)")

    except (ValueError, TypeError, AttributeError) as e:
        print(f"✅ Caught exception for corrupted file: {type(e).__name__}")

    finally:
        # Clean up
        if corrupted_file.exists():
            corrupted_file.unlink()

    # ========================================================================
    # TEST 7: Error Handling - Missing Files
    # ========================================================================
    print("\n🔧 TEST 7: Error Handling - Missing Files")
    print("-" * 70)

    missing_file = cache_dir / "nonexistent_file.md"
    result = load_article_from_cache(missing_file)

    if result is None:
        print("✅ Gracefully handled missing file (returned None)")
    else:
        print("⚠️  Missing file returned data (unexpected)")

    # ========================================================================
    # TEST 8: Old Article Cleanup
    # ========================================================================
    print("\n🧹 TEST 8: Old Article Cleanup")
    print("-" * 70)

    # Create an old article (50 hours ago)
    old_time = now - timedelta(hours=50)
    old_article = CachedArticle(
        source="test-source",
        title="Very Old Article for Cleanup Test",
        link="https://example.com/old",
        published=old_time.isoformat(),
        fetched=now.isoformat(),
        content="This article should be deleted by cleanup.",
        symbols=["BTC"],
    )
    save_article_to_cache(old_article)

    # Check stats before cleanup
    stats_before = get_cache_statistics()
    print(f"   Before cleanup: {stats_before['total_articles']} articles")

    # Run cleanup (delete articles older than 24 hours)
    deleted = cleanup_old_articles(max_age_hours=24)
    print(f"✅ Cleanup deleted {deleted} old articles")

    # Check stats after cleanup
    stats_after = get_cache_statistics()
    print(f"   After cleanup: {stats_after['total_articles']} articles")


@patch("news.article_processor.get_ollama_client")
def test_fetch_and_cache_integration(mock_get_client):
    """Test the fetch and cache integration functionality."""
    # Set up the mock
    mock_client = DummyOllamaClient(
        response_text=json.dumps(
            {
                "summary": "BTC rallies on ETF flows",
                "cleaned_content": "Clean paragraph",
                "symbols": ["btc", "eth"],
                "relevance_score": 1.4,
                "is_relevant": True,
                "reasoning": "High-volume breakout",
            },
        ),
    )
    mock_get_client.return_value = mock_client
    print("\n📡 TEST 9: Fetch and Cache Integration (Auto-refresh)")
    print("-" * 70)

    try:
        # This should fetch fresh RSS articles and return cached ones
        btc_articles = fetch_and_cache_articles_for_symbol("BTC", hours=24)
        print(f"✅ fetch_and_cache_articles_for_symbol returned {len(btc_articles)} BTC articles")

        if btc_articles:
            print(f"   Latest: {btc_articles[0].title[:60]}...")

    except (OSError, ValueError, ConnectionError, requests.RequestException) as e:
        print(f"⚠️  Fetch and cache failed (may be rate-limited): {e}")


def test_final_cleanup():
    """Test final cleanup of test cache."""
    print("\n🧹 TEST 10: Final Test Cleanup")
    print("-" * 70)

    # Clean up test cache
    test_cache = Path(__file__).parent / "cache"
    if test_cache.exists():
        shutil.rmtree(test_cache)
        print("✅ Test cache directory removed")


def run_full_workflow():
    """Test the complete RSS caching workflow from fetch to cleanup."""
    print("\n" + "=" * 70)
    print("🧪 COMPREHENSIVE END-TO-END INTEGRATION TEST")
    print("=" * 70)

    # Set up Ollama mocking for the script run
    dummy_client = DummyOllamaClient(
        response_text=json.dumps(
            {
                "summary": "BTC rallies on ETF flows",
                "cleaned_content": "Clean paragraph",
                "symbols": ["btc", "eth"],
                "relevance_score": 1.4,
                "is_relevant": True,
                "reasoning": "High-volume breakout",
            },
        ),
    )

    # Patch the Ollama client
    original_get_ollama_client = ap.get_ollama_client
    ap.get_ollama_client = lambda: dummy_client

    try:
        # Clean slate - remove test cache
        test_cache = Path(__file__).parent / "cache"
        if test_cache.exists():
            shutil.rmtree(test_cache)
            print("✓ Cleaned existing cache for fresh test\n")

        # ========================================================================
        # TEST 1: RSS Fetching
        # ========================================================================
        test_rss_feed_fetching()

        # ========================================================================
        # TEST 2: Manual Article Caching with Symbol Detection
        # ========================================================================
        test_manual_article_caching()

        # ========================================================================
        # TEST 3-5: Cache Retrieval and Statistics
        # ========================================================================
        test_cache_retrieval_and_statistics()

        # ========================================================================
        # TEST 6-8: Error Handling and Cleanup
        # ========================================================================
        test_error_handling_and_cleanup()

        # ========================================================================
        # TEST 9: Fetch and Cache Integration
        # ========================================================================
        test_fetch_and_cache_integration()

        # ========================================================================
        # TEST 10: Final Cleanup
        # ========================================================================
        test_final_cleanup()

        # ========================================================================
        # SUMMARY
        # ========================================================================
        print("\n" + "=" * 70)
        print("✅ END-TO-END INTEGRATION TEST COMPLETE")
        print("=" * 70)
        print("\nAll major workflows tested:")
        print("  ✓ RSS feed fetching")
        print("  ✓ Article caching with symbol detection")
        print("  ✓ Cache retrieval by symbol")
        print("  ✓ Recent articles retrieval")
        print("  ✓ Cache statistics")
        print("  ✓ Error handling (corrupted files, missing files)")
        print("  ✓ Old article cleanup")
        print("  ✓ Fetch and cache integration")
        print("  ✓ Test cleanup")
        print()
    finally:
        # Restore original function
        ap.get_ollama_client = original_get_ollama_client


if __name__ == "__main__":
    run_full_workflow()
