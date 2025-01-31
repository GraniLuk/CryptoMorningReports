import pandas as pd
from sharedCode.binance import fetch_close_prices_from_Binance
from sharedCode.coingecko import fetch_coingecko_price
from source_repository import SourceID
from kucoin import fetch_close_prices_from_Kucoin

def fetch_close_prices(symbol: str, limit: int = 14) -> pd.DataFrame:
    if (symbol.source_id == SourceID.KUCOIN):
        df = fetch_close_prices_from_Kucoin(symbol.kucoin_name)
    if (symbol.source_id == SourceID.BINANCE):
        df = fetch_close_prices_from_Binance(symbol.binance_name)
    if (symbol.source_id == SourceID.COINGECKO):
        df = fetch_coingecko_price(symbol.symbol_name)
    return df
