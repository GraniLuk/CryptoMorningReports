"""Fetch and save derivatives market data (Open Interest and Funding Rate) for symbols.
"""

import sys
from pathlib import Path


# Add parent directory to path for imports when run standalone
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from datetime import UTC, datetime

from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from shared_code.binance import fetch_binance_futures_metrics
from source_repository import SourceID, Symbol
from technical_analysis.repositories.funding_rate_repository import (
    FundingRateRepository,
)
from technical_analysis.repositories.open_interest_repository import (
    OpenInterestRepository,
)


def fetch_derivatives_report(symbols: list[Symbol], conn) -> PrettyTable:
    """Fetch Open Interest and Funding Rate for all symbols and save to database.

    Args:
        symbols: List of Symbol objects to fetch data for
        conn: Database connection

    Returns:
        PrettyTable with derivatives data

    """
    oi_repo = OpenInterestRepository(conn)
    fr_repo = FundingRateRepository(conn)

    table = PrettyTable()
    table.field_names = [
        "Symbol",
        "Open Interest",
        "OI Value (USD)",
        "Funding Rate (%)",
        "Next Funding",
    ]
    table.align["Symbol"] = "l"
    table.align["Open Interest"] = "r"
    table.align["OI Value (USD)"] = "r"
    table.align["Funding Rate (%)"] = "r"
    table.align["Next Funding"] = "l"

    indicator_date = datetime.now(UTC)
    successful = 0
    failed = 0

    for symbol in symbols:
        # Only fetch for Binance symbols (futures are on Binance)
        if symbol.source_id != SourceID.BINANCE:
            continue

        try:
            metrics = fetch_binance_futures_metrics(symbol)

            if metrics is None:
                app_logger.warning(f"No futures data available for {symbol.symbol_name}")
                failed += 1
                continue

            # Save to database
            oi_repo.save_open_interest(
                symbol.symbol_id,
                metrics.open_interest,
                metrics.open_interest_value,
                indicator_date,
            )

            fr_repo.save_funding_rate(
                symbol.symbol_id,
                metrics.funding_rate,
                metrics.next_funding_time,
                indicator_date,
            )

            # Add to table
            table.add_row(
                [
                    symbol.symbol_name,
                    f"{metrics.open_interest:,.2f}",
                    f"${metrics.open_interest_value:,.0f}",
                    f"{metrics.funding_rate:.4f}%",
                    metrics.next_funding_time.strftime("%H:%M UTC"),
                ]
            )

            successful += 1

        except Exception as e:
            app_logger.error(f"Error processing derivatives data for {symbol.symbol_name}: {e!s}")
            failed += 1

    app_logger.info(f"Derivatives data fetch complete: {successful} successful, {failed} failed")

    return table


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import fetch_symbols

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)

    print("Fetching derivatives data...")
    table = fetch_derivatives_report(symbols, conn)
    print(table)
