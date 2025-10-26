"""
Local runner for Azure Functions
Run this script to test your functions locally without Azure Functions Core Tools
"""

import asyncio
import sys

from dotenv import load_dotenv


# Load environment variables
load_dotenv()


async def main():
    """Run the function locally"""
    # Check command line arguments
    report_type = "daily"  # default

    if len(sys.argv) > 1:
        report_type = sys.argv[1].lower()
        if report_type not in ["daily", "weekly", "current"]:
            print("Usage: python local_runner.py [daily|weekly|current] [symbol]")
            print("  daily   - Run daily report")
            print("  weekly  - Run weekly report")
            print("  current [symbol] - Run current situation report")
            print("\nDefault: daily")
            sys.exit(1)

    print(f"Starting {report_type} report locally...")
    print("=" * 60)

    try:
        if report_type == "current":
            # Current situation report
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
            # Daily/weekly report
            from function_app import run_report

            await run_report(report_type)

        print("=" * 60)
        print(f"SUCCESS: {report_type.capitalize()} report completed!")

    except Exception as e:
        print("=" * 60)
        print(f"ERROR: Failed to run {report_type} report: {e!s}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
