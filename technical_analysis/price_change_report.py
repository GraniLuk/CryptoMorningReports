"""Price change analysis and reporting for cryptocurrency markets."""

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from shared_code.price_checker import fetch_daily_candles
from source_repository import Symbol, fetch_symbols


if TYPE_CHECKING:
    import pyodbc

    from infra.sql_connection import SQLiteConnectionWrapper


def fetch_price_change_report(
    symbols: list[Symbol],
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None",
    target_date: date,
) -> PrettyTable:
    """Fetch and generate a price change report showing 24h and 7d changes."""
    target_date = target_date or datetime.now(UTC).date()
    start_date = target_date - timedelta(days=7)  # Get 7 days of data

    table = PrettyTable()
    table.field_names = ["Symbol", "24h Change %", "7d Change %"]
    table.align = "r"  # Right align all columns
    table.float_format = ".2"  # Show 2 decimal places for float values

    # Create a list to store rows with their sorting values
    rows_with_sort_values = []

    min_candles_for_calculation = 7
    for symbol in symbols:
        try:
            candles = fetch_daily_candles(symbol, start_date, target_date, conn)
            if len(candles) >= min_candles_for_calculation:  # Ensure we have enough data
                # Convert candles to list of closing prices
                closes = [candle.close for candle in candles]

                current_price = closes[-1]
                day_ago_price = closes[-2]
                week_ago_price = closes[0]

                # Calculate percentage changes
                day_change = ((current_price - day_ago_price) / day_ago_price) * 100
                week_change = ((current_price - week_ago_price) / week_ago_price) * 100

                # Format strings for display
                day_change_str = f"{'+' if day_change >= 0 else ''}{day_change:.2f}"
                week_change_str = f"{'+' if week_change >= 0 else ''}{week_change:.2f}"

                # Store both the display row and the sorting value
                rows_with_sort_values.append(
                    (
                        [symbol.symbol_name, day_change_str, week_change_str],
                        day_change,  # This will be used for sorting
                    ),
                )
        except (KeyError, ValueError, TypeError, IndexError) as e:
            app_logger.error(
                f"Unexpected error when processing 24change report for {symbol.symbol_name}: {e!s}",
            )

    # Sort rows based on the day_change value
    rows_with_sort_values.sort(key=lambda x: x[1], reverse=True)

    # Add sorted rows to the table
    for row, _ in rows_with_sort_values:
        table.add_row(row)

    return table


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import Symbol

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)

    table = fetch_price_change_report(symbols, conn, target_date=datetime.now(UTC).date())
