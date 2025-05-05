from datetime import date, datetime, timedelta, timezone

import pandas as pd
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException

from infra.telegram_logging_handler import app_logger
from sharedCode.commonPrice import Candle, TickerPrice
from source_repository import SourceID, Symbol


def fetch_binance_price(symbol: Symbol) -> TickerPrice:
    """Fetch price data from Binance exchange."""
    # Initialize the client
    client = BinanceClient()
    try:
        # Get 24hr stats
        ticker = client.get_ticker(symbol=symbol.binance_name)
        return TickerPrice(
            source=SourceID.BINANCE,
            symbol=symbol.symbol_name,
            low=float(ticker["lowPrice"]),
            high=float(ticker["highPrice"]),
            last=float(ticker["lastPrice"]),
            volume=float(ticker["volume"]),
            volume_quote=float(ticker.get("quoteVolume", 0)),
        )
    except BinanceAPIException as e:
        app_logger.error(f"Error fetching {symbol}: {e.message}")
        return None
    except Exception as e:
        app_logger.error(f"Unexpected error for {symbol}: {str(e)}")
        return None


def fetch_close_prices_from_Binance(
    symbol: str, lookback_days: int = 14
) -> pd.DataFrame:
    client = BinanceClient()

    try:
        start_time = datetime.now() - timedelta(days=lookback_days)

        klines = client.get_historical_klines(
            symbol=symbol,
            interval=BinanceClient.KLINE_INTERVAL_1DAY,
            start_str=start_time.strftime("%d %b %Y"),
            limit=lookback_days,
        )

        # Create DataFrame with numeric types
        df = pd.DataFrame(
            klines,
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_volume",
                "trades",
                "taker_buy_base",
                "taker_buy_quote",
                "ignore",
            ],
        )

        # Convert price columns to float
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        return df

    except BinanceAPIException as e:
        app_logger.error(f"Error fetching data for {symbol}: {e.message}")
        return pd.DataFrame()
    except Exception as e:
        app_logger.error(f"Unexpected error for {symbol}: {str(e)}")
        return pd.DataFrame()


def fetch_binance_daily_kline(symbol: Symbol, end_date: date = date.today()) -> Candle:
    """Fetch open and close prices from Binance for the last full day."""
    client = BinanceClient()

    # Get yesterday's date
    end_date_timestamp = datetime.combine(end_date, datetime.min.time()).timestamp()
    start_date_timestamp = datetime.combine(
        end_date - timedelta(days=1), datetime.min.time()
    ).timestamp()

    try:
        # Fetch 1-day Kline (candlestick) data
        klines = client.get_klines(
            symbol=symbol.binance_name,
            interval=client.KLINE_INTERVAL_1DAY,
            startTime=int(start_date_timestamp * 1000),
            endTime=int(end_date_timestamp * 1000),
        )

        if not klines:
            app_logger.error(f"No Kline data found for {symbol}")
            return None

        return Candle(
            end_date=end_date,
            source=SourceID.BINANCE,
            open=float(klines[0][1]),
            close=float(klines[0][4]),
            symbol=symbol.symbol_name,
            low=float(klines[0][3]),
            high=float(klines[0][2]),
            last=float(klines[0][4]),
            volume=float(klines[0][5]),
            volume_quote=float(klines[0][7]),
        )

    except BinanceAPIException as e:
        app_logger.error(f"Error fetching {symbol}: {e.message}")
        return None
    except Exception as e:
        app_logger.error(f"Unexpected error for {symbol}: {str(e)}")
        return None


# Adding hourly and fifteen-minute candle fetching functions


def fetch_binance_hourly_kline(symbol: Symbol, end_time: datetime = None) -> Candle:
    """
    Fetch open, close, high, low prices and volume from Binance for the specified hour.

    Args:
        symbol: Symbol object with binance_name property
        end_time: End time for the candle period (defaults to current hour)

    Returns:
        Candle object if successful, None otherwise
    """
    client = BinanceClient()
    end_time = end_time or datetime.now().replace(minute=0, second=0, microsecond=0)

    # Start time is 1 hour before end time
    start_time = end_time - timedelta(hours=1)

    # Convert to milliseconds for Binance API
    start_timestamp_ms = int(start_time.timestamp() * 1000)
    end_timestamp_ms = int(end_time.timestamp() * 1000)

    try:
        # Fetch 1-hour Kline data
        klines = client.get_klines(
            symbol=symbol.binance_name,
            interval=client.KLINE_INTERVAL_1HOUR,
            startTime=start_timestamp_ms,
            endTime=end_timestamp_ms,
            limit=1,
        )

        if not klines:
            app_logger.error(f"No hourly Kline data found for {symbol.symbol_name}")
            return None

        return Candle(
            end_date=end_time,
            source=SourceID.BINANCE,
            open=float(klines[0][1]),
            close=float(klines[0][4]),
            symbol=symbol.symbol_name,
            low=float(klines[0][3]),
            high=float(klines[0][2]),
            last=float(klines[0][4]),
            volume=float(klines[0][5]),
            volume_quote=float(klines[0][7]),
        )

    except BinanceAPIException as e:
        app_logger.error(
            f"Error fetching hourly data for {symbol.symbol_name}: {e.message}"
        )
        return None
    except Exception as e:
        app_logger.error(
            f"Unexpected error for {symbol.symbol_name} hourly data: {str(e)}"
        )
        return None


def fetch_binance_fifteen_min_kline(
    symbol: Symbol, end_time: datetime = None
) -> Candle:
    """
    Fetch open, close, high, low prices and volume from Binance for the specified 15-minute interval.

    Args:
        symbol: Symbol object with binance_name property
        end_time: End time for the candle period (defaults to current 15-minute interval)

    Returns:
        Candle object if successful, None otherwise
    """
    client = BinanceClient()

    if end_time is None:
        end_time = datetime.now()
        # Round to nearest 15 minutes
        minutes = (end_time.minute // 15) * 15
        end_time = end_time.replace(minute=minutes, second=0, microsecond=0)

    # Start time is 15 minutes before end time
    start_time = end_time - timedelta(minutes=15)

    # Convert to milliseconds for Binance API
    start_timestamp_ms = int(start_time.timestamp() * 1000)
    end_timestamp_ms = int(end_time.timestamp() * 1000)

    try:
        # Fetch 15-minute Kline data
        klines = client.get_klines(
            symbol=symbol.binance_name,
            interval=client.KLINE_INTERVAL_15MINUTE,
            startTime=start_timestamp_ms,
            endTime=end_timestamp_ms,
            limit=1,
        )

        if not klines:
            app_logger.error(f"No 15-minute Kline data found for {symbol.symbol_name}")
            return None

        return Candle(
            end_date=end_time,
            source=SourceID.BINANCE,
            open=float(klines[0][1]),
            close=float(klines[0][4]),
            symbol=symbol.symbol_name,
            low=float(klines[0][3]),
            high=float(klines[0][2]),
            last=float(klines[0][4]),
            volume=float(klines[0][5]),
            volume_quote=float(klines[0][7]),
        )

    except BinanceAPIException as e:
        app_logger.error(
            f"Error fetching 15-minute data for {symbol.symbol_name}: {e.message}"
        )
        return None
    except Exception as e:
        app_logger.error(
            f"Unexpected error for {symbol.symbol_name} 15-minute data: {str(e)}"
        )
        return None


if __name__ == "__main__":
    symbol = Symbol(
        symbol_id=1,
        symbol_name="BTC",
        full_name="Bitcoin",
        source_id=SourceID.BINANCE,
    )

    # # Fetch current price
    # price = fetch_binance_price(symbol)
    # if price is not None:
    #     print(price)

    # # Fetch close prices
    # df = fetch_close_prices_from_Binance(symbol.binance_name)
    # if not df.empty:
    #     print(df)
    # else:
    #     print("No data found")

    # Fetch open and close prices for the last full day
    response = fetch_binance_daily_kline(
        symbol, datetime.now(timezone.utc) - timedelta(days=1)
    )
    if response is not None:
        print(f"Yesterday price: {response}")
    else:
        print("No data found")
