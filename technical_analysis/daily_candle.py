from datetime import date, timedelta
from typing import List

from sharedCode.commonPrice import Candle
from sharedCode.priceChecker import fetch_daily_candle
from source_repository import Symbol
from technical_analysis.repositories.daily_candle_repository import (
    DailyCandleRepository,
)


def fetch_daily_candles(
    symbols: List[Symbol], conn, end_date: date = None
) -> List[Candle]:
    """
    Fetches daily candles for given symbols and returns a list of Candle objects
    """
    end_date = end_date or date.today()

    candles = []
    for symbol in symbols:
        candle = fetch_daily_candle(symbol, end_date, conn)
        if candle is not None:
            candles.append(candle)

    return candles


def fetch_old_daily_candles(symbols, conn):
    repo = DailyCandleRepository(conn)
    oldest_date = repo.get_min_candle_date()
    if oldest_date:
        print(f"Oldest candle date: {oldest_date}")
    current_date = oldest_date - timedelta(days=1)
    end_date = current_date - timedelta(days=31)
    while current_date >= end_date:
        print(f"Fetching data for {current_date}")
        fetch_daily_candles(symbols, conn, current_date)
        # Process your candles here
        current_date -= timedelta(days=1)


if __name__ == "__main__":
    import time  # Add this import at the top

    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import Symbol, fetch_symbols

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)
    filtered_symbols = [symbol for symbol in symbols if symbol.symbol_name not in ["TON", "VIRTUAL","DYM","OSMO","AKT","NEXO"]]
    for symbols in filtered_symbols:
        print(symbols.symbol_name)
    # Define start and end dates for January 2025
    start_date = date(2024, 10, 1)
    end_date = date(2024, 10, 31)

    # Loop through each day
    current_date = start_date
    fetch_old_daily_candles(filtered_symbols, conn)
