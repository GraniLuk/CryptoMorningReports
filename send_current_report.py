"""Send current situation report for a specific symbol to Telegram."""

import asyncio
import os
import sys

from dotenv import load_dotenv

from infra.sql_connection import connect_to_sql
from infra.telegram_logging_handler import app_logger
from reports.current_report import generate_crypto_situation_report
from shared_code.telegram import send_telegram_message


async def send_current_report(symbol: str):
    """Generate and send current situation report to Telegram."""
    load_dotenv()

    # Check if Telegram is enabled
    telegram_enabled = os.environ.get("TELEGRAM_ENABLED", "False").lower() == "true"
    telegram_token = os.environ.get("TELEGRAM_TOKEN", "")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    "***" + telegram_token[-10:] if telegram_token else "Not set"

    if not telegram_enabled:
        pass

    if not telegram_token or not telegram_chat_id:
        app_logger.error("Telegram credentials not configured in .env")
        return False

    conn = connect_to_sql()
    try:
        # Generate report
        report = await generate_crypto_situation_report(conn, symbol)

        if report and not report.startswith("Failed") and not report.startswith("Error"):
            # Send to Telegram
            result = await send_telegram_message(
                enabled=True,  # Force send for testing
                token=telegram_token,
                chat_id=telegram_chat_id,
                message=report,
                parse_mode="HTML",
            )

            return bool(result)
        error_preview = report[:200] if report else "No report"
        app_logger.error(f"Failed to generate report: {error_preview}...")
        return False

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    symbol = sys.argv[1].upper() if len(sys.argv) > 1 else "VIRTUAL"
    asyncio.run(send_current_report(symbol))
