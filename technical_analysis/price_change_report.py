from typing import List

from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from sharedCode.priceChecker import fetch_close_prices
from source_repository import Symbol


def fetch_price_change_report(symbols: List[Symbol]) -> PrettyTable:
    table = PrettyTable()
    table.field_names = ["Symbol", "24h Change %", "7d Change %"]
    table.align = "r"  # Right align all columns
    table.float_format = ".2"  # Show 2 decimal places for float values

    # Create a list to store rows with their sorting values
    rows_with_sort_values = []

    for symbol in symbols:
        try:
            df = fetch_close_prices(symbol, 7)
            if len(df) >= 7:  # Ensure we have enough data
                current_price = df["close"].iloc[-1]
                day_ago_price = df["close"].iloc[-2]
                week_ago_price = df["close"].iloc[0]

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
                    )
                )
        except Exception as e:
            app_logger.error(
                f"Unexpected error when processing 24change report for {symbol.symbol_name}: {str(e)}"
            )

    # Sort rows based on the day_change value
    rows_with_sort_values.sort(key=lambda x: x[1], reverse=True)

    # Add sorted rows to the table
    for row, _ in rows_with_sort_values:
        table.add_row(row)

    return table


if __name__ == "__main__":
    from source_repository import SourceID, Symbol

    symbols = [
        Symbol(
            symbol_id=1,
            symbol_name="BTC",
            full_name="Bitcoin",
            source_id=SourceID.BINANCE,
        ),
        Symbol(
            symbol_id=2,
            symbol_name="ETH",
            full_name="Ethereum",
            source_id=SourceID.BINANCE,
        ),
    ]

    table = fetch_price_change_report(symbols)
    print(table)
