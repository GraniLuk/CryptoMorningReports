from datetime import datetime, timedelta, timezone
from typing import List, Optional

from infra.telegram_logging_handler import app_logger
from sharedCode.commonPrice import Candle
from sharedCode.priceChecker import fetch_hourly_candle, fetch_hourly_candles
from source_repository import Symbol
from technical_analysis.candle_fetcher import CandleFetcher
from technical_analysis.repositories.hourly_candle_repository import (
    HourlyCandleRepository,
)
from technical_analysis.rsi_calculator import update_rsi_for_all_candles


def calculate_hourly_rsi(symbols: List[Symbol], conn):
    """Calculate RSI for hourly candles for all symbols"""

    def fetch_candles_for_symbol(symbol, conn):
        repository = HourlyCandleRepository(conn)
        return repository.get_all_candles(symbol)

    update_rsi_for_all_candles(conn, symbols, fetch_candles_for_symbol, "hourly")


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


def fetch_candles(
    symbols: List[Symbol],
    conn,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
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
    end_date = end_date or datetime.now(timezone.utc)
    start_date = start_date or (end_date - timedelta(days=1))

    all_candles = []
    for symbol in symbols:
        symbol_candles = fetch_hourly_candles(symbol, start_date, end_date, conn)
        all_candles.extend(symbol_candles)

    return all_candles


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

    # Test fetching hourly candles
    fetch_hourly_candles(only_btc[0], conn=conn)
    # Test calculating hourly RSI
    calculate_hourly_rsi(only_btc, conn=conn)
