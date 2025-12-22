"""Integration tests for daily report news aggregation pipeline."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from logging import Logger
from typing import Any, cast

import pytest

from infra.sql_connection import SQLiteConnectionWrapper
from news.article_cache import CachedArticle
from reports import daily_report as dr


def _build_article(
    *,
    title: str,
    content: str,
    summary: str = "",
    relevance: float = 0.8,
) -> CachedArticle:
    """Helper to construct cached article instances for tests."""
    timestamp = datetime.now(tz=UTC).isoformat()
    return CachedArticle(
        source="test-source",
        title=title,
        link=f"https://example.com/{title.lower().replace(' ', '-')}",
        published=timestamp,
        fetched=timestamp,
        content=content,
        symbols=["BTC"],
        summary=summary,
        raw_content=content,
        relevance_score=relevance,
        is_relevant=True,
        processed_at=timestamp,
        analysis_notes="notes",
    )


def test_collect_relevant_news_limits_and_truncates(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ensure news payload builder enforces limits and logs truncation."""
    articles = [
        _build_article(title="One", content="Short body", summary="Sum 1"),
        _build_article(title="Two", content="Word " * 100, summary=""),
        _build_article(title="Three", content="Another body", summary="Sum 3"),
    ]

    def fake_get_relevant_cached_articles(*, hours: int) -> list[CachedArticle]:
        _ = hours
        return articles

    monkeypatch.setattr(dr, "get_relevant_cached_articles", fake_get_relevant_cached_articles)
    monkeypatch.setenv("NEWS_ARTICLE_LIMIT", "2")
    monkeypatch.setenv("NEWS_ARTICLE_MAX_CHARS", "60")

    with caplog.at_level("INFO"):
        payload_json, stats, included_links = dr._collect_relevant_news(
            hours=12,
            logger=logging.getLogger(),
        )

    payload = json.loads(payload_json)

    assert stats["articles_available"] == 3
    assert stats["articles_included"] == 2
    assert stats["articles_truncated"] == 1
    assert stats["max_articles"] == 2
    assert stats["max_content_chars"] == 60
    assert len(payload) == 2
    assert payload[0]["summary"] == "Sum 1"
    assert payload[1]["summary"].startswith("Word")  # fallback summary
    assert payload[1]["content"].endswith("...")
    assert included_links == {articles[0].link, articles[1].link}
    assert any("Truncated article" in message for message in caplog.messages)


def test_process_ai_analysis_uses_filtered_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate AI analysis workflow consumes filtered news payload."""
    collected: dict[str, Any] = {"news_hours": None}

    async def fake_upload_to_onedrive(*args: Any, **kwargs: Any) -> bool:
        collected.setdefault("upload_calls", []).append((args, kwargs))
        return True

    async def fake_convert_markdown_to_epub_async(*_args: Any, **_kwargs: Any) -> bytes:
        return b"epub-bytes"

    monkeypatch.setenv("DAILY_REPORT_EMAIL_RECIPIENTS", "test@example.com")

    def fake_collect(
        *,
        hours: int,
        logger: Logger,
    ) -> tuple[str, dict[str, int], set[str]]:
        collected["news_hours"] = hours
        return (
            '[{"source":"test"}]',
            {
                "articles_available": 1,
                "articles_truncated": 0,
                "estimated_tokens": 120,
                "articles_included": 1,
                "avg_summary_chars": 40,
                "avg_content_chars": 120,
                "max_articles": 20,
                "max_content_chars": 2600,
            },
            {"https://example.com/article"},
        )

    monkeypatch.setattr(dr, "_collect_relevant_news", fake_collect)

    def fake_build_sections(
        *,
        included_links: set[str],
        stats: dict[str, float | int] | None,
        hours: int,
    ) -> tuple[str | None, str | None]:
        collected["audit_included"] = included_links
        collected["audit_hours"] = hours
        collected["audit_stats_keys"] = sorted(stats.keys()) if stats else []
        return ("plain audit", "markdown audit")

    monkeypatch.setattr(dr, "_build_news_audit_sections", fake_build_sections)
    monkeypatch.setattr(
        dr,
        "get_aggregated_data",
        lambda _conn: [
            {"SymbolName": "BTC", "RSI": 55, "RSIClosePrice": "65000"},
        ],
    )

    analysis_text = "AI analysis content"
    highlight_text = "Bullet highlights"

    def fake_analysis(*_args: Any, **_kwargs: Any) -> tuple[str, str]:
        return analysis_text, "gemini-2.5-pro"

    def fake_highlight(*_args: Any, **_kwargs: Any) -> str:
        return highlight_text

    async def fake_send_epub_report_via_email(*args: Any, **kwargs: Any) -> None:
        collected.setdefault("email_calls", []).append((args, kwargs))

    async def fake_save_highlighted_articles_to_onedrive(*args: Any, **kwargs: Any) -> None:
        collected.setdefault("highlights_calls", []).append((args, kwargs))

    def fake_append_article_list(*args: Any, **kwargs: Any) -> str:
        # Return the first arg (analysis) unchanged for simplicity
        return args[0] if args else ""

    monkeypatch.setattr(dr, "get_detailed_crypto_analysis_with_news", fake_analysis)
    monkeypatch.setattr(dr, "highlight_articles", fake_highlight)
    monkeypatch.setattr(dr, "upload_to_onedrive", fake_upload_to_onedrive)
    monkeypatch.setattr(dr, "convert_markdown_to_epub_async", fake_convert_markdown_to_epub_async)
    # Patch functions - must patch where they're imported in daily_report, not where they're defined
    monkeypatch.setattr(dr, "send_epub_report_via_email", fake_send_epub_report_via_email)
    monkeypatch.setattr(
        dr,
        "save_highlighted_articles_to_onedrive",
        fake_save_highlighted_articles_to_onedrive,
    )
    monkeypatch.setattr(dr, "append_article_list_to_analysis", fake_append_article_list)

    class DummySymbol:
        symbol_id = 1
        symbol_name = "BTC"
        full_name = "Bitcoin"

    # Use typing.cast to satisfy static typing for test doubles
    analysis_result, news_meta = asyncio.run(
        dr._process_ai_analysis(
            ai_api_key="key",
            ai_api_type="gemini",
            symbols=cast(list[dr.Symbol], [DummySymbol()]),
            current_prices_section="Prices\n",
            conn=cast(SQLiteConnectionWrapper, object()),
            today_date="2025-11-04",
            logger=dr.app_logger,
        ),
    )

    # Analysis result now includes model info prefix: "Generated using {model} model\n\n{analysis}"
    assert "Generated using gemini-2.5-pro model" in analysis_result
    assert analysis_text in analysis_result
    assert "## News Audit Summary" in analysis_result
    assert analysis_result.rstrip().endswith("markdown audit")
    assert news_meta["included_links"] == {"https://example.com/article"}
    assert news_meta["audit_plain"] == "plain audit"
    assert news_meta["audit_markdown"] == "markdown audit"
    assert collected["news_hours"] == 12  # Changed from 24 to 12 for twice-daily runs
    assert collected["audit_hours"] == 12  # Changed from 24 to 12 for twice-daily runs
    assert collected["audit_included"] == {"https://example.com/article"}
    assert "articles_available" in collected["audit_stats_keys"]
    assert collected.get("upload_calls")
    assert collected.get("email_calls")
