from datetime import datetime, timedelta
from technical_analysis.movingAveragesReport import calculate_indicators
from technical_analysis.macd_report import calculate_macd
from source_repository import fetch_symbols
from sharedCode.telegram import send_telegram_message
from infra.telegram_logging_handler import app_logger


async def process_weekly_report(
    conn, telegram_enabled, telegram_token, telegram_chat_id
):
    logger = app_logger
    symbols = fetch_symbols(conn)
    logger.info("Processing %d symbols for weekly report...", len(symbols))

    # Calculate date range for weekly report
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    # Generate weekly specific reports
    ma_average_table, ema_average_table = calculate_indicators(
        symbols, conn, start_date
    )
    macd_table = calculate_macd(symbols, conn, start_date)

    # Format messages
    message = f"Weekly Crypto Report: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n\n"
    message += f"Weekly Moving Average Report: <pre>{ma_average_table}</pre>\n\n"
    message += f"Weekly EMA Report: <pre>{ema_average_table}</pre>\n\n"
    message += f"Weekly MACD Report: <pre>{macd_table}</pre>\n\n"

    # Send weekly report
    await send_telegram_message(
        telegram_enabled, telegram_token, telegram_chat_id, message, parse_mode="HTML"
    )
