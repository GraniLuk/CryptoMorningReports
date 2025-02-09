from datetime import date, datetime, timezone
from typing import Dict, Tuple

import pandas as pd

from sharedCode.binance import (
    fetch_binance_daily_kline,
    fetch_binance_price,
    fetch_close_prices_from_Binance,
)
from sharedCode.coingecko import fetch_coingecko_price
from sharedCode.commonPrice import Candle, TickerPrice
from sharedCode.kucoin import (
    fetch_close_prices_from_Kucoin,
    fetch_kucoin_daily_kline,
    fetch_kucoin_price,
)
from source_repository import SourceID, Symbol
from technical_analysis.repositories.daily_candle_repository import (
    DailyCandleRepository,
)

# Simple cache stores
_price_cache: Dict[Tuple[str, SourceID], TickerPrice] = {}
_close_prices_cache: Dict[Tuple[str, SourceID, int], pd.DataFrame] = {}


def fetch_close_prices(symbol: Symbol, limit: int = 14) -> pd.DataFrame:
    # Find the maximum cached limit for this symbol and source
    max_cached_limit = 0
    cached_df = None

    for sym, src, lmt in _close_prices_cache.keys():
        if sym == symbol.symbol_name and src == symbol.source_id:
            if lmt > max_cached_limit:
                max_cached_limit = lmt
                cached_df = _close_prices_cache[(sym, src, lmt)]

    # If we found cached data with higher or equal limit, return subset
    if cached_df is not None and max_cached_limit >= limit:
        return cached_df.iloc[-limit:]

    # Fetch new data
    if symbol.source_id == SourceID.KUCOIN:
        df = fetch_close_prices_from_Kucoin(symbol.kucoin_name, limit)
    if symbol.source_id == SourceID.BINANCE:
        df = fetch_close_prices_from_Binance(symbol.binance_name, limit)
    if symbol.source_id == SourceID.COINGECKO:
        df = fetch_coingecko_price(symbol.symbol_name)

    # Update cache
    _close_prices_cache[(symbol.symbol_name, symbol.source_id, limit)] = df
    return df


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
