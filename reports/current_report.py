import argparse
import asyncio
import os
import sqlite3
from datetime import datetime

from infra.telegram_logging_handler import app_logger
from integrations.onedrive_uploader import upload_to_onedrive
from sharedCode.telegram import send_telegram_message
from technical_analysis.crypto_situation import generate_crypto_situation_report


async def main():
    """
    Command-line interface for generating cryptocurrency situation reports
    """
    parser = argparse.ArgumentParser(
        description="Generate a situation report for a specific cryptocurrency"
    )
    parser.add_argument(
        "symbol", help="Cryptocurrency symbol to analyze (e.g., BTC, ETH)"
    )
    parser.add_argument(
        "--save-to-onedrive", action="store_true", help="Save the report to OneDrive"
    )
    parser.add_argument(
        "--send-to-telegram", action="store_true", help="Send the report to Telegram"
    )
    args = parser.parse_args()

    # Connect to the database
    db_path = os.environ.get("DB_PATH", "cryptoDB.db")
    conn = sqlite3.connect(db_path)

    try:
        # Generate the report
        report = await generate_crypto_situation_report(conn, args.symbol.upper())

        if not report or report.startswith("Failed") or report.startswith("Error"):
            print(f"Failed to generate report: {report}")
            return

        # Print to console
        print(report)

        today_date = datetime.now().strftime("%Y-%m-%d")

        # Save to OneDrive if requested
        if args.save_to_onedrive:
            onedrive_filename = f"{args.symbol.upper()}_Situation_{today_date}.md"
            upload_success = await upload_to_onedrive(
                filename=onedrive_filename, content=report
            )
            if upload_success:
                print(f"Report saved to OneDrive as {onedrive_filename}")
            else:
                print("Failed to upload report to OneDrive")

        # Send to Telegram if requested
        if args.send_to_telegram:
            telegram_enabled = (
                os.environ.get("TELEGRAM_ENABLED", "False").lower() == "true"
            )
            telegram_token = os.environ.get("TELEGRAM_TOKEN", "")
            telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

            if telegram_enabled and telegram_token and telegram_chat_id:
                await send_telegram_message(
                    telegram_enabled,
                    telegram_token,
                    telegram_chat_id,
                    report,
                    parse_mode="HTML",
                )
                print("Report sent to Telegram")
            else:
                print(
                    "Telegram not configured properly. Check your environment variables."
                )

    except Exception as e:
        app_logger.error(f"Error in crypto_situation_report.py: {str(e)}")
        print(f"An error occurred: {str(e)}")
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
