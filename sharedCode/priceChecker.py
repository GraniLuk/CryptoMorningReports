from datetime import date, datetime, timedelta
from typing import Dict, Tuple, Optional, List

import pandas as pd

from sharedCode.binance import (
    fetch_binance_daily_kline,
    fetch_binance_price
)
from sharedCode.coingecko import fetch_coingecko_price
from sharedCode.commonPrice import Candle, TickerPrice
from sharedCode.kucoin import (
    fetch_kucoin_daily_kline,
    fetch_kucoin_price,
)
from source_repository import SourceID, Symbol
from technical_analysis.repositories.daily_candle_repository import (
    DailyCandleRepository,
)
from technical_analysis.repositories.hourly_candle_repository import (
    HourlyCandleRepository,
)
from technical_analysis.repositories.fifteen_min_candle_repository import (
    FifteenMinCandleRepository,
)

# Simple cache stores
_price_cache: Dict[Tuple[str, SourceID], TickerPrice] = {}

def fetch_daily_candle(
    symbol: Symbol, end_date: date = date.today(), conn=None
) -> Candle:
    # If connection provided, try to get from database first
    if conn:
        repo = DailyCandleRepository(conn)
        cached_candle = repo.get_candle(symbol, end_date)
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

    return candle

def fetch_hourly_candle(
    symbol: Symbol, end_time: datetime = None, conn=None
) -> Optional[Candle]:
    """
    Fetch hourly candle data for a symbol at the specified end time
    
    Args:
        symbol: Symbol object
        end_time: End time for the candle period (defaults to current time)
        conn: Optional database connection
        
    Returns:
        Candle object if successful, None otherwise
    """
    end_time = end_time or datetime.now()
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
        from sharedCode.kucoin import fetch_kucoin_hourly_kline
        candle = fetch_kucoin_hourly_kline(symbol, end_time)
    if symbol.source_id == SourceID.BINANCE:
        from sharedCode.binance import fetch_binance_hourly_kline
        candle = fetch_binance_hourly_kline(symbol, end_time)
    
    # Save to database if connection provided and candle fetched
    if conn and candle:
        repo = HourlyCandleRepository(conn)
        repo.save_candle(symbol, candle, source=symbol.source_id.value)
    
    return candle

def fetch_fifteen_min_candle(
    symbol: Symbol, end_time: datetime = None, conn=None
) -> Optional[Candle]:
    """
    Fetch 15-minute candle data for a symbol at the specified end time
    
    Args:
        symbol: Symbol object
        end_time: End time for the candle period (defaults to current time)
        conn: Optional database connection
        
    Returns:
        Candle object if successful, None otherwise
    """
    end_time = end_time or datetime.now()
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
        from sharedCode.kucoin import fetch_kucoin_fifteen_min_kline
        candle = fetch_kucoin_fifteen_min_kline(symbol, end_time)
    if symbol.source_id == SourceID.BINANCE:
        from sharedCode.binance import fetch_binance_fifteen_min_kline
        candle = fetch_binance_fifteen_min_kline(symbol, end_time)
    
    # Save to database if connection provided and candle fetched
    if conn and candle:
        repo = FifteenMinCandleRepository(conn)
        repo.save_candle(symbol, candle, source=symbol.source_id.value)
    
    return candle

def fetch_daily_candles(
    symbol: Symbol, start_date: date, end_date: date = date.today(), conn=None
) -> list[Candle]:
    """
    Fetch multiple daily candles for a given symbol between start_date and end_date.
    If a database connection is provided, attempts to fetch from database first.
    """
    # If connection provided, try to get from database first
    if conn:
        repo = DailyCandleRepository(conn)
        cached_candles = repo.get_candles(symbol, start_date, end_date)
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

def fetch_current_price(symbol: Symbol, source_id: SourceID = None) -> TickerPrice:
    # Use provided source_id if available, otherwise use symbol's source_id
    used_source_id = source_id if source_id is not None else symbol.source_id
    cache_key = (symbol.symbol_name, used_source_id)

    # Check cache
    if cache_key in _price_cache:
        return _price_cache[cache_key]

    # Fetch new price
    price = None
    if used_source_id == SourceID.KUCOIN:
        price = fetch_kucoin_price(symbol)
    if used_source_id == SourceID.BINANCE:
        price = fetch_binance_price(symbol)
    if used_source_id == SourceID.COINGECKO:
        price = fetch_coingecko_price(symbol)

    # Update cache
    _price_cache[cache_key] = price
    return price


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import Symbol

    load_dotenv()
    conn = connect_to_sql()
    symbol = Symbol(
        symbol_id=1,  # Added required field
        symbol_name="KCS",
        full_name="Bitcoin",  # Added required field
        source_id=SourceID.KUCOIN,
    )

    daily_candle = fetch_daily_candle(symbol, conn=conn)
    print(f"Daily candle for {symbol.symbol_name}: {daily_candle}")
    # current_price = fetch_current_price(symbol)
    # print(f"Current price for {symbol.symbol_name}: {current_price}")

    symbol = Symbol(
        symbol_id=1,  # Added required field
        symbol_name="BTC",
        full_name="Bitcoin",  # Added required field
        source_id=SourceID.BINANCE,
    )

    daily_candle = fetch_daily_candle(symbol, conn=conn)
    print(f"Daily candle for {symbol.symbol_name}: {daily_candle}")
    # current_price = fetch_current_price(symbol)
    # print(f"Current price for {symbol.symbol_name}: {current_price}")

    # close_prices = fetch_close_prices(symbol, 14)
    # if isinstance(close_prices, pd.DataFrame):  # Handle DataFrame correctly
    #     for index, row in close_prices.iterrows():
    #         print(f"Date: {index}, Close: {row['close']}")
