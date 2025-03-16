from typing import List

from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from sharedCode.numberFormat import format_to_6digits_withoutTrailingZeros
from sharedCode.priceChecker import fetch_daily_candle
from source_repository import Symbol
from technical_analysis.repositories.priceRangeRepository import (
    save_price_range_results,
)


def fetch_range_price(symbols: List[Symbol], conn) -> PrettyTable:
    results = []
    for symbol in symbols:
        try:
            price_data = fetch_daily_candle(symbol, conn=conn)
            if price_data:
                results.append(price_data)

            # Save to database if connection is available
            if conn and price_data:
                try:
                    price_range_percent = (
                        (price_data.high - price_data.low) / price_data.low
                    ) * 100
                    save_price_range_results(
                        conn=conn,
                        symbol_id=symbol.symbol_id,
                        low_price=price_data.low,
                        high_price=price_data.high,
                        range_percent=price_range_percent,
                    )
                except Exception as e:
                    app_logger.error(
                        f"Failed to save price range results for {symbol.symbol_name}: {str(e)}"
                    )

        except Exception as e:
            app_logger.error(f"Unexpected error for {symbol.symbol_name}: {str(e)}")

    range_table = PrettyTable()
    range_table.field_names = ["Symbol", "24h Low", "24h High", "Range %"]

    # Sort by price range descending
    sorted_results = sorted(
        results, key=lambda x: ((x.high - x.low) / x.low) * 100, reverse=True
    )
    # Store rows with range calculation
    range_rows = []
    for result in sorted_results:
        symbol = result.symbol
        high = format_to_6digits_withoutTrailingZeros(result.high)
        low = format_to_6digits_withoutTrailingZeros(result.low)
        price_range = ((result.high - result.low) / result.low) * 100
        price_range_percent = f"{price_range:.2f}%"
        range_rows.append((symbol, low, high, price_range_percent))

    for row in range_rows:
        range_table.add_row(row)
    return range_table


if __name__ == "__main__":
    from dotenv import load_dotenv

    from source_repository import SourceID, Symbol

    load_dotenv()
    conn = None
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

    table = fetch_range_price(symbols, conn)
    print(table)
