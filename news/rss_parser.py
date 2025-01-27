import feedparser

def fetch_rss_news(feed_url):
    feed = feedparser.parse(feed_url)
    latest_news = []
    for entry in feed.entries[:5]:  # Fetch top 5 news articles
        latest_news.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.published,
            "summary": entry.summary
        })
    return latest_news

if __name__ == "__main__":
    url = "https://www.newsbtc.com/feed"
    print(fetch_rss_news(url))