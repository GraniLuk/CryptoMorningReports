import logging
import time
from abc import ABC, abstractmethod

import google.generativeai as genai
import requests

from news.rss_parser import get_news

# Define common system and user prompts as constants
SYSTEM_PROMPT_ANALYSIS = """\
You are an advanced crypto analyst specializing in detailed technical and on-chain analysis.
Provide in-depth explanations, including the reasoning behind resistance levels, support for analysis with charts and statistics, and comprehensive on-chain metrics interpretation.
Format all responses using Telegram's HTML syntax:
- Bold: <b>text</b>
- Italic: <i>text</i>
- Underline: <u>text</u>
- Strikethrough: <s>text</s>
- Links: <a href="https://example.com">text</a>
- Code: <code>inline code</code> or <pre>multi-line code</pre>
- No need to escape special characters like . ! ? = 

Ensure responses are cleanly formatted with proper HTML tags.
"""

USER_PROMPT_ANALYSIS = """\
Analyze the situation of current crypto market situation.
Focus on:
1. Detailed technical analysis, explaining why specific resistance/support levels are important.
2. On-chain analysis, interpreting metrics like active addresses, transaction volume, and network health.
3. Statistical data and charts that support your analysis.
4. Market sentiment with specific reasons.
Base your analysis on these indicators as well: {indicators_message}.
You need to choose one cryptocurrency to make a daily trade, short or long with explanations. 
If there is no significant information to report, state that there is no noteworthy information.
"""

SYSTEM_PROMPT_ANALYSIS_NEWS = """\
You are an advanced crypto analyst specializing in detailed technical and on-chain analysis.
Provide in-depth explanations, including the reasoning behind resistance levels, support for analysis with charts and statistics, and comprehensive on-chain metrics interpretation.
Focus only on the news articles provided.
Format all responses using Telegram's HTML syntax:
- Bold: <b>text</b>
- Italic: <i>text</i>
- Underline: <u>text</u>
- Strikethrough: <s>text</s>
- Links: <a href="https://example.com">text</a>
- Code: <code>inline code</code> or <pre>multi-line code</pre>
- No need to escape special characters like . ! ? = 
Ensure responses are cleanly formatted with proper HTML tags.
"""

USER_PROMPT_ANALYSIS_NEWS = """\
Analyze the following crypto news and data: {news_feeded}.
Focus on:
1. Detailed technical analysis, explaining why specific resistance/support levels are important.
2. On-chain analysis, interpreting metrics like active addresses, transaction volume, and network health.
3. Statistical data and charts that support your analysis.
4. Market sentiment with specific reasons.
Only use the provided news articles for your analysis. 
Base your analysis on these indicators as well: {indicators_message}.
You need to choose one cryptocurrency to make a daily trade, short or long with explanations. 
If there is no significant information to report, state that there is no noteworthy information.
"""

SYSTEM_PROMPT_HIGHLIGHT = """\
You are an advanced crypto article curator. Your task is to highlight articles that provide deep insights, detailed explanations, and comprehensive analysis of market trends, technical indicators, and on-chain metrics. Only consider the articles provided in the input.

Categorize your analysis into:
    1. Bitcoin
    2. Ethereum
    3. Other cryptocurrencies from a provided list
    4. Other cryptocurrencies not from the list

Format all responses using Telegram's HTML syntax:
    - Bold: <b>text</b>
    - Italic: <i>text</i>
    - Underline: <u>text</u>
    - Strikethrough: <s>text</s>
    - Links: <a href="https://example.com">text</a>
    - Code: <code>inline code</code> or <pre>multi-line code</pre>
    - No need to escape special characters like . ! ? = 

Ensure responses are cleanly formatted with proper HTML tags.
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
    def get_detailed_crypto_analysis(self, indicators_message, news_feeded):
        pass

    @abstractmethod
    def get_detailed_crypto_analysis_with_news(self, indicators_message, news_feeded):
        pass

    @abstractmethod
    def highlight_articles(self, user_crypto_list, news_feeded):
        pass


class PerplexityClient(AIClient):
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self.url = "https://api.perplexity.ai/chat/completions"

    def get_detailed_crypto_analysis(self, indicators_message, news_feeded):
        start_time = time.time()
        logging.info("Starting detailed crypto analysis with Perplexity")

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
                            indicators_message=indicators_message
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

    def get_detailed_crypto_analysis_with_news(self, indicators_message, news_feeded):
        start_time = time.time()
        logging.info("Starting detailed crypto analysis with Perplexity")
        logging.debug(f"Input news articles count: {len(news_feeded)}")

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

    def highlight_articles(self, user_crypto_list, news_feeded):
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
        genai.configure(api_key=api_key)
        # Default to most capable model
        self.model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25")

    def get_detailed_crypto_analysis(self, indicators_message, news_feeded):
        start_time = time.time()
        logging.info("Starting detailed crypto analysis with Gemini")

        try:
            prompt = f"{SYSTEM_PROMPT_ANALYSIS}\n\n{USER_PROMPT_ANALYSIS.format(indicators_message=indicators_message)}"

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

    def get_detailed_crypto_analysis_with_news(self, indicators_message, news_feeded):
        start_time = time.time()
        logging.info("Starting detailed crypto analysis with news using Gemini")
        logging.debug(f"Input news articles count: {len(news_feeded)}")

        try:
            prompt = f"{SYSTEM_PROMPT_ANALYSIS_NEWS}\n\n{USER_PROMPT_ANALYSIS_NEWS.format(news_feeded=news_feeded, indicators_message=indicators_message)}"

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

    def highlight_articles(self, user_crypto_list, news_feeded):
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
    api_key, indicators_message, news_feeded, api_type="perplexity"
):
    client = create_ai_client(api_type, api_key)
    return client.get_detailed_crypto_analysis(indicators_message, news_feeded)


def get_detailed_crypto_analysis_with_news(
    api_key, indicators_message, news_feeded, api_type="perplexity"
):
    client = create_ai_client(api_type, api_key)
    return client.get_detailed_crypto_analysis_with_news(
        indicators_message, news_feeded
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
