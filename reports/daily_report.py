"""Daily cryptocurrency market report generation and distribution."""

import json
import math
import os
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from etf.etf_report import fetch_etf_summary_report, update_etf_data
from etf.etf_repository import ETFRepository
from infra.configuration import get_telegram_parse_mode
from infra.telegram_logging_handler import app_logger
from integrations.email_sender import send_email_with_epub_attachment
from integrations.onedrive_uploader import (
    upload_to_onedrive,  # Import for OneDrive uploads
)
from integrations.pandoc_converter import convert_markdown_to_epub_async
from launchpool.launchpool_report import check_gempool_articles
from news.article_cache import (
    CachedArticle,
    cleanup_old_articles,
    get_cache_statistics,
    get_recent_articles,
)
from news.news_agent import (
    get_detailed_crypto_analysis_with_news,
    get_relevant_cached_articles,
    highlight_articles,
)
from news.rss_parser import get_news
from shared_code.price_checker import (
    fetch_current_price,
    fetch_daily_candles,
    fetch_fifteen_min_candles,
    fetch_hourly_candles,
)
from shared_code.telegram import send_telegram_document, send_telegram_message
from source_repository import Symbol, fetch_symbols
from stepn.stepn_report import fetch_stepn_report
from technical_analysis.derivatives_report import fetch_derivatives_report
from technical_analysis.macd_report import calculate_macd
from technical_analysis.marketcap_report import fetch_marketcap_report
from technical_analysis.moving_averages_report import calculate_indicators
from technical_analysis.order_book_report import (
    build_cvd_ai_context,
    build_order_book_ai_context,
    fetch_cvd_report,
    fetch_order_book_report,
)
from technical_analysis.price_change_report import fetch_price_change_report
from technical_analysis.price_range_report import fetch_range_price
from technical_analysis.reports.rsi_daily import create_rsi_table
from technical_analysis.repositories.aggregated_repository import get_aggregated_data
from technical_analysis.sopr import fetch_sopr_metrics
from technical_analysis.volume_report import fetch_volume_report


if TYPE_CHECKING:
    from logging import Logger

    import pyodbc

    from infra.sql_connection import SQLiteConnectionWrapper
    from source_repository import Symbol


def _configure_ai_api():
    """Configure AI API settings and return api_type and api_key."""
    ai_api_type = os.environ.get("AI_API_TYPE", "perplexity").lower()
    ai_api_key = ""

    if ai_api_type == "perplexity":
        ai_api_key = os.environ.get("PERPLEXITY_API_KEY", "")
        app_logger.info("Using Perplexity API for analysis")
    elif ai_api_type == "gemini":
        ai_api_key = os.environ.get("GEMINI_API_KEY", "")
        app_logger.info("Using Gemini API for analysis")
    else:
        app_logger.warning(f"Unknown AI API type: {ai_api_type}, defaulting to Perplexity")
        ai_api_type = "perplexity"
        ai_api_key = os.environ.get("PERPLEXITY_API_KEY", "")

    if not ai_api_key:
        app_logger.error(f"No API key found for {ai_api_type}")

    return ai_api_type, ai_api_key


def _build_etf_flows_section(conn: "pyodbc.Connection | SQLiteConnectionWrapper") -> str:
    """Build ETF flows section for AI analysis context.

    Dynamically fetches ETF data for all available coins (not just BTC/ETH).

    Args:
        conn: Database connection

    Returns:
        Formatted ETF flows section for AI analysis
    """
    try:
        repo = ETFRepository(conn)

        # Get all available coins with ETF data
        available_coins = repo.get_available_etf_coins()
        if not available_coins:
            return "ETF Flows: No ETF data available\n\n"

        lines = ["ETF Institutional Flows (Daily & 7-Day Aggregates):"]

        # Process each coin dynamically
        for coin in available_coins:
            flows = repo.get_latest_etf_flows(coin)
            weekly = repo.get_weekly_etf_flows(coin, days=7)

            if flows:
                total_daily = sum(
                    float(etf.get("flows", 0) or 0)
                    for etf in flows
                    if etf.get("flows") is not None
                )
                weekly_total = weekly.get("total_flows", 0) if weekly else 0
                lines.append(f"{coin} ETF Daily Flows: ${total_daily:,.0f}")
                lines.append(f"{coin} ETF 7-Day Total: ${weekly_total:,.0f}")
            else:
                lines.append(f"{coin} ETF Daily Flows: No data available")

        # Add interpretation guidance
        lines.append("")
        lines.append(
            "Interpretation: Positive flows indicate institutional buying (bullish), "
            "negative flows indicate selling (bearish).",
        )

        return "\n".join(lines) + "\n\n"

    except Exception as e:  # noqa: BLE001
        app_logger.error(f"Error building ETF flows section: {e!s}")
        return "ETF Flows: Data unavailable\n\n"


def _build_analysis_context(
    current_prices_section: str,
    conn: "pyodbc.Connection | SQLiteConnectionWrapper",
) -> str:
    """Build complete analysis context with prices, indicators, and ETF flows."""
    aggregated_data = get_aggregated_data(conn)

    def format_aggregated(agg_list: list) -> str:
        if not agg_list:
            return "No aggregated indicator data available.\n"
        header = (
            "Symbol | RSI | Close | MA50 | MA200 | EMA50 | EMA200 | Low | High | "
            "Range% | OI | OI Value | Fund Rate\n"
            "-------|-----|-------|------|-------|------|--------|-----|------|"
            "--------|----|-----------|-----------\n"
        )
        lines = []
        for row in agg_list:
            try:
                oi_str = f"{row.get('OpenInterest', 0):,.0f}" if row.get("OpenInterest") else "N/A"
                oi_val_str = (
                    f"${row.get('OpenInterestValue', 0):,.0f}"
                    if row.get("OpenInterestValue")
                    else "N/A"
                )
                fr_str = f"{row.get('FundingRate', 0):.4f}%" if row.get("FundingRate") else "N/A"

                lines.append(
                    f"{row.get('SymbolName', ''):>6} | "
                    f"{row.get('RSI', '')!s:>4} | "
                    f"{row.get('RSIClosePrice', ''):>6} | "
                    f"{row.get('MA50', ''):>5} | "
                    f"{row.get('MA200', ''):>6} | "
                    f"{row.get('EMA50', ''):>6} | "
                    f"{row.get('EMA200', ''):>7} | "
                    f"{row.get('LowPrice', ''):>5} | "
                    f"{row.get('HighPrice', ''):>6} | "
                    f"{row.get('RangePercent', ''):>6} | "
                    f"{oi_str:>10} | "
                    f"{oi_val_str:>11} | "
                    f"{fr_str:>11}",
                )
            except (KeyError, ValueError, TypeError) as e:
                lines.append(f"Row format error: {e}")
        note = (
            "Aggregated Indicators "
            "(showing most recent values from last 7 days of data for trend analysis)"
        )
        newline = "\n"
        return f"{note}:{newline}<pre>{header}{newline.join(lines)}</pre>{newline}{newline}"

    aggregated_formatted = format_aggregated(aggregated_data)
    aggregated_with_prices = current_prices_section + aggregated_formatted
    etf_flows_section = _build_etf_flows_section(conn)
    order_book_section = _build_order_book_section(conn)
    return aggregated_with_prices + etf_flows_section + order_book_section


def _build_order_book_section(conn: "pyodbc.Connection | SQLiteConnectionWrapper") -> str:
    """Build order book liquidity and CVD section for AI analysis context.

    Args:
        conn: Database connection

    Returns:
        Formatted order book and CVD section for AI analysis
    """
    try:
        from source_repository import fetch_symbols  # noqa: PLC0415

        symbols = fetch_symbols(conn)
        order_book_context = build_order_book_ai_context(symbols, conn)
        cvd_context = build_cvd_ai_context(symbols, conn)
        return order_book_context + "\n\n" + cvd_context + "\n\n"
    except Exception as e:  # noqa: BLE001
        app_logger.error(f"Error building order book section: {e!s}")
        return "Order Book Data: Unavailable\n\n"


async def _process_ai_analysis(
    ai_api_key,
    ai_api_type,
    symbols,
    current_prices_section,
    conn,
    today_date,
    logger,
):
    """Process AI analysis with news and handle uploads/email."""
    analysis_reported_with_news = "Failed: Analysis with news not generated"
    news_metadata: dict[str, object] = {
        "included_links": set(),
        "stats": {},
        "hours": 24,
    }

    if not ai_api_key:
        logger.error("No API key found for %s", ai_api_type)
        return analysis_reported_with_news, news_metadata

    # Build filtered news payload from cached articles (already processed by Ollama earlier)
    news_payload, news_stats, included_links = _collect_relevant_news(hours=24, logger=logger)
    logger.info(
        "News filtering stats - available: %d, truncated: %d, est_tokens: ~%d",
        news_stats["articles_available"],
        news_stats["articles_truncated"],
        news_stats["estimated_tokens"],
    )
    if news_stats["articles_available"] == 0:
        logger.warning("No relevant news articles available for AI analysis.")

    audit_plain, audit_markdown = _build_news_audit_sections(
        included_links=included_links,
        stats=news_stats,
        hours=24,
    )

    news_metadata = {
        "included_links": included_links,
        "stats": news_stats,
        "hours": 24,
        "audit_plain": audit_plain,
        "audit_markdown": audit_markdown,
    }

    aggregated_with_prices = _build_analysis_context(current_prices_section, conn)

    # Use None to let configured primary model be used for detailed analysis
    # Fallback to secondary model will trigger automatically on rate limits
    analysis_reported_with_news = get_detailed_crypto_analysis_with_news(
        ai_api_key,
        aggregated_with_prices,
        news_payload,
        ai_api_type,
        conn,
        model=None,  # Use configured primary model (gemini-2.5-pro from .env)
    )
    # Use configured secondary model for highlighting - simple categorization
    # Get secondary model from environment for Gemini, None for other providers
    secondary_model = None
    if ai_api_type == "gemini":
        secondary_model = os.environ.get(
            "GEMINI_SECONDARY_MODEL",
            "gemini-2.5-flash-preview-09-2025",
        )

    highlight_articles_message = highlight_articles(
        ai_api_key,
        symbols,
        news_payload,
        ai_api_type,
        model=secondary_model,
    )

    # Add list of articles included in analysis
    if not analysis_reported_with_news.startswith("Failed"):
        try:
            articles = json.loads(news_payload)
            article_list = "\n\n## Articles Included in Analysis\n\n" + "\n".join(
                f"- {art['title']} ({art['source']})" for art in articles
            )
            analysis_reported_with_news += article_list
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to parse news payload for article list: %s", e)

    if not analysis_reported_with_news.startswith("Failed") and audit_markdown:
        analysis_reported_with_news += "\n\n## News Audit Summary\n\n" + audit_markdown

    # --- OneDrive Uploads ---
    if not analysis_reported_with_news.startswith("Failed"):
        onedrive_filename_analysis_with_news = f"CryptoAnalysisWithNews_{today_date}.md"
        await upload_to_onedrive(
            filename=onedrive_filename_analysis_with_news,
            content=analysis_reported_with_news,
            folder_path="detailed_analysis_with_news",
        )

        epub_filename = onedrive_filename_analysis_with_news.replace(".md", ".epub")
        try:
            epub_bytes = await convert_markdown_to_epub_async(
                analysis_reported_with_news,
                metadata={
                    "title": f"Crypto Analysis with News {today_date}",
                    "author": "Crypto Morning Reports Bot",
                    "date": today_date,
                },
            )
        except RuntimeError as convert_err:
            logger.warning("Failed to convert analysis markdown to EPUB: %s", convert_err)
        else:
            recipients_env = os.environ.get("DAILY_REPORT_EMAIL_RECIPIENTS", "")
            recipients = [addr.strip() for addr in recipients_env.split(",") if addr.strip()]

            if not recipients:
                logger.info(
                    "No recipients configured in DAILY_REPORT_EMAIL_RECIPIENTS; "
                    "skipping email dispatch.",
                )
            else:
                email_body = (
                    "Hi,\n\n"
                    "Please find attached the EPUB version of today's detailed "
                    "crypto analysis with news.\n\n"
                    "Regards,\n"
                    "Crypto Morning Reports Bot"
                )
                email_sent = await send_email_with_epub_attachment(
                    subject=f"Crypto Analysis with News {today_date}",
                    body=email_body,
                    attachment_bytes=epub_bytes,
                    attachment_filename=epub_filename,
                    recipients=recipients,
                )
                if not email_sent:
                    logger.warning("Failed to send EPUB analysis report via email.")

        # Save highlighted articles in "news" subfolder
        if not highlight_articles_message.startswith("Failed"):
            onedrive_filename_highlights = f"HighlightedNews_{today_date}.md"
            highlights_saved_to_onedrive = await upload_to_onedrive(
                filename=onedrive_filename_highlights,
                content=highlight_articles_message,
                folder_path="news",
            )
            if highlights_saved_to_onedrive:
                logger.info(
                    "Highlighted articles for %s saved to OneDrive news folder.",
                    today_date,
                )
            else:
                logger.warning(
                    "Failed to save highlighted articles for %s to OneDrive.",
                    today_date,
                )

    return analysis_reported_with_news, news_metadata


def _collect_relevant_news(
    *,
    hours: int,
    logger: "Logger",
) -> tuple[str, dict[str, float | int], set[str]]:
    """Collect relevant cached articles and prepare payload for AI consumption."""
    relevant_articles = get_relevant_cached_articles(hours=hours)
    total_available = len(relevant_articles)

    max_articles = max(int(os.environ.get("NEWS_ARTICLE_LIMIT", "20")), 0)
    if max_articles > 0:
        relevant_articles = relevant_articles[:max_articles]

    included_links: set[str] = set()

    logger.info("Articles included in daily report: %s", [a.title for a in relevant_articles])

    payload: list[dict[str, object]] = []

    total_summary_chars = 0
    total_content_chars = 0
    truncated_count = 0
    max_content_chars = max(int(os.environ.get("NEWS_ARTICLE_MAX_CHARS", "2600")), 0)

    for article in relevant_articles:
        serialized, truncated, summary_chars, content_chars = _serialize_article(
            article,
            max_content_chars=max_content_chars,
        )
        payload.append(serialized)
        link = serialized.get("link")
        if isinstance(link, str) and link:
            included_links.add(link)
        total_summary_chars += summary_chars
        total_content_chars += content_chars
        if truncated:
            truncated_count += 1

    estimated_tokens = math.ceil((total_summary_chars + total_content_chars) / 4) if payload else 0
    avg_summary = (total_summary_chars / len(payload)) if payload else 0.0
    avg_content = (total_content_chars / len(payload)) if payload else 0.0

    stats: dict[str, float | int] = {
        "articles_available": total_available,
        "articles_included": len(payload),
        "articles_truncated": truncated_count,
        "estimated_tokens": estimated_tokens,
        "avg_summary_chars": round(avg_summary, 1),
        "avg_content_chars": round(avg_content, 1),
        "max_articles": max_articles,
        "max_content_chars": max_content_chars,
    }

    return json.dumps(payload, indent=2), stats, included_links


def _build_news_audit_sections(
    *,
    included_links: set[str],
    stats: dict[str, float | int] | None,
    hours: int,
) -> tuple[str | None, str | None]:
    """Build both plain-text and markdown summaries of news article decisions."""
    articles = get_recent_articles(hours=hours)
    if not articles:
        return None, None

    limit_default = 15
    audit_limit_raw = os.environ.get("NEWS_ARTICLE_AUDIT_LIMIT", "").strip()
    try:
        audit_limit = int(audit_limit_raw) if audit_limit_raw else limit_default
    except ValueError:
        audit_limit = limit_default

    if audit_limit <= 0:
        audit_limit = len(articles)

    selected_articles = articles[:audit_limit]

    plain_lines: list[str] = [f"News Article Review (last {hours}h)"]
    markdown_lines: list[str] = [f"**News Article Review (last {hours}h)**"]

    if stats:
        total_available = stats.get("articles_available", len(articles))
        included_count = stats.get("articles_included", len(included_links))
        truncated = stats.get("articles_truncated", 0)
        plain_lines.append(
            f"Total available: {total_available} | Included: {included_count} | "
            f"Truncated: {truncated}",
        )
    else:
        plain_lines.append(
            f"Total available: {len(articles)} | Included: {len(included_links)}",
        )

    total_avail = stats.get("articles_available", len(articles)) if stats else len(articles)
    total_incl = (
        stats.get("articles_included", len(included_links)) if stats else len(included_links)
    )
    truncated_info = f" | Truncated: {stats.get('articles_truncated', 0)}" if stats else ""
    markdown_lines.append(
        f"Total available: {total_avail} | Included: {total_incl}{truncated_info}",
    )

    plain_lines.append("")
    markdown_lines.append("")

    for idx, article in enumerate(selected_articles, start=1):
        score_val = article.relevance_score
        score_str = f"{float(score_val):.2f}" if isinstance(score_val, (int, float)) else "N/A"
        included_flag = "yes" if article.link in included_links else "no"
        relevant_flag = "yes" if article.is_relevant else "no"
        title = (article.title or "Untitled article").strip()
        source = (article.source or "unknown source").strip()
        url = article.link or "N/A"

        plain_lines.append(
            f"{idx}. Included: {included_flag} | Relevant: {relevant_flag} | Score: {score_str}",
        )
        plain_lines.append(f"   Source: {source}")
        plain_lines.append(f"   Title: {title}")
        plain_lines.append(f"   URL: {url}")

        if idx != len(selected_articles):
            plain_lines.append("")

        include_marker = "YES" if included_flag == "yes" else "NO"
        relevant_marker = "YES" if relevant_flag == "yes" else "NO"
        url_display = url if url != "N/A" else ""
        link_fragment = f"[{title}]({url})" if url_display else title
        markdown_lines.append(
            f"{idx}. Included: {include_marker} | Relevant: {relevant_marker} | Score: {score_str}",
        )
        markdown_lines.append(f"   • Source: {source}")
        markdown_lines.append(f"   • Article: {link_fragment}")

        if url_display:
            markdown_lines.append(f"   • URL: {url}")
        markdown_lines.append("")

    if len(articles) > len(selected_articles):
        plain_lines.append("")
        plain_lines.append(
            f"(Showing first {len(selected_articles)} of {len(articles)} recent articles. "
            "Adjust NEWS_ARTICLE_AUDIT_LIMIT to include more.)",
        )
        markdown_lines.append(
            f"(Showing first {len(selected_articles)} of {len(articles)} recent articles. "
            "Adjust NEWS_ARTICLE_AUDIT_LIMIT to include more.)",
        )

    plain_text = "\n".join(plain_lines)
    markdown_text = "\n".join(markdown_lines)

    return plain_text, markdown_text


def _serialize_article(
    article: CachedArticle,
    *,
    max_content_chars: int,
) -> tuple[dict[str, object], bool, int, int]:
    """Convert a cached article into an AI-friendly payload."""
    summary = (article.summary or "").strip()
    if not summary:
        summary = _fallback_summary(article.content or article.raw_content or "")

    content = (article.content or "").strip()
    truncated = False
    original_length = len(content)
    if content and max_content_chars > 0 and len(content) > max_content_chars:
        trimmed = content[: max_content_chars - 3].rstrip()
        if " " in trimmed:
            trimmed = trimmed.rsplit(" ", 1)[0]
        content = f"{trimmed}..."
        truncated = True
        app_logger.info(
            "Truncated article '%s' from %d to %d chars (limit %d)",
            article.title,
            original_length,
            len(content),
            max_content_chars,
        )

    payload = {
        "source": article.source,
        "title": article.title,
        "link": article.link,
        "published": article.published,
        "symbols": article.symbols,
        "summary": summary,
        "content": content,
        "relevance_score": article.relevance_score,
        "analysis_notes": article.analysis_notes,
        "processed_at": article.processed_at,
    }

    return payload, truncated, len(summary), len(content)


def _fallback_summary(content: str, max_chars: int = 320) -> str:
    """Create a fallback summary when no AI-generated summary is available."""
    normalized = (content or "").strip().replace("\n", " ")
    if not normalized:
        return ""
    if len(normalized) <= max_chars:
        return normalized
    snippet = normalized[: max_chars - 3].rstrip()
    if " " in snippet:
        snippet = snippet.rsplit(" ", 1)[0]
    return f"{snippet}..."


async def process_daily_report(  # noqa: PLR0915
    conn,
    telegram_enabled,
    telegram_token,
    telegram_chat_id,
):
    """Process and send the daily cryptocurrency report via Telegram."""
    logger = app_logger

    # Get configured Telegram parse mode
    telegram_parse_mode = get_telegram_parse_mode()
    logger.info("Using Telegram parse mode: %s", telegram_parse_mode)

    symbols = fetch_symbols(conn)
    logger.info("Processing %d symbols for daily report...", len(symbols))

    # 🧹 CLEANUP OLD CACHED ARTICLES - Remove articles older than 24 hours
    logger.info("🧹 Cleaning up old cached articles...")
    try:
        deleted_count = cleanup_old_articles(max_age_hours=24)
        stats = get_cache_statistics()
        logger.info(
            "✓ Cleanup complete: %d articles deleted, %d remain (%.2f MB)",
            deleted_count,
            stats["total_articles"],
            stats["total_size_mb"],
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("⚠️ Article cache cleanup failed: %s", e)

    # 📰 FETCH RSS NEWS EARLY - Ollama processing happens here (~30 min)
    logger.info("📰 Fetching and processing RSS news with Ollama...")
    get_news()
    logger.info("✓ RSS news fetched and processed")

    # ✅ UPDATE LATEST DATA - Ensures fresh market data for analysis
    logger.info("📊 Updating latest market data...")

    # Fetch missing daily candles for all symbols (last 30 days for RSI calculation)
    # RSI needs at least 14 periods, plus extra for Wilder's smoothing
    today = datetime.now(UTC).date()
    start_date = today - timedelta(days=30)
    daily_candles_by_symbol = {}
    for symbol in symbols:
        candles = fetch_daily_candles(symbol, start_date, today, conn)
        daily_candles_by_symbol[symbol.symbol_id] = candles
    logger.info("✓ Daily candles: fetched for all %d symbols", len(symbols))

    # Fetch missing hourly candles for all symbols (last 24 hours)
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=24)
    hourly_updated = 0
    for symbol in symbols:
        candles = fetch_hourly_candles(symbol, start_time, end_time, conn)
        hourly_updated += len(candles)
    logger.info("✓ Hourly candles: %d fetched/cached for all symbols", hourly_updated)

    # Fetch missing 15-minute candles for all symbols (last 2 hours)
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=2)
    fifteen_updated = 0
    for symbol in symbols:
        candles = fetch_fifteen_min_candles(symbol, start_time, end_time, conn)
        fifteen_updated += len(candles)
    logger.info("✓ 15-minute candles: %d fetched/cached for all symbols", fifteen_updated)

    # Commit all the data updates to the database
    conn.commit()
    logger.info("✓ All candle data updates committed to database")

    # Fetch ETF data for institutional analysis
    logger.info("📊 Fetching latest ETF data for institutional analysis...")
    try:
        update_etf_data(conn)
    except Exception:
        logger.exception("⚠️ ETF data update failed")

    # Generate all reports
    # NOTE: Candles are now fetched once and passed to RSI calculator
    # This avoids duplicate fetching and ensures candle IDs are properly set

    # Prepare symbols with their candles for RSI calculation
    symbols_with_candles = [
        (symbol, daily_candles_by_symbol[symbol.symbol_id]) for symbol in symbols
    ]

    rsi_table = create_rsi_table(symbols_with_candles, conn, target_date=datetime.now(UTC).date())
    ma_average_table, ema_average_table = calculate_indicators(
        symbols,
        conn,
        target_date=datetime.now(UTC).date(),
    )
    range_table = fetch_range_price(symbols, conn)
    stepn_table = fetch_stepn_report(conn)
    macd_table = calculate_macd(symbols, conn, target_date=datetime.now(UTC).date())
    launchpool_report = check_gempool_articles()
    volume_table = fetch_volume_report(symbols, conn)
    marketcap_table = fetch_marketcap_report(symbols, conn)
    pricechange_table = fetch_price_change_report(
        symbols,
        conn,
        target_date=datetime.now(UTC).date(),
    )
    sopr_table = fetch_sopr_metrics(conn)
    derivatives_table = fetch_derivatives_report(symbols, conn)
    order_book_table = fetch_order_book_report(symbols, conn)
    cvd_table = fetch_cvd_report(symbols, conn)
    etf_summary_table = fetch_etf_summary_report(conn)

    # Format messages
    today_date = datetime.now(UTC).strftime("%Y-%m-%d")

    # --- Current Prices Section (added to indicators message) ---
    def build_current_prices_section(symbols: list[Symbol], limit: int = 20) -> str:
        """Build a current prices snapshot for inclusion in analysis prompt.

        Includes all active symbols sorted alphabetically for comprehensive analysis.
        Returns an HTML-formatted <pre> block consistent with other sections.
        """
        # Sort alphabetically - no priority given to any specific symbols
        ordered = sorted(symbols, key=lambda s: s.symbol_name)[:limit]
        lines = [
            "Symbol  | Last        | 24h Low     | 24h High    | Range% | FromLow% | FromHigh%",
        ]
        lines.append(
            "--------|------------|------------|------------|--------|----------|-----------",
        )
        for sym in ordered:
            try:
                tp = fetch_current_price(sym)
                rng = tp.high - tp.low if tp.high and tp.low else 0
                pos_pct = ((tp.last - tp.low) / rng * 100) if rng > 0 else 0
                from_low = ((tp.last - tp.low) / tp.low * 100) if tp.low else 0
                from_high = ((tp.high - tp.last) / tp.high * 100) if tp.high else 0
                lines.append(
                    f"{sym.symbol_name:<7}| {tp.last:>10.6f} | {tp.low:>10.6f} | "
                    f"{tp.high:>10.6f} | {pos_pct:>6.2f} | {from_low:>8.2f} | "
                    f"{from_high:>9.2f}",
                )
            except (KeyError, ValueError, TypeError, AttributeError, ZeroDivisionError) as e:
                lines.append(f"{sym.symbol_name:<7}| price fetch failed: {e}")
        return "Current Prices (spot / last 24h):\n<pre>" + "\n".join(lines) + "</pre>\n\n"

    current_prices_section = build_current_prices_section(symbols)

    message_part1 = f"Crypto Report: {today_date}\n" + current_prices_section
    message_part1 += f"24h Range Report:\n<pre>{range_table}</pre>"
    message_part1 += f"Price Change Report: <pre>{pricechange_table}</pre>\n\n"
    message_part1 += f"RSI Report: <pre>{rsi_table}</pre>\n\n"

    message_part2 = f"Simple Moving Average Report: <pre>{ma_average_table}</pre>\n\n"
    message_part2 += f"Exponential Moving Average Report: <pre>{ema_average_table}</pre>\n\n"
    message_part2 += f"MACD Report: <pre>{macd_table}</pre>\n\n"

    volume_report = f"Volume Report: <pre>{volume_table}</pre>"
    marketcap_report = f"Market Cap Report: <pre>{marketcap_table}</pre>"
    stepn_report = f"StepN Report: <pre>{stepn_table}</pre>"
    sopr_report = f"SOPR Report (BTC on-chain): <pre>{sopr_table}</pre>" if sopr_table else None
    derivatives_report = (
        f"Derivatives Report (Open Interest & Funding Rate): <pre>{derivatives_table}</pre>"
    )
    order_book_report = f"Order Book Liquidity: <pre>{order_book_table}</pre>"
    cvd_report = f"Order Flow (CVD): <pre>{cvd_table}</pre>"
    etf_report = f"ETF Institutional Flows: <pre>{etf_summary_table}</pre>"

    # Configure AI API settings
    ai_api_type, ai_api_key = _configure_ai_api()

    # Process AI analysis with news
    analysis_report, news_metadata = await _process_ai_analysis(
        ai_api_key,
        ai_api_type,
        symbols,
        current_prices_section,
        conn,
        today_date,
        logger,
    )

    news_audit_plain = news_metadata.get("audit_plain")

    # Send all messages
    await send_telegram_message(
        enabled=telegram_enabled,
        token=telegram_token,
        chat_id=telegram_chat_id,
        message=message_part1,
        parse_mode=telegram_parse_mode,
    )
    await send_telegram_message(
        enabled=telegram_enabled,
        token=telegram_token,
        chat_id=telegram_chat_id,
        message=message_part2,
        parse_mode=telegram_parse_mode,
    )
    await send_telegram_message(
        enabled=telegram_enabled,
        token=telegram_token,
        chat_id=telegram_chat_id,
        message=stepn_report,
        parse_mode=telegram_parse_mode,
    )
    await send_telegram_message(
        enabled=telegram_enabled,
        token=telegram_token,
        chat_id=telegram_chat_id,
        message=volume_report,
        parse_mode=telegram_parse_mode,
    )

    if sopr_report:
        await send_telegram_message(
            enabled=telegram_enabled,
            token=telegram_token,
            chat_id=telegram_chat_id,
            message=sopr_report,
            parse_mode=telegram_parse_mode,
        )

    await send_telegram_message(
        enabled=telegram_enabled,
        token=telegram_token,
        chat_id=telegram_chat_id,
        message=marketcap_report,
        parse_mode=telegram_parse_mode,
    )

    await send_telegram_message(
        enabled=telegram_enabled,
        token=telegram_token,
        chat_id=telegram_chat_id,
        message=derivatives_report,
        parse_mode=telegram_parse_mode,
    )

    await send_telegram_message(
        enabled=telegram_enabled,
        token=telegram_token,
        chat_id=telegram_chat_id,
        message=order_book_report,
        parse_mode=telegram_parse_mode,
    )

    await send_telegram_message(
        enabled=telegram_enabled,
        token=telegram_token,
        chat_id=telegram_chat_id,
        message=cvd_report,
        parse_mode=telegram_parse_mode,
    )

    await send_telegram_message(
        enabled=telegram_enabled,
        token=telegram_token,
        chat_id=telegram_chat_id,
        message=etf_report,
        parse_mode=telegram_parse_mode,
    )

    if isinstance(news_audit_plain, str) and news_audit_plain.strip():
        await send_telegram_message(
            enabled=telegram_enabled,
            token=telegram_token,
            chat_id=telegram_chat_id,
            message=news_audit_plain,
            parse_mode=None,
        )

    if launchpool_report:
        message_part3 = f"New Launchpool Report: <pre>{launchpool_report}</pre>"
        await send_telegram_message(
            enabled=telegram_enabled,
            token=telegram_token,
            chat_id=telegram_chat_id,
            message=message_part3,
            parse_mode=telegram_parse_mode,
        )

    # Send the detailed analysis with news as a Telegram document (last message)
    if not analysis_report.startswith("Failed"):
        try:
            await send_telegram_document(
                enabled=telegram_enabled,
                token=telegram_token,
                chat_id=telegram_chat_id,
                file_bytes=analysis_report.encode("utf-8"),
                filename=f"CryptoAnalysisWithNews_{today_date}.md",
                caption=f"Detailed Crypto Analysis with News {today_date}",
                parse_mode=None,  # treat as plain text/markdown without Telegram parsing
            )
        except (OSError, ValueError, TypeError, KeyError) as doc_err:
            logger.warning("Failed to send analysis with news as document: %s", doc_err)


if __name__ == "__main__":
    import asyncio

    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import fetch_symbols

    load_dotenv()
    conn = connect_to_sql()
    telegram_enabled = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
    telegram_token = os.getenv("TELEGRAM_TOKEN", "")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    async def main():
        """Run the main entry point for the daily report process."""
        await process_daily_report(conn, telegram_enabled, telegram_token, telegram_chat_id)

    asyncio.run(main())
