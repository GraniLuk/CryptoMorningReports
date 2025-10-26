"""
AI client orchestrator for crypto analysis.

This module provides a factory function to create AI clients and maintains
backward compatibility with legacy function interfaces.
"""

from news.clients import GeminiClient, PerplexityClient


def create_ai_client(api_type, api_key):
    """
    Factory function to create appropriate AI client based on type

    Args:
        api_type (str): "perplexity" or "gemini"
        api_key (str): API key for the selected service

    Returns:
        AIClient: An instance of the appropriate AI client
    """
    if api_type.lower() == "perplexity":
        return PerplexityClient(api_key)
    if api_type.lower() == "gemini":
        return GeminiClient(api_key)
    raise ValueError(f"Unsupported AI API type: {api_type}")


def get_detailed_crypto_analysis_with_news(
    api_key, indicators_message, news_feeded, api_type="perplexity", conn=None
):
    client = create_ai_client(api_type, api_key)
    return client.get_detailed_crypto_analysis_with_news(
        indicators_message, news_feeded, conn
    )


def highlight_articles(api_key, user_crypto_list, news_feeded, api_type="perplexity"):
    client = create_ai_client(api_type, api_key)
    return client.highlight_articles(user_crypto_list, news_feeded)


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    from news.rss_parser import get_news

    load_dotenv()
    # Example usage
    perplexity_api_key = os.environ.get("PERPLEXITY_API_KEY")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")

    class Symbol:
        def __init__(self, symbol_id, symbol_name, full_name):
            self.symbol_id = symbol_id
            self.symbol_name = symbol_name
            self.full_name = full_name

    user_crypto_list = [
        # Example list of user crypto symbols
        # Replace with actual symbol objects
        Symbol(symbol_id=1, symbol_name="BTC", full_name="Bitcoin"),
        Symbol(symbol_id=2, symbol_name="ETH", full_name="Etherum"),
    ]

    news_feeded = get_news()

    # Test with Perplexity
    if perplexity_api_key:
        print("Testing with Perplexity API...")
        highlighted_news = highlight_articles(
            perplexity_api_key, user_crypto_list, news_feeded, "perplexity"
        )
        print(highlighted_news)

    # Test with Gemini
    if gemini_api_key:
        print("Testing with Gemini API...")
        highlighted_news = highlight_articles(
            gemini_api_key, user_crypto_list, news_feeded, "gemini"
        )
        print(highlighted_news)
