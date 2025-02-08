import pandas as pd
from sharedCode.binance import fetch_close_prices_from_Binance, fetch_binance_price
from sharedCode.coingecko import fetch_coingecko_price
from source_repository import SourceID, Symbol
from sharedCode.kucoin import fetch_close_prices_from_Kucoin, fetch_kucoin_price
from sharedCode.commonPrice import TickerPrice
from typing import Dict, Tuple

# Simple cache stores
_price_cache: Dict[Tuple[str, SourceID], TickerPrice] = {}
_close_prices_cache: Dict[Tuple[str, SourceID, int], pd.DataFrame] = {}

def fetch_close_prices(symbol: Symbol, limit: int = 14) -> pd.DataFrame:
    cache_key = (symbol.symbol_name, symbol.source_id, limit)
    
    # Check cache
    if cache_key in _close_prices_cache:
        return _close_prices_cache[cache_key]

    # Fetch new data
    if (symbol.source_id == SourceID.KUCOIN):
        df = fetch_close_prices_from_Kucoin(symbol.kucoin_name, limit)
    if (symbol.source_id == SourceID.BINANCE):
        df = fetch_close_prices_from_Binance(symbol.binance_name, limit)
    if (symbol.source_id == SourceID.COINGECKO):
        df = fetch_coingecko_price(symbol.symbol_name)
    
    # Update cache
    _close_prices_cache[cache_key] = df
    return df

def fetch_current_price(symbol: Symbol) -> TickerPrice:
    cache_key = (symbol.symbol_name, symbol.source_id)
    
    # Check cache
    if cache_key in _price_cache:
        return _price_cache[cache_key]

    # Fetch new price
    price = None
    if (symbol.source_id == SourceID.KUCOIN):
        price = fetch_kucoin_price(symbol)
    if (symbol.source_id == SourceID.BINANCE):
        price = fetch_binance_price(symbol)
    if (symbol.source_id == SourceID.COINGECKO):
        price = fetch_coingecko_price(symbol)
    
    # Update cache
    _price_cache[cache_key] = price
    return price

if __name__ == "__main__":
    symbol = Symbol(
        symbol_id=1,  # Added required field
        symbol_name="KCS",
        full_name="Bitcoin",  # Added required field
        source_id=SourceID.KUCOIN
    )
    
    current_price = fetch_current_price(symbol)
    print(f"Current price for {symbol.symbol_name}: {current_price}")
    
    symbol = Symbol(
        symbol_id=1,  # Added required field
        symbol_name="BTC",
        full_name="Bitcoin",  # Added required field
        source_id=SourceID.BINANCE
    )
    
    current_price = fetch_current_price(symbol)
    print(f"Current price for {symbol.symbol_name}: {current_price}")

    # close_prices = fetch_close_prices(symbol, 14)
    # if isinstance(close_prices, pd.DataFrame):  # Handle DataFrame correctly
    #     for index, row in close_prices.iterrows():
    #         print(f"Date: {index}, Close: {row['close']}")