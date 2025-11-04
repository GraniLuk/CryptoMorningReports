"""Configuration management and environment variable handling.

Environment Variables:
    ARTICLE_CACHE_ROOT: Root directory for storing cached RSS articles.
                       Supports user home expansion with ~. Defaults to news/cache.
    ENABLE_ARTICLE_CACHE: Enable/disable article caching (default: true).
    KUCOIN_API_KEY: KuCoin API key for market data access.
    KUCOIN_API_SECRET: KuCoin API secret for authentication.
    KUCOIN_API_PASSPHRASE: KuCoin API passphrase for authentication.
    TELEGRAM_PARSE_MODE: Telegram message parse mode (HTML or MarkdownV2).
    TWITTER_AUTH_TOKEN: Twitter authentication token.
    TWITTER_CT0: Twitter CT0 token.
    TWITTER_EMAIL: Twitter account email.
    TWITTER_LOGIN: Twitter login username.
    TWITTER_PASSWORD: Twitter account password.
"""

import os
from dataclasses import dataclass
from pathlib import Path

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


def get_telegram_parse_mode() -> str:
    """Get the Telegram parse mode from environment variables.

    Returns the configured parse mode for Telegram messages. Defaults to "HTML"
    if not specified or if an invalid value is provided.

    Returns:
        str: The parse mode to use - either "HTML" or "MarkdownV2"

    Environment Variables:
        TELEGRAM_PARSE_MODE: The parse mode to use (HTML or MarkdownV2)

    Examples:
        >>> os.environ["TELEGRAM_PARSE_MODE"] = "HTML"
        >>> get_telegram_parse_mode()
        'HTML'
        >>> os.environ["TELEGRAM_PARSE_MODE"] = "MarkdownV2"
        >>> get_telegram_parse_mode()
        'MarkdownV2'
    """
    parse_mode = os.getenv("TELEGRAM_PARSE_MODE", "HTML").strip()

    # Validate and normalize the parse mode
    valid_modes = {"HTML", "MarkdownV2"}
    if parse_mode not in valid_modes:
        # Default to HTML if invalid value provided
        return "HTML"

    return parse_mode


def get_article_cache_root() -> Path:
    """Get the root directory for article caching from environment variables.

    Returns the configured root directory for storing cached RSS articles.
    Defaults to 'news/cache' relative to the project root if not specified.

    The directory path supports user home directory expansion (e.g., ~/cache/articles)
    and will be resolved to an absolute path to prevent relative path traversal.

    Returns:
        Path: Absolute path to the article cache root directory

    Environment Variables:
        ARTICLE_CACHE_ROOT: Absolute or relative path to the cache root directory.
                           Supports user home expansion with ~.

    Examples:
        >>> # Default behavior (no env var set)
        >>> get_article_cache_root()
        PosixPath('/path/to/project/news/cache')
        >>> # With environment variable
        >>> os.environ["ARTICLE_CACHE_ROOT"] = "/tmp/article_cache"
        >>> get_article_cache_root()
        PosixPath('/tmp/article_cache')
        >>> # With user home expansion
        >>> os.environ["ARTICLE_CACHE_ROOT"] = "~/my_cache"
        >>> get_article_cache_root()
        PosixPath('/home/user/my_cache')
    """
    cache_root_env = os.getenv("ARTICLE_CACHE_ROOT", "").strip()

    if cache_root_env:
        # Expand user home directory and resolve to absolute path
        cache_root = Path(cache_root_env).expanduser().resolve()
    else:
        # Default to news/cache relative to the project root
        # This assumes configuration.py is in infra/, so parent is project root
        cache_root = Path(__file__).resolve().parents[1] / "news" / "cache"

    return cache_root


@dataclass(frozen=True)
class OllamaSettings:
    """Typed representation of Ollama configuration values."""

    host: str
    model: str
    timeout: float


def get_ollama_settings() -> OllamaSettings:
    """Get Ollama client configuration with sensible defaults."""
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").strip()
    model = os.getenv("OLLAMA_MODEL", "gpt-oss:20b").strip()
    timeout_value = os.getenv("OLLAMA_TIMEOUT", "30").strip()

    try:
        timeout = float(timeout_value)
    except ValueError:
        timeout = 30.0

    return OllamaSettings(
        host=host or "http://localhost:11434",
        model=model or "gpt-oss:20b",
        timeout=timeout,
    )
