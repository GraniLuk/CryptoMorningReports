"""Fetch recent TradingView ideas for a symbol."""

from __future__ import annotations

import contextlib
import json
import os
import re
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

import requests
from bs4 import BeautifulSoup, Tag

from infra.telegram_logging_handler import app_logger


DEFAULT_SYMBOL_SUFFIX = "USDT"
DEFAULT_IDEAS_LIMIT = 3
DEFAULT_IDEAS_URL_TEMPLATE = "https://www.tradingview.com/symbols/{symbol}/ideas/?sort=recent"
MAX_IDEA_CONTENT_CHARS = 6000
MAX_IDEA_LOOKBACK_HOURS = 24
MIN_IDEA_BODY_LENGTH = 200


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
    content_limit_raw = os.getenv(
        "TRADINGVIEW_IDEA_CONTENT_CHARS",
        str(MAX_IDEA_CONTENT_CHARS),
    )
    try:
        ideas_limit = max(1, int(ideas_limit_raw))
    except ValueError:
        ideas_limit = DEFAULT_IDEAS_LIMIT
    try:
        content_limit = max(0, int(content_limit_raw))
    except ValueError:
        content_limit = MAX_IDEA_CONTENT_CHARS

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

    ideas = ideas[:ideas_limit]
    _enrich_ideas_with_content(ideas, content_limit=content_limit)
    return _filter_recent_ideas(ideas, hours=MAX_IDEA_LOOKBACK_HOURS)


def _extract_ideas_from_html(
    html: str,
    *,
    base_url: str,
    symbol_pair: str,
) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    symbol_slug = symbol_pair.strip().upper()

    ideas: list[dict[str, str]] = []
    seen: set[str] = set()

    _extend_from_json(soup, base_url, symbol_slug, ideas, seen)
    _extend_from_slug_pattern(html, base_url, symbol_slug, ideas, seen)

    if ideas:
        return ideas

    idea_links = soup.find_all("a", href=True)

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


def _extend_from_json(
    soup: BeautifulSoup,
    base_url: str,
    symbol_slug: str,
    ideas: list[dict[str, str]],
    seen: set[str],
) -> None:
    for script in soup.find_all("script"):
        script_text = script.string
        if not script_text:
            continue

        payloads = _load_json_candidates(script_text)
        for payload in payloads:
            for title, url in _extract_chart_links_from_json(payload, symbol_slug):
                full_url = url if url.startswith("http") else base_url + url
                if full_url in seen:
                    continue
                ideas.append({"title": title, "url": full_url})
                seen.add(full_url)


def _load_json_candidates(script_text: str) -> list[object]:
    script_text = script_text.strip()
    if not script_text:
        return []

    candidates = []
    with contextlib.suppress(json.JSONDecodeError):
        candidates.append(json.loads(script_text))

    # Heuristic: look for embedded JSON assignment blocks.
    match = re.search(r"(\{.*\}|\[.*\])", script_text, flags=re.DOTALL)
    if match:
        with contextlib.suppress(json.JSONDecodeError):
            candidates.append(json.loads(match.group(1)))

    return candidates


def _extract_chart_links_from_json(
    payload: object,
    symbol_slug: str,
) -> list[tuple[str, str]]:
    matches: list[tuple[str, str]] = []
    for node in _walk_json(payload):
        if not isinstance(node, dict):
            continue
        url = node.get("url") or node.get("link")
        if not isinstance(url, str):
            continue
        if f"/chart/{symbol_slug}/" not in url:
            continue
        title = _coerce_title(node)
        matches.append((title, url))
    return matches


def _coerce_title(node: dict) -> str:
    for key in ("title", "headline", "name"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "TradingView Idea"


def _walk_json(payload: object) -> list[object]:
    stack = [payload]
    nodes: list[object] = []
    while stack:
        node = stack.pop()
        nodes.append(node)
        if isinstance(node, dict):
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return nodes


def _extend_from_slug_pattern(
    html: str,
    base_url: str,
    symbol_slug: str,
    ideas: list[dict[str, str]],
    seen: set[str],
) -> None:
    pattern = re.compile(
        rf"/chart/{re.escape(symbol_slug)}/[A-Za-z0-9]+-[A-Za-z0-9\-]+/",
    )

    for match in pattern.finditer(html):
        href = match.group(0)
        full_url = base_url + href
        if full_url in seen:
            continue
        ideas.append({"title": _derive_title_from_href(href), "url": full_url})
        seen.add(full_url)


def _extract_link_title(link: Tag) -> str:
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


def _enrich_ideas_with_content(
    ideas: list[dict[str, str]],
    *,
    content_limit: int,
) -> None:
    for idea in ideas:
        url = idea.get("url", "")
        if not url:
            idea["content"] = ""
            continue
        content, published_at = _fetch_idea_content(url, content_limit=content_limit)
        idea["content"] = content
        if published_at is not None:
            idea["published_at"] = published_at.isoformat()


def _fetch_idea_content(url: str, *, content_limit: int) -> tuple[str, datetime | None]:
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        app_logger.warning("TradingView idea request failed: %s", exc)
        return "", None

    soup = BeautifulSoup(response.text, "html.parser")

    published_at = _extract_published_time(soup)

    dom_text = _extract_idea_body_from_dom(soup)
    if dom_text:
        return _truncate_text(dom_text, content_limit), published_at

    article = soup.find("article")
    if article:
        text = " ".join(paragraph.get_text(" ", strip=True) for paragraph in article.find_all("p"))
        if text:
            return _truncate_text(text, content_limit), published_at

    meta_description = _get_meta_description(soup)
    if meta_description:
        return _truncate_text(meta_description, content_limit), published_at

    return "", published_at


def _get_meta_description(soup: BeautifulSoup) -> str:
    meta = soup.find("meta", attrs={"property": "og:description"})
    if meta and meta.get("content"):
        return str(meta.get("content")).strip()

    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return str(meta.get("content")).strip()

    return ""


def _extract_idea_body_from_dom(soup: BeautifulSoup) -> str:
    keywords = [
        "Entry Price",
        "Target 1",
        "Stop Loss",
        "Trade active",
        "Trade closed",
    ]

    keyword_node = soup.find(
        string=lambda text: isinstance(text, str) and any(k in text for k in keywords),
    )
    if keyword_node:
        for parent in keyword_node.parents:
            if parent.name in ("div", "section", "article"):
                text = parent.get_text(" ", strip=True)
                if len(text) >= MIN_IDEA_BODY_LENGTH:
                    return text

    candidates = []
    for tag in soup.find_all(["div", "section", "article"]):
        text = tag.get_text(" ", strip=True)
        if len(text) >= MIN_IDEA_BODY_LENGTH and "#" in text:
            candidates.append(text)

    if not candidates:
        return ""

    return max(candidates, key=len)


def _extract_published_time(soup: BeautifulSoup) -> datetime | None:
    time_tag = soup.find("time", attrs={"datetime": True})
    if time_tag and time_tag.get("datetime"):
        parsed = _parse_datetime(time_tag.get("datetime"))
        if parsed:
            return parsed

    meta = soup.find("meta", attrs={"property": "article:published_time"})
    if meta and meta.get("content"):
        parsed = _parse_datetime(meta.get("content"))
        if parsed:
            return parsed

    meta = soup.find("meta", attrs={"name": "article:published_time"})
    if meta and meta.get("content"):
        parsed = _parse_datetime(meta.get("content"))
        if parsed:
            return parsed

    return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _truncate_text(text: str, limit: int) -> str:
    cleaned = text.strip()
    if limit <= 0 or len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."


def _filter_recent_ideas(
    ideas: list[dict[str, str]],
    *,
    hours: int,
) -> list[dict[str, str]]:
    if not ideas:
        return []

    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    filtered: list[dict[str, str]] = []
    for idea in ideas:
        published_at = idea.get("published_at")
        parsed = _parse_datetime(published_at) if isinstance(published_at, str) else None
        if parsed and parsed >= cutoff:
            filtered.append(idea)
    return filtered


__all__ = ["fetch_tradingview_ideas"]
