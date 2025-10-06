"""Gemini AI client implementation."""

import logging
import time
from typing import Any

import google.generativeai as genai  # type: ignore

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
        logging.info(
            f"GeminiClient [__init__]: Initializing. API key provided: {bool(api_key)}"
        )
        
        if not self.api_key:
            raise ValueError("GeminiClient initialization failed: API key missing")

        try:
            configure_fn = getattr(genai, "configure", None)
            if not callable(configure_fn):
                raise RuntimeError(
                    "genai.configure not available in google.generativeai module"
                )
            configure_fn(api_key=self.api_key)

            generative_cls = getattr(genai, "GenerativeModel", None)
            if generative_cls is None:
                raise RuntimeError(
                    "GenerativeModel not available in google.generativeai module"
                )
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
            else:
                error_msg = "Failed: No valid response from Gemini API"
                logging.error(error_msg)
                return error_msg
                
        except Exception as e:
            error_msg = f"Failed to get response from Gemini: {str(e)}"
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

        prompt_parts = [
            {"role": "user", "parts": [{"text": SYSTEM_PROMPT_ANALYSIS_NEWS}]}
        ] + [
            {"role": "user", "parts": [{"text": message}]}
            for message in user_messages
        ]

        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug("Generated prompt length for each part: %s", [
                (part["role"], sum(len(p["text"]) for p in part["parts"]))
                for part in prompt_parts
            ])
        logging.debug("Generated prompt parts: %s", prompt_parts)

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
