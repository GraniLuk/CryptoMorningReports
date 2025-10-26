from datetime import UTC, date, datetime, timedelta

from shared_code.binance import fetch_binance_daily_kline, fetch_binance_price
from shared_code.coingecko import fetch_coingecko_price
from shared_code.common_price import Candle, TickerPrice
from shared_code.kucoin import (
    fetch_kucoin_daily_kline,
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


# Simple cache stores
_price_cache: dict[tuple[str, SourceID], TickerPrice] = {}


def fetch_daily_candle(symbol: Symbol, end_date: date | None = None, conn=None) -> Candle | None:
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


def fetch_hourly_candle(symbol: Symbol, end_time: datetime, conn=None) -> Candle | None:
    """
    Fetch hourly candle data for a symbol at the specified end time

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
        from shared_code.kucoin import fetch_kucoin_hourly_kline

        candle = fetch_kucoin_hourly_kline(symbol, end_time)
    if symbol.source_id == SourceID.BINANCE:
        from shared_code.binance import fetch_binance_hourly_kline

        candle = fetch_binance_hourly_kline(symbol, end_time)

    # Save to database if connection provided and candle fetched
    if conn and candle:
        repo = HourlyCandleRepository(conn)
        repo.save_candle(symbol, candle, source=symbol.source_id.value)

    return candle


def fetch_hourly_candles(
    symbol: Symbol, start_time: datetime, end_time: datetime, conn=None
) -> list[Candle]:
    """
    Fetch multiple hourly candles for a given symbol between start_time and end_time.
    If a database connection is provided, attempts to fetch from database first.
    Will check if all expected candles are available and fetch missing ones.

    Args:
        symbol: Symbol object
        start_time: Start time for fetching candles
        end_time: End time for fetching candles (defaults to current time)
        conn: Optional database connection

    Returns:
        List of Candle objects
    """

    if not start_time:
        start_time = datetime.now(UTC) - timedelta(days=1)  # Default to 1 day back
    if not end_time:
        end_time = datetime.now(UTC)
    end_time = end_time or datetime.now(UTC)
    # Ensure both start_time and end_time are timezone-aware
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=UTC)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=UTC)

    # Round to the nearest hour
    start_time = start_time.replace(minute=0, second=0, microsecond=0)
    end_time = end_time.replace(minute=0, second=0, microsecond=0)

    # Generate all expected timestamps
    expected_timestamps = []
    current_time = start_time
    while current_time <= end_time:
        expected_timestamps.append(current_time)
        current_time += timedelta(hours=1)

    # Dictionary to store candles by timestamp
    candle_dict = {}

    # If connection provided, try to get from database first
    if conn:
        repo = HourlyCandleRepository(conn)
        cached_candles = repo.get_candles(symbol, start_time, end_time)

        # Add cached candles to dictionary
        for candle in cached_candles:
            # Parse end_date string to datetime for comparison
            if isinstance(candle.end_date, str):
                candle_end_date = datetime.fromisoformat(candle.end_date.replace("Z", "+00:00"))
            else:
                candle_end_date = candle.end_date

            # Ensure candle end_date is timezone-aware for comparison
            if candle_end_date.tzinfo is None:
                candle_end_date = candle_end_date.replace(tzinfo=UTC)
            candle_dict[candle_end_date] = candle

    # Check for missing timestamps and fetch from source
    for timestamp in expected_timestamps:
        if timestamp not in candle_dict:
            candle = None
            if symbol.source_id == SourceID.KUCOIN:
                from shared_code.kucoin import fetch_kucoin_hourly_kline

                candle = fetch_kucoin_hourly_kline(symbol, timestamp)
            if symbol.source_id == SourceID.BINANCE:
                from shared_code.binance import fetch_binance_hourly_kline

                candle = fetch_binance_hourly_kline(symbol, timestamp)

            # Save to database if connection provided and candle fetched
            if conn and candle:
                repo = HourlyCandleRepository(conn)
                repo.save_candle(symbol, candle, source=symbol.source_id.value)

            if candle:
                candle_dict[timestamp] = candle

    # Convert dictionary to sorted list
    return [candle_dict[timestamp] for timestamp in sorted(candle_dict.keys())]


def fetch_fifteen_min_candle(symbol: Symbol, end_time: datetime, conn=None) -> Candle | None:
    """
    Fetch 15-minute candle data for a symbol at the specified end time

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
        from shared_code.kucoin import fetch_kucoin_fifteen_min_kline

        candle = fetch_kucoin_fifteen_min_kline(symbol, end_time)
    if symbol.source_id == SourceID.BINANCE:
        from shared_code.binance import fetch_binance_fifteen_min_kline

        candle = fetch_binance_fifteen_min_kline(symbol, end_time)

    # Save to database if connection provided and candle fetched
    if conn and candle:
        repo = FifteenMinCandleRepository(conn)
        repo.save_candle(symbol, candle, source=symbol.source_id.value)

    return candle


def fetch_fifteen_min_candles(
    symbol: Symbol, start_time: datetime, end_time: datetime, conn=None
) -> list[Candle]:
    """
    Fetch multiple 15-minute candles for a given symbol between start_time and end_time.
    If a database connection is provided, attempts to fetch from database first.
    Will check if all expected candles are available and fetch missing ones.

    Args:
        symbol: Symbol object
        start_time: Start time for fetching candles
        end_time: End time for fetching candles (defaults to current time)
        conn: Optional database connection

    Returns:
        List of Candle objects
    """
    end_time = end_time or datetime.now(UTC)

    if not start_time:
        start_time = end_time - timedelta(hours=8)

    # Ensure both start_time and end_time are timezone-aware
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=UTC)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=UTC)

    # Round to nearest 15 minutes
    start_minutes = (start_time.minute // 15) * 15
    start_time = start_time.replace(minute=start_minutes, second=0, microsecond=0)

    end_minutes = (end_time.minute // 15) * 15
    end_time = end_time.replace(minute=end_minutes, second=0, microsecond=0)

    # Generate all expected timestamps
    expected_timestamps = []
    current_time = start_time
    while current_time <= end_time:
        expected_timestamps.append(current_time)
        current_time += timedelta(minutes=15)

    # Dictionary to store candles by timestamp
    candle_dict = {}

    # If connection provided, try to get from database first
    if conn:
        repo = FifteenMinCandleRepository(conn)
        cached_candles = repo.get_candles(symbol, start_time, end_time)

        # Add cached candles to dictionary
        for candle in cached_candles:
            # Parse end_date string to datetime for comparison
            if isinstance(candle.end_date, str):
                candle_end_date = datetime.fromisoformat(candle.end_date.replace("Z", "+00:00"))
            else:
                candle_end_date = candle.end_date

            # Ensure candle end_date is timezone-aware for comparison
            if candle_end_date.tzinfo is None:
                candle_end_date = candle_end_date.replace(tzinfo=UTC)
            candle_dict[candle_end_date] = candle

    # Check for missing timestamps and fetch from source
    for timestamp in expected_timestamps:
        if timestamp not in candle_dict:
            candle = None
            if symbol.source_id == SourceID.KUCOIN:
                from shared_code.kucoin import fetch_kucoin_fifteen_min_kline

                candle = fetch_kucoin_fifteen_min_kline(symbol, timestamp)
            if symbol.source_id == SourceID.BINANCE:
                from shared_code.binance import fetch_binance_fifteen_min_kline

                candle = fetch_binance_fifteen_min_kline(symbol, timestamp)

            # Save to database if connection provided and candle fetched
            if conn and candle:
                repo = FifteenMinCandleRepository(conn)
                repo.save_candle(symbol, candle, source=symbol.source_id.value)

            if candle:
                candle_dict[timestamp] = candle

    # Convert dictionary to sorted list
    return [candle_dict[timestamp] for timestamp in sorted(candle_dict.keys())]


def fetch_daily_candles(
    symbol: Symbol, start_date: date, end_date: date | None = None, conn=None
) -> list[Candle]:
    """
    Fetch multiple daily candles for a given symbol between start_date and end_date.
    If a database connection is provided, attempts to fetch from database first.
    """
    if end_date is None:
        end_date = datetime.now(UTC).date()
    # If connection provided, try to get from database first
    if conn:
        repo = DailyCandleRepository(conn)
        cached_candles = repo.get_candles(
            symbol,
            datetime.combine(start_date, datetime.min.time()),
            datetime.combine(end_date, datetime.min.time()),
        )
        if cached_candles:
            return cached_candles

    # If not in database or no connection, fetch each day individually
    candles = []
    current_date = start_date
    while current_date <= end_date:
        candle = fetch_daily_candle(symbol, current_date, conn)
        if candle:
            candles.append(candle)
        current_date += timedelta(days=1)

    return candles


def fetch_current_price(symbol: Symbol) -> TickerPrice:
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
        raise ValueError(f"Failed to fetch price for {symbol.symbol_name} from {symbol.source_id}")
    _price_cache[cache_key] = price
    return price


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import Symbol

    load_dotenv()
    conn = connect_to_sql()
    # symbol = Symbol(
    #     symbol_id=7,  # Added required field
    #     symbol_name="KCS",
    #     full_name="Bitcoin",  # Added required field
    #     source_id=SourceID.KUCOIN,
    # )

    # daily_candle = fetch_hourly_candles(symbol, conn=conn)
    # print(
    #     f"Daily candle for {symbol.symbol_name}: {daily_candle.close} {daily_candle.end_date}"
    # )
    # current_price = fetch_current_price(symbol)
    # print(f"Current price for {symbol.symbol_name}: {current_price}")

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
        symbol, start_time=start_time, end_time=end_time, conn=conn
    )
    for daily_candle in daily_candles:
        print(
            f"Daily candle for {symbol.symbol_name}: {daily_candle.close} {daily_candle.end_date}"
        )
    # current_price = fetch_current_price(symbol)
    # print(f"Current price for {symbol.symbol_name}: {current_price}")

    # close_prices = fetch_close_prices(symbol, 14)
    # if isinstance(close_prices, pd.DataFrame):  # Handle DataFrame correctly
    #     for index, row in close_prices.iterrows():
    #         print(f"Date: {index}, Close: {row['close']}")
