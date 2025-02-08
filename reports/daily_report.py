from datetime import datetime
import os
from technical_analysis.marketcap_report import fetch_marketcap_report
from technical_analysis.priceRangeReport import fetch_range_price
from technical_analysis.RSIReport import create_rsi_table
from technical_analysis.movingAveragesReport import calculate_indicators
from technical_analysis.macd_report import calculate_macd
from technical_analysis.price_change_report import fetch_price_change_report
from technical_analysis.volume_report import fetch_volume_report
from stepn.stepn_report import fetch_stepn_report
from launchpool.launchpool_report import check_gempool_articles
from news.news_agent import get_detailed_crypto_analysis
from news.rss_parser import get_news
from sharedCode.telegram import send_telegram_message
from source_repository import fetch_symbols
from infra.telegram_logging_handler import app_logger


async def process_daily_report(
    conn, telegram_enabled, telegram_token, telegram_chat_id
):
    logger = app_logger
    symbols = fetch_symbols(conn)
    logger.info("Processing %d symbols for daily report...", len(symbols))

    # Generate all reports
    rsi_table = create_rsi_table(symbols, conn)
    ma_average_table, ema_average_table = calculate_indicators(symbols, conn)
    range_table = fetch_range_price(symbols, conn)
    stepn_table = fetch_stepn_report(conn)
    macd_table = calculate_macd(symbols, conn)
    launchpool_report = check_gempool_articles()
    volume_table = fetch_volume_report(symbols, conn)
    marketcap_table = fetch_marketcap_report(symbols, conn)
    pricechange_table = fetch_price_change_report(symbols)

    # Format messages
    today_date = datetime.now().strftime("%Y-%m-%d")

    message_part1 = f"Crypto Report: {today_date}\n"
    message_part1 += f"24h Range Report:\n<pre>{range_table}</pre>"
    message_part1 += f"Simple Moving Average Report: <pre>{ma_average_table}</pre>\n\n"
    message_part1 += (
        f"Exponential Moving Average Report: <pre>{ema_average_table}</pre>\n\n"
    )

    message_part2 = f"RSI Report: <pre>{rsi_table}</pre>\n\n"
    message_part2 += f"MACD Report: <pre>{macd_table}</pre>\n\n"
    message_part2 += f"Price Change Report: <pre>{pricechange_table}</pre>\n\n"

    volume_report = f"Volume Report: <pre>{volume_table}</pre>"
    volume_report = f"Market Cap Report: <pre>{marketcap_table}</pre>"
    stepn_report = f"StepN Report: <pre>{stepn_table}</pre>"

    # Process and send news reports
    fetched_news = get_news()
    # aggregated_data = get_aggregated_data(conn)
    analysis_reported_without_news = get_detailed_crypto_analysis(
        os.environ["PERPLEXITY_API_KEY"],
        message_part1 + message_part2 + volume_report,
        fetched_news,
    )
    # analysis_reported_with_news = get_detailed_crypto_analysis_with_news(os.environ["PERPLEXITY_API_KEY"], aggregated_data , fetched_news)
    # highlight_articles_message = highlight_articles(os.environ["PERPLEXITY_API_KEY"], symbols, fetched_news)

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

    # if not analysis_reported_with_news.startswith("Failed"):
    #     await send_telegram_message(telegram_enabled, telegram_token, telegram_chat_id, analysis_reported_with_news, parse_mode="HTML")
    # if not highlight_articles_message.startswith("Failed"):
    #     await send_telegram_message(telegram_enabled, telegram_token, telegram_chat_id, highlight_articles_message, parse_mode="HTML")
