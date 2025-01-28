import feedparser
from datetime import datetime, timedelta
from time import mktime
import requests
from bs4 import BeautifulSoup

def fetch_rss_news(feed_url):
    try:
        feed = feedparser.parse(feed_url)
        latest_news = []
        current_time = datetime.now()
        
        for entry in feed.entries:
            published_time = datetime.fromtimestamp(mktime(entry.published_parsed))
            
            if current_time - published_time <= timedelta(days=1):
                full_content = fetch_full_content(entry.link)
                latest_news.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.published,
                    "content": full_content
                })
                
                if len(latest_news) >= 15:
                    break
                    
        return latest_news
    except Exception as e:
        print(f"Error fetching news from {feed_url}: {str(e)}")
        return []

def fetch_full_content(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # This is a basic extraction and might need to be adjusted based on the specific structure of each news site
        article = soup.find('article') or soup.find('div', class_='article-content')
        if article:
            return article.get_text()
        else:
            return "Failed to extract full content"
    except Exception as e:
        print(f"Error fetching full content from {url}: {str(e)}")
        return "Failed to fetch full content"

if __name__ == "__main__":
    url = "https://www.newsbtc.com/feed"
    print(fetch_rss_news(url))