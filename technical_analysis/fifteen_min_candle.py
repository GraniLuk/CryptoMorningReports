from typing import List

from infra.telegram_logging_handler import app_logger
from source_repository import Symbol
from technical_analysis.candle_fetcher import CandleFetcher
from technical_analysis.repositories.fifteen_min_candle_repository import (
    FifteenMinCandleRepository,
)
from technical_analysis.rsi_calculator import update_rsi_for_all_candles


def fetch_fifteen_min_candles(symbols: List[Symbol], conn):
    """Fetches fifteen minute candles for all symbols"""
    fetcher = FifteenMinCandles()
    all_candles = {}

    for symbol in symbols:
        try:
            app_logger.info(f"Fetching fifteen minute candles for {symbol.symbol_name}")
            candles = fetcher.get_candles_for_symbol(symbol, conn)
            all_candles[symbol.symbol_name] = candles
        except Exception as e:
            app_logger.error(
                f"Error fetching fifteen minute candles for {symbol.symbol_name}: {str(e)}"
            )

    return all_candles


def calculate_fifteen_min_rsi(symbols: List[Symbol], conn):
    """Calculate RSI for fifteen minute candles for all symbols"""

    def fetch_candles_for_symbol(symbol, conn):
        repository = FifteenMinCandleRepository(conn)
        return repository.get_all_candles(symbol)

    update_rsi_for_all_candles(conn, symbols, fetch_candles_for_symbol, "fifteen_min")


class FifteenMinCandles(CandleFetcher):
    """Class for handling fifteen minute candles"""

    def __init__(self):
        from sharedCode.priceChecker import fetch_fifteen_min_candle

        super().__init__(
            "fifteen_min", fetch_fifteen_min_candle, FifteenMinCandleRepository
        )


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import fetch_symbols

    load_dotenv()
    conn = connect_to_sql()

    symbols = fetch_symbols(conn)
    symbols = [symbol for symbol in symbols if symbol.symbol_name == "VIRTUAL"]
    # Test fetching fifteen minute candles
    fetch_fifteen_min_candles(symbols, conn)
    # Test calculating fifteen minute RSI
    calculate_fifteen_min_rsi(symbols, conn)
