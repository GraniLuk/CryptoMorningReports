import os
from datetime import date, datetime, timedelta
from typing import List

from infra.telegram_logging_handler import app_logger
from sharedCode.binance import BinanceClient
from sharedCode.priceChecker import fetch_hourly_candle
from source_repository import Symbol
from technical_analysis.candle_fetcher import CandleFetcher
from technical_analysis.repositories.hourly_candle_repository import (
    HourlyCandleRepository,
)
from technical_analysis.rsi_calculator import update_rsi_for_all_candles


def get_hourly_candle_class():
    """
    This class must have fields that match those in the DB: SymbolID, EndDate, Open, High, Low, Close, Volume
    """

    class HourlyCandle:
        def __init__(self, candle, symbol_id, id=None):
            self.id = id
            self.end_date = datetime.fromtimestamp(candle[0] / 1000)
            self.open = float(candle[1])
            self.high = float(candle[2])
            self.low = float(candle[3])
            self.close = float(candle[4])
            self.volume = float(candle[5])
            self.symbol_id = symbol_id

    return HourlyCandle


def fetch_hourly_candles(
    symbols: List[Symbol], conn, start_date: date = None, end_date: date = None
):
    """Fetches hourly candles for the specified symbols and date range"""
    if not start_date:
        start_date = datetime.now().date() - timedelta(days=1)  # Default to 1 day back
    if not end_date:
        end_date = datetime.now().date()

    repository = HourlyCandleRepository(conn)
    apiKey = os.environ.get("BINANCE_KEY", "")
    apiSecret = os.environ.get("BINANCE_SECRET", "")
    client = BinanceClient(apiKey, apiSecret)

    all_candles = {}

    for symbol in symbols:
        try:
            app_logger.info(
                f"Fetching hourly candles for {symbol.symbol_name} from {start_date} to {end_date}"
            )

            start_date_ts = (
                datetime.combine(start_date, datetime.min.time()).timestamp() * 1000
            )
            end_date_ts = (
                datetime.combine(end_date, datetime.max.time()).timestamp() * 1000
            )

            # Fetch hourly candles from Binance
            candles = client.get_klines(
                symbol=symbol.symbol_name, interval="1h", limit=1000
            )
            app_logger.info(f"Fetched {len(candles)} hourly candles from Binance")

            HourlyCandle = get_hourly_candle_class()
            hourly_candles = []

            for candle in candles:
                # Filter only candles within the date range
                candle_ts = candle[0]
                if candle_ts >= start_date_ts and candle_ts <= end_date_ts:
                    hourly_candle = HourlyCandle(candle, symbol.symbol_id)
                    hourly_candles.append(hourly_candle)

            # Save to database
            candle_ids = repository.save_candles(hourly_candles)

            # Associate candle IDs with the candles
            for i, candle_id in enumerate(candle_ids):
                if i < len(hourly_candles):
                    hourly_candles[i].id = candle_id

            # Store candles for the symbol
            all_candles[symbol.symbol_name] = hourly_candles

        except Exception as e:
            app_logger.error(
                f"Error fetching hourly candles for {symbol.symbol_name}: {str(e)}"
            )

    return all_candles


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
    fetch_hourly_candles(only_btc, conn)
    # Test calculating hourly RSI
    calculate_hourly_rsi(only_btc, conn)
