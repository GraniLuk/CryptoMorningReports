"""Gemini AI client implementation."""

import json
import logging
import re
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
        """Initialize Gemini client.

        Args:
            api_key (str): Google Gemini API key

        Raises:
            ValueError: If API key is missing
            RuntimeError: If Gemini SDK initialization fails

        """
        self.api_key = api_key
        logging.info(f"GeminiClient [__init__]: Initializing. API key provided: {bool(api_key)}")

        if not self.api_key:
            msg = "GeminiClient initialization failed: API key missing"
            raise ValueError(msg)

        configure_fn = getattr(genai, "configure", None)
        if not callable(configure_fn):
            msg = "genai.configure not available in google.generativeai module"
            raise TypeError(msg)

        generative_cls = getattr(genai, "GenerativeModel", None)
        if generative_cls is None:
            msg = "GenerativeModel not available in google.generativeai module"
            raise RuntimeError(msg)

        try:
            configure_fn(api_key=self.api_key)
            self.model: Any = generative_cls("gemini-2.5-flash-preview-09-2025")
            logging.info("GeminiClient [__init__]: Gemini model initialized.")
        except Exception as e:
            msg = f"GeminiClient initialization failed: {e}"
            raise RuntimeError(msg) from e

    def _generate_content(self, prompt: Any) -> str:
        """Generate content using Gemini API.

        Args:
            prompt: Combined system and user prompt; can be a single string or
                a structured list of chat messages compatible with the Gemini SDK.

        Returns:
            str: Generated content or error message

        """
        try:
            response = self.model.generate_content(prompt)
        except Exception as e:
            error_msg = f"Failed to get response from Gemini: {e!s}"
            logging.exception(error_msg)
            return error_msg
        else:
            if response.candidates and len(response.candidates) > 0:
                content = response.text
                logging.info(f"Successfully processed. Length: {len(content)} chars")
                return content
            error_msg = "Failed: No valid response from Gemini API"
            logging.error(error_msg)
            return error_msg

    def _identify_part_type(self, idx: int, text_content: str) -> str:
        """Identify the type of prompt part for logging purposes."""
        if idx == 0:
            return "SYSTEM_PROMPT"

        text_preview = text_content[:200]

        if "News Article" in text_content[:100]:
            match = re.search(r"News Article (\d+)/(\d+)", text_content[:100])
            if match:
                return f"NEWS_ARTICLE_{match.group(1)}_of_{match.group(2)}"
            return "NEWS_ARTICLE"

        if "Input News" in text_preview[:100]:
            return "NEWS_HEADER"

        if any(
            keyword in text_preview
            for keyword in ["Technical Indicators", "Indicators Provided", "Momentum"]
        ):
            return "INDICATORS"

        if any(keyword in text_preview for keyword in ["Price Data", "Recent Price Data"]):
            return "PRICE_DATA"

        if "Core principles" in text_preview or "MANDATORY OUTPUT SECTIONS" in text_preview:
            return "USER_INSTRUCTIONS"

        return "OTHER"

    def _log_news_article_details(self, text_content: str) -> None:
        """Extract and log news article details if available."""
        max_news_article_log_length = 10000
        if len(text_content) >= max_news_article_log_length:
            return

        try:
            if "News Article" in text_content:
                article_json_start = text_content.find("{")
                if article_json_start > 0:
                    article_json = text_content[article_json_start:]
                    article_data = json.loads(article_json)
                    logging.info(f"  Source: {article_data.get('source', 'N/A')}")
                    logging.info(f"  Title: {article_data.get('title', 'N/A')[:100]}")
        except Exception:
            logging.exception("Failed to parse article JSON from Gemini response")

    def _log_prompt_part(self, idx: int, part: dict, part_type: str) -> None:
        """Log details about a single prompt part."""
        text_content = part["parts"][0]["text"]
        text_length = len(text_content)

        logging.info(f"\n--- Part {idx}: {part_type} ---")
        logging.info(f"Role: {part['role']}")
        logging.info(f"Length: {text_length:,} characters")

        # Log preview
        preview = text_content[:300].replace("\n", " ")
        logging.info(f"Preview: {preview}...")

        # Special handling for different part types
        if "NEWS_ARTICLE" in part_type:
            self._log_news_article_details(text_content)

        max_debug_log_length = 2000
        if part_type in ["INDICATORS", "PRICE_DATA"]:
            logging.info(f"Full {part_type} content:")
            logging.info(text_content)
            logging.info(f"--- End of {part_type} ---")
        elif text_length < max_debug_log_length:
            logging.debug(f"Full content:\n{text_content}\n")

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

        # Log request details
        logging.info("=" * 80)
        logging.info(f"GEMINI API REQUEST - Total parts: {len(prompt_parts)}")
        logging.info("=" * 80)

        # Log each prompt part
        for idx, part in enumerate(prompt_parts):
            text_content = part["parts"][0]["text"]
            part_type = self._identify_part_type(idx, text_content)
            self._log_prompt_part(idx, part, part_type)

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
