"""Local runner for Azure Functions.

Run this script to test your functions locally without Azure Functions Core Tools.
"""

import asyncio
import sys
import traceback

from dotenv import load_dotenv

from function_app import run_report
from infra.sql_connection import connect_to_sql
from infra.telegram_logging_handler import app_logger
from reports.current_report import generate_crypto_situation_report


# Load environment variables
load_dotenv()


async def main():
    """Run the function locally."""
    # Check command line arguments
    report_type = "daily"  # default
    run_id = "AM"  # default for daily reports

    if len(sys.argv) > 1:
        report_type = sys.argv[1].lower()
        if report_type not in ["daily", "weekly", "current"]:
            app_logger.error(
                "Invalid report type '%s'\n"
                "Usage:\n"
                "  python local_runner.py [daily|weekly] [AM|PM]\n"
                "  python local_runner.py current <SYMBOL>\n"
                "\n"
                "Examples:\n"
                "  python local_runner.py              # Run daily report (AM)\n"
                "  python local_runner.py daily        # Run daily report (AM)\n"
                "  python local_runner.py daily PM     # Run daily report (PM)\n"
                "  python local_runner.py weekly       # Run weekly report\n"
                "  python local_runner.py current ETH  # Run current report for ETH",
                sys.argv[1],
            )
            sys.exit(1)

    # Get run_id for daily reports (second argument if provided)
    run_id_arg_index = 2
    if report_type == "daily" and len(sys.argv) > run_id_arg_index:
        run_id = sys.argv[run_id_arg_index].upper()
        if run_id not in ["AM", "PM"]:
            app_logger.error(
                "Invalid run_id '%s'. Use 'AM' or 'PM'.\nExample: python local_runner.py daily PM",
                sys.argv[run_id_arg_index],
            )
            sys.exit(1)

    try:
        if report_type == "current":
            # Current situation report
            min_args_for_current = 3
            if len(sys.argv) < min_args_for_current:
                app_logger.error(
                    "Symbol is required for current report\n"
                    "Usage: python local_runner.py current <SYMBOL>\n"
                    "Example: python local_runner.py current ETH",
                )
                sys.exit(1)

            symbol = sys.argv[2].upper()

            conn = connect_to_sql()
            try:
                await generate_crypto_situation_report(conn, symbol)
            finally:
                if conn:
                    conn.close()

        else:
            # Daily/weekly report
            await run_report(report_type, run_id=run_id)

    except (ValueError, KeyError, TypeError, OSError, RuntimeError):
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
