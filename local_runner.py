"""Local runner for Azure Functions.

Run this script to test your functions locally without Azure Functions Core Tools.
"""

import asyncio
import sys
import traceback

from dotenv import load_dotenv

from function_app import run_report
from infra.sql_connection import connect_to_sql
from reports.current_report import generate_crypto_situation_report


# Load environment variables
load_dotenv()


async def main():
    """Run the function locally."""
    # Check command line arguments
    report_type = "daily"  # default

    if len(sys.argv) > 1:
        report_type = sys.argv[1].lower()
        if report_type not in ["daily", "weekly", "current"]:
            sys.exit(1)

    try:
        if report_type == "current":
            # Current situation report
            min_args_for_current = 3
            if len(sys.argv) < min_args_for_current:
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
            await run_report(report_type)

    except (ValueError, KeyError, TypeError, OSError, RuntimeError):
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
