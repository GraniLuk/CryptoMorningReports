import json
import time  # Added for struct_time type checking
from datetime import UTC, datetime, timedelta
from time import mktime

import feedparser
import requests
from bs4 import BeautifulSoup

from infra.telegram_logging_handler import app_logger


def get_news():
    feeds = {
        "decrypt": {"url": "https://decrypt.co/feed", "class": "post-content"},
        "coindesk": {
            "url": "https://www.coindesk.com/arc/outboundfeeds/rss",
            "class": "document-body",
        },
        "newsBTC": {
            "url": "https://www.newsbtc.com/feed",
            "class": "content-inner jeg_link_underline",
        },
        "coinJournal": {
            "url": "https://coinjournal.net/feed",
            "class": "post-article-content lg:col-span-8",
        },
        "coinpedia": {
            "url": "https://coinpedia.org/feed",
            "class": "entry-content entry clearfix",
        },
        "cryptopotato": {
            "url": "https://cryptopotato.com/feed",
            "class": "entry-content col-sm-11",
        },
        "ambcrypto": {
            "url": "https://ambcrypto.com/feed/",
            "class": "single-post-main-middle",
        },
    }

    all_news = []
    for source, feed_info in feeds.items():
        all_news.extend(fetch_rss_news(feed_info["url"], source, feed_info["class"]))

    return json.dumps(all_news, indent=2)


def fetch_rss_news(feed_url, source, class_name):
    try:
        feed = feedparser.parse(feed_url)
        latest_news = []
        current_time = datetime.now(UTC)
        for entry in feed.entries:
            # Make published_time timezone-aware by adding UTC timezone
            if hasattr(entry, "published_parsed") and isinstance(
                entry.published_parsed, time.struct_time
            ):
                published_time = datetime.fromtimestamp(mktime(entry.published_parsed), tz=UTC)
            else:
                # Fallback to current time if published_parsed is not valid
                published_time = current_time

            if current_time - published_time <= timedelta(days=1):
                full_content = fetch_full_content(entry.link, class_name)
                latest_news.append(
                    {
                        "source": source,
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.published,
                        "content": full_content,
                    }
                )

                if len(latest_news) >= 10:
                    break

        return latest_news
    except Exception as e:
        app_logger.error(f"Error fetching news from {feed_url}: {e!s}")
        return []


def fetch_full_content(url, class_name):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")

        article = soup.find("div", class_=class_name) or soup.find("article")
        if article:
            article_text = article.get_text()
            return "\n".join(line.strip() for line in article_text.splitlines() if line.strip())
        return "Failed to extract full content"
    except Exception as e:
        app_logger.error(f"Error fetching full content from {url}: {e!s}")
        return "Failed to fetch full content"


if __name__ == "__main__":
    print(get_news())
