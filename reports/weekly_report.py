from datetime import UTC, datetime, timedelta

from database.update_latest_data import update_latest_daily_candles
from infra.telegram_logging_handler import app_logger
from shared_code.telegram import send_telegram_message
from source_repository import fetch_symbols
from technical_analysis.macd_report import calculate_macd
from technical_analysis.moving_averages_report import calculate_indicators


async def process_weekly_report(conn, telegram_enabled, telegram_token, telegram_chat_id):
    logger = app_logger
    symbols = fetch_symbols(conn)
    logger.info("Processing %d symbols for weekly report...", len(symbols))

    # ✅ UPDATE LATEST DATA FIRST - Ensures fresh market data for analysis
    logger.info("📊 Updating latest market data before weekly analysis...")
    updated_count, failed_count = update_latest_daily_candles(conn, days_to_update=3)
    logger.info(f"✓ Data refresh complete: {updated_count} candles updated, {failed_count} failed")

    # Calculate date range for weekly report
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=7)

    # Generate weekly specific reports
    ma_average_table, ema_average_table = calculate_indicators(symbols, conn, start_date)
    macd_table = calculate_macd(symbols, conn, start_date)

    # Format messages
    message = (
        f"Weekly Crypto Report: {start_date.strftime('%Y-%m-%d')} to "
        f"{end_date.strftime('%Y-%m-%d')}\n\n"
    )
    message += f"Weekly Moving Average Report: <pre>{ma_average_table}</pre>\n\n"
    message += f"Weekly EMA Report: <pre>{ema_average_table}</pre>\n\n"
    message += f"Weekly MACD Report: <pre>{macd_table}</pre>\n\n"

    # Send weekly report
    await send_telegram_message(
        telegram_enabled, telegram_token, telegram_chat_id, message, parse_mode="HTML"
    )
