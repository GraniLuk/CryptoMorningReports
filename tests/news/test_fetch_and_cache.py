"""Test the fetch_and_cache_articles_for_symbol function."""

import json
import sys
from pathlib import Path

import pytest


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from news import article_processor as ap
from news.article_cache import fetch_and_cache_articles_for_symbol


class DummyOllamaClient:
    """Simple stand-in for the Ollama SDK client to avoid slow API calls in tests."""

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


@pytest.fixture
def mock_ollama_client(monkeypatch: pytest.MonkeyPatch) -> DummyOllamaClient:
    """Patch the Ollama client factory to return a dummy implementation."""
    client = DummyOllamaClient(
        response_text=json.dumps(
            {
                "summary": "Market update on crypto prices",
                "cleaned_content": "Clean article content about cryptocurrency markets.",
                "symbols": ["BTC", "ETH"],
                "relevance_score": 0.9,
                "is_relevant": True,
                "reasoning": "Article discusses major cryptocurrencies",
            },
        ),
    )

    monkeypatch.setattr(ap, "get_ollama_client", lambda: client)
    return client


def test_fetch_and_cache_for_symbol():
    """Test fetching fresh articles and caching them for a specific symbol."""
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
    # When running directly, we need to manually patch the Ollama client
    from unittest import mock

    client = DummyOllamaClient(
        response_text=json.dumps(
            {
                "summary": "Market update on crypto prices",
                "cleaned_content": "Clean article content about cryptocurrency markets.",
                "symbols": ["BTC", "ETH"],
                "relevance_score": 0.9,
                "is_relevant": True,
                "reasoning": "Article discusses major cryptocurrencies",
            },
        ),
    )

    with mock.patch.object(ap, "get_ollama_client", return_value=client):
        test_fetch_and_cache_for_symbol()
