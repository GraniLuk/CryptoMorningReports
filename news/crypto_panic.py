import os
import requests
from datetime import datetime, timedelta, timezone

CRYPTOPANIC_API = "https://cryptopanic.com/api/v1/posts/"

def get_panic_news(symbols):
    """Fetch regulatory news from CryptoPanic for multiple symbols
    
    Args:
        api_key (str): CryptoPanic API key
        symbols (list): List of cryptocurrency symbols to filter (e.g. ["BTC", "ETH"])
    
    Returns:
        str: Aggregated news message for all symbols
    """
    try:
        all_news = []
        # Calculate cutoff time for last 24 hours
        now = datetime.now()
        api_key = os.getenv('CRYPTOPANIC_API_KEY') 
        
        # Fetch news for each symbol separately
        for symbol in symbols:
            params = {
                'auth_token': api_key,
                'currencies': symbol,
                'filter': 'rising',
                'kind': 'news'
            }
            
            response = requests.get(CRYPTOPANIC_API, params=params)
            data = response.json()
            
            # Add symbol's news to the collection if within last 24h
            symbol_news = [{
                'symbol': symbol,
                'title': post['title'],
                'url': post['url'],
                'created_at': post['created_at'],
                'content': post.get('body', ''),
                'currencies': [
                    currency['code'] for currency in post.get('currencies', [])
                ]
            } for post in data.get('results', [])
                if now - datetime.strptime(post['created_at'], "%Y-%m-%dT%H:%M:%SZ") <= timedelta(days=3)]
            
            all_news.extend(symbol_news)
        
        # Sort all news by creation date (newest first)
        all_news.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Create aggregated message
        message = "📰 Latest Cryptocurrency News (Last 24 Hours):\n\n"
        
        for news in all_news[:10]:  # Limit to top 10 most recent news
            message += f"🔸 {news['symbol']} - {news['title']}\n"
            message += f"   Related to: {', '.join(news['currencies'])}\n"
            message += f"   {news['url']}\n"
            if news['content']:
                message += f"   Summary: {news['content'][:200]}...\n"
            message += "\n"
        
        return message if all_news else "No news found in the last 24 hours."
        
    except Exception as e:
        return f"Error fetching news: {str(e)}"


if __name__ == "__main__":
        # Get API keys from environment
  
    print("🔄 Fetching news from cryptopanic...\n")
    symbols = ["BTC","ETH","VIRTUAL"]
    
    # News
    news_message = get_panic_news(symbols)