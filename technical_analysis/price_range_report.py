"""Price range analysis and reporting for cryptocurrency markets."""

from datetime import UTC, datetime, timedelta

from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from shared_code.number_format import format_to_6digits_without_trailing_zeros
from shared_code.price_checker import fetch_hourly_candles
from source_repository import Symbol
from technical_analysis.repositories.priceRangeRepository import (
    save_price_range_results,
)


def fetch_range_price(symbols: list[Symbol], conn) -> PrettyTable:
    """Calculate 24-hour price range using hourly candles.

    Fetches hourly candles for the last 24 hours. If hourly data is missing from the database,
    it will automatically fetch from the exchange API (Binance/KuCoin).
    """
    results = []

    # Calculate 24 hours ago from now
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=24)

    for symbol in symbols:
        try:
            if not conn:
                app_logger.warning(f"No database connection, skipping {symbol.symbol_name}")
                continue

            # Fetch hourly candles for the last 24 hours
            # This will fetch from DB if available, or from API if missing
            candles = fetch_hourly_candles(symbol, start_time, end_time, conn)

            if not candles:
                app_logger.warning(f"No hourly candles found for {symbol.symbol_name}")
                continue

            # Calculate high and low from all hourly candles in the 24-hour period
            high_price = max(float(c.high) for c in candles)
            low_price = min(float(c.low) for c in candles)

            # Create a result object with symbol name and price range
            price_data = type(
                "PriceRange",
                (),
                {"symbol": symbol.symbol_name, "high": high_price, "low": low_price},
            )()

            results.append(price_data)

            # Save to database
            try:
                price_range_percent = ((high_price - low_price) / low_price) * 100
                save_price_range_results(
                    conn=conn,
                    symbol_id=symbol.symbol_id,
                    low_price=low_price,
                    high_price=high_price,
                    range_percent=price_range_percent,
                )
            except Exception as e:
                app_logger.error(
                    f"Failed to save price range results for {symbol.symbol_name}: {e!s}"
                )

        except Exception as e:
            app_logger.error(f"Unexpected error for {symbol.symbol_name}: {e!s}")

    range_table = PrettyTable()
    range_table.field_names = ["Symbol", "24h Low", "24h High", "Range %"]

    # Sort by price range descending
    sorted_results = sorted(results, key=lambda x: ((x.high - x.low) / x.low) * 100, reverse=True)
    # Store rows with range calculation
    range_rows = []
    for result in sorted_results:
        symbol_name = result.symbol
        high = format_to_6digits_without_trailing_zeros(result.high)
        low = format_to_6digits_without_trailing_zeros(result.low)
        price_range = ((result.high - result.low) / result.low) * 100
        price_range_percent = f"{price_range:.2f}%"
        range_rows.append((symbol_name, low, high, price_range_percent))

    for row in range_rows:
        range_table.add_row(row)
    return range_table


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import fetch_symbols

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)

    table = fetch_range_price(symbols, conn)
    print(table)
