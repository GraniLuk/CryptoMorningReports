"""Perplexity AI client implementation."""

import time
from http import HTTPStatus
from typing import Any

import requests

from infra.telegram_logging_handler import app_logger
from news.clients.base_client import AIClient
from news.prompts import (
    SYSTEM_PROMPT_ANALYSIS_NEWS,
    SYSTEM_PROMPT_HIGHLIGHT,
    USER_PROMPT_HIGHLIGHT,
    build_analysis_user_messages,
)
from news.utils.candle_data import fetch_and_format_candle_data
from news.utils.retry_handler import retry_with_fallback_models


class PerplexityClient(AIClient):
    """Client for Perplexity AI API."""

    def __init__(self, api_key):
        """Initialize Perplexity client.

        Args:
            api_key (str): Perplexity API key

        """
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self.url = "https://api.perplexity.ai/chat/completions"

    def _make_request(self, model: str, messages: list[dict[str, str]]) -> tuple[bool, Any]:
        """Make a request to Perplexity API.

        Args:
            model (str): Model name to use
            messages (list): List of message dictionaries

        Returns:
            tuple[bool, any]: (success, result) where result is content on
                success or error message on failure

        """
        data = {"model": model, "messages": messages}

        try:
            response = requests.post(self.url, json=data, headers=self.headers, timeout=30)
        except (requests.RequestException, ValueError, TypeError, OSError) as e:
            error_msg = f"Request failed: {e!s}"
            return False, error_msg
        else:
            app_logger.info(f"API Response Status: {response.status_code}")

            if response.status_code == HTTPStatus.OK:
                content = response.json()["choices"][0]["message"]["content"]
                app_logger.info(f"Successfully processed. Length: {len(content)} chars")
                return True, content
            error_msg = f"Failed: API error: {response.status_code} - {response.text}"
            return False, error_msg

    def get_detailed_crypto_analysis_with_news(
        self,
        indicators_message,
        news_feeded,
        conn=None,
    ) -> str:
        """Get detailed crypto analysis with news using Perplexity API."""
        start_time = time.time()
        app_logger.info("Starting detailed crypto analysis with news using Perplexity")
        app_logger.debug(f"Input news articles count: {len(news_feeded)}")

        price_data = fetch_and_format_candle_data(conn)

        models = ["sonar-deep-research"]

        def request_func(model):
            user_messages = build_analysis_user_messages(
                news_feeded=news_feeded,
                indicators_message=indicators_message,
                price_data=price_data,
            )

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_ANALYSIS_NEWS},
            ]
            messages.extend({"role": "user", "content": chunk} for chunk in user_messages)
            return self._make_request(model, messages)

        result = retry_with_fallback_models(models, request_func, "Crypto analysis with news")

        app_logger.debug(f"Processing time: {time.time() - start_time:.2f} seconds")
        return result

    def highlight_articles(self, user_crypto_list, news_feeded) -> str:
        """Highlight articles based on user crypto list and news feed."""
        symbol_names = [symbol.symbol_name for symbol in user_crypto_list]
        app_logger.info("Starting article highlighting with Perplexity")
        app_logger.debug(f"Symbol names provided: {symbol_names}")

        models = ["sonar-deep-research", "sonar-pro"]

        def request_func(model):
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_HIGHLIGHT},
                {
                    "role": "user",
                    "content": USER_PROMPT_HIGHLIGHT.format(
                        news_feeded=news_feeded,
                        symbol_names=symbol_names,
                    ),
                },
            ]
            return self._make_request(model, messages)

        return retry_with_fallback_models(models, request_func, "Article highlighting")
