from datetime import date
from typing import List

from sharedCode.commonPrice import Candle
from sharedCode.priceChecker import fetch_daily_candle
from source_repository import Symbol


def fetch_daily_candles(
    symbols: List[Symbol], conn, end_date: date = None
) -> List[Candle]:
    """
    Fetches daily candles for given symbols and returns a list of Candle objects
    """
    end_date = end_date or date.today()

    candles = []
    for symbol in symbols:
        candle = fetch_daily_candle(symbol, end_date, conn)
        if candle is not None:
            candles.append(candle)

    return candles


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import Symbol, fetch_symbols

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)
    candles = fetch_daily_candles(symbols, conn, date(2025, 2, 8))
    print(candles)
