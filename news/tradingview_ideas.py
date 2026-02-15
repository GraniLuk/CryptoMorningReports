"""Fetch recent TradingView ideas for a symbol."""

from __future__ import annotations

import os
import re
from typing import Iterable

import requests
from bs4 import BeautifulSoup

from infra.telegram_logging_handler import app_logger


DEFAULT_SYMBOL_SUFFIX = "USDT"
DEFAULT_IDEAS_LIMIT = 3
DEFAULT_IDEAS_URL_TEMPLATE = "https://www.tradingview.com/symbols/{symbol}/ideas/?sort=recent"


def fetch_tradingview_ideas(symbol: str) -> list[dict[str, str]]:
    """Fetch recent TradingView ideas for the given symbol.

    Args:
        symbol: Cryptocurrency symbol (e.g., "DOT", "BTC")

    Returns:
        List of dicts with keys: title, url
    """
    enabled = os.getenv("TRADINGVIEW_IDEAS_ENABLED", "true").lower()
    if enabled not in ("true", "1", "yes", "on"):
        return []

    symbol_suffix = os.getenv("TRADINGVIEW_IDEAS_SYMBOL_SUFFIX", DEFAULT_SYMBOL_SUFFIX)
    ideas_limit_raw = os.getenv("TRADINGVIEW_IDEAS_LIMIT", str(DEFAULT_IDEAS_LIMIT))
    try:
        ideas_limit = max(1, int(ideas_limit_raw))
    except ValueError:
        ideas_limit = DEFAULT_IDEAS_LIMIT

    symbol_pair = f"{symbol.strip().upper()}{symbol_suffix}"
    if not symbol_pair.strip():
        return []

    url_template = os.getenv("TRADINGVIEW_IDEAS_URL_TEMPLATE", DEFAULT_IDEAS_URL_TEMPLATE)
    ideas_url = url_template.format(symbol=symbol_pair)

    try:
        response = requests.get(ideas_url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        app_logger.warning("TradingView ideas request failed: %s", exc)
        return []

    ideas = _extract_ideas_from_html(
        response.text,
        base_url="https://www.tradingview.com",
        symbol_pair=symbol_pair,
    )
    if not ideas:
        return []

    return ideas[:ideas_limit]


def _extract_ideas_from_html(
    html: str,
    *,
    base_url: str,
    symbol_pair: str,
) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    idea_links = soup.find_all("a", href=True)

    symbol_slug = symbol_pair.strip().upper()

    ideas: list[dict[str, str]] = []
    seen: set[str] = set()

    for link in idea_links:
        href = link.get("href", "")
        if not isinstance(href, str):
            continue
        if not href.startswith(f"/chart/{symbol_slug}/"):
            continue

        full_url = base_url + href
        if full_url in seen:
            continue

        title = _extract_link_title(link)
        if not title:
            # Fallback to a cleaned slug if no title exists.
            title = _derive_title_from_href(href)

        ideas.append({"title": title, "url": full_url})
        seen.add(full_url)

    return ideas


def _extract_link_title(link) -> str:
    aria_label = link.get("aria-label", "")
    if isinstance(aria_label, str) and aria_label.strip():
        return aria_label.strip()

    text = link.get_text(strip=True)
    return text.strip() if text else ""


def _derive_title_from_href(href: str) -> str:
    match = re.search(r"/chart/[^/]+/[^/]+-([^/]+)/?", href)
    if match:
        return match.group(1).replace("-", " ").strip()
    return "TradingView Idea"


__all__ = ["fetch_tradingview_ideas"]
