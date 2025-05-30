import time
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pandas as pd
from kucoin import Client as KucoinClient

from infra.configuration import get_kucoin_credentials
from infra.telegram_logging_handler import app_logger
from sharedCode.commonPrice import Candle, TickerPrice
from source_repository import SourceID, Symbol


def fetch_kucoin_price(symbol: Symbol) -> Optional[TickerPrice]:
    """Fetch price data from Kucoin exchange."""
    # Initialize the client
    kucoin_credentials = get_kucoin_credentials()
    api_key = kucoin_credentials["api_key"]
    api_secret = kucoin_credentials["api_secret"]
    api_passphrase = kucoin_credentials["api_passphrase"]
    client = KucoinClient(api_key, api_secret, api_passphrase)
    try:
        # Get 24hr stats
        ticker = client.get_24hr_stats(symbol.kucoin_name)

        return TickerPrice(
            source=SourceID.KUCOIN,
            symbol=symbol.symbol_name,
            low=float(ticker["low"]),
            high=float(ticker["high"]),
            last=float(ticker["last"]),
            volume=float(ticker["vol"]),
            volume_quote=float(ticker["volValue"]),
        )
    except Exception as e:
        app_logger.error(f"Kucoin error for {symbol}: {str(e)}")
        return None


def fetch_kucoin_daily_kline(symbol: Symbol, end_date: date = date.today()) -> Optional[Candle]:
    """Fetch open, close, high, low prices and volume from KuCoin for the last full day."""
    client = KucoinClient()

    start_time = end_date - timedelta(days=1)
    # Get yesterday's date
    end_time_as_int = int(datetime.combine(end_date, datetime.min.time()).timestamp())
    start_time_as_int = int(
        datetime.combine(start_time, datetime.min.time()).timestamp()
    )

    try:
        # Fetch 1-day Kline (candlestick) data
        klines = client.get_kline_data(
            symbol.kucoin_name,
            kline_type="1day",  # 1-day interval
            start=start_time_as_int,
            end=end_time_as_int,
        )

        if not klines:
            app_logger.error(f"No Kline data found for {symbol}")
            return None

        return Candle(
            end_date=end_date,
            source=SourceID.KUCOIN.value,
            open=float(klines[0][1]),
            close=float(klines[0][2]),
            symbol=symbol.symbol_name,
            low=float(klines[0][4]),
            high=float(klines[0][3]),
            last=float(klines[0][2]),
            volume=float(klines[0][5]),
            volume_quote=float(klines[0][6]),
            id=symbol.symbol_id,
        )

    except Exception as e:
        app_logger.error(
            f"Unexpected error when fetching Kucoin daily kline for {symbol}: {str(e)}"
        )
        return None


def fetch_close_prices_from_Kucoin(symbol: str, limit: int = 14) -> pd.DataFrame:
    try:
        # Initialize Kucoin client
        kucoin_credentials = get_kucoin_credentials()
        api_key = kucoin_credentials["api_key"]
        api_secret = kucoin_credentials["api_secret"]
        api_passphrase = kucoin_credentials["api_passphrase"]
        client = KucoinClient(api_key, api_secret, api_passphrase)

        # Calculate start time (limit days ago)
        end_time = int(time.time())
        start_time = int(
            (datetime.now(timezone.utc) - timedelta(days=limit)).timestamp()
        )

        # Get kline data with start and end time
        klines = client.get_kline_data(symbol, "1day", start=start_time, end=end_time)

        # Kucoin returns data in format:
        # [timestamp, open, close, high, low, volume, turnover]
        df = pd.DataFrame(
            klines,
            columns=["timestamp", "open", "close", "high", "low", "volume", "turnover"],
        )

        # Convert timestamp strings to numeric first, then to datetime
        df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="s")
        # df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        # Convert string values to float
        df["close"] = pd.to_numeric(df["close"], errors="coerce")

        # Sort by timestamp ascending first
        df = df.sort_values("timestamp", ascending=True)

        # Set timestamp as index after sorting
        df.set_index("timestamp", inplace=True)

        return df

    except Exception as e:
        app_logger.error(f"Error fetching data from Kucoin: {str(e)}")
        return pd.DataFrame()


# Adding hourly and fifteen-minute candle fetching functions


def fetch_kucoin_hourly_kline(symbol: Symbol, end_time: datetime) -> Optional[Candle]:
    """
    Fetch open, close, high, low prices and volume from KuCoin for the specified hour.

    Args:
        symbol: Symbol object with kucoin_name property
        end_time: End time for the candle period (defaults to current hour)

    Returns:
        Candle object if successful, None otherwise
    """
    client = KucoinClient()
    # Handle end_time parameter
    if end_time is None:
        # Get the current time in UTC
        current_time = datetime.now(timezone.utc)
        # Round down to the previous full hour
        end_time = current_time.replace(minute=0, second=0, microsecond=0)
    elif end_time.tzinfo is None:
        # Convert naive datetime to timezone-aware
        end_time = end_time.replace(tzinfo=timezone.utc)

    # Start time is 1 hour before end time
    start_time = end_time - timedelta(hours=1)

    # Convert to Unix timestamps (seconds)
    end_time_as_int = int(end_time.timestamp())
    start_time_as_int = int(start_time.timestamp())

    try:
        # Fetch 1-hour Kline data
        klines = client.get_kline_data(
            symbol.kucoin_name,
            kline_type="1hour",
            start=start_time_as_int,
            end=end_time_as_int,
        )

        if not klines:
            app_logger.error(f"No hourly Kline data found for {symbol.symbol_name}")
            return None

        return Candle(
            end_date=end_time,
            source=SourceID.KUCOIN.value,
            open=float(klines[0][1]),
            close=float(klines[0][2]),
            symbol=symbol.symbol_name,
            high=float(klines[0][3]),
            low=float(klines[0][4]),
            last=float(klines[0][2]),  # Using close as last
            volume=float(klines[0][5]),
            volume_quote=float(klines[0][6]),
            id=symbol.symbol_id,
        )

    except Exception as e:
        app_logger.error(
            f"Error fetching hourly data for {symbol.symbol_name}: {str(e)}"
        )
        return None


def fetch_kucoin_fifteen_min_kline(symbol: Symbol, end_time: datetime) -> Optional[Candle]:
    """
    Fetch open, close, high, low prices and volume from KuCoin for the specified 15-minute interval.

    Args:
        symbol: Symbol object with kucoin_name property
        end_time: End time for the candle period (defaults to current 15-minute interval)

    Returns:
        Candle object if successful, None otherwise
    """
    client = KucoinClient()

    if end_time.tzinfo is None:
        # Convert naive datetime to timezone-aware
        end_time = end_time.replace(tzinfo=timezone.utc)

    # Start time is 15 minutes before end time
    start_time = end_time - timedelta(minutes=15)

    # Convert to Unix timestamps (seconds)
    end_time_as_int = int(end_time.timestamp())
    start_time_as_int = int(start_time.timestamp())

    try:
        # Fetch 15-minute Kline data
        klines = client.get_kline_data(
            symbol.kucoin_name,
            kline_type="15min",
            start=start_time_as_int,
            end=end_time_as_int,
        )

        if not klines:
            app_logger.error(f"No 15-minute Kline data found for {symbol.symbol_name}")
            return None

        return Candle(
            end_date=end_time,
            source=SourceID.KUCOIN.value,
            open=float(klines[0][1]),
            close=float(klines[0][2]),
            symbol=symbol.symbol_name,
            high=float(klines[0][3]),
            low=float(klines[0][4]),
            last=float(klines[0][2]),  # Using close as last
            volume=float(klines[0][5]),
            volume_quote=float(klines[0][6]),
            id=symbol.symbol_id,
        )

    except Exception as e:
        app_logger.error(
            f"Error fetching 15-minute data for {symbol.symbol_name}: {str(e)}"
        )
        return None


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import fetch_symbols

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)
    symbol = [symbol for symbol in symbols if symbol.symbol_name == "VIRTUAL"][0]
    start_date = "2025-01-11"  # Start date (YYYY-MM-DD)
    end_date = datetime.now(timezone.utc)
    end_date = end_date.replace(minute=0, second=0, microsecond=0)  # End date (YYYY-MM-DD)

    hourly_candle = fetch_kucoin_hourly_kline(symbol, end_time=end_date)
    if hourly_candle:
        # Print the fetched hourly candle data
        print(
            f"Date: {hourly_candle.end_date}, High: {hourly_candle.high}, Low: {hourly_candle.low}, "
            f"Open: {hourly_candle.open}, Close: {hourly_candle.close}, Volume: {hourly_candle.volume}"
        )
    else:
        print("Failed to fetch hourly candle data.")    