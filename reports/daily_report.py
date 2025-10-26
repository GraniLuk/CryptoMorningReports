import os
from datetime import UTC, date, datetime

from database.update_latest_data import update_latest_daily_candles
from infra.telegram_logging_handler import app_logger
from integrations.email_sender import send_email_with_epub_attachment
from integrations.onedrive_uploader import (
    upload_to_onedrive,  # Import for OneDrive uploads
)
from integrations.pandoc_converter import convert_markdown_to_epub_async
from launchpool.launchpool_report import check_gempool_articles
from news.news_agent import (
    get_detailed_crypto_analysis_with_news,
    highlight_articles,
)
from news.rss_parser import get_news
from sharedCode.priceChecker import fetch_current_price
from sharedCode.telegram import send_telegram_document, send_telegram_message
from source_repository import fetch_symbols
from stepn.stepn_report import fetch_stepn_report
from technical_analysis.derivatives_report import fetch_derivatives_report
from technical_analysis.macd_report import calculate_macd
from technical_analysis.marketcap_report import fetch_marketcap_report
from technical_analysis.movingAveragesReport import calculate_indicators
from technical_analysis.price_change_report import fetch_price_change_report
from technical_analysis.priceRangeReport import fetch_range_price
from technical_analysis.reports.rsi_daily import create_rsi_table
from technical_analysis.repositories.aggregated_repository import get_aggregated_data
from technical_analysis.sopr import fetch_sopr_metrics
from technical_analysis.volume_report import fetch_volume_report


async def process_daily_report(
    conn, telegram_enabled, telegram_token, telegram_chat_id
):
    logger = app_logger
    symbols = fetch_symbols(conn)
    logger.info("Processing %d symbols for daily report...", len(symbols))

    # ✅ UPDATE LATEST DATA FIRST - Ensures fresh market data for analysis
    logger.info("📊 Updating latest market data before analysis...")
    updated_count, failed_count = update_latest_daily_candles(conn, days_to_update=3)
    logger.info(
        f"✓ Data refresh complete: {updated_count} candles updated, {failed_count} failed"
    )

    # Generate all reports
    # NOTE: fetch_daily_candles() removed - redundant with update_latest_daily_candles() above
    # Calling it causes duplicate inserts → candle IDs change → RSI becomes orphaned

    rsi_table = create_rsi_table(symbols, conn, target_date=date.today())
    ma_average_table, ema_average_table = calculate_indicators(
        symbols, conn, target_date=date.today()
    )
    range_table = fetch_range_price(symbols, conn)
    stepn_table = fetch_stepn_report(conn)
    macd_table = calculate_macd(symbols, conn, target_date=date.today())
    launchpool_report = check_gempool_articles()
    volume_table = fetch_volume_report(symbols, conn)
    marketcap_table = fetch_marketcap_report(symbols, conn)
    pricechange_table = fetch_price_change_report(
        symbols, conn, target_date=date.today()
    )
    sopr_table = fetch_sopr_metrics(conn)
    derivatives_table = fetch_derivatives_report(symbols, conn)

    # Format messages
    today_date = datetime.now(UTC).strftime("%Y-%m-%d")

    # --- Current Prices Section (added to indicators message) ---
    def build_current_prices_section(symbols, limit: int = 12) -> str:
        """Build a current prices snapshot for inclusion in analysis prompt.

        Prioritizes BTC & ETH, then fills remaining slots with other symbols.
        Returns an HTML-formatted <pre> block consistent with other sections.
        """
        # Reorder symbols so BTC/ETH first
        priority = ["BTC", "ETH"]
        ordered = sorted(
            symbols,
            key=lambda s: (0 if s.symbol_name in priority else 1, s.symbol_name),
        )[:limit]
        lines = [
            "Symbol  | Last        | 24h Low     | 24h High    | Range% | FromLow% | FromHigh%"
        ]
        lines.append(
            "--------|------------|------------|------------|--------|----------|-----------"
        )
        for sym in ordered:
            try:
                tp = fetch_current_price(sym)
                rng = tp.high - tp.low if tp.high and tp.low else 0
                pos_pct = ((tp.last - tp.low) / rng * 100) if rng > 0 else 0
                from_low = ((tp.last - tp.low) / tp.low * 100) if tp.low else 0
                from_high = ((tp.high - tp.last) / tp.high * 100) if tp.high else 0
                lines.append(
                    f"{sym.symbol_name:<7}| {tp.last:>10.6f} | {tp.low:>10.6f} | {tp.high:>10.6f} | {pos_pct:>6.2f} | {from_low:>8.2f} | {from_high:>9.2f}"
                )
            except Exception as e:
                lines.append(f"{sym.symbol_name:<7}| price fetch failed: {e}")
        return (
            "Current Prices (spot / last 24h):\n<pre>" + "\n".join(lines) + "</pre>\n\n"
        )

    current_prices_section = build_current_prices_section(symbols)

    message_part1 = f"Crypto Report: {today_date}\n" + current_prices_section
    message_part1 += f"24h Range Report:\n<pre>{range_table}</pre>"
    message_part1 += f"Price Change Report: <pre>{pricechange_table}</pre>\n\n"
    message_part1 += f"RSI Report: <pre>{rsi_table}</pre>\n\n"

    message_part2 = f"Simple Moving Average Report: <pre>{ma_average_table}</pre>\n\n"
    message_part2 += (
        f"Exponential Moving Average Report: <pre>{ema_average_table}</pre>\n\n"
    )
    message_part2 += f"MACD Report: <pre>{macd_table}</pre>\n\n"

    volume_report = f"Volume Report: <pre>{volume_table}</pre>"
    marketcap_report = f"Market Cap Report: <pre>{marketcap_table}</pre>"
    stepn_report = f"StepN Report: <pre>{stepn_table}</pre>"
    sopr_report = (
        f"SOPR bitcoin report: <pre>{sopr_table}</pre>" if sopr_table else None
    )
    derivatives_report = f"Derivatives Report (Open Interest & Funding Rate): <pre>{derivatives_table}</pre>"

    # Determine which API to use (Perplexity or Gemini)
    ai_api_type = os.environ.get("AI_API_TYPE", "perplexity").lower()
    ai_api_key = ""

    if ai_api_type == "perplexity":
        ai_api_key = os.environ.get("PERPLEXITY_API_KEY", "")
        logger.info("Using Perplexity API for analysis")
    elif ai_api_type == "gemini":
        ai_api_key = os.environ.get("GEMINI_API_KEY", "")
        logger.info("Using Gemini API for analysis")
    else:
        logger.warning(f"Unknown AI API type: {ai_api_type}, defaulting to Perplexity")
        ai_api_type = "perplexity"
        ai_api_key = os.environ.get("PERPLEXITY_API_KEY", "")

    highlight_articles_message = "Failed: Highlight articles message not generated"

    if not ai_api_key:
        logger.error(f"No API key found for {ai_api_type}")
    else:
        # Process and send news reports
        fetched_news = get_news()
        aggregated_data = get_aggregated_data(conn)

        # Reuse current_prices_section also for the news-enhanced analysis by prepending it to aggregated indicators
        def format_aggregated(agg_list) -> str:
            if not agg_list:
                return "No aggregated indicator data available.\n"
            header = (
                "Symbol | RSI | Close | MA50 | MA200 | EMA50 | EMA200 | Low | High | Range% | OI | OI Value | Fund Rate\n"
                "-------|-----|-------|------|-------|------|--------|-----|------|--------|----|-----------|-----------\n"
            )
            lines = []
            for row in agg_list:
                try:
                    # Format Open Interest and Funding Rate with proper handling of None values
                    oi_str = (
                        f"{row.get('OpenInterest', 0):,.0f}"
                        if row.get("OpenInterest")
                        else "N/A"
                    )
                    oi_val_str = (
                        f"${row.get('OpenInterestValue', 0):,.0f}"
                        if row.get("OpenInterestValue")
                        else "N/A"
                    )
                    fr_str = (
                        f"{row.get('FundingRate', 0):.4f}%"
                        if row.get("FundingRate")
                        else "N/A"
                    )

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
                        f"{fr_str:>11}"
                    )
                except Exception as e:
                    lines.append(f"Row format error: {e}")
            return (
                "Aggregated Indicators:\n<pre>"
                + header
                + "\n".join(lines)
                + "</pre>\n\n"
            )

        aggregated_formatted = format_aggregated(aggregated_data)
        aggregated_with_prices = current_prices_section + aggregated_formatted
        analysis_reported_with_news = get_detailed_crypto_analysis_with_news(
            ai_api_key, aggregated_with_prices, fetched_news, ai_api_type, conn
        )
        highlight_articles_message = highlight_articles(
            ai_api_key, symbols, fetched_news, ai_api_type
        )
        # --- OneDrive Uploads ---
        if not analysis_reported_with_news.startswith("Failed"):
            onedrive_filename_analysis_with_news = (
                f"CryptoAnalysisWithNews_{today_date}.md"
            )
            await upload_to_onedrive(
                filename=onedrive_filename_analysis_with_news,
                content=analysis_reported_with_news,
                folder_path="detailed_analysis_with_news",
            )

            # Attempt to send the detailed analysis with news as a Telegram document for better readability
            # Use in-memory bytes to avoid filesystem dependency; could alternatively write a temp file.
            try:
                await send_telegram_document(
                    telegram_enabled,
                    telegram_token,
                    telegram_chat_id,
                    file_bytes=analysis_reported_with_news.encode("utf-8"),
                    filename=onedrive_filename_analysis_with_news,
                    caption=f"Detailed Crypto Analysis with News {today_date}",
                    parse_mode=None,  # treat as plain text/markdown without Telegram parsing
                )
            except Exception as doc_err:
                logger.warning(
                    "Failed to send analysis with news as document: %s", doc_err
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
                logger.warning(
                    "Failed to convert analysis markdown to EPUB: %s", convert_err
                )
            else:
                recipients_env = os.environ.get("DAILY_REPORT_EMAIL_RECIPIENTS", "")
                recipients = [
                    addr.strip() for addr in recipients_env.split(",") if addr.strip()
                ]

                if not recipients:
                    logger.info(
                        "No recipients configured in DAILY_REPORT_EMAIL_RECIPIENTS; skipping email dispatch."
                    )
                else:
                    email_body = (
                        "Hi,\n\n"
                        "Please find attached the EPUB version of today's detailed crypto analysis with news.\n\n"
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
                        f"Highlighted articles for {today_date} saved to OneDrive news folder."
                    )
                else:
                    logger.warning(
                        f"Failed to save highlighted articles for {today_date} to OneDrive."
                    )
        else:
            pass
        # --- End OneDrive Uploads ---

    # Send all messages
    await send_telegram_message(
        telegram_enabled,
        telegram_token,
        telegram_chat_id,
        message_part1,
        parse_mode="HTML",
    )
    await send_telegram_message(
        telegram_enabled,
        telegram_token,
        telegram_chat_id,
        message_part2,
        parse_mode="HTML",
    )
    await send_telegram_message(
        telegram_enabled,
        telegram_token,
        telegram_chat_id,
        stepn_report,
        parse_mode="HTML",
    )
    await send_telegram_message(
        telegram_enabled,
        telegram_token,
        telegram_chat_id,
        volume_report,
        parse_mode="HTML",
    )

    if sopr_report:
        await send_telegram_message(
            telegram_enabled,
            telegram_token,
            telegram_chat_id,
            sopr_report,
            parse_mode="HTML",
        )

    await send_telegram_message(
        telegram_enabled,
        telegram_token,
        telegram_chat_id,
        marketcap_report,
        parse_mode="HTML",
    )

    await send_telegram_message(
        telegram_enabled,
        telegram_token,
        telegram_chat_id,
        derivatives_report,
        parse_mode="HTML",
    )

    if launchpool_report:
        message_part3 = f"New Launchpool Report: <pre>{launchpool_report}</pre>"
        await send_telegram_message(
            telegram_enabled,
            telegram_token,
            telegram_chat_id,
            message_part3,
            parse_mode="HTML",
        )


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
        await process_daily_report(
            conn, telegram_enabled, telegram_token, telegram_chat_id
        )

    asyncio.run(main())
