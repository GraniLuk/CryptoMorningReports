import time
from datetime import datetime, timedelta, timezone

import pandas as pd
from kucoin import Client as KucoinClient

from infra.configuration import get_kucoin_credentials
from infra.telegram_logging_handler import app_logger
from sharedCode.commonPrice import TickerPrice
from source_repository import SourceID, Symbol


def fetch_kucoin_price(symbol: Symbol) -> TickerPrice:
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


def fetch_daily_ranges(
    symbol: str, start_date: str, end_date: str, api_key, api_secret, api_passphrase
):
    """
    Fetches the daily high and low prices for a given symbol within a date range.

    Args:
        symbol (str): Trading pair symbol (e.g., 'BTC-USDT').
        start_date (str): Start date in the format 'YYYY-MM-DD'.
        end_date (str): End date in the format 'YYYY-MM-DD'.

    Returns:
        list of dict: A list containing date, high, and low prices for each day.
    """
    client = KucoinClient(api_key, api_secret, api_passphrase)
    date_ranges = []
    current_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")

    while current_date <= end_date:
        start_time = int(current_date.timestamp() * 1000)
        end_time = int((current_date + timedelta(days=1)).timestamp() * 1000)

        candles = client.get_kline_data(
            symbol, "1day", startAt=start_time // 1000, endAt=end_time // 1000
        )
        if candles:
            # KuCoin returns data in [time, open, close, high, low, volume, turnover] format
            _, _, _, high, low, _, _ = candles[0]
            date_ranges.append(
                {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "high": float(high),
                    "low": float(low),
                }
            )

        current_date += timedelta(days=1)

    return date_ranges


def fetch_kucoin_daily_kline(symbol: str, day: datetime = datetime.now(timezone.utc)):
    """Fetch open, close, high, low prices and volume from KuCoin for the last full day."""
    client = KucoinClient()

    # Get yesterday's date
    end_time = int(day.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    start_time = int(
        (day - timedelta(days=1))
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .timestamp()
    )

    try:
        # Fetch 1-day Kline (candlestick) data
        klines = client.get_kline_data(
            symbol,
            kline_type="1day",  # 1-day interval
            start=start_time,
            end=end_time,
        )

        if not klines:
            app_logger.error(f"No Kline data found for {symbol}")
            return None

        # KuCoin Kline format: [time, open, close, high, low, volume, turnover]
        open_price = float(klines[0][1])
        close_price = float(klines[0][2])
        high_price = float(klines[0][3])
        low_price = float(klines[0][4])
        volume = float(klines[0][5])
        quote_asset_volume = float(klines[0][6])  # Turnover in quote asset

        return (
            open_price,
            close_price,
            high_price,
            low_price,
            volume,
            quote_asset_volume,
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
        start_time = int((datetime.now() - timedelta(days=limit)).timestamp())

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


if __name__ == "__main__":
    symbol = "KCS-USDT"  # Specify the trading pair
    start_date = "2025-01-11"  # Start date (YYYY-MM-DD)
    end_date = "2025-01-14"  # End date (YYYY-MM-DD)
    kucoin_credentials = get_kucoin_credentials()
    (kucoin_credentials["api_key"],)
    (kucoin_credentials["api_secret"],)
    kucoin_credentials["api_passphrase"]

    daily_ranges = fetch_daily_ranges(symbol, start_date, end_date)
    for day_range in daily_ranges:
        print(
            f"Date: {day_range['date']}, High: {day_range['high']}, Low: {day_range['low']}"
        )
