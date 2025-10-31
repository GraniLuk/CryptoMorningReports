"""Launchpool and Gempool article monitoring and reporting."""

from http import HTTPStatus

import requests


# Endpoint to fetch articles
URL = "https://www.kucoin.com/_api/seo-content-eco-service/web/article/searchRec?keyword=gempool+burningdrop&lang=en_US"


def check_gempool_articles():
    """Check for new articles from the Gempool API."""
    seen_articles = set()

    # Fetch articles from the API
    response = requests.get(URL)
    new_articles = []

    if response.status_code == HTTPStatus.OK:
        data = response.json()
        if data.get("success") and "items" in data:
            new_articles = []

            for item in data["items"]:
                article_id = item["id"]
                article_code = item["articleCode"]
                title = (
                    item["title"].replace("<em>", "").replace("</em>", "")
                )  # Clean up formatting tags
                article_url = f"https://www.kucoin.com/news/flash/{article_code}"

                # Check if the article is new
                if article_id not in seen_articles:
                    seen_articles.add(article_id)
                    new_articles.append(f"Title: {title}\nURL: {article_url}\n")

            # Notify if there are new articles
            if new_articles:
                print("New Gempool Articles Found:\n")
                for article in new_articles:
                    print(article)
            else:
                print("No new articles found.")
        else:
            print("Failed to fetch articles: Unexpected response format.")
    else:
        print(f"Failed to fetch articles: HTTP {response.status_code}")

    return new_articles
