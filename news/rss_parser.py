import feedparser
from datetime import datetime, timedelta
from time import mktime
import requests
import json
from bs4 import BeautifulSoup

def get_news():
    feeds = {
        "decrypt": "https://decrypt.co/feed",
        "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss",
        "newsBTC": "https://www.newsbtc.com/feed",
        "coinJournal": "https://coinjournal.net/feed",
        "coinpedia": "https://coinpedia.org/feed",
        "cryptopotato": "https://cryptopotato.com/feed",
        "beincrypto" : "https://beincrypto.com/bitcoin-news/feed/",
        "ambcrypto" : "https://ambcrypto.com/feed/",
    }
    
    all_news = []
    for source, url in feeds.items():
        all_news.extend(fetch_rss_news(url, source))
    
    return json.dumps(all_news, indent=2)

def fetch_rss_news(feed_url, source):
    try:
        feed = feedparser.parse(feed_url)
        latest_news = []
        current_time = datetime.now()
        
        for entry in feed.entries:
            published_time = datetime.fromtimestamp(mktime(entry.published_parsed))
            
            if current_time - published_time <= timedelta(days=1):
                full_content = fetch_full_content(entry.link)
                latest_news.append({
                    "source": source,
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.published,
                    "content": full_content
                })
                
                if len(latest_news) >= 2:
                    break
                    
        return latest_news
    except Exception as e:
        print(f"Error fetching news from {feed_url}: {str(e)}")
        return []

def fetch_full_content(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        article = soup.find('article') or soup.find('div', class_='article-content')
        if article:
            return article.get_text()
        else:
            return "Failed to extract full content"
    except Exception as e:
        print(f"Error fetching full content from {url}: {str(e)}")
        return "Failed to fetch full content"

if __name__ == "__main__":
    print(get_news())