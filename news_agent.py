import requests

def get_crypto_news_summary(api_key):
    url = "https://api.perplexity.ai/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "llama-3.1-sonar-large-128k-online",
        "messages": [
            {
                "role": "system",
                "content": "You are a crypto news analyst. Summarize the latest crypto news, focusing on major cryptocurrencies like Bitcoin and Ethereum. Provide a brief overview of market sentiment (bullish or bearish) for each major cryptocurrency mentioned."
            },
            {
                "role": "user",
                "content": "Summarize today's top crypto news and provide sentiment analysis for major cryptocurrencies."
            }
        ]
    }
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Error: {response.status_code} - {response.text}"