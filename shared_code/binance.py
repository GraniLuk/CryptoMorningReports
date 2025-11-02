"""Binance API integration for cryptocurrency data fetching."""

from datetime import UTC, date, datetime, timedelta

import pandas as pd
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException

from infra.telegram_logging_handler import app_logger
from shared_code.common_price import Candle, TickerPrice
from source_repository import SourceID, Symbol


class FuturesMetrics:
    """Data class for futures market metrics."""

    def __init__(
        self,
        symbol: str,
        open_interest: float,
        open_interest_value: float,
        funding_rate: float,
        next_funding_time: datetime,
        timestamp: datetime,
    ):
        """Initialize futures market metrics with the provided data."""
        self.symbol = symbol
        self.open_interest = open_interest
        self.open_interest_value = open_interest_value
        self.funding_rate = funding_rate
        self.next_funding_time = next_funding_time
        self.timestamp = timestamp

    def __repr__(self):
        """Return a string representation of the FuturesMetrics object."""
        return (
            f"FuturesMetrics(symbol={self.symbol}, "
            f"open_interest={self.open_interest}, "
            f"open_interest_value={self.open_interest_value}, "
            f"funding_rate={self.funding_rate:.6f}%, "
            f"next_funding_time={self.next_funding_time})"
        )


def fetch_binance_futures_metrics(symbol: Symbol) -> FuturesMetrics | None:
    """Fetch Open Interest and Funding Rate from Binance Futures.

    Args:
        symbol: Symbol object with binance_name property

    Returns:
        FuturesMetrics object if successful, None otherwise

    """
    client = BinanceClient()

    try:
        # Fetch Open Interest
        oi_response = client.futures_open_interest(symbol=symbol.binance_name)
        open_interest = float(oi_response.get("openInterest", 0))
        oi_timestamp = datetime.fromtimestamp(oi_response.get("time", 0) / 1000, tz=UTC)

        # Fetch current price to calculate OI value
        ticker = client.futures_ticker(symbol=symbol.binance_name)
        last_price = float(ticker.get("lastPrice", 0))
        open_interest_value = open_interest * last_price

        # Fetch Funding Rate
        funding_response = client.futures_funding_rate(symbol=symbol.binance_name, limit=1)

        if not funding_response:
            app_logger.warning(f"No funding rate data for {symbol.symbol_name}")
            return None

        funding_rate = (
            float(funding_response[0].get("fundingRate", 0)) * 100
        )  # Convert to percentage

        # Get next funding time from mark price
        mark_price = client.futures_mark_price(symbol=symbol.binance_name)
        next_funding_time = datetime.fromtimestamp(
            mark_price.get("nextFundingTime", 0) / 1000,
            tz=UTC,
        )

        return FuturesMetrics(
            symbol=symbol.symbol_name,
            open_interest=open_interest,
            open_interest_value=open_interest_value,
            funding_rate=funding_rate,
            next_funding_time=next_funding_time,
            timestamp=oi_timestamp,
        )

    except BinanceAPIException as e:
        app_logger.error(f"Error fetching futures metrics for {symbol.symbol_name}: {e.message}")
        return None
    except (KeyError, ValueError, TypeError, ConnectionError) as e:
        app_logger.error(
            f"Unexpected error fetching futures metrics for {symbol.symbol_name}: {e!s}",
        )
        return None


def fetch_binance_price(symbol: Symbol) -> TickerPrice | None:
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
    except (KeyError, ValueError, TypeError, ConnectionError) as e:
        app_logger.error(f"Unexpected error for {symbol}: {e!s}")
        return None


def fetch_close_prices_from_binance(symbol: str, lookback_days: int = 14) -> pd.DataFrame:
    """Fetch historical close prices from Binance for a given symbol."""
    client = BinanceClient()

    try:
        start_time = datetime.now(UTC) - timedelta(days=lookback_days)

        klines = client.get_historical_klines(
            symbol=symbol,
            interval=BinanceClient.KLINE_INTERVAL_1DAY,
            start_str=start_time.strftime("%d %b %Y"),
            limit=lookback_days,
        )

        # Create DataFrame with numeric types
        # Using list comprehension to create DataFrame with named columns
        if klines:
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
        else:
            # Return empty DataFrame with proper columns if no data
            return pd.DataFrame(columns=["timestamp", "close"])

        # Convert price columns to float
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("timestamp")

    except BinanceAPIException as e:
        app_logger.error(f"Error fetching data for {symbol}: {e.message}")
        return pd.DataFrame()
    except (KeyError, ValueError, TypeError, ConnectionError) as e:
        app_logger.error(f"Unexpected error for {symbol}: {e!s}")
        return pd.DataFrame()
    else:
        return df


def fetch_binance_daily_kline(symbol: Symbol, end_date: date | None = None) -> Candle | None:
    """Fetch open and close prices from Binance for the last full day."""
    if end_date is None:
        end_date = datetime.now(UTC).date()
    client = BinanceClient()

    # Get yesterday's date
    end_date_timestamp = datetime.combine(end_date, datetime.min.time()).timestamp()
    start_date_timestamp = datetime.combine(
        end_date - timedelta(days=1),
        datetime.min.time(),
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
            end_date=end_date.isoformat() if isinstance(end_date, date) else str(end_date),
            source=SourceID.BINANCE.value,
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
    except (KeyError, ValueError, TypeError, IndexError, ConnectionError) as e:
        app_logger.error(f"Unexpected error for {symbol}: {e!s}")
        return None


# Adding hourly and fifteen-minute candle fetching functions


def fetch_binance_hourly_kline(symbol: Symbol, end_time: datetime) -> Candle | None:
    """Fetch open, close, high, low prices and volume from Binance for the specified hour.

    Args:
        symbol: Symbol object with binance_name property
        end_time: End time for the candle period (defaults to current hour)

    Returns:
        Candle object if successful, None otherwise

    """
    client = BinanceClient()

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
            end_date=end_time.isoformat() if isinstance(end_time, datetime) else str(end_time),
            source=SourceID.BINANCE.value,
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
        app_logger.error(f"Error fetching hourly data for {symbol.symbol_name}: {e.message}")
        return None
    except (KeyError, ValueError, TypeError, IndexError, ConnectionError) as e:
        app_logger.error(f"Unexpected error for {symbol.symbol_name} hourly data: {e!s}")
        return None


def fetch_binance_fifteen_min_kline(symbol: Symbol, end_time: datetime) -> Candle | None:
    """Fetch 15-minute kline data from Binance for the specified symbol and time.

    Args:
        symbol: Symbol object with binance_name property
        end_time: End time for the candle period (defaults to current 15-minute interval)

    Returns:
        Candle object if successful, None otherwise

    """
    client = BinanceClient()

    if end_time.tzinfo is None:
        # Convert naive datetime to timezone-aware
        end_time = end_time.replace(tzinfo=UTC)

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
            end_date=end_time.isoformat() if isinstance(end_time, datetime) else str(end_time),
            source=SourceID.BINANCE.value,
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
        app_logger.error(f"Error fetching 15-minute data for {symbol.symbol_name}: {e.message}")
        return None
    except (KeyError, ValueError, TypeError, IndexError, ConnectionError) as e:
        app_logger.error(f"Unexpected error for {symbol.symbol_name} 15-minute data: {e!s}")
        return None


def fetch_binance_fifteen_min_klines_batch(
    symbol: Symbol,
    start_time: datetime,
    end_time: datetime,
) -> list[Candle]:
    """Fetch multiple 15-minute klines from Binance in a single API call.

    This function is optimized to fetch up to 1000 candles in one request,
    significantly reducing API overhead compared to individual fetches.

    Args:
        symbol: Symbol object with binance_name property
        start_time: Start time for the candle range
        end_time: End time for the candle range

    Returns:
        List of Candle objects, empty list if fetch fails

    """
    max_candles_per_request = 1000
    client = BinanceClient()

    # Ensure timezone-aware datetimes
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=UTC)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=UTC)

    # Round to nearest 15 minutes
    start_minutes = (start_time.minute // 15) * 15
    start_time = start_time.replace(minute=start_minutes, second=0, microsecond=0)

    end_minutes = (end_time.minute // 15) * 15
    end_time = end_time.replace(minute=end_minutes, second=0, microsecond=0)

    # Calculate expected number of candles
    time_diff = end_time - start_time
    expected_candles = int(time_diff.total_seconds() / (15 * 60)) + 1

    # Binance API limit is 1000 candles per request
    if expected_candles > max_candles_per_request:
        app_logger.warning(
            f"Requested {expected_candles} candles for {symbol.symbol_name}, "
            f"limiting to {max_candles_per_request} (max per API call)",
        )
        expected_candles = max_candles_per_request

    # Convert to milliseconds for Binance API
    start_timestamp_ms = int(start_time.timestamp() * 1000)
    end_timestamp_ms = int(end_time.timestamp() * 1000)

    try:
        # Fetch 15-minute Kline data in batch
        klines = client.get_klines(
            symbol=symbol.binance_name,
            interval=client.KLINE_INTERVAL_15MINUTE,
            startTime=start_timestamp_ms,
            endTime=end_timestamp_ms,
            limit=expected_candles,
        )

        if not klines:
            app_logger.error(f"No 15-minute Kline data found for {symbol.symbol_name}")
            return []

        # Convert each kline to Candle object
        candles = []
        for kline in klines:
            # kline[0] is the open time in milliseconds
            candle_end_time = datetime.fromtimestamp(
                kline[0] / 1000,
                tz=UTC,
            ) + timedelta(minutes=15)

            candles.append(
                Candle(
                    end_date=candle_end_time.isoformat(),
                    source=SourceID.BINANCE.value,
                    open=float(kline[1]),
                    close=float(kline[4]),
                    symbol=symbol.symbol_name,
                    low=float(kline[3]),
                    high=float(kline[2]),
                    last=float(kline[4]),
                    volume=float(kline[5]),
                    volume_quote=float(kline[7]),
                ),
            )

        app_logger.info(
            f"✓ Fetched {len(candles)} 15-minute candles for {symbol.symbol_name} "
            f"in single API call (requested {expected_candles})",
        )

    except BinanceAPIException as e:
        app_logger.error(
            f"Error batch fetching 15-minute data for {symbol.symbol_name}: {e.message}",
        )
        return []
    except (KeyError, ValueError, TypeError, IndexError, ConnectionError) as e:
        app_logger.error(
            f"Unexpected error batch fetching {symbol.symbol_name} 15-minute data: {e!s}",
        )
        return []
    else:
        return candles


def fetch_binance_hourly_klines_batch(
    symbol: Symbol,
    start_time: datetime,
    end_time: datetime,
) -> list[Candle]:
    """Fetch multiple hourly klines from Binance in a single API call.

    This function is optimized to fetch up to 1000 candles in one request,
    significantly reducing API overhead compared to individual fetches.

    Args:
        symbol: Symbol object with binance_name property
        start_time: Start time for the candle range
        end_time: End time for the candle range

    Returns:
        List of Candle objects, empty list if fetch fails

    """
    max_candles_per_request = 1000
    client = BinanceClient()

    # Ensure timezone-aware datetimes
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=UTC)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=UTC)

    # Round to nearest hour
    start_time = start_time.replace(minute=0, second=0, microsecond=0)
    end_time = end_time.replace(minute=0, second=0, microsecond=0)

    # Calculate expected number of candles
    time_diff = end_time - start_time
    expected_candles = int(time_diff.total_seconds() / 3600) + 1  # 3600 seconds = 1 hour

    # Binance API limit is 1000 candles per request
    if expected_candles > max_candles_per_request:
        app_logger.warning(
            f"Requested {expected_candles} hourly candles for {symbol.symbol_name}, "
            f"limiting to {max_candles_per_request} (max per API call)",
        )
        expected_candles = max_candles_per_request

    # Convert to milliseconds for Binance API
    start_timestamp_ms = int(start_time.timestamp() * 1000)
    end_timestamp_ms = int(end_time.timestamp() * 1000)

    try:
        # Fetch hourly Kline data in batch
        klines = client.get_klines(
            symbol=symbol.binance_name,
            interval=client.KLINE_INTERVAL_1HOUR,
            startTime=start_timestamp_ms,
            endTime=end_timestamp_ms,
            limit=expected_candles,
        )

        if not klines:
            app_logger.error(f"No hourly Kline data found for {symbol.symbol_name}")
            return []

        # Convert each kline to Candle object
        candles = []
        for kline in klines:
            # kline[0] is the open time in milliseconds
            candle_end_time = datetime.fromtimestamp(
                kline[0] / 1000,
                tz=UTC,
            ) + timedelta(hours=1)

            candles.append(
                Candle(
                    end_date=candle_end_time.isoformat(),
                    source=SourceID.BINANCE.value,
                    open=float(kline[1]),
                    close=float(kline[4]),
                    symbol=symbol.symbol_name,
                    low=float(kline[3]),
                    high=float(kline[2]),
                    last=float(kline[4]),
                    volume=float(kline[5]),
                    volume_quote=float(kline[7]),
                ),
            )

        app_logger.info(
            f"✓ Fetched {len(candles)} hourly candles for {symbol.symbol_name} "
            f"in single API call (requested {expected_candles})",
        )

    except BinanceAPIException as e:
        app_logger.error(
            f"Error batch fetching hourly data for {symbol.symbol_name}: {e.message}",
        )
        return []
    except (KeyError, ValueError, TypeError, IndexError, ConnectionError) as e:
        app_logger.error(
            f"Unexpected error batch fetching {symbol.symbol_name} hourly data: {e!s}",
        )
        return []
    else:
        return candles


def fetch_binance_daily_klines_batch(
    symbol: Symbol,
    start_date: date,
    end_date: date,
) -> list[Candle]:
    """Fetch multiple daily klines from Binance in a single API call.

    This function is optimized to fetch up to 1000 candles in one request,
    significantly reducing API overhead compared to individual fetches.

    Args:
        symbol: Symbol object with binance_name property
        start_date: Start date for the candle range
        end_date: End date for the candle range

    Returns:
        List of Candle objects, empty list if fetch fails

    """
    max_candles_per_request = 1000
    client = BinanceClient()

    # Convert dates to datetime objects for timestamp calculation
    start_datetime = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
    end_datetime = datetime.combine(end_date, datetime.max.time(), tzinfo=UTC)

    # Calculate expected number of candles
    days_diff = (end_date - start_date).days + 1
    expected_candles = days_diff

    # Binance API limit is 1000 candles per request
    if expected_candles > max_candles_per_request:
        app_logger.warning(
            f"Requested {expected_candles} daily candles for {symbol.symbol_name}, "
            f"limiting to {max_candles_per_request} (max per API call)",
        )
        expected_candles = max_candles_per_request
        # Adjust end_datetime to match the limit
        end_datetime = start_datetime + timedelta(days=max_candles_per_request - 1)

    # Convert to milliseconds for Binance API
    start_timestamp_ms = int(start_datetime.timestamp() * 1000)
    end_timestamp_ms = int(end_datetime.timestamp() * 1000)

    try:
        # Fetch daily Kline data in batch
        klines = client.get_klines(
            symbol=symbol.binance_name,
            interval=client.KLINE_INTERVAL_1DAY,
            startTime=start_timestamp_ms,
            endTime=end_timestamp_ms,
            limit=expected_candles,
        )

        if not klines:
            app_logger.error(f"No daily Kline data found for {symbol.symbol_name}")
            return []

        # Convert each kline to Candle object
        candles = []
        for kline in klines:
            # kline[0] is the open time in milliseconds
            candle_date = datetime.fromtimestamp(
                kline[0] / 1000,
                tz=UTC,
            ).date()

            # Use end of day for end_date (consistent with individual fetch)
            candle_end_datetime = datetime.combine(
                candle_date,
                datetime.max.time(),
                tzinfo=UTC,
            )

            candles.append(
                Candle(
                    end_date=candle_end_datetime.isoformat(),
                    source=SourceID.BINANCE.value,
                    open=float(kline[1]),
                    close=float(kline[4]),
                    symbol=symbol.symbol_name,
                    low=float(kline[3]),
                    high=float(kline[2]),
                    last=float(kline[4]),
                    volume=float(kline[5]),
                    volume_quote=float(kline[7]),
                ),
            )

        app_logger.info(
            f"✓ Fetched {len(candles)} daily candles for {symbol.symbol_name} "
            f"in single API call (requested {expected_candles})",
        )

    except BinanceAPIException as e:
        app_logger.error(
            f"Error batch fetching daily data for {symbol.symbol_name}: {e.message}",
        )
        return []
    except (KeyError, ValueError, TypeError, IndexError, ConnectionError) as e:
        app_logger.error(
            f"Unexpected error batch fetching {symbol.symbol_name} daily data: {e!s}",
        )
        return []
    else:
        return candles


if __name__ == "__main__":
    symbol = Symbol(
        symbol_id=1,
        symbol_name="BTC",
        full_name="Bitcoin",
        source_id=SourceID.BINANCE,
        coingecko_name="bitcoin",
    )

    # Fetch open and close prices for the last full day
    response = fetch_binance_daily_kline(symbol, datetime.now(UTC) - timedelta(days=1))
    if response is not None:
        pass
    else:
        pass
