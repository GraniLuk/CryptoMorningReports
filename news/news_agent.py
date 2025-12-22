"""AI client orchestrator for crypto analysis.

This module provides a factory function to create AI clients and maintains
backward compatibility with legacy function interfaces.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from news.article_cache import CachedArticle, get_recent_articles
from news.clients import GeminiClient, PerplexityClient


if TYPE_CHECKING:
    from logging import Logger

    import pyodbc

    from infra.sql_connection import SQLiteConnectionWrapper


def create_ai_client(
    api_type: str,
    api_key: str,
    primary_model: str | None = None,
    secondary_model: str | None = None,
) -> GeminiClient | PerplexityClient:
    """Create appropriate AI client based on type.

    Args:
        api_type (str): "perplexity" or "gemini"
        api_key (str): API key for the selected service
        primary_model (str | None): Primary model to use (Gemini only)
        secondary_model (str | None): Fallback model to use (Gemini only)

    Returns:
        AIClient: An instance of the appropriate AI client

    """
    if api_type.lower() == "perplexity":
        return PerplexityClient(api_key)
    if api_type.lower() == "gemini":
        # Get model configuration from environment or use defaults
        primary = primary_model or os.environ.get(
            "GEMINI_PRIMARY_MODEL",
            "gemini-2.5-flash",
        )
        secondary = secondary_model or os.environ.get(
            "GEMINI_SECONDARY_MODEL",
            "gemini-2.0-flash",
        )
        return GeminiClient(api_key, primary_model=primary, secondary_model=secondary)
    msg = f"Unsupported AI API type: {api_type}"
    raise ValueError(msg)


def get_detailed_crypto_analysis_with_news(
    api_key: str,
    indicators_message: str,
    news_feeded: str,
    api_type: str = "perplexity",
    conn: pyodbc.Connection | SQLiteConnectionWrapper | None = None,
    model: str | None = None,
    primary_model: str | None = None,
    secondary_model: str | None = None,
) -> tuple[str, str]:
    """Get detailed cryptocurrency analysis combining indicators and news data.

    Args:
        api_key: API key for the AI service
        indicators_message: Technical indicators data
        news_feeded: JSON-formatted news articles
        api_type: "perplexity" or "gemini"
        conn: Database connection
        model: Specific model to use for this request (Gemini only)
        primary_model: Primary model for client creation (Gemini only)
        secondary_model: Secondary/fallback model for client creation (Gemini only)

    Returns:
        tuple[str, str]: (Generated analysis or error message, model_used)

    """
    client = create_ai_client(api_type, api_key, primary_model, secondary_model)
    if isinstance(client, GeminiClient):
        return client.get_detailed_crypto_analysis_with_news(
            indicators_message,
            news_feeded,
            conn,
            model=model,
        )
    return client.get_detailed_crypto_analysis_with_news(
        indicators_message,
        news_feeded,
        conn,
    )


def highlight_articles(
    api_key: str,
    user_crypto_list: list,
    news_feeded: str,
    api_type: str = "perplexity",
    model: str | None = None,
    primary_model: str | None = None,
    secondary_model: str | None = None,
) -> str:
    """Highlight relevant articles from news feed based on user's crypto list.

    Args:
        api_key: API key for the AI service
        user_crypto_list: List of Symbol objects
        news_feeded: JSON-formatted news articles
        api_type: "perplexity" or "gemini"
        model: Specific model to use for this request (Gemini only)
        primary_model: Primary model for client creation (Gemini only)
        secondary_model: Secondary/fallback model for client creation (Gemini only)

    Returns:
        str: Highlighted articles or error message

    """
    client = create_ai_client(api_type, api_key, primary_model, secondary_model)
    if isinstance(client, GeminiClient):
        return client.highlight_articles(user_crypto_list, news_feeded, model=model)
    return client.highlight_articles(user_crypto_list, news_feeded)


def get_relevant_cached_articles(hours: int = 24) -> list[CachedArticle]:
    """Retrieve cached articles that remain relevant after AI preprocessing."""
    cached_articles = get_recent_articles(hours=hours)
    return [article for article in cached_articles if article.is_relevant]


def append_article_list_to_analysis(
    analysis: str,
    news_payload: str,
    logger: Logger,
) -> str:
    """Append list of articles to analysis report.

    Args:
        analysis: Analysis report text
        news_payload: JSON string of news articles
        logger: Logger instance

    Returns:
        Analysis report with article list appended
    """
    if analysis.startswith("Failed"):
        return analysis

    try:
        articles = json.loads(news_payload)
        article_list = "\n\n## Articles Included in Analysis\n\n" + "\n".join(
            f"- {art['title']} ({art['source']})" for art in articles
        )
        return analysis + article_list
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Failed to parse news payload for article list: %s", e)
        return analysis


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    from news.rss_parser import get_news

    load_dotenv()
    # Example usage
    perplexity_api_key = os.environ.get("PERPLEXITY_API_KEY")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")

    class Symbol:
        """Represents a cryptocurrency symbol with ID, name, and full name."""

        def __init__(self, symbol_id, symbol_name, full_name):
            """Initialize a Symbol with ID, name, and full name."""
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
        highlighted_news = highlight_articles(
            perplexity_api_key,
            user_crypto_list,
            news_feeded,
            "perplexity",
        )

    # Test with Gemini
    if gemini_api_key:
        highlighted_news = highlight_articles(
            gemini_api_key,
            user_crypto_list,
            news_feeded,
            "gemini",
        )
