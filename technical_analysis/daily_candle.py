"""Daily candle data processing and analysis for cryptocurrency markets."""

from datetime import UTC, date, datetime, timedelta

from shared_code.common_price import Candle
from shared_code.price_checker import fetch_daily_candle
from shared_code.price_checker import (
    fetch_daily_candles as fetch_daily_candles_for_symbol,
)
from source_repository import Symbol
from technical_analysis.repositories.daily_candle_repository import (
    DailyCandleRepository,
)


def fetch_daily_candles(
    symbols: list[Symbol],
    conn,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[Candle]:
    """Fetches daily candles for given symbols and returns a list of Candle objects.

    Args:
        symbols: List of Symbol objects
        conn: Database connection
        start_date: Start date for fetching candles (defaults to 7 days before end_date)
        end_date: End date for fetching candles (defaults to current date)

    Returns:
        List of Candle objects

    """
    end_date = end_date or datetime.now(UTC).date()
    start_date = start_date or (end_date - timedelta(days=7))

    all_candles = []
    for symbol in symbols:
        symbol_candles = fetch_daily_candles_for_symbol(symbol, start_date, end_date, conn)
        all_candles.extend(symbol_candles)

    return all_candles


def check_if_all_candles(symbol, conn):
    repo = DailyCandleRepository(conn)
    all_candles = repo.get_all_candles(symbol)

    # Parse the oldest date from string
    if all_candles:
        oldest_date_str = all_candles[0].end_date
        if isinstance(oldest_date_str, str):
            oldest_date = datetime.fromisoformat(
                oldest_date_str.replace("Z", "+00:00").split("T")[0]
            ).date()
        else:
            oldest_date = oldest_date_str if isinstance(oldest_date_str, date) else date(2017, 1, 1)
    else:
        oldest_date = date(2017, 1, 1)

    if oldest_date:
        print(f"Oldest candle date: {oldest_date}")
    end_date = datetime.now(UTC).date()
    current_date = oldest_date
    while current_date <= end_date:
        print(f"Fetching data for {current_date}")

        # Compare dates properly - convert end_date string to date for comparison
        from_db = next(
            (
                item
                for item in all_candles
                if (
                    datetime.fromisoformat(
                        item.end_date.replace("Z", "+00:00").split("T")[0]
                    ).date()
                    if isinstance(item.end_date, str)
                    else item.end_date
                )
                == current_date
            ),
            None,
        )
        if from_db is None:
            fetch_daily_candle(symbol, current_date, conn)
            print("Fetched from API")
        # Process your candles here
        current_date += timedelta(days=1)


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import Symbol, fetch_symbols

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)
    # Define start and end dates for January 2025
    for symbol in symbols:
        print(f"Checking candles for {symbol}")
        check_if_all_candles(symbol, conn)
