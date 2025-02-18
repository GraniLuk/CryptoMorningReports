import os
import requests
from datetime import datetime, timedelta

CRYPTOPANIC_API = "https://cryptopanic.com/api/v1/posts/"

def get_news(api_key, symbol):
    """Fetch regulatory news from CryptoPanic for the last 24 hours
    
    Args:
        api_key (str): CryptoPanic API key
        symbols (list): List of cryptocurrency symbols to filter (e.g. ["BTC", "ETH"])
    """
    try:
        params = {
            'auth_token': api_key,
            'currencies': symbol, 
            'kind': 'news',
            'panic_score': 'true',
            'public': 'true'  # Ensure we're using the public API
        }
        
        response = requests.get(CRYPTOPANIC_API, params=params)
        data = response.json()
        
        # Get the current time
        now = datetime.utcnow()
        
        # Filter news from the last 24 hours
        filtered_news = [
            {
                'title': post['title'],
                'url': post['url'],
                'created_at': post['created_at'],
                'content': post.get('body', ''),
                'currencies': [
                    currency['code'] for currency in post.get('currencies', [])
                ]
            }
            for post in data.get('results', [])
            if now - datetime.strptime(post['created_at'], "%Y-%m-%dT%H:%M:%SZ") <= timedelta(days=3)
        ]
        
        return filtered_news
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    from source_repository import SourceID, Symbol
        # Get API keys from environment
    cryptopanic_key = os.getenv('CRYPTOPANIC_API_KEY')
    
    print("🔄 Fetching news from cryptopanic...\n")
    symbols = [
        Symbol(
            symbol_id=1,
            symbol_name="BTC",
            full_name="Bitcoin",
            source_id=SourceID.BINANCE,
        ),
        Symbol(
            symbol_id=2,
            symbol_name="ETH",
            full_name="Ethereum",
            source_id=SourceID.BINANCE,
        ),
        Symbol(
            symbol_id=3,
            symbol_name="VIRTUAL",
            full_name="Ethereum",
            source_id=SourceID.BINANCE
        )
    ]
    
        # Regulatory News
    if cryptopanic_key:
        for symbol in symbols:
            news = get_news(cryptopanic_key, symbol.symbol_name)
            if isinstance(news, list):
                print(f"📰 Latest Regulatory News for {symbol.symbol_name}:")
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