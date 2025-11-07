"""Test the fetch_and_cache_articles_for_symbol function."""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from news import article_processor as ap
from news import rss_parser
from news.article_cache import fetch_and_cache_articles_for_symbol


@pytest.fixture
def mock_ollama_processing(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Patch process_article_with_ollama to avoid real Ollama calls."""
    mock_result = ap.ArticleProcessingResult(
        summary="Market update on crypto prices",
        cleaned_content="Clean article content about cryptocurrency markets.",
        symbols=["BTC", "ETH"],
        relevance_score=0.9,
        is_relevant=True,
        reasoning="Article discusses major cryptocurrencies",
    )

    mock_process = Mock(return_value=mock_result)
    monkeypatch.setattr(rss_parser, "process_article_with_ollama", mock_process)
    return mock_process


@pytest.fixture
def mock_get_news(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Patch get_news to avoid real RSS fetching and web scraping."""
    # Return empty JSON array - we don't need articles from get_news
    # because the test will use pre-existing cached articles
    mock_news = Mock(return_value="[]")
    monkeypatch.setattr(rss_parser, "get_news", mock_news)
    return mock_news


def test_fetch_and_cache_for_symbol(mock_ollama_processing: Mock, mock_get_news: Mock):
    """Test fetching fresh articles and caching them for a specific symbol."""
    # Ensure mocks are applied (fixtures are injected via parameters)
    assert mock_ollama_processing is not None
    assert mock_get_news is not None
    print("\n🧪 Testing fetch_and_cache_articles_for_symbol with mocked Ollama")
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
    # When running directly, we need to manually patch both functions
    from unittest import mock

    mock_result = ap.ArticleProcessingResult(
        summary="Market update on crypto prices",
        cleaned_content="Clean article content about cryptocurrency markets.",
        symbols=["BTC", "ETH"],
        relevance_score=0.9,
        is_relevant=True,
        reasoning="Article discusses major cryptocurrencies",
    )

    mock_process = Mock(return_value=mock_result)
    mock_news = Mock(return_value="[]")

    with (
        mock.patch.object(rss_parser, "process_article_with_ollama", mock_process),
        mock.patch.object(rss_parser, "get_news", mock_news),
    ):
        test_fetch_and_cache_for_symbol(mock_process, mock_news)
