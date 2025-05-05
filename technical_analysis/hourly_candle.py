from datetime import datetime, timedelta
from typing import List, Optional

from sharedCode.commonPrice import Candle
from sharedCode.priceChecker import fetch_hourly_candle
from sharedCode.priceChecker import (
    fetch_hourly_candles as fetch_hourly_candles_for_symbol,
)
from source_repository import Symbol
from technical_analysis.candle_fetcher import CandleFetcher
from technical_analysis.repositories.hourly_candle_repository import (
    HourlyCandleRepository,
)


def fetch_hourly_candles(
    symbols: List[Symbol],
    conn,
    end_time: Optional[datetime] = None,
    start_time: Optional[datetime] = None,
) -> List[Candle]:
    """
    Fetches hourly candles for given symbols and returns a list of Candle objects

    Args:
        symbols: List of Symbol objects
        conn: Database connection
        end_time: End time for fetching candles (defaults to current time)
        start_time: Start time for fetching candles (defaults to 24 hours before end_time)

    Returns:
        List of Candle objects
    """
    end_time = end_time or datetime.now()
    start_time = start_time or (end_time - timedelta(hours=24))

    all_candles = []
    for symbol in symbols:
        symbol_candles = fetch_hourly_candles_for_symbol(
            symbol, start_time, end_time, conn
        )
        all_candles.extend(symbol_candles)

    return all_candles


def check_if_all_hourly_candles(symbol, conn, days_back: int = 7):
    """
    Checks if all hourly candles for the symbol are available in the database for the past days,
    fetches missing ones from API

    Args:
        symbol: Symbol object
        conn: Database connection
        days_back: Number of days to look back (default: 7)
    """
    fetcher = HourlyCandles()
    fetcher.check_if_all_candles(symbol, conn, days_back)


class HourlyCandles(CandleFetcher):
    """Class for handling hourly candles"""

    def __init__(self):
        super().__init__("hourly", fetch_hourly_candle, HourlyCandleRepository)


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import fetch_symbols

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)
    only_btc = [symbol for symbol in symbols if symbol.symbol_name == "VIRTUAL"]

    # Check and fetch hourly candles for BTC for the last 3 days
    for symbol in only_btc:
        check_if_all_hourly_candles(symbol, conn, days_back=3)
