from datetime import date, timedelta
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
    import time  # Add this import at the top

    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import Symbol, fetch_symbols

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)
    # Define start and end dates for January 2025
    start_date = date(2024, 12, 4)
    end_date = date(2024, 12, 31)

    # Loop through each day
    current_date = start_date
    while current_date <= end_date:
        print(f"Fetching data for {current_date}")
        candles = fetch_daily_candles(symbols, conn, current_date)
        # Process your candles here

        print("Waitin 60 seconds before next execution...")
        time.sleep(30)  # Wait for 60 seconds (1 minute)
        current_date += timedelta(days=1)
