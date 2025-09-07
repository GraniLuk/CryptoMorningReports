import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import google.generativeai as genai  # type: ignore
import requests

from news.rss_parser import get_news
from source_repository import fetch_symbols
from technical_analysis.utilities.candle_formatter import (
    format_candle_data_for_prompt,
    get_candle_data,
)

# Define common system and user prompts as constants
SYSTEM_PROMPT_ANALYSIS = """\
You are an advanced crypto analyst specializing in detailed technical and on-chain analysis.
Provide in-depth explanations, including the reasoning behind resistance levels, support for analysis with charts and statistics, and comprehensive on-chain metrics interpretation.
Ensure responses are cleanly formatted with proper Markdown syntax.
"""

USER_PROMPT_ANALYSIS = """\
Analyze the situation of current crypto market situation.
Focus on:
1. Detailed technical analysis, explaining why specific resistance/support levels are important.
2. On-chain analysis, interpreting metrics like active addresses, transaction volume, and network health.
3. Statistical data and charts that support your analysis.
4. Market sentiment with specific reasons.
Base your analysis on these indicators: {indicators_message}
And this recent price data (most recent entries last):
{price_data}
You need to choose one cryptocurrency to make a daily trade, short or long with explanations. 
If there is no significant information to report, state that there is no noteworthy information.
At the end of the analysis, provide information about missing indicators and suggest what to look for in the future.
"""

SYSTEM_PROMPT_ANALYSIS_NEWS = """\
You are an advanced crypto analyst specializing in detailed technical and on-chain analysis.
Provide in-depth explanations, including the reasoning behind resistance levels, support for analysis with charts and statistics, and comprehensive on-chain metrics interpretation.
Focus only on the news articles provided.
Ensure responses are cleanly formatted with proper Markdown syntax.
"""

USER_PROMPT_ANALYSIS_NEWS = """\
Analyze the following crypto news and data: {news_feeded}.
Focus on:
1. Detailed technical analysis, explaining why specific resistance/support levels are important.
2. On-chain analysis, interpreting metrics like active addresses, transaction volume, and network health.
3. Statistical data and charts that support your analysis.
4. Market sentiment with specific reasons.
Only use the provided news articles for your analysis. 
Base your analysis on these indicators: {indicators_message}
And this recent price data (most recent entries last):
{price_data}
You need to choose one cryptocurrency to make a daily trade, short or long with explanations. 
If there is no significant information to report, state that there is no noteworthy information.
At the end of the analysis, provide information about missing indicators and suggest what to look for in the future.
"""

SYSTEM_PROMPT_HIGHLIGHT = """\
You are an advanced crypto article curator. Your task is to highlight articles that provide deep insights, detailed explanations, and comprehensive analysis of market trends, technical indicators, and on-chain metrics. Only consider the articles provided in the input.

Categorize your analysis into:
    1. Bitcoin
    2. Ethereum
    3. Other cryptocurrencies from a provided list
    4. Other cryptocurrencies not from the list

Format all responses using Markdown syntax.
"""

USER_PROMPT_HIGHLIGHT = """\
From the following news articles {news_feeded}, highlight the most insightful and detailed ones. Categorize your analysis as follows:

1. Bitcoin
2. Ethereum
3. Other cryptocurrencies from this list: {symbol_names}
4. Other cryptocurrencies not from the list: {symbol_names}

For each category, prioritize articles that:
1. Offer in-depth technical analysis with clear explanations of resistance/support levels.
2. Provide comprehensive on-chain analysis with interpretation of key metrics.
3. Include statistical data, charts, or graphs to support their analysis.
4. Discuss cryptocurrencies with high growth potential (especially for categories 3 and 4).
5. Explain complex market dynamics or new technological developments in the crypto space.

For each highlighted article, provide a brief explanation of its key insights and include the URL. If there are no significant articles for a category, state that there's no noteworthy information to report. 
Only consider the articles provided in the input.
"""


class AIClient(ABC):
    @abstractmethod
    def get_detailed_crypto_analysis(self, indicators_message, conn=None) -> str:
        pass

    @abstractmethod
    def get_detailed_crypto_analysis_with_news(
        self, indicators_message, news_feeded, conn=None
    ) -> str:
        pass

    @abstractmethod
    def highlight_articles(self, user_crypto_list, news_feeded) -> str:
        """Highlight articles based on user crypto list and news feed"""
        pass


class PerplexityClient(AIClient):
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self.url = "https://api.perplexity.ai/chat/completions"

    def get_detailed_crypto_analysis(self, indicators_message, conn=None) -> str:
        """Get detailed crypto analysis using Perplexity API
        Args:
            indicators_message (str): Indicators message for analysis
            conn (object, optional): Database connection object
        Returns:
            str: Analysis result or error message"""
        start_time = time.time()
        logging.info("Starting detailed crypto analysis with Perplexity")

        # Get candle data if database connection is provided
        price_data = ""
        if conn:
            try:
                symbols = fetch_symbols(conn)
                # Filter for BTC and ETH
                btc_eth = [
                    symbol for symbol in symbols if symbol.symbol_name in ["BTC", "ETH"]
                ]
                candle_data = get_candle_data(btc_eth, conn)
                price_data = format_candle_data_for_prompt(candle_data)
                logging.info("Successfully fetched candle data for analysis")
            except Exception as e:
                logging.error(f"Failed to fetch candle data: {str(e)}")
                price_data = "No price data available."
        else:
            price_data = "No price data available (database connection not provided)."

        models = ["sonar-pro"]  # Models to try in order
        max_retries = len(models)
        current_try = 0

        while current_try < max_retries:
            current_model = models[current_try]
            logging.info(f"Attempting with model: {current_model}")

            data = {
                "model": current_model,
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT_ANALYSIS,
                    },
                    {
                        "role": "user",
                        "content": USER_PROMPT_ANALYSIS.format(
                            indicators_message=indicators_message, price_data=price_data
                        ),
                    },
                ],
            }

            try:
                response = requests.post(self.url, json=data, headers=self.headers)
                logging.info(f"API Response Status: {response.status_code}")

                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    logging.info(
                        f"Successfully processed analysis. Length: {len(content)} chars"
                    )
                    logging.debug(
                        f"Processing time: {time.time() - start_time:.2f} seconds"
                    )
                    return content
                elif response.status_code == 504 and current_try < max_retries - 1:
                    logging.warning(
                        f"Received 504 error with {current_model}, retrying with next model"
                    )
                    current_try += 1
                    continue
                else:
                    error_msg = (
                        f"Failed: API error: {response.status_code} - {response.text}"
                    )
                    logging.error(error_msg)
                    return error_msg

            except Exception as e:
                error_msg = f"Failed to get crypto analysis: {str(e)}"
                logging.error(error_msg)
                return error_msg

        return f"Failed: All retry attempts exhausted after trying models: {', '.join(models)}"

    def get_detailed_crypto_analysis_with_news(
        self, indicators_message, news_feeded, conn=None
    ) -> str:
        """Get detailed crypto analysis with news using Perplexity API
        Args:
            indicators_message (str): Indicators message for analysis
            news_feeded (str): News articles to analyze
            conn (object, optional): Database connection object
        Returns:
            str: Analysis result or error message"""
        start_time = time.time()
        logging.info("Starting detailed crypto analysis with news using Perplexity")
        logging.debug(f"Input news articles count: {len(news_feeded)}")

        # Get candle data if database connection is provided
        price_data = ""
        if conn:
            try:
                symbols = fetch_symbols(conn)
                # Filter for BTC and ETH
                btc_eth = [
                    symbol for symbol in symbols if symbol.symbol_name in ["BTC", "ETH"]
                ]
                candle_data = get_candle_data(btc_eth, conn)
                price_data = format_candle_data_for_prompt(candle_data)
                logging.info("Successfully fetched candle data for analysis with news")
            except Exception as e:
                logging.error(f"Failed to fetch candle data: {str(e)}")
                price_data = "No price data available."
        else:
            price_data = "No price data available (database connection not provided)."

        models = ["sonar-deep-research"]  # Models to try in order
        max_retries = len(models)
        current_try = 0

        while current_try < max_retries:
            current_model = models[current_try]
            logging.info(f"Attempting with model: {current_model}")

            data = {
                "model": current_model,
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT_ANALYSIS_NEWS,
                    },
                    {
                        "role": "user",
                        "content": USER_PROMPT_ANALYSIS_NEWS.format(
                            news_feeded=news_feeded,
                            indicators_message=indicators_message,
                            price_data=price_data,
                        ),
                    },
                ],
            }

            try:
                response = requests.post(self.url, json=data, headers=self.headers)
                logging.info(f"API Response Status: {response.status_code}")

                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    logging.info(
                        f"Successfully processed analysis. Length: {len(content)} chars"
                    )
                    logging.debug(
                        f"Processing time: {time.time() - start_time:.2f} seconds"
                    )
                    return content
                elif response.status_code == 504 and current_try < max_retries - 1:
                    logging.warning(
                        f"Received 504 error with {current_model}, retrying with next model"
                    )
                    current_try += 1
                    continue
                else:
                    error_msg = (
                        f"Failed: API error: {response.status_code} - {response.text}"
                    )
                    logging.error(error_msg)
                    return error_msg

            except Exception as e:
                error_msg = f"Failed to get crypto analysis: {str(e)}"
                logging.error(error_msg)
                return error_msg

        return f"Failed: All retry attempts exhausted after trying models: {', '.join(models)}"

    def highlight_articles(self, user_crypto_list, news_feeded) -> str:
        symbol_names = [symbol.symbol_name for symbol in user_crypto_list]

        models = ["sonar-deep-research", "sonar-pro"]  # Models to try in order
        max_retries = len(models)
        current_try = 0

        while current_try < max_retries:
            current_model = models[current_try]
            logging.info(f"Attempting with model: {current_model}")

            data = {
                "model": current_model,
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT_HIGHLIGHT,
                    },
                    {
                        "role": "user",
                        "content": USER_PROMPT_HIGHLIGHT.format(
                            news_feeded=news_feeded, symbol_names=symbol_names
                        ),
                    },
                ],
            }

            logging.info(
                f"Making API request with {len(news_feeded)} articles using {current_model}"
            )
            logging.debug(f"Symbol names provided: {symbol_names}")

            try:
                response = requests.post(self.url, json=data, headers=self.headers)
                logging.info(f"API Response Status Code: {response.status_code}")
                logging.debug(f"Response Headers: {response.headers}")

                if response.status_code == 200:
                    response_content = response.json()["choices"][0]["message"][
                        "content"
                    ]
                    logging.info("Successfully received API response")
                    logging.debug(f"Response content length: {len(response_content)}")
                    return response_content
                elif response.status_code == 504 and current_try < max_retries - 1:
                    logging.warning(
                        f"Received 504 error with {current_model}, retrying with next model"
                    )
                    current_try += 1
                    continue
                else:
                    error_msg = f"Failed: {response.status_code} - {response.text}"
                    logging.error(error_msg)
                    if current_try < max_retries - 1:
                        current_try += 1
                        continue
                    return error_msg

            except Exception as e:
                error_msg = f"Failed to highlight articles: {str(e)}"
                logging.error(error_msg)
                if current_try < max_retries - 1:
                    current_try += 1
                    continue
                return error_msg

        return f"Failed: All retry attempts exhausted after trying models: {', '.join(models)}"


class GeminiClient(AIClient):
    def __init__(self, api_key):
        self.api_key = api_key
        logging.info(
            f"GeminiClient [__init__]: Initializing. API key provided: {bool(api_key)}"
        )
        if not self.api_key:
            raise ValueError("GeminiClient initialization failed: API key missing")

        try:
            configure_fn = getattr(genai, "configure", None)
            if not callable(configure_fn):
                raise RuntimeError("genai.configure not available in google.generativeai module")
            configure_fn(api_key=self.api_key)

            generative_cls = getattr(genai, "GenerativeModel", None)
            if generative_cls is None:
                raise RuntimeError(
                    "GenerativeModel not available in google.generativeai module"
                )
            self.model: Any = generative_cls("gemini-2.5-flash-preview-05-20")
            logging.info("GeminiClient [__init__]: Gemini model initialized.")
        except Exception as e:
            raise RuntimeError(
                f"GeminiClient initialization failed: {e}"
            ) from e

    def get_detailed_crypto_analysis(self, indicators_message, conn=None) -> str:
        """Get detailed crypto analysis using Gemini API
        Args:
            indicators_message (str): Indicators message for analysis
            conn (object, optional): Database connection object
        Returns:
            str: Analysis result or error message"""
        start_time = time.time()
        logging.info("Starting detailed crypto analysis with Gemini")

        # Get candle data if database connection is provided
        price_data = ""
        if conn:
            try:
                symbols = fetch_symbols(conn)
                # Filter for BTC and ETH
                btc_eth = [
                    symbol for symbol in symbols if symbol.symbol_name in ["BTC", "ETH"]
                ]
                candle_data = get_candle_data(btc_eth, conn)
                price_data = format_candle_data_for_prompt(candle_data)
                logging.info("Successfully fetched candle data for analysis")
            except Exception as e:
                logging.error(f"Failed to fetch candle data: {str(e)}")
                price_data = "No price data available."
        else:
            price_data = "No price data available (database connection not provided)."

        try:
            prompt = f"{SYSTEM_PROMPT_ANALYSIS}\n\n{USER_PROMPT_ANALYSIS.format(indicators_message=indicators_message, price_data=price_data)}"

            response = self.model.generate_content(prompt)

            if response.candidates and len(response.candidates) > 0:
                content = response.text
                logging.info(
                    f"Successfully processed analysis with Gemini. Length: {len(content)} chars"
                )
                logging.debug(
                    f"Processing time: {time.time() - start_time:.2f} seconds"
                )
                return content
            else:
                error_msg = "Failed: No valid response from Gemini API"
                logging.error(error_msg)
                return error_msg

        except Exception as e:
            error_msg = f"Failed to get crypto analysis from Gemini: {str(e)}"
            logging.error(error_msg)
            return error_msg

    def get_detailed_crypto_analysis_with_news(
        self, indicators_message, news_feeded, conn=None
    ) -> str:
        """Get detailed crypto analysis with news using Gemini API
        Args:
            indicators_message (str): Indicators message for analysis
            news_feeded (str): News articles to analyze
            conn: Database connection object (optional)
        Returns:
            str: Analysis result or error message"""
        start_time = time.time()
        logging.info("Starting detailed crypto analysis with news using Gemini")
        logging.debug(f"Input news articles count: {len(news_feeded)}")

        # Get candle data if database connection is provided
        price_data = ""
        if conn:
            try:
                symbols = fetch_symbols(conn)
                # Filter for BTC and ETH
                btc_eth = [
                    symbol for symbol in symbols if symbol.symbol_name in ["BTC", "ETH"]
                ]
                candle_data = get_candle_data(btc_eth, conn)
                price_data = format_candle_data_for_prompt(candle_data)
                logging.info("Successfully fetched candle data for analysis with news")
            except Exception as e:
                logging.error(f"Failed to fetch candle data: {str(e)}")
                price_data = "No price data available."
        else:
            price_data = "No price data available (database connection not provided)."

        try:
            prompt = f"{SYSTEM_PROMPT_ANALYSIS_NEWS}\n\n{USER_PROMPT_ANALYSIS_NEWS.format(news_feeded=news_feeded, indicators_message=indicators_message, price_data=price_data)}"

            response = self.model.generate_content(prompt)

            if response.candidates and len(response.candidates) > 0:
                content = response.text
                logging.info(
                    f"Successfully processed analysis with Gemini. Length: {len(content)} chars"
                )
                logging.debug(
                    f"Processing time: {time.time() - start_time:.2f} seconds"
                )
                return content
            else:
                error_msg = "Failed: No valid response from Gemini API"
                logging.error(error_msg)
                return error_msg

        except Exception as e:
            error_msg = f"Failed to get crypto analysis with news from Gemini: {str(e)}"
            logging.error(error_msg)
            return error_msg

    def highlight_articles(self, user_crypto_list, news_feeded) -> str:
        """Highlight articles based on user crypto list and news feed using Gemini API
        Args:
            user_crypto_list (list): List of user crypto symbols
            news_feeded (str): News articles to analyze
        Returns:
            str: Highlighted articles or error message"""
        symbol_names = [symbol.symbol_name for symbol in user_crypto_list]
        logging.info("Starting article highlighting with Gemini")
        logging.debug(f"Symbol names provided: {symbol_names}")

        try:
            prompt = f"{SYSTEM_PROMPT_HIGHLIGHT}\n\n{USER_PROMPT_HIGHLIGHT.format(news_feeded=news_feeded, symbol_names=symbol_names)}"

            response = self.model.generate_content(prompt)

            if response.candidates and len(response.candidates) > 0:
                content = response.text
                logging.info("Successfully received Gemini API response")
                logging.debug(f"Response content length: {len(content)}")
                return content
            else:
                error_msg = "Failed: No valid response from Gemini API"
                logging.error(error_msg)
                return error_msg

        except Exception as e:
            error_msg = f"Failed to highlight articles with Gemini: {str(e)}"
            logging.error(error_msg)
            return error_msg


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
    elif api_type.lower() == "gemini":
        return GeminiClient(api_key)
    else:
        raise ValueError(f"Unsupported AI API type: {api_type}")


# Legacy functions for backwards compatibility
def get_detailed_crypto_analysis(
    api_key, indicators_message, api_type="perplexity", conn=None
):
    client = create_ai_client(api_type, api_key)
    return client.get_detailed_crypto_analysis(indicators_message, conn)


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
