import requests

from rss_parser import fetch_rss_news

def get_crypto_news_summary(api_key, indicators_message):
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
                "content": "You are a crypto news analyst. Summarize the latest crypto news, focusing on cryptocurrencies mentioned in news and technical indicators tables. Provide a brief overview of market sentiment (bullish or bearish) for each major cryptocurrency mentioned."
            },
            {
                "role": "user",
                "content": f"Summarize today's top crypto news content provided here {news_feeded} and provide sentiment analysis for major cryptocurrencies. You can also base your analysis on the following indicators: " + indicators_message
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
        crypto_panic = "https://cryptopanic.com/news/rss/"
        news_feeded = fetch_rss_news(decrypt)
        news_feeded += fetch_rss_news(coindesk)
        news_feeded += fetch_rss_news(crypto_panic)
        return news_feeded