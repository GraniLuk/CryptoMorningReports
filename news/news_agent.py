import requests
import logging
import time

def get_detailed_crypto_analysis(api_key, indicators_message, news_feeded):
    start_time = time.time()
    logging.info(f"Starting detailed crypto analysis")
    logging.debug(f"Input news articles count: {len(news_feeded)}")

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    models = ["sonar-reasoning", "sonar-pro"]  # Models to try in order
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
                    "content": "You are an advanced crypto analyst specializing in detailed technical and on-chain analysis. Provide in-depth explanations, including the reasoning behind resistance levels, support for analysis with charts and statistics, and comprehensive on-chain metrics interpretation. Focus only on the news articles provided."
                },
                {
                    "role": "user",
                    "content": f"Analyze the following crypto news and data: {news_feeded}. Focus on:\n1. Detailed technical analysis, explaining why specific resistance/support levels are important.\n2. On-chain analysis, interpreting metrics like active addresses, transaction volume, and network health.\n3. Statistical data and charts that support your analysis.\n4. Market sentiment with specific reasons.\nOnly use the provided news articles for your analysis. Base your analysis on these indicators as well: {indicators_message}"
                }
            ]
        }

        try:
            response = requests.post(url, json=data, headers=headers)
            logging.info(f"API Response Status: {response.status_code}")

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                logging.info(f"Successfully processed analysis. Length: {len(content)} chars")
                logging.debug(f"Processing time: {time.time() - start_time:.2f} seconds")
                return content
            elif response.status_code == 504 and current_try < max_retries - 1:
                logging.warning(f"Received 504 error with {current_model}, retrying with next model")
                current_try += 1
                continue
            else:
                error_msg = f"Failed: API error: {response.status_code} - {response.text}"
                logging.error(error_msg)
                return error_msg

        except Exception as e:
            error_msg = f"Failed to get crypto analysis: {str(e)}"
            logging.error(error_msg)
            return error_msg

    return f"Failed: All retry attempts exhausted after trying models: {', '.join(models)}"

def highlight_articles(api_key, user_crypto_list, news_feeded):
    url = "https://api.perplexity.ai/chat/completions"
    
    symbol_names = [symbol.symbol_name for symbol in user_crypto_list]
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
    "model": "sonar-reasoning",
    "messages": [
        {
            "role": "system",
            "content": "You are an advanced crypto article curator. Highlight articles that provide deep insights, detailed explanations, and comprehensive analysis of market trends, technical indicators, and on-chain metrics. Only consider the articles provided in the input. Categorize your analysis into Bitcoin, Ethereum, other cryptocurrencies from a provided list, and other cryptocurrencies not from the list."
        },
        {
            "role": "user",
            "content": f"""From the following news articles {news_feeded}, highlight the most insightful and detailed ones. Categorize your analysis as follows:

1. Bitcoin
2. Ethereum
3. Other cryptocurrencies from this list: {symbol_names}
4. Other cryptocurrencies not from this list: {symbol_names}

For each category, prioritize articles that:
1. Offer in-depth technical analysis with clear explanations of resistance/support levels.
2. Provide comprehensive on-chain analysis with interpretation of key metrics.
3. Include statistical data, charts, or graphs to support their analysis.
4. Discuss cryptocurrencies with high growth potential (especially for categories 3 and 4).
5. Explain complex market dynamics or new technological developments in the crypto space.

For each highlighted article, provide a brief explanation of its key insights and include the URL. If there are no significant articles for a category, state that there's no noteworthy information to report. Only consider the articles provided in the input."""
        }
    ]
}

    logging.info(f"Making API request with {len(news_feeded)} articles")
    logging.debug(f"Symbol names provided: {symbol_names}")

    response = requests.post(url, json=data, headers=headers)

    logging.info(f"API Response Status Code: {response.status_code}")
    logging.debug(f"Response Headers: {response.headers}")

    if response.status_code == 200:
        response_content = response.json()["choices"][0]["message"]["content"]
        logging.info("Successfully received API response")
        logging.debug(f"Response content length: {len(response_content)}")
        return response_content
    else:
        error_msg = f"Failed: {response.status_code} - {response.text}"
        logging.error(error_msg)
        return error_msg
    
if __name__ == "__main__":
    # Example usage
    api_key = "your_api_key_here"

    class Symbol:
        def __init__(self, symbol_id, symbol_name, full_name):
            self.symbol_id = symbol_id
            self.symbol_name = symbol_name
            self.full_name = full_name
    user_crypto_list = [
        # Example list of user crypto symbols
        # Replace with actual symbol objects
    Symbol(symbol_id=1, symbol_name='BTC', full_name='Bitcoin'),
    Symbol(symbol_id=2, symbol_name='ETH', full_name='Etherum')
    ]
    
    news_feeded = [
        # Example list of news articles
        # Replace with actual news articles
        {"title": "Bitcoin hits new high", "url": "http://example.com/bitcoin-high"},
        {"title": "Ethereum 2.0 launch", "url": "http://example.com/ethereum-launch"}
    ]
    
    highlighted_news = highlight_articles(api_key, user_crypto_list, news_feeded)
    
    # Print results
    print(highlighted_news)