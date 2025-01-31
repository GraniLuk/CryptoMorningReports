import requests

def get_detailed_crypto_analysis(api_key, indicators_message, news_feeded):
    url = "https://api.perplexity.ai/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "sonar-pro",
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
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Error: {response.status_code} - {response.text}"
    
    
def highlight_articles(api_key, user_crypto_list, news_feeded):
    url = "https://api.perplexity.ai/chat/completions"
    
    symbol_names = [symbol.symbol_name for symbol in user_crypto_list]
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
    "model": "sonar-pro",
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

For each highlighted article, provide a brief explanation of its key insights. If there are no significant articles for a category, state that there's no noteworthy information to report. Only consider the articles provided in the input."""
        }
    ]
}
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Error: {response.status_code} - {response.text}"