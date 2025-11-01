"""Configuration management and environment variable handling."""

import os

from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


def get_kucoin_credentials():
    """Get KuCoin API credentials from environment variables."""
    return {
        "api_key": os.getenv("KUCOIN_API_KEY"),
        "api_secret": os.getenv("KUCOIN_API_SECRET"),
        "api_passphrase": os.getenv("KUCOIN_API_PASSPHRASE"),
    }


def get_twitter_credentials():
    """Get Twitter credentials from environment variables."""
    return {
        "login": os.getenv("TWITTER_LOGIN"),
        "email": os.getenv("TWITTER_EMAIL"),
        "password": os.getenv("TWITTER_PASSWORD"),
        "auth_token": os.getenv("TWITTER_AUTH_TOKEN"),
        "ct0": os.getenv("TWITTER_CT0"),
    }


def is_article_cache_enabled() -> bool:
    """Check if article caching is enabled.

    Returns True by default for local development, can be disabled via
    ENABLE_ARTICLE_CACHE environment variable.
    """
    enabled = os.getenv("ENABLE_ARTICLE_CACHE", "true").lower()
    return enabled in ("true", "1", "yes", "on")
