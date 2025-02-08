from technical_analysis.repositories.priceRangeRepository import (
    save_price_range_results,
)
from prettytable import PrettyTable
from infra.telegram_logging_handler import app_logger
from typing import List
from source_repository import Symbol
from sharedCode.priceChecker import fetch_current_price


def fetch_range_price(symbols: List[Symbol], conn) -> PrettyTable:
    results = []
    for symbol in symbols:
        try:
            price_data = fetch_current_price(symbol)
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
        high = result.high
        low = result.low
        price_range = ((high - low) / low) * 100
        price_range_percent = f"{price_range:.2f}%"
        range_rows.append((symbol, low, high, price_range_percent))

    for row in range_rows:
        range_table.add_row(row)
    return range_table


if __name__ == "__main__":
    from source_repository import Symbol, SourceID
    from infra.sql_connection import connect_to_sql
    from dotenv import load_dotenv

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
