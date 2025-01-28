import requests

from news.rss_parser import fetch_rss_news

def get_detailed_crypto_analysis(api_key, indicators_message):
    url = "https://api.perplexity.ai/chat/completions"
    
    news_feeded = get_news()
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "system",
                "content": "You are an advanced crypto analyst specializing in detailed technical and on-chain analysis. Provide in-depth explanations, including the reasoning behind resistance levels, support for analysis with charts and statistics, and comprehensive on-chain metrics interpretation."
            },
            {
                "role": "user",
                "content": f"Analyze the following crypto news and data: {news_feeded}. Focus on:\n1. Detailed technical analysis, explaining why specific resistance/support levels are important.\n2. On-chain analysis, interpreting metrics like active addresses, transaction volume, and network health.\n3. Statistical data and charts that support your analysis.\n4. Market sentiment with specific reasons.\nBase your analysis on these indicators as well: {indicators_message}"
            }
        ]
    }
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Error: {response.status_code} - {response.text}"
    
def get_news():
        decrypt = "https://decrypt.co/feed"
        coindesk = "https://www.coindesk.com/arc/outboundfeeds/rss"
        newsBTC = "https://www.newsbtc.com/feed"
        coinJournal = "https://coinjournal.net/feed"
        coinpedia = "https://coinpedia.org/feed"
        cryptopotato = "https://cryptopotato.com/feed"
        news_feeded = fetch_rss_news(decrypt)
        news_feeded += fetch_rss_news(coindesk)
        news_feeded += fetch_rss_news(newsBTC)
        news_feeded += fetch_rss_news(coinJournal)
        news_feeded += fetch_rss_news(coinpedia)
        news_feeded += fetch_rss_news(cryptopotato)
        return news_feeded
    
def highlight_articles(api_key, news_feeded, user_crypto_list):
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
                "content": "You are an advanced crypto article curator. Highlight articles that provide deep insights, detailed explanations, and comprehensive analysis of market trends, technical indicators, and on-chain metrics."
            },
            {
                "role": "user",
                "content": f"From the following news articles {news_feeded}, highlight the most insightful and detailed ones. Prioritize articles that:\n1. Offer in-depth technical analysis with clear explanations of resistance/support levels.\n2. Provide comprehensive on-chain analysis with interpretation of key metrics.\n3. Include statistical data, charts, or graphs to support their analysis.\n4. Discuss cryptocurrencies with high growth potential not in this list: {symbol_names}.\n5. Explain complex market dynamics or new technological developments in the crypto space.\nFor each highlighted article, provide a brief explanation of its key insights and include the URL."
            }
        ]
    }
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Error: {response.status_code} - {response.text}"