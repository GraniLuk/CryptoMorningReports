from datetime import date, timedelta
from typing import List, Optional

from sharedCode.commonPrice import Candle
from sharedCode.priceChecker import fetch_daily_candle
from sharedCode.priceChecker import (
    fetch_daily_candles as fetch_daily_candles_for_symbol,
)
from source_repository import Symbol
from technical_analysis.repositories.daily_candle_repository import (
    DailyCandleRepository,
)


def fetch_daily_candles(
    symbols: List[Symbol],
    conn,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[Candle]:
    """
    Fetches daily candles for given symbols and returns a list of Candle objects

    Args:
        symbols: List of Symbol objects
        conn: Database connection
        start_date: Start date for fetching candles (defaults to 7 days before end_date)
        end_date: End date for fetching candles (defaults to current date)

    Returns:
        List of Candle objects
    """
    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=7))

    all_candles = []
    for symbol in symbols:
        symbol_candles = fetch_daily_candles_for_symbol(
            symbol, start_date, end_date, conn
        )
        all_candles.extend(symbol_candles)

    return all_candles


def check_if_all_candles(symbol, conn):
    repo = DailyCandleRepository(conn)
    all_candles = repo.get_all_candles(symbol)
    oldest_date = all_candles[0].end_date if all_candles else date(2017, 1, 1)
    if oldest_date:
        print(f"Oldest candle date: {oldest_date}")
    end_date = date.today()
    current_date = oldest_date
    while current_date <= end_date:
        print(f"Fetching data for {current_date}")
        from_db = next(
            (item for item in all_candles if item.end_date == current_date), None
        )
        if from_db is None:
            fetch_daily_candle(symbol, current_date, conn)
            print("Fetched from API")
        # Process your candles here
        current_date += timedelta(days=1)


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import Symbol, fetch_symbols

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)
    # Define start and end dates for January 2025
    for symbol in symbols:
        print(f"Checking candles for {symbol}")
        check_if_all_candles(symbol, conn)
