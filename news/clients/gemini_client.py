"""Gemini AI client implementation."""

import json
import re
import time
from typing import TYPE_CHECKING

from google import genai  # type: ignore[import-untyped]

from infra.telegram_logging_handler import app_logger
from news.clients.base_client import AIClient
from news.prompts import (
    SYSTEM_PROMPT_ANALYSIS_NEWS,
    SYSTEM_PROMPT_HIGHLIGHT,
    USER_PROMPT_HIGHLIGHT,
    build_analysis_user_messages,
)
from news.utils.candle_data import fetch_and_format_candle_data


if TYPE_CHECKING:
    import pyodbc

    from infra.sql_connection import SQLiteConnectionWrapper
    from source_repository import Symbol


class GeminiClient(AIClient):
    """Client for Google Gemini AI API."""

    def __init__(
        self,
        api_key: str,
        primary_model: str = "gemini-2.5-flash",
        secondary_model: str = "gemini-2.0-flash",
    ):
        """Initialize Gemini client.

        Args:
            api_key (str): Google Gemini API key
            primary_model (str): Primary model to use (default: gemini-2.5-flash)
            secondary_model (str): Fallback model for retries (default: gemini-2.0-flash)

        Raises:
            ValueError: If API key is missing
            RuntimeError: If Gemini SDK initialization fails

        """
        self.api_key = api_key
        self.primary_model = primary_model
        self.secondary_model = secondary_model
        app_logger.info(
            f"GeminiClient [__init__]: Initializing. API key provided: {bool(api_key)}, "
            f"Primary model: {primary_model}, Secondary model: {secondary_model}",
        )

        if not self.api_key:
            msg = "GeminiClient initialization failed: API key missing"
            raise ValueError(msg)

        try:
            # Create a new client instance for each GeminiClient
            # This is simple and sufficient for twice-daily usage
            self.client = genai.Client(api_key=self.api_key)
            app_logger.info("GeminiClient [__init__]: Gemini SDK client created.")
        except Exception as e:
            msg = f"GeminiClient initialization failed: {e}"
            raise RuntimeError(msg) from e

    def _generate_content(
        self,
        prompt: str | list[dict[str, str]],
        model: str | None = None,
    ) -> tuple[str, str]:
        """Generate content using Gemini API with retry-with-fallback support.

        Args:
            prompt: Combined system and user prompt; can be a single string or
                a structured list of chat messages compatible with the Gemini SDK.
            model: Specific model to use (if None, uses primary_model)

        Returns:
            str: Generated content or error message

        """
        models_to_try = [model or self.primary_model, self.secondary_model]
        # Remove duplicates while preserving order
        models_to_try = list(dict.fromkeys(models_to_try))

        for idx, model_name in enumerate(models_to_try):
            is_last_attempt = idx == len(models_to_try) - 1
            model_type = "PRIMARY" if idx == 0 else "SECONDARY (FALLBACK)"
            app_logger.info(f"🤖 [{model_type}] Attempting generation with model: {model_name}")

            try:
                # Convert prompt format for new SDK
                if isinstance(prompt, str):
                    # Simple string prompt
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                else:
                    # Structured prompt with multiple parts
                    # New SDK expects list of Content objects or compatible dicts
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
            except Exception as e:  # noqa: BLE001 - Need to catch all Google API exceptions
                # Catch all exceptions including google.api_core.exceptions.ResourceExhausted
                error_msg = f"Failed with {model_name}: {e!s}"
                app_logger.warning(error_msg)

                # Check for rate limit errors (429, quota, resource exhausted)
                error_str = str(e).lower()
                error_type = type(e).__name__
                if (
                    "429" in error_str
                    or "quota" in error_str
                    or "rate limit" in error_str
                    or "resourceexhausted" in error_type.lower()
                ):
                    app_logger.warning(f"⚠️  Rate limit/quota error detected with {model_name}")

                if not is_last_attempt:
                    app_logger.info(f"⚠️  Retrying with fallback model: {models_to_try[idx + 1]}")
                    continue

                app_logger.exception(f"All retry attempts exhausted: {error_msg}")
                return f"Failed: {error_msg}", model_name
            else:
                if response.candidates and len(response.candidates) > 0:
                    try:
                        content = response.text
                        if content is None:
                            error_msg = f"Empty response from Gemini API with {model_name}"
                            app_logger.warning(error_msg)
                            if not is_last_attempt:
                                app_logger.info(
                                    f"⚠️  Retrying with fallback model: {models_to_try[idx + 1]}",
                                )
                                continue
                            return f"Failed: {error_msg}", model_name

                        model_type = "PRIMARY" if idx == 0 else "SECONDARY (FALLBACK)"
                        app_logger.info(
                            f"✅ [{model_type}] Successfully processed with {model_name}. "
                            f"Length: {len(content)} chars",
                        )
                    except ValueError as e:
                        # Handle case where response has candidates but no valid text
                        error_msg = f"Invalid response from Gemini API with {model_name}: {e!s}"
                        app_logger.warning(error_msg)

                        if not is_last_attempt:
                            app_logger.info(
                                f"⚠️  Retrying with fallback model: {models_to_try[idx + 1]}",
                            )
                            continue

                        return f"Failed: {error_msg}", model_name
                    else:
                        return content, model_name

                error_msg = f"No valid response from Gemini API with {model_name}"
                app_logger.warning(error_msg)

                if not is_last_attempt:
                    app_logger.info(f"⚠️  Retrying with fallback model: {models_to_try[idx + 1]}")
                    continue

                return f"Failed: {error_msg}", model_name

        last_model = models_to_try[-1] if models_to_try else "unknown"
        return (
            f"Failed: All retry attempts exhausted after trying models: {', '.join(models_to_try)}",
            last_model,
        )

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
                    app_logger.info(f"  Source: {article_data.get('source', 'N/A')}")
                    app_logger.info(f"  Title: {article_data.get('title', 'N/A')[:100]}")
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            app_logger.exception("Failed to parse article JSON from Gemini response")

    def _log_prompt_part(self, idx: int, part: dict, part_type: str) -> None:
        """Log details about a single prompt part."""
        text_content = part["parts"][0]["text"]
        text_length = len(text_content)

        app_logger.info(f"\n--- Part {idx}: {part_type} ---")
        app_logger.info(f"Role: {part['role']}")
        app_logger.info(f"Length: {text_length:,} characters")

        # Log preview
        preview = text_content[:300].replace("\n", " ")
        app_logger.info(f"Preview: {preview}...")

        # Special handling for different part types
        if "NEWS_ARTICLE" in part_type:
            self._log_news_article_details(text_content)

        max_debug_log_length = 2000
        if part_type in ["INDICATORS", "PRICE_DATA"]:
            app_logger.info(f"Full {part_type} content:")
            app_logger.info(text_content)
            app_logger.info(f"--- End of {part_type} ---")
        elif text_length < max_debug_log_length:
            app_logger.debug(f"Full content:\n{text_content}\n")

    def get_detailed_crypto_analysis_with_news(
        self,
        indicators_message: str,
        news_feeded: str,
        conn: "pyodbc.Connection | SQLiteConnectionWrapper | None" = None,
        model: str | None = None,
    ) -> tuple[str, str]:
        """Get detailed crypto analysis with news using Gemini API.

        Args:
            indicators_message: Technical indicators data
            news_feeded: JSON-formatted news articles
            conn: Database connection for fetching candle data
            model: Optional specific model to use (overrides primary_model)

        Returns:
            tuple[str, str]: (Generated analysis or error message, model_used)

        """
        start_time = time.time()
        app_logger.info("=" * 80)
        app_logger.info("📊 DETAILED CRYPTO ANALYSIS - Starting")
        app_logger.info(
            f"Configured models - Primary: {self.primary_model}, Secondary: {self.secondary_model}",
        )
        app_logger.info(f"Requested model for this call: {model or 'PRIMARY'}")
        app_logger.info("=" * 80)
        app_logger.info("Starting detailed crypto analysis with news using Gemini")
        app_logger.info(f"Input news articles count: {len(news_feeded)}")

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
        app_logger.info("=" * 80)
        app_logger.info(f"GEMINI API REQUEST - Total parts: {len(prompt_parts)}")
        app_logger.info("=" * 80)

        # Log each prompt part
        for idx, part in enumerate(prompt_parts):
            text_content = part["parts"][0]["text"]
            part_type = self._identify_part_type(idx, text_content)
            self._log_prompt_part(idx, part, part_type)

        app_logger.info(f"\n{'=' * 80}")
        app_logger.info("Sending request to Gemini API...")
        app_logger.info(f"{'=' * 80}\n")

        result, model_used = self._generate_content(prompt_parts, model=model)
        app_logger.debug(f"Processing time: {time.time() - start_time:.2f} seconds")
        return result, model_used

    def highlight_articles(
        self,
        user_crypto_list: list["Symbol"],
        news_feeded: str,
        model: str | None = None,
    ) -> str:
        """Highlight articles based on user crypto list and news feed using Gemini API.

        Args:
            user_crypto_list: List of Symbol objects representing user's crypto portfolio
            news_feeded: JSON-formatted news articles
            model: Optional specific model to use (overrides primary_model)

        Returns:
            str: Highlighted articles or error message

        """
        symbol_names = [symbol.symbol_name for symbol in user_crypto_list]
        app_logger.info("=" * 80)
        app_logger.info("🔍 ARTICLE HIGHLIGHTING - Starting")
        app_logger.info(
            f"Configured models - Primary: {self.primary_model}, Secondary: {self.secondary_model}",
        )
        app_logger.info(f"Requested model for this call: {model or 'PRIMARY'}")
        app_logger.info(f"Symbol names provided: {symbol_names}")
        app_logger.info("=" * 80)

        prompt = (
            f"{SYSTEM_PROMPT_HIGHLIGHT}\n\n"
            f"{USER_PROMPT_HIGHLIGHT.format(news_feeded=news_feeded, symbol_names=symbol_names)}"
        )

        result, _ = self._generate_content(prompt, model=model)
        return result
