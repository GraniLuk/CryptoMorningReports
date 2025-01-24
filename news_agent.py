import requests

def get_crypto_news_summary(api_key, news_feeded, indicators_message):
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