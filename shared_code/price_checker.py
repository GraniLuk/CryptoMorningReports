"""Price checking and validation utilities for cryptocurrency data.

This module provides centralized candle fetching with intelligent batch API optimization.

Recommended Usage Patterns:
--------------------------

1. **Fetching Daily Candles (Preferred Method)**:
    ```python
    from shared_code.price_checker import fetch_daily_candles
    from datetime import date, timedelta
    from infra.sql_connection import connect_to_sql

    conn = connect_to_sql()
    symbol = get_symbol_by_name("BTC")  # Symbol with source_id property

    # Fetch last 30 days of daily candles (uses batch API + cache)
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    candles = fetch_daily_candles(symbol, start_date, end_date, conn)
    ```

2. **Fetching Hourly Candles**:
    ```python
    from shared_code.price_checker import fetch_hourly_candles
    from datetime import datetime, timedelta, UTC

    # Fetch last 48 hours (uses batch API + cache)
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=48)
    hourly_candles = fetch_hourly_candles(symbol, start_time, end_time, conn)
    ```

3. **Fetching 15-Minute Candles**:
    ```python
    from shared_code.price_checker import fetch_fifteen_min_candles

    # Fetch last 8 hours of 15-min candles (uses batch API + cache)
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=8)
    candles = fetch_fifteen_min_candles(symbol, start_time, end_time, conn)
    ```

Key Benefits:
-------------
- **Automatic batch optimization**: BINANCE (1000 candles/call), KUCOIN (1500 candles/call)
- **Database caching**: Checks SQLite first, only fetches missing data
- **Source-aware**: Automatically dispatches to correct exchange based on symbol.source_id
- **Performance**: ~97% fewer API calls, 30-50x faster than individual fetching
- **Consistent interface**: Same function signature for all timeframes

Architecture:
-------------
All fetch_*_candles() functions follow this pattern:
1. Generate expected timestamps/dates for the requested range
2. Check database for cached candles
3. Identify missing candles
4. Dispatch to batch API based on source_id (BINANCE/KUCOIN) or fallback
5. Save newly fetched candles to database
6. Return sorted list of all candles (cached + new)

Notes:
------
- Always pass a database connection for optimal performance
- Use timezone-aware datetime objects (UTC) for hourly/15-min fetches
- Batch functions respect API limits (1000 for Binance, 1500 for KuCoin)
- Database automatically handles deduplication
"""

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

from shared_code.binance import (
    fetch_binance_daily_kline,
    fetch_binance_fifteen_min_kline,
    fetch_binance_hourly_kline,
    fetch_binance_price,
)
from shared_code.coingecko import fetch_coingecko_price
from shared_code.common_price import Candle, TickerPrice
from shared_code.kucoin import (
    fetch_kucoin_daily_kline,
    fetch_kucoin_fifteen_min_kline,
    fetch_kucoin_hourly_kline,
    fetch_kucoin_price,
)
from source_repository import SourceID, Symbol
from technical_analysis.repositories.daily_candle_repository import (
    DailyCandleRepository,
)
from technical_analysis.repositories.fifteen_min_candle_repository import (
    FifteenMinCandleRepository,
)
from technical_analysis.repositories.hourly_candle_repository import (
    HourlyCandleRepository,
)


if TYPE_CHECKING:
    import pyodbc

    from infra.sql_connection import SQLiteConnectionWrapper


# Simple cache stores
_price_cache: dict[tuple[str, SourceID], TickerPrice] = {}


def _parse_candle_datetime(
    candle_end_date: str | datetime | date,
    *,
    round_to_hour: bool = True,
) -> datetime:
    """Parse candle end_date to datetime object with consistent timezone and rounding.

    Args:
        candle_end_date: End date as string, datetime, or date object
        round_to_hour: Whether to round to the nearest hour

    Returns:
        datetime object (timezone-aware, rounded if requested)
    """
    if isinstance(candle_end_date, str):
        candle_datetime = datetime.fromisoformat(candle_end_date.replace("Z", "+00:00"))
    elif isinstance(candle_end_date, datetime):
        candle_datetime = candle_end_date
    else:
        # If it's a date object, convert to datetime at midnight
        candle_datetime = datetime.combine(candle_end_date, datetime.min.time())

    # Ensure timezone aware
    candle_datetime = candle_datetime.replace(tzinfo=UTC)

    if round_to_hour:
        # Round to the nearest hour
        candle_datetime = candle_datetime.replace(minute=0, second=0, microsecond=0)

    return candle_datetime


def _add_candles_to_dict(
    candle_dict: dict[datetime, Candle],
    candles: list[Candle],
    *,
    round_to_hour: bool = True,
) -> None:
    """Add candles to dictionary using parsed datetime as key.

    Args:
        candle_dict: Dictionary to add candles to
        candles: List of candles to add
        round_to_hour: Whether to round timestamps to hour
    """
    for candle in candles:
        candle_datetime = _parse_candle_datetime(candle.end_date, round_to_hour=round_to_hour)
        candle_dict[candle_datetime] = candle


def _fetch_missing_candles_batch(
    symbol: Symbol,
    missing_timestamps: list[datetime],
    timeframe: str,
) -> list[Candle]:
    """Fetch missing candles using batch API calls.

    Args:
        symbol: Symbol to fetch candles for
        missing_timestamps: List of timestamps that need fetching
        timeframe: 'hourly' or 'fifteen_min'

    Returns:
        List of fetched candles
    """
    if not missing_timestamps:
        return []

    if symbol.source_id == SourceID.BINANCE:
        if timeframe == "hourly":
            from shared_code.binance import fetch_binance_hourly_klines_batch
            return fetch_binance_hourly_klines_batch(
                symbol, missing_timestamps[0], missing_timestamps[-1],
            )
        if timeframe == "fifteen_min":
            from shared_code.binance import fetch_binance_fifteen_min_klines_batch
            return fetch_binance_fifteen_min_klines_batch(
                symbol, missing_timestamps[0], missing_timestamps[-1],
            )

    if symbol.source_id == SourceID.KUCOIN:
        if timeframe == "hourly":
            from shared_code.kucoin import fetch_kucoin_hourly_klines_batch
            return fetch_kucoin_hourly_klines_batch(
                symbol, missing_timestamps[0], missing_timestamps[-1],
            )
        if timeframe == "fifteen_min":
            from shared_code.kucoin import fetch_kucoin_fifteen_min_klines_batch
            return fetch_kucoin_fifteen_min_klines_batch(
                symbol, missing_timestamps[0], missing_timestamps[-1],
            )

    # Fallback to individual fetching for unsupported sources
    return []


def fetch_daily_candle(
    symbol: Symbol,
    end_date: date | None = None,
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None" = None,
) -> Candle | None:
    """Fetch a daily candle for a symbol, checking database first if connection provided."""
    if end_date is None:
        end_date = datetime.now(UTC).date()
    # If connection provided, try to get from database first
    if conn:
        repo = DailyCandleRepository(conn)
        cached_candle = repo.get_candle(symbol, datetime.combine(end_date, datetime.min.time()))
        if cached_candle:
            return cached_candle

    # Fetch from source if not in database
    candle = None
    if symbol.source_id == SourceID.KUCOIN:
        candle = fetch_kucoin_daily_kline(symbol, end_date)
    if symbol.source_id == SourceID.BINANCE:
        candle = fetch_binance_daily_kline(symbol, end_date)
    # Save to database if connection provided and candle fetched
    if conn and candle:
        repo = DailyCandleRepository(conn)
        repo.save_candle(symbol, candle, source=symbol.source_id.value)
        # Re-fetch from database to get the ID
        candle = repo.get_candle(symbol, datetime.combine(end_date, datetime.min.time()))

    return candle


def fetch_hourly_candle(
    symbol: Symbol,
    end_time: datetime,
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None" = None,
) -> Candle | None:
    """Fetch hourly candle data for a symbol at the specified end time.

    Args:
        symbol: Symbol object
        end_time: End time for the candle period (defaults to current time)
        conn: Optional database connection

    Returns:
        Candle object if successful, None otherwise

    """
    # Ensure end_time is timezone-aware
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=UTC)
    # Round to the nearest hour
    end_time = end_time.replace(minute=0, second=0, microsecond=0)

    # If connection provided, try to get from database first
    if conn:
        repo = HourlyCandleRepository(conn)
        cached_candle = repo.get_candle(symbol, end_time)
        if cached_candle:
            return cached_candle

    # Fetch from source if not in database
    candle = None
    if symbol.source_id == SourceID.KUCOIN:
        candle = fetch_kucoin_hourly_kline(symbol, end_time)
    if symbol.source_id == SourceID.BINANCE:
        candle = fetch_binance_hourly_kline(symbol, end_time)

    # Save to database if connection provided and candle fetched
    if conn and candle:
        repo = HourlyCandleRepository(conn)
        repo.save_candle(symbol, candle, source=symbol.source_id.value)

    return candle


def fetch_hourly_candles(
    symbol: Symbol,
    start_time: datetime,
    end_time: datetime,
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None" = None,
) -> list[Candle]:
    """Fetch multiple hourly candles for a given symbol between start_time and end_time.

    Uses intelligent batch fetching for BINANCE and KUCOIN:
    - BINANCE: Up to 1000 candles per API call
    - KUCOIN: Up to 1500 candles per API call
    Falls back to individual fetching for other sources.

    If a database connection is provided, attempts to fetch from database first
    and only fetches missing candles from the API.

    Args:
        symbol: Symbol object
        start_time: Start time for fetching candles (timezone-aware)
        end_time: End time for fetching candles (timezone-aware)
        conn: Optional database connection for caching

    Returns:
        List of Candle objects sorted by end_date

    """
    # Default values and timezone handling
    start_time = start_time or datetime.now(UTC) - timedelta(days=1)
    end_time = end_time or datetime.now(UTC)
    start_time = start_time.replace(tzinfo=UTC) if start_time.tzinfo is None else start_time
    end_time = end_time.replace(tzinfo=UTC) if end_time.tzinfo is None else end_time

    # Round to the nearest hour
    start_time = start_time.replace(minute=0, second=0, microsecond=0)
    end_time = end_time.replace(minute=0, second=0, microsecond=0)

    # Generate all expected hourly timestamps
    expected_timestamps = []
    current_time = start_time
    while current_time <= end_time:
        expected_timestamps.append(current_time)
        current_time += timedelta(hours=1)

    # Dictionary to store candles by timestamp
    candle_dict = {}

    # Fetch cached candles from database if connection provided
    if conn:
        repo = HourlyCandleRepository(conn)
        cached_candles = repo.get_candles(symbol, start_time, end_time)

        # Add cached candles to dictionary using full datetime as key
        _add_candles_to_dict(candle_dict, cached_candles, round_to_hour=True)

    # Identify missing timestamps
    missing_timestamps = [ts for ts in expected_timestamps if ts not in candle_dict]

    if missing_timestamps:
        # Fetch missing candles using source-aware batch strategy
        fetched_candles = _fetch_missing_candles_batch(symbol, missing_timestamps, "hourly")

        # Save fetched candles to database and add to dictionary
        if conn and fetched_candles:
            repo = HourlyCandleRepository(conn)
            for candle in fetched_candles:
                repo.save_candle(symbol, candle, source=symbol.source_id.value)

            # Re-fetch saved candles to get database-assigned IDs
            refetched_candles = repo.get_candles(
                symbol,
                missing_timestamps[0],
                missing_timestamps[-1],
            )

            # Add refetched candles with IDs to dictionary using full datetime as key
            _add_candles_to_dict(candle_dict, refetched_candles, round_to_hour=True)
        elif fetched_candles:
            # No database connection, just use fetched candles without IDs
            _add_candles_to_dict(candle_dict, fetched_candles, round_to_hour=True)

    # Return candles sorted by end_date
    return [candle_dict[timestamp] for timestamp in sorted(candle_dict.keys())]


def fetch_fifteen_min_candle(
    symbol: Symbol,
    end_time: datetime,
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None" = None,
) -> Candle | None:
    """Fetch 15-minute candle data for a symbol at the specified end time.

    Args:
        symbol: Symbol object
        end_time: End time for the candle period (defaults to current time)
        conn: Optional database connection

    Returns:
        Candle object if successful, None otherwise

    """
    end_time = end_time or datetime.now(UTC)
    # Ensure end_time is timezone-aware
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=UTC)
    # Round to nearest 15 minutes
    minutes = (end_time.minute // 15) * 15
    end_time = end_time.replace(minute=minutes, second=0, microsecond=0)

    # If connection provided, try to get from database first
    if conn:
        repo = FifteenMinCandleRepository(conn)
        cached_candle = repo.get_candle(symbol, end_time)
        if cached_candle:
            return cached_candle

    # Fetch from source if not in database
    candle = None
    if symbol.source_id == SourceID.KUCOIN:
        candle = fetch_kucoin_fifteen_min_kline(symbol, end_time)
    if symbol.source_id == SourceID.BINANCE:
        candle = fetch_binance_fifteen_min_kline(symbol, end_time)

    # Save to database if connection provided and candle fetched
    if conn and candle:
        repo = FifteenMinCandleRepository(conn)
        repo.save_candle(symbol, candle, source=symbol.source_id.value)

    return candle


def fetch_fifteen_min_candles(
    symbol: Symbol,
    start_time: datetime,
    end_time: datetime,
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None" = None,
) -> list[Candle]:
    """Fetch multiple 15-minute candles for a given symbol between start_time and end_time.

    Uses intelligent batch fetching for BINANCE and KUCOIN:
    - BINANCE: Up to 1000 candles per API call
    - KUCOIN: Up to 1500 candles per API call
    Falls back to individual fetching for other sources.

    If a database connection is provided, attempts to fetch from database first
    and only fetches missing candles from the API.

    Args:
        symbol: Symbol object
        start_time: Start time for fetching candles (timezone-aware)
        end_time: End time for fetching candles (timezone-aware, defaults to now)
        conn: Optional database connection for caching

    Returns:
        List of Candle objects sorted by end_date

    """
    # Default values and timezone handling
    end_time = end_time or datetime.now(UTC)
    start_time = start_time or end_time - timedelta(hours=8)
    start_time = start_time.replace(tzinfo=UTC) if start_time.tzinfo is None else start_time
    end_time = end_time.replace(tzinfo=UTC) if end_time.tzinfo is None else end_time

    # Round to nearest 15 minutes
    start_minutes = (start_time.minute // 15) * 15
    start_time = start_time.replace(minute=start_minutes, second=0, microsecond=0)
    end_minutes = (end_time.minute // 15) * 15
    end_time = end_time.replace(minute=end_minutes, second=0, microsecond=0)

    # Generate all expected 15-minute timestamps
    expected_timestamps = []
    current_time = start_time
    while current_time <= end_time:
        expected_timestamps.append(current_time)
        current_time += timedelta(minutes=15)

    # Dictionary to store candles by timestamp
    candle_dict = {}

    # Fetch cached candles from database if connection provided
    if conn:
        repo = FifteenMinCandleRepository(conn)
        cached_candles = repo.get_candles(symbol, start_time, end_time)

        # Add cached candles to dictionary using full datetime as key
        for candle in cached_candles:
            candle_datetime = _parse_candle_datetime(candle.end_date, round_to_hour=False)
            candle_dict[candle_datetime] = candle

    # Identify missing timestamps
    missing_timestamps = [ts for ts in expected_timestamps if ts not in candle_dict]

    if missing_timestamps:
        # Fetch missing candles using source-aware batch strategy
        fetched_candles = _fetch_missing_candles_batch(symbol, missing_timestamps, "fifteen_min")

        # Save fetched candles to database and add to dictionary
        if conn and fetched_candles:
            repo = FifteenMinCandleRepository(conn)
            for candle in fetched_candles:
                repo.save_candle(symbol, candle, source=symbol.source_id.value)

            # Re-fetch saved candles to get database-assigned IDs
            refetched_candles = repo.get_candles(
                symbol,
                missing_timestamps[0],
                missing_timestamps[-1],
            )

            # Add refetched candles with IDs to dictionary using full datetime as key
            _add_candles_to_dict(candle_dict, refetched_candles, round_to_hour=False)
        elif fetched_candles:
            # No database connection, just use fetched candles without IDs
            _add_candles_to_dict(candle_dict, fetched_candles, round_to_hour=False)

    # Return candles sorted by end_date
    return [candle_dict[timestamp] for timestamp in sorted(candle_dict.keys())]


def fetch_daily_candles(
    symbol: Symbol,
    start_date: date,
    end_date: date | None = None,
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None" = None,
) -> list[Candle]:
    """Fetch multiple daily candles for a given symbol between start_date and end_date.

    Uses intelligent batch fetching:
    - Checks database for existing candles in the range
    - Identifies missing dates
    - For BINANCE: Fetches all missing candles in one batch API call (up to 1000)
    - For KUCOIN: Fetches all missing candles in one batch API call (up to 1500)
    - For other sources: Fetches missing candles individually
    - Saves newly fetched candles to database
    - Returns combined list of cached + newly fetched candles (sorted)

    Args:
        symbol: Symbol object with source_id property
        start_date: Start date for the candle range
        end_date: End date for the candle range (defaults to today)
        conn: Optional database connection

    Returns:
        List of Candle objects sorted by date

    """
    if end_date is None:
        end_date = datetime.now(UTC).date()

    # Generate all expected dates in the range
    expected_dates = []
    current_date = start_date
    while current_date <= end_date:
        expected_dates.append(current_date)
        current_date += timedelta(days=1)

    # Dictionary to store candles by date
    candle_dict = {}

    # If connection provided, try to get existing candles from database
    if conn:
        repo = DailyCandleRepository(conn)
        # Use max.time() for end_date to capture candles stored at end of day (23:59:59.999999)
        # Must include tzinfo=UTC for proper string comparison in SQLite
        cached_candles = repo.get_candles(
            symbol,
            datetime.combine(start_date, datetime.min.time(), tzinfo=UTC),
            datetime.combine(end_date, datetime.max.time(), tzinfo=UTC),
        )

        # Add cached candles to dictionary
        for candle in cached_candles:
            candle_date = _parse_candle_datetime(candle.end_date, round_to_hour=True)
            candle_dict[candle_date] = candle

    # Identify missing dates
    missing_dates = [d for d in expected_dates if d not in candle_dict]

    if missing_dates:
        # Fetch missing candles using source-aware batch strategy
        if symbol.source_id == SourceID.BINANCE:
            # Use batch API for BINANCE (up to 1000 candles per call)
            # Local import to avoid circular dependency between price_checker and binance
            from shared_code.binance import fetch_binance_daily_klines_batch

            batch_start = missing_dates[0]
            batch_end = missing_dates[-1]
            fetched_candles = fetch_binance_daily_klines_batch(symbol, batch_start, batch_end)

        elif symbol.source_id == SourceID.KUCOIN:
            # Use batch API for KUCOIN (up to 1500 candles per call)
            # Local import to avoid circular dependency between price_checker and kucoin
            from shared_code.kucoin import fetch_kucoin_daily_klines_batch

            batch_start = missing_dates[0]
            batch_end = missing_dates[-1]
            fetched_candles = fetch_kucoin_daily_klines_batch(symbol, batch_start, batch_end)

        else:
            # For other sources, fetch individually (fallback)
            fetched_candles = []
            for missing_date in missing_dates:
                candle = fetch_daily_candle(symbol, missing_date, conn)
                if candle:
                    fetched_candles.append(candle)

        # Save to database and add to dictionary
        if conn:
            repo = DailyCandleRepository(conn)
            for candle in fetched_candles:
                repo.save_candle(symbol, candle, source=symbol.source_id.value)

            # Re-fetch saved candles to get database-assigned IDs
            # This is critical for RSI and other operations that need candle IDs
            # Use max.time() for end_date to capture candles stored at end of day (23:59:59.999999)
            # Must include tzinfo=UTC for proper string comparison in SQLite
            refetched_candles = repo.get_candles(
                symbol,
                datetime.combine(missing_dates[0], datetime.min.time(), tzinfo=UTC),
                datetime.combine(missing_dates[-1], datetime.max.time(), tzinfo=UTC),
            )

            # Add refetched candles with IDs to dictionary
            for candle in refetched_candles:
                candle_date = _parse_candle_datetime(candle.end_date, round_to_hour=True)
                candle_dict[candle_date] = candle
        else:
            # No database connection, just use fetched candles without IDs
            for candle in fetched_candles:
                candle_date = _parse_candle_datetime(candle.end_date, round_to_hour=True)
                candle_dict[candle_date] = candle

    # Convert dictionary to sorted list
    return [candle_dict[d] for d in sorted(candle_dict.keys()) if d in candle_dict]


def fetch_current_price(symbol: Symbol) -> TickerPrice:
    """Fetch the current price for a symbol, using cache if available."""
    cache_key = (symbol.symbol_name, symbol.source_id)

    # Check cache
    if cache_key in _price_cache:
        return _price_cache[cache_key]

    # Fetch new price
    price = None
    if symbol.source_id == SourceID.KUCOIN:
        price = fetch_kucoin_price(symbol)
    if symbol.source_id == SourceID.BINANCE:
        price = fetch_binance_price(symbol)
    if symbol.source_id == SourceID.COINGECKO:
        price = fetch_coingecko_price(symbol)

    # Update cache
    if price is None:
        msg = f"Failed to fetch price for {symbol.symbol_name} from {symbol.source_id}"
        raise ValueError(msg)
    _price_cache[cache_key] = price
    return price


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import Symbol

    load_dotenv()
    conn = connect_to_sql()

    symbol = Symbol(
        symbol_id=3,  # Added required field
        symbol_name="XRP",
        full_name="Bitcoin",  # Added required field
        source_id=SourceID.BINANCE,
        coingecko_name="ripple",
    )

    start_time = datetime.now(UTC) - timedelta(days=1)
    end_time = datetime.now(UTC)

    daily_candles = fetch_hourly_candles(
        symbol,
        start_time=start_time,
        end_time=end_time,
        conn=conn,
    )
    for _daily_candle in daily_candles:
        pass
