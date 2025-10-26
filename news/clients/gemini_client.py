"""Gemini AI client implementation."""

import logging
import time
from typing import Any

import google.generativeai as genai

from news.clients.base_client import AIClient
from news.prompts import (
    SYSTEM_PROMPT_ANALYSIS_NEWS,
    SYSTEM_PROMPT_HIGHLIGHT,
    USER_PROMPT_HIGHLIGHT,
    build_analysis_user_messages,
)
from news.utils.candle_data import fetch_and_format_candle_data


class GeminiClient(AIClient):
    """Client for Google Gemini AI API."""

    def __init__(self, api_key):
        """
        Initialize Gemini client.

        Args:
            api_key (str): Google Gemini API key

        Raises:
            ValueError: If API key is missing
            RuntimeError: If Gemini SDK initialization fails
        """
        self.api_key = api_key
        logging.info(f"GeminiClient [__init__]: Initializing. API key provided: {bool(api_key)}")

        if not self.api_key:
            raise ValueError("GeminiClient initialization failed: API key missing")

        try:
            configure_fn = getattr(genai, "configure", None)
            if not callable(configure_fn):
                raise RuntimeError("genai.configure not available in google.generativeai module")
            configure_fn(api_key=self.api_key)

            generative_cls = getattr(genai, "GenerativeModel", None)
            if generative_cls is None:
                raise RuntimeError("GenerativeModel not available in google.generativeai module")
            self.model: Any = generative_cls("gemini-2.5-flash-preview-09-2025")
            logging.info("GeminiClient [__init__]: Gemini model initialized.")
        except Exception as e:
            raise RuntimeError(f"GeminiClient initialization failed: {e}") from e

    def _generate_content(self, prompt: Any) -> str:
        """
        Generate content using Gemini API.

        Args:
            prompt: Combined system and user prompt; can be a single string or
                a structured list of chat messages compatible with the Gemini SDK.

        Returns:
            str: Generated content or error message
        """
        try:
            response = self.model.generate_content(prompt)

            if response.candidates and len(response.candidates) > 0:
                content = response.text
                logging.info(f"Successfully processed. Length: {len(content)} chars")
                return content
            error_msg = "Failed: No valid response from Gemini API"
            logging.error(error_msg)
            return error_msg

        except Exception as e:
            error_msg = f"Failed to get response from Gemini: {e!s}"
            logging.error(error_msg)
            return error_msg

    def get_detailed_crypto_analysis_with_news(
        self, indicators_message, news_feeded, conn=None
    ) -> str:
        """Get detailed crypto analysis with news using Gemini API."""
        start_time = time.time()
        logging.info("Starting detailed crypto analysis with news using Gemini")
        logging.info(f"Input news articles count: {len(news_feeded)}")

        price_data = fetch_and_format_candle_data(conn)

        user_messages = build_analysis_user_messages(
            news_feeded=news_feeded,
            indicators_message=indicators_message,
            price_data=price_data,
        )

        # Build prompt parts - system prompt first, then each user message separately
        prompt_parts = [{"role": "user", "parts": [{"text": SYSTEM_PROMPT_ANALYSIS_NEWS}]}] + [
            {"role": "user", "parts": [{"text": message}]} for message in user_messages
        ]

        # Log each message part separately for debugging
        logging.info("=" * 80)
        logging.info(f"GEMINI API REQUEST - Total parts: {len(prompt_parts)}")
        logging.info("=" * 80)

        for idx, part in enumerate(prompt_parts):
            text_content = part["parts"][0]["text"]
            text_length = len(text_content)

            # Identify the part type for clearer logging
            if idx == 0:
                part_type = "SYSTEM_PROMPT"
            elif "News Article" in text_content[:100]:
                # Extract article number from the message
                import re

                match = re.search(r"News Article (\d+)/(\d+)", text_content[:100])
                if match:
                    part_type = f"NEWS_ARTICLE_{match.group(1)}_of_{match.group(2)}"
                else:
                    part_type = "NEWS_ARTICLE"
            elif "Input News" in text_content[:100]:
                part_type = "NEWS_HEADER"
            elif (
                "Technical Indicators" in text_content[:100]
                or "Indicators Provided" in text_content[:100]
                or "Momentum" in text_content[:100]
            ):
                part_type = "INDICATORS"
            elif "Price Data" in text_content[:100] or "Recent Price Data" in text_content[:100]:
                part_type = "PRICE_DATA"
            elif (
                "Core principles" in text_content[:100]
                or "MANDATORY OUTPUT SECTIONS" in text_content[:200]
            ):
                part_type = "USER_INSTRUCTIONS"
            else:
                part_type = "OTHER"

            logging.info(f"\n--- Part {idx}: {part_type} ---")
            logging.info(f"Role: {part['role']}")
            logging.info(f"Length: {text_length:,} characters")

            # Log preview (first 300 chars)
            preview = text_content[:300].replace("\n", " ")
            logging.info(f"Preview: {preview}...")

            # For news articles, log the source and title if available
            MAX_NEWS_ARTICLE_LOG_LENGTH = 10000
            if "NEWS_ARTICLE" in part_type and text_length < MAX_NEWS_ARTICLE_LOG_LENGTH:
                try:
                    import json

                    # Try to extract article info
                    if "News Article" in text_content:
                        article_json_start = text_content.find("{")
                        if article_json_start > 0:
                            article_json = text_content[article_json_start:]
                            article_data = json.loads(article_json)
                            logging.info(f"  Source: {article_data.get('source', 'N/A')}")
                            logging.info(f"  Title: {article_data.get('title', 'N/A')[:100]}")
                except Exception:
                    pass

            # For INDICATORS and PRICE_DATA, log full content for debugging
            MAX_DEBUG_LOG_LENGTH = 2000
            if part_type in ["INDICATORS", "PRICE_DATA"]:
                logging.info(f"Full {part_type} content:")
                logging.info(text_content)
                logging.info(f"--- End of {part_type} ---")
            # For other short parts, log full content at debug level
            elif text_length < MAX_DEBUG_LOG_LENGTH:
                logging.debug(f"Full content:\n{text_content}\n")

        logging.info(f"\n{'=' * 80}")
        logging.info("Sending request to Gemini API...")
        logging.info(f"{'=' * 80}\n")

        result = self._generate_content(prompt_parts)
        logging.debug(f"Processing time: {time.time() - start_time:.2f} seconds")
        return result

    def highlight_articles(self, user_crypto_list, news_feeded) -> str:
        """Highlight articles based on user crypto list and news feed using Gemini API."""
        symbol_names = [symbol.symbol_name for symbol in user_crypto_list]
        logging.info("Starting article highlighting with Gemini")
        logging.debug(f"Symbol names provided: {symbol_names}")

        prompt = (
            f"{SYSTEM_PROMPT_HIGHLIGHT}\n\n"
            f"{USER_PROMPT_HIGHLIGHT.format(news_feeded=news_feeded, symbol_names=symbol_names)}"
        )

        return self._generate_content(prompt)
