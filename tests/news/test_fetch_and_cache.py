"""Test the fetch_and_cache_articles_for_symbol function."""

import sys
from pathlib import Path


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from news.article_cache import fetch_and_cache_articles_for_symbol


def test_fetch_and_cache_for_symbol():
    """Test fetching fresh articles and caching them for a specific symbol."""
    print("\n🧪 Testing fetch_and_cache_articles_for_symbol")
    print("=" * 50)

    # Test with BTC - should fetch fresh RSS articles and cache new ones
    print("\n📡 Step 1: Fetching fresh articles for BTC (includes RSS fetch)...")
    btc_articles = fetch_and_cache_articles_for_symbol("BTC", hours=24)
    print(f"  Found {len(btc_articles)} BTC articles")

    if btc_articles:
        print("\n  Sample articles:")
        for i, article in enumerate(btc_articles[:3], 1):  # Show first 3
            print(f"    {i}. {article.title}")
            print(f"       Source: {article.source} | Symbols: {', '.join(article.symbols)}")

    # Test with ETH
    print("\n📡 Step 2: Fetching fresh articles for ETH...")
    eth_articles = fetch_and_cache_articles_for_symbol("ETH", hours=24)
    print(f"  Found {len(eth_articles)} ETH articles")

    if eth_articles:
        print("\n  Sample articles:")
        for i, article in enumerate(eth_articles[:3], 1):
            print(f"    {i}. {article.title}")
            print(f"       Source: {article.source} | Symbols: {', '.join(article.symbols)}")

    # Test with a symbol that likely has no articles
    print("\n📡 Step 3: Testing with symbol that has no articles (XYZ)...")
    xyz_articles = fetch_and_cache_articles_for_symbol("XYZ", hours=24)
    print(f"  Found {len(xyz_articles)} XYZ articles (expected 0)")

    print("\n" + "=" * 50)
    print("✅ fetch_and_cache_articles_for_symbol test complete!")
    print(f"   BTC: {len(btc_articles)} articles")
    print(f"   ETH: {len(eth_articles)} articles")
    print(f"   XYZ: {len(xyz_articles)} articles")
    print()


if __name__ == "__main__":
    test_fetch_and_cache_for_symbol()
