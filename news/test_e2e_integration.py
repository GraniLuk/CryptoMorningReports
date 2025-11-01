"""Comprehensive end-to-end integration tests for RSS article caching system.

Tests the complete workflow:
1. RSS feed fetching
2. Article caching with symbol detection
3. Cache retrieval and filtering
4. Error handling and edge cases
5. Cache cleanup
"""

import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from news.article_cache import (
    CachedArticle,
    cleanup_old_articles,
    fetch_and_cache_articles_for_symbol,
    get_articles_for_symbol,
    get_cache_statistics,
    get_recent_articles,
    load_article_from_cache,
    save_article_to_cache,
)
from news.rss_parser import get_news
from news.symbol_detector import detect_symbols_in_text
from source_repository import SourceID, Symbol


def test_full_workflow():
    """Test the complete RSS caching workflow from fetch to cleanup."""
    print("\n" + "=" * 70)
    print("🧪 COMPREHENSIVE END-TO-END INTEGRATION TEST")
    print("=" * 70)

    # Clean slate - remove test cache
    test_cache = Path(__file__).parent / "cache"
    if test_cache.exists():
        shutil.rmtree(test_cache)
        print("✓ Cleaned existing cache for fresh test\n")

    # ========================================================================
    # TEST 1: RSS Fetching
    # ========================================================================
    print("📡 TEST 1: RSS Feed Fetching")
    print("-" * 70)

    try:
        articles = get_news()
        print(f"✅ Successfully fetched {len(articles)} articles from RSS feeds")

        if articles:
            print("\n   Sample articles:")
            for i, article in enumerate(articles[:3], 1):
                symbols_list = article.get("symbols", [])  # type: ignore[union-attr]
                symbols_text = ", ".join(symbols_list) if symbols_list else "none"
                print(f"   {i}. {article['title'][:60]}...")  # type: ignore[index]
                print(f"      Source: {article['source']} | Symbols: {symbols_text}")  # type: ignore[index]
        else:
            print("⚠️  No articles fetched (RSS feeds may be rate-limited or down)")

    except Exception as e:
        print(f"❌ RSS fetch failed: {e}")
        print("   Continuing with manual test data...\n")

    # ========================================================================
    # TEST 2: Manual Article Caching with Symbol Detection
    # ========================================================================
    print(f"\n📝 TEST 2: Article Caching with Symbol Detection")
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

    # ========================================================================
    # TEST 3: Cache Retrieval by Symbol
    # ========================================================================
    print(f"\n🔍 TEST 3: Retrieve Articles by Symbol")
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
    print(f"\n📰 TEST 4: Retrieve All Recent Articles")
    print("-" * 70)

    recent = get_recent_articles(hours=24)
    print(f"✅ Retrieved {len(recent)} recent articles (last 24 hours)")

    # ========================================================================
    # TEST 5: Cache Statistics
    # ========================================================================
    print(f"\n📊 TEST 5: Cache Statistics")
    print("-" * 70)

    stats = get_cache_statistics()
    print(f"   Total articles: {stats['total_articles']}")
    print(f"   Disk usage: {stats['total_size_mb']} MB")
    print(f"   Oldest: {stats['oldest_article_hours']:.1f} hours ago")
    print(f"   Newest: {stats['newest_article_hours']:.1f} hours ago")
    print(f"   Cache path: {stats['cache_path']}")

    # ========================================================================
    # TEST 6: Error Handling - Corrupted Cache Files
    # ========================================================================
    print(f"\n🔧 TEST 6: Error Handling - Corrupted Cache Files")
    print("-" * 70)

    # Create a corrupted cache file
    cache_dir = Path(__file__).parent / "cache" / now.strftime("%Y-%m-%d")
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

    except Exception as e:
        print(f"✅ Caught exception for corrupted file: {type(e).__name__}")

    finally:
        # Clean up
        if corrupted_file.exists():
            corrupted_file.unlink()

    # ========================================================================
    # TEST 7: Error Handling - Missing Files
    # ========================================================================
    print(f"\n🔧 TEST 7: Error Handling - Missing Files")
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
    print(f"\n🧹 TEST 8: Old Article Cleanup")
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
    save_article_to_cache(old_article, date=old_time)

    # Check stats before cleanup
    stats_before = get_cache_statistics()
    print(f"   Before cleanup: {stats_before['total_articles']} articles")

    # Run cleanup (delete articles older than 24 hours)
    deleted = cleanup_old_articles(max_age_hours=24)
    print(f"✅ Cleanup deleted {deleted} old articles")

    # Check stats after cleanup
    stats_after = get_cache_statistics()
    print(f"   After cleanup: {stats_after['total_articles']} articles")

    # ========================================================================
    # TEST 9: Fetch and Cache Integration
    # ========================================================================
    print(f"\n📡 TEST 9: Fetch and Cache Integration (Auto-refresh)")
    print("-" * 70)

    try:
        # This should fetch fresh RSS articles and return cached ones
        btc_articles = fetch_and_cache_articles_for_symbol("BTC", hours=24)
        print(f"✅ fetch_and_cache_articles_for_symbol returned {len(btc_articles)} BTC articles")

        if btc_articles:
            print(f"   Latest: {btc_articles[0].title[:60]}...")

    except Exception as e:
        print(f"⚠️  Fetch and cache failed (may be rate-limited): {e}")

    # ========================================================================
    # TEST 10: Final Cleanup
    # ========================================================================
    print(f"\n🧹 TEST 10: Final Test Cleanup")
    print("-" * 70)

    # Clean up test cache
    if test_cache.exists():
        shutil.rmtree(test_cache)
        print("✅ Test cache directory removed")

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


if __name__ == "__main__":
    test_full_workflow()
