"""Demonstration of how current_report.py fetches fresh articles automatically.

This script shows that when you generate a current report, it will:
1. Check RSS feeds for new articles
2. Cache any new articles (skip duplicates)
3. Return all relevant articles for the symbol

This ensures reports always have the latest news without manual RSS fetching.
"""

from datetime import UTC, datetime

from news.rss_parser import fetch_and_cache_articles_for_symbol


def demonstrate_auto_fetch():
    """Demonstrate automatic RSS fetching and caching."""
    print("\n" + "=" * 70)
    print("DEMONSTRATION: Auto-Fetch Fresh Articles for Current Reports")
    print("=" * 70)

    print("\n📊 Scenario: Generating a current report for Bitcoin (BTC)")
    print("-" * 70)

    print("\n1️⃣  current_report.py calls: fetch_and_cache_articles_for_symbol('BTC')")
    print("    ↓")
    print("2️⃣  System checks RSS feeds for new articles (last 24 hours)")
    print("    ↓")
    print("3️⃣  New articles are cached to disk with detected symbols")
    print("    ↓")
    print("4️⃣  All BTC articles (old + new) are returned to the report")
    print("    ↓")
    print("5️⃣  Report includes latest news in AI analysis & output")

    print("\n" + "-" * 70)
    print("🚀 Running actual fetch for BTC...")
    print("-" * 70)

    start_time = datetime.now(UTC)
    articles = fetch_and_cache_articles_for_symbol("BTC", hours=24)
    elapsed = (datetime.now(UTC) - start_time).total_seconds()

    print(f"\n✅ Completed in {elapsed:.2f} seconds")
    print(f"📰 Found {len(articles)} BTC articles")

    if articles:
        print("\n📋 Article Preview:")
        for i, article in enumerate(articles[:5], 1):  # Show first 5
            # Parse timestamp
            try:
                pub_time = datetime.fromisoformat(article.published)
                time_str = pub_time.strftime("%Y-%m-%d %H:%M UTC")
            except (ValueError, AttributeError):
                time_str = article.published

            print(f"\n  {i}. {article.title}")
            print(f"     📡 Source: {article.source}")
            print(f"     🕒 Published: {time_str}")
            print(f"     🏷️  Symbols: {', '.join(article.symbols)}")
            print(f"     🔗 Link: {article.link}")

    print("\n" + "=" * 70)
    print("KEY BENEFITS:")
    print("=" * 70)
    print("✅ No manual RSS fetching needed")
    print("✅ Always up-to-date with latest news")
    print("✅ Duplicates automatically skipped")
    print("✅ Fast subsequent lookups (uses cache)")
    print("✅ Works seamlessly in current_report.py")
    print("=" * 70)
    print()


if __name__ == "__main__":
    demonstrate_auto_fetch()
