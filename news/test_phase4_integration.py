"""Integration tests for Phase 4: Article cache integration with current reports."""

import sys
from datetime import UTC, datetime
from pathlib import Path


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from news.article_cache import (
    CachedArticle,
    get_articles_for_symbol,
    get_recent_articles,
    save_article_to_cache,
)


def test_end_to_end_article_integration():
    """Test end-to-end workflow: save articles -> retrieve by symbol."""
    print("\n🧪 Running Phase 4 Integration Tests")
    print("=" * 50)

    # Step 1: Create test articles with different symbols
    now = datetime.now(tz=UTC)
    test_articles = [
        CachedArticle(
            source="coindesk",
            title="Bitcoin Surges Past $100k on Strong Institutional Demand",
            link="https://www.coindesk.com/markets/btc-100k",
            published=now.isoformat(),
            fetched=now.isoformat(),
            content=(
                "Bitcoin reached a new all-time high today as institutional "
                "investors continued to accumulate. Major firms like BlackRock "
                "and Fidelity have been steadily buying BTC, pushing the price "
                "above the psychological $100,000 mark."
            ),
            symbols=["BTC"],
        ),
        CachedArticle(
            source="decrypt",
            title="Ethereum Layer 2 Solutions See Record Activity",
            link="https://decrypt.co/eth-l2-growth",
            published=now.isoformat(),
            fetched=now.isoformat(),
            content=(
                "Ethereum layer 2 networks including Arbitrum and Optimism "
                "processed record transaction volumes this week. The scalability "
                "improvements are attracting more developers and users to the "
                "ETH ecosystem."
            ),
            symbols=["ETH"],
        ),
        CachedArticle(
            source="cointelegraph",
            title="Solana DeFi TVL Hits New High Amid Market Rally",
            link="https://cointelegraph.com/solana-defi-growth",
            published=now.isoformat(),
            fetched=now.isoformat(),
            content=(
                "Solana's decentralized finance ecosystem continues to grow with "
                "total value locked reaching new records. SOL price has "
                "benefited from the increased activity."
            ),
            symbols=["SOL"],
        ),
        CachedArticle(
            source="coindesk",
            title="BTC and ETH Lead Crypto Market Recovery",
            link="https://www.coindesk.com/markets/recovery",
            published=now.isoformat(),
            fetched=now.isoformat(),
            content=(
                "Both Bitcoin and Ethereum are leading the broader cryptocurrency "
                "market recovery. BTC is up 15% while ETH has gained 20% over "
                "the past week."
            ),
            symbols=["BTC", "ETH"],
        ),
    ]

    # Step 2: Save articles to cache
    print("\n📝 Step 1: Saving test articles to cache...")
    for article in test_articles:
        saved = save_article_to_cache(article)
        if saved:
            print(f"  ✅ Saved: {article.title[:50]}...")
        else:
            print(f"  ❌ Failed to save: {article.title[:50]}...")
            return

    # Step 3: Retrieve articles for specific symbols
    print("\n🔍 Step 2: Retrieving articles by symbol...")

    btc_articles = get_articles_for_symbol("BTC", hours=24)
    print(f"\n  BTC Articles (found {len(btc_articles)}):")
    for article in btc_articles:
        print(f"    - {article.title}")
    assert len(btc_articles) == 2, f"Expected 2 BTC articles, found {len(btc_articles)}"

    eth_articles = get_articles_for_symbol("ETH", hours=24)
    print(f"\n  ETH Articles (found {len(eth_articles)}):")
    for article in eth_articles:
        print(f"    - {article.title}")
    assert len(eth_articles) == 2, f"Expected 2 ETH articles, found {len(eth_articles)}"

    sol_articles = get_articles_for_symbol("SOL", hours=24)
    print(f"\n  SOL Articles (found {len(sol_articles)}):")
    for article in sol_articles:
        print(f"    - {article.title}")
    assert len(sol_articles) == 1, f"Expected 1 SOL article, found {len(sol_articles)}"

    # Step 4: Test get_recent_articles
    print("\n📰 Step 3: Retrieving all recent articles...")
    recent_articles = get_recent_articles(hours=24)
    print(f"  Total recent articles: {len(recent_articles)}")
    assert len(recent_articles) == 4, f"Expected 4 recent articles, found {len(recent_articles)}"

    # Step 5: Verify article content
    print("\n📝 Step 4: Verifying article content...")
    assert any("Bitcoin" in a.title for a in btc_articles), "Expected Bitcoin in BTC articles"
    assert any("Ethereum" in a.title for a in eth_articles), "Expected Ethereum in ETH articles"
    assert any("Solana" in a.title for a in sol_articles), "Expected Solana in SOL articles"
    print("  ✅ Article content verified")

    # Step 6: Test empty articles handling
    print("\n🔍 Step 5: Testing empty articles handling...")
    ada_articles = get_articles_for_symbol("ADA", hours=24)
    print(f"  ADA Articles: {len(ada_articles)} (should be 0)")
    assert len(ada_articles) == 0, f"Expected 0 ADA articles, found {len(ada_articles)}"
    print("  ✅ Empty result handled correctly")

    print("\n" + "=" * 50)
    print("✅ All Phase 4 integration tests passed!")
    print("Note: Formatting functions are tested via current_report.py integration")
    print()


if __name__ == "__main__":
    test_end_to_end_article_integration()
