import pandas as pd
from sharedCode.binance import fetch_close_prices_from_Binance  
from sharedCode.coingecko import fetch_coingecko_price
from source_repository import SourceID, Symbol
from sharedCode.kucoin import fetch_close_prices_from_Kucoin

def fetch_close_prices(symbol: Symbol, limit: int = 14) -> pd.DataFrame:
    if (symbol.source_id == SourceID.KUCOIN):
        df = fetch_close_prices_from_Kucoin(symbol.kucoin_name, limit)  # Fixed typo
    if (symbol.source_id == SourceID.BINANCE):
        df = fetch_close_prices_from_Binance(symbol.binance_name, limit) 
    if (symbol.source_id == SourceID.COINGECKO):
        df = fetch_coingecko_price(symbol.symbol_name)
    return df

if __name__ == "__main__":
    symbol = Symbol(
        symbol_id=1,  # Added required field
        symbol_name="BTC-USDT",
        full_name="Bitcoin",  # Added required field
        kucoin_name="BTC-USDT",
        binance_name="BTCUSDT",
        source_id=SourceID.BINANCE
    )

    close_prices = fetch_close_prices(symbol, 14)
    if isinstance(close_prices, pd.DataFrame):  # Handle DataFrame correctly
        for index, row in close_prices.iterrows():
            print(f"Date: {index}, Close: {row['close']}")