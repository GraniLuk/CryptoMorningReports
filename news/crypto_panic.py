import os
import requests


CRYPTOPANIC_API = "https://cryptopanic.com/api/v1/posts/"

def get_news(api_key, symbols):
    """Fetch regulatory news from CryptoPanic
    
    Args:
        api_key (str): CryptoPanic API key
        symbols (list): List of cryptocurrency symbols to filter (e.g. ["BTC", "ETH"])
    """
    try:
        params = {
            'auth_token': api_key,
            'currencies': ','.join(symbols),  # Join symbols with commas for API
            'filter': 'rising',
            'kind': 'news'
        }
        
        response = requests.get(CRYPTOPANIC_API, params=params)
        data = response.json()
        
        return [{
            'title': post['title'],
            'url': post['url'],
            'created_at': post['created_at'],
            'content': post.get('body', ''),  # Add content/body
            'currencies': [  # Add list of related cryptocurrencies
                currency['code'] for currency in post.get('currencies', [])
            ]
        } for post in data.get('results', [])]
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
        # Get API keys from environment
    cryptopanic_key = os.getenv('CRYPTOPANIC_API_KEY')
    
    print("🔄 Fetching news from cryptopanic...\n")
    symbols = ["VIRTUAL"]
    
    # Regulatory News
    if cryptopanic_key:
        news = get_news(cryptopanic_key, symbols)
        if isinstance(news, list):
            print("📰 Latest Regulatory News:")
            for item in news[:3]:  # Show top 3
                print(f"• {item['title']}")
                print(f"  Related to: {', '.join(item['currencies'])}")
                print(f"  {item['url']}")
                if item['content']:
                    print(f"  Summary: {item['content'][:200]}...")  # Show first 200 chars
                print()
        else:
            print(f"❌ News Error: {news.get('error', 'Unknown error')}")
    else:
        print("⚠️ CryptoPanic API key missing (news skipped)")