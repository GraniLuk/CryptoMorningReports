"""15-minute candle data processing and analysis for cryptocurrency markets."""

from datetime import UTC, datetime, timedelta

from shared_code.common_price import Candle
from shared_code.price_checker import (
    fetch_fifteen_min_candle,
    fetch_fifteen_min_candles,
)
from source_repository import Symbol
from technical_analysis.candle_fetcher import CandleFetcher
from technical_analysis.repositories.fifteen_min_candle_repository import (
    FifteenMinCandleRepository,
)
from technical_analysis.rsi_calculator import update_rsi_for_all_candles


def fetch_fifteen_minutes_candles_for_all_symbols(
    symbols: list[Symbol],
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    conn=None,
) -> list[Candle]:
    """Fetches daily candles for given symbols and returns a list of Candle objects.

    Args:
        symbols: List of Symbol objects
        conn: Database connection
        start_date: Start date for fetching candles (defaults to 7 days before end_date)
        end_date: End date for fetching candles (defaults to current date)

    Returns:
        List of Candle objects

    """
    end_time = end_time or datetime.now(UTC)
    start_time = start_time or (end_time - timedelta(days=1))

    all_candles = []
    for symbol in symbols:
        symbol_candles = fetch_fifteen_min_candles(symbol, start_time, end_time, conn)
        all_candles.extend(symbol_candles)

    return all_candles


def calculate_fifteen_min_rsi(symbols: list[Symbol], conn):
    """Calculate RSI for fifteen minute candles for all symbols."""

    def fetch_candles_for_symbol(symbol, conn):
        repository = FifteenMinCandleRepository(conn)
        return repository.get_all_candles(symbol)

    update_rsi_for_all_candles(conn, symbols, fetch_candles_for_symbol, "fifteen_min")


class FifteenMinCandles(CandleFetcher):
    """Class for handling fifteen minute candles."""

    def __init__(self):
        super().__init__("fifteen_min", fetch_fifteen_min_candle, FifteenMinCandleRepository)


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import fetch_symbols

    load_dotenv()
    conn = connect_to_sql()

    symbols = fetch_symbols(conn)
    only_btc = [symbol for symbol in symbols if symbol.symbol_name == "VIRTUAL"]
    end_time = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(hours=1)
    # Test fetching hourly candles
    fetch_fifteen_min_candles(only_btc[0], start_time=start_time, end_time=end_time, conn=conn)
    # Test calculating hourly RSI
    calculate_fifteen_min_rsi(only_btc, conn=conn)
