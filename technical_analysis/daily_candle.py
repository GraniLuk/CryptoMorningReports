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
    from source_repository import SourceID, Symbol, fetch_symbols

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)
    only_link = [symbol for symbol in symbols if symbol.symbol_name == "LINK"]
    # Define start and end dates for January 2025
    for symbol in only_link:
        check_if_all_candles(symbol, conn)
