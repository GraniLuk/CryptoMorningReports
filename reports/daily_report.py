import os
from datetime import datetime

from infra.telegram_logging_handler import app_logger
from launchpool.launchpool_report import check_gempool_articles
from news.crypto_panic import get_panic_news
from news.news_agent import (
    get_detailed_crypto_analysis,
    get_detailed_crypto_analysis_with_news,
    highlight_articles,
)
from news.rss_parser import get_news
from sharedCode.telegram import send_telegram_message
from source_repository import fetch_symbols
from stepn.stepn_report import fetch_stepn_report
from technical_analysis.daily_candle import fetch_daily_candles
from technical_analysis.macd_report import calculate_macd
from technical_analysis.marketcap_report import fetch_marketcap_report
from technical_analysis.movingAveragesReport import calculate_indicators
from technical_analysis.price_change_report import fetch_price_change_report
from technical_analysis.priceRangeReport import fetch_range_price
from technical_analysis.reports.rsi_daily import create_rsi_table
from technical_analysis.repositories.aggregated_repository import get_aggregated_data
from technical_analysis.sopr import fetch_sopr_metrics
from technical_analysis.volume_report import fetch_volume_report
from integrations.onedrive_uploader import upload_to_onedrive # Added import


async def process_daily_report(
    conn, telegram_enabled, telegram_token, telegram_chat_id
):
    logger = app_logger
    symbols = fetch_symbols(conn)
    logger.info("Processing %d symbols for daily report...", len(symbols))

    # Generate all reports
    fetch_daily_candles(symbols, conn)
    rsi_table = create_rsi_table(symbols, conn)
    ma_average_table, ema_average_table = calculate_indicators(symbols, conn)
    range_table = fetch_range_price(symbols, conn)
    stepn_table = fetch_stepn_report(conn)
    macd_table = calculate_macd(symbols, conn)
    launchpool_report = check_gempool_articles()
    volume_table = fetch_volume_report(symbols, conn)
    marketcap_table = fetch_marketcap_report(symbols, conn)
    pricechange_table = fetch_price_change_report(symbols, conn)
    sopr_table = fetch_sopr_metrics(conn)
    symbols_list = [symbol.symbol_name for symbol in symbols]
    news = get_panic_news(symbols_list)

    # Format messages
    today_date = datetime.now().strftime("%Y-%m-%d")

    message_part1 = f"Crypto Report: {today_date}\n"
    message_part1 += f"24h Range Report:\n<pre>{range_table}</pre>"
    message_part1 += f"Price Change Report: <pre>{pricechange_table}</pre>\n\n"
    message_part1 += f"RSI Report: <pre>{rsi_table}</pre>\n\n"

    message_part2 = f"Simple Moving Average Report: <pre>{ma_average_table}</pre>\n\n"
    message_part2 += (
        f"Exponential Moving Average Report: <pre>{ema_average_table}</pre>\n\n"
    )
    message_part2 += f"MACD Report: <pre>{macd_table}</pre>\n\n"

    volume_report = f"Volume Report: <pre>{volume_table}</pre>"
    volume_report = f"Market Cap Report: <pre>{marketcap_table}</pre>"
    stepn_report = f"StepN Report: <pre>{stepn_table}</pre>"
    sopr_report = f"SOPR bitcoin report: <pre>{sopr_table}</pre>"

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

    if not ai_api_key:
        logger.error(f"No API key found for {ai_api_type}")
        analysis_reported_without_news = (
            f"Failed: No {ai_api_type.title()} API key found"
        )
        analysis_saved_to_onedrive = False # Flag to track upload status
    else:
        # Process and send news reports
        fetched_news = get_news()
        # aggregated_data = get_aggregated_data(conn)
        analysis_reported_without_news = get_detailed_crypto_analysis(
            ai_api_key,
            message_part1 + message_part2 + volume_report + sopr_report,
            fetched_news,
            ai_api_type,
        )
        # analysis_reported_with_news = get_detailed_crypto_analysis_with_news(
        #     ai_api_key, aggregated_data, fetched_news, ai_api_type
        # )
        # highlight_articles_message = highlight_articles(ai_api_key, symbols, fetched_news, ai_api_type)

        # --- Added OneDrive Upload ---
        if not analysis_reported_without_news.startswith("Failed"):
            onedrive_filename = f"CryptoAnalysis_{today_date}.md"
            analysis_saved_to_onedrive = await upload_to_onedrive(
                filename=onedrive_filename,
                content=analysis_reported_without_news,
            )
        else:
             analysis_saved_to_onedrive = False
        # --- End Added OneDrive Upload ---

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

    await send_telegram_message(
        telegram_enabled,
        telegram_token,
        telegram_chat_id,
        sopr_report,
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

    if not analysis_reported_without_news.startswith("Failed"):
        await send_telegram_message(
            telegram_enabled,
            telegram_token,
            telegram_chat_id,
            analysis_reported_without_news,
            parse_mode="HTML",
        )
        # Optionally notify about OneDrive save status
        if analysis_saved_to_onedrive:
             logger.info(f"Analysis report for {today_date} saved to OneDrive.")
        else:
             logger.warning(f"Failed to save analysis report for {today_date} to OneDrive.")


    await send_telegram_message(
        telegram_enabled, telegram_token, telegram_chat_id, news, parse_mode="HTML"
    )

    # if not analysis_reported_with_news.startswith("Failed"):
    #     await send_telegram_message(
    #         telegram_enabled,
    #         telegram_token,
    #         telegram_chat_id,
    #         analysis_reported_with_news,
    #         parse_mode="HTML",
    #     )
    # if not highlight_articles_message.startswith("Failed"):
    #     await send_telegram_message(
    #         telegram_enabled,
    #         telegram_token,
    #         telegram_chat_id,
    #         highlight_articles_message,
    #         parse_mode="HTML",
    #     )
