"""
Local runner for Azure Functions
Run this script to test your functions locally without Azure Functions Core Tools
Supports offline mode with mock data when database is unavailable.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def main():
    """Run the function locally"""
    # Check for offline mode
    offline_mode = os.getenv("OFFLINE_MODE", "false").lower() == "true"

    # Check command line arguments
    report_type = "daily"  # default

    if len(sys.argv) > 1:
        report_type = sys.argv[1].lower()
        if report_type not in ["daily", "weekly", "current", "offline"]:
            print(
                "Usage: python local_runner.py [daily|weekly|current|offline] [symbol]"
            )
            print("  daily   - Run daily report (requires database)")
            print("  weekly  - Run weekly report (requires database)")
            print(
                "  current [symbol] - Run current situation report (requires database)"
            )
            print("  offline - Run offline report with mock data (no database needed)")
            print("\nSet OFFLINE_MODE=true in .env to use mock data for daily reports")
            print("\nDefault: daily")
            sys.exit(1)

    # Force offline mode if explicitly requested
    if report_type == "offline":
        offline_mode = True

    if offline_mode:
        print("OFFLINE MODE - Using mock data (no database required)")
    else:
        print("ONLINE MODE - Connecting to database")

    print(f"Starting {report_type} report locally...")
    print("=" * 60)

    try:
        if offline_mode or report_type == "offline":
            # Use offline report generator
            from reports.offline_report import (
                generate_offline_report,
                generate_offline_situation_report,
            )

            if report_type == "current" or (
                len(sys.argv) > 2 and sys.argv[1] == "offline"
            ):
                # Offline situation report
                symbol = sys.argv[2].upper() if len(sys.argv) > 2 else "BTC"
                print(f"📊 Generating offline situation report for {symbol}...")
                await generate_offline_situation_report(symbol)
            else:
                # Offline daily report
                print(
                    "📊 Generating offline daily report with real news + mock indicators..."
                )
                await generate_offline_report()

        elif report_type == "current":
            # Online current situation report
            from infra.sql_connection import connect_to_sql
            from reports.current_report import generate_crypto_situation_report

            if len(sys.argv) < 3:
                print("❌ Error: Symbol required for current situation report")
                print("Usage: python local_runner.py current BTC")
                sys.exit(1)

            symbol = sys.argv[2].upper()
            print(f"📊 Generating situation report for {symbol}...")

            conn = connect_to_sql()
            try:
                report = await generate_crypto_situation_report(conn, symbol)
                print("\n" + "=" * 60)
                print("REPORT OUTPUT:")
                print("=" * 60)
                print(report)
            finally:
                if conn:
                    conn.close()

        else:
            # Online daily/weekly report
            from function_app import run_report

            await run_report(report_type)

        print("=" * 60)
        print(f"SUCCESS: {report_type.capitalize()} report completed!")

    except Exception as e:
        print("=" * 60)
        print(f"ERROR: Failed to run {report_type} report: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
