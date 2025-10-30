import pandas as pd

from infra.telegram_logging_handler import app_logger
from technical_analysis.repositories.daily_candle_repository import (
    DailyCandleRepository,
)
from technical_analysis.repositories.rsi_repository import (
    save_rsi_by_timeframe,
)
from technical_analysis.rsi import calculate_rsi_using_rma


def calculate_rsi_for_candles(candles, _timeframe="daily"):
    """Calculate RSI for a list of candles

    Args:
        candles (list): List of candle objects
        timeframe (str): The timeframe of the candles ("daily", "hourly", "fifteen_min")

    Returns:
        dict: Dictionary with candle_id as keys and RSI values as values

    """
    if not candles:
        return {}

    # Create DataFrame from candles
    df = pd.DataFrame(
        [
            {
                "Date": candle.end_date,
                "close": candle.close,
                "candle_id": candle.id,  # Assumes each candle has an id attribute
            }
            for candle in candles
        ]
    )

    # Sort by date
    df.set_index("Date", inplace=True)
    df.sort_index(inplace=True)

    # Calculate RSI for the entire series
    df["RSI"] = calculate_rsi_using_rma(df["close"])

    # Create dictionary mapping candle_id to RSI value
    rsi_results = {}
    for _, row in df.iterrows():
        if not pd.isna(row["RSI"]):
            rsi_results[int(row["candle_id"])] = float(row["RSI"])

    return rsi_results


def update_rsi_for_all_candles(conn, symbols, candle_fetcher, timeframe="daily"):
    """Calculate and update RSI for all candles of multiple symbols

    Args:
        conn: Database connection
        symbols (list): List of Symbol objects
        candle_fetcher (function): Function to fetch candles for a symbol
        timeframe (str): The timeframe of the candles ("daily", "hourly", "fifteen_min")

    """
    for symbol in symbols:
        try:
            # Fetch candles for the symbol
            candles = candle_fetcher(symbol, conn)

            if not candles:
                app_logger.warning(f"No {timeframe} candles found for {symbol.symbol_name}")
                continue

            # Calculate RSI
            rsi_results = calculate_rsi_for_candles(candles, timeframe)

            # Save RSI values
            for candle_id, rsi_value in rsi_results.items():
                try:
                    save_rsi_by_timeframe(conn, candle_id, rsi_value, timeframe)
                    app_logger.info(
                        f"Saved {timeframe} RSI for {symbol.symbol_name} "
                        f"candle {candle_id}: RSI={rsi_value:.2f}"
                    )
                except Exception as e:
                    app_logger.error(
                        f"Failed to save {timeframe} RSI results for candle {candle_id}: {e!s}"
                    )

        except Exception as e:
            app_logger.error(f"Error processing {timeframe} RSI for {symbol.symbol_name}: {e!s}")


def update_daily_rsi_for_all_symbols(conn, symbols):
    """Calculate and update RSI for all daily candles of multiple symbols

    Args:
        conn: Database connection
        symbols (list): List of Symbol objects

    """

    def fetch_all_daily_candles(symbol, conn):
        daily_candle_repository = DailyCandleRepository(conn)
        return daily_candle_repository.get_all_candles(symbol)

    update_rsi_for_all_candles(conn, symbols, fetch_all_daily_candles, "daily")


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import fetch_symbols

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)

    # Update RSI for all timeframes
    update_daily_rsi_for_all_symbols(conn, symbols)

    # Examples for hourly and fifteen-minute candles
    # These would need to be implemented based on your existing candle fetching functions
    # update_rsi_for_all_candles(conn, symbols, fetch_hourly_candles, "hourly")
    # update_rsi_for_all_candles(conn, symbols, fetch_fifteen_min_candles, "fifteen_min")
