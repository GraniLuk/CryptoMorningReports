from prettytable import PrettyTable
from infra.telegram_logging_handler import app_logger
from typing import List
from source_repository import Symbol
from sharedCode.priceChecker import fetch_close_prices


def fetch_price_change_report(symbols: List[Symbol]) -> PrettyTable:
    table = PrettyTable()
    table.field_names = ["Symbol", "24h Change %", "7d Change %"]
    table.align = "r"  # Right align all columns
    table.float_format = ".2"  # Show 2 decimal places for float values

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

                # Add row to table with color formatting based on change direction
                day_change_str = f"{'+' if day_change >= 0 else ''}{day_change:.2f}"
                week_change_str = f"{'+' if week_change >= 0 else ''}{week_change:.2f}"

                table.add_row([symbol.symbol_name, day_change_str, week_change_str])
        except Exception as e:
            app_logger.error(
                f"Unexpected error when processing 24change report for {symbol.symbol_name}: {str(e)}"
            )

    # Sort table by 24h change in descending order
    table.sortby = "24h Change %"
    table.reversesort = True

    return table


if __name__ == "__main__":
    from source_repository import Symbol, SourceID

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
