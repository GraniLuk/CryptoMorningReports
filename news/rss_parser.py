import feedparser
from datetime import datetime, timedelta
from time import mktime

def fetch_rss_news(feed_url):
    feed = feedparser.parse(feed_url)
    latest_news = []
    current_time = datetime.now()
    
    for entry in feed.entries:
        # Convert published time to datetime
        published_time = datetime.fromtimestamp(mktime(entry.published_parsed))
        
        # Check if article is within last 24 hours
        if current_time - published_time <= timedelta(days=1):
            latest_news.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.published,
                "summary": entry.summary
            })
            
            # Still limit to max 10 articles
            if len(latest_news) >= 15:
                break
                
    return latest_news

if __name__ == "__main__":
    url = "https://www.newsbtc.com/feed"
    print(fetch_rss_news(url))