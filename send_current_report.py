"""Send current situation report for a specific symbol to Telegram
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

from infra.sql_connection import connect_to_sql
from reports.current_report import generate_crypto_situation_report
from shared_code.telegram import send_telegram_message


async def send_current_report(symbol: str):
    """Generate and send current situation report to Telegram"""
    load_dotenv()

    # Check if Telegram is enabled
    telegram_enabled = os.environ.get("TELEGRAM_ENABLED", "False").lower() == "true"
    telegram_token = os.environ.get("TELEGRAM_TOKEN", "")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    print(f"Telegram Enabled: {telegram_enabled}")
    token_display = "***" + telegram_token[-10:] if telegram_token else "Not set"
    print(f"Telegram Token: {token_display}")
    print(f"Telegram Chat ID: {telegram_chat_id if telegram_chat_id else 'Not set'}")
    print()

    if not telegram_enabled:
        print("⚠️  Warning: TELEGRAM_ENABLED is set to False in .env")
        print("Note: Will still attempt to send for testing purposes")
        print()

    if not telegram_token or not telegram_chat_id:
        print("❌ Error: Telegram credentials not configured in .env")
        return False

    conn = connect_to_sql()
    try:
        print(f"📊 Generating current situation report for {symbol}...")

        # Generate report
        report = await generate_crypto_situation_report(conn, symbol)

        if report and not report.startswith("Failed") and not report.startswith("Error"):
            print(f"✅ Report generated successfully ({len(report)} characters)")
            print("📤 Sending to Telegram...")

            # Send to Telegram
            result = await send_telegram_message(
                enabled=True,  # Force send for testing
                token=telegram_token,
                chat_id=telegram_chat_id,
                message=report,
                parse_mode="HTML",
            )

            if result:
                print("✅ SUCCESS: Report sent to Telegram!")
                print("📱 Check your Telegram group for the message!")
                return True
            print("❌ ERROR: Failed to send report to Telegram")
            return False
        error_preview = report[:200] if report else "No report"
        print(f"❌ ERROR: Failed to generate report: {error_preview}...")
        return False

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    symbol = sys.argv[1].upper() if len(sys.argv) > 1 else "VIRTUAL"
    print(f"Symbol: {symbol}")
    print("=" * 60)
    asyncio.run(send_current_report(symbol))
