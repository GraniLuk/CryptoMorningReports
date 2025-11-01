"""RSI (Relative Strength Index) calculation utilities.

This module provides various implementations of RSI calculations for technical analysis,
including different smoothing methods and timeframes.
"""

import pandas as pd

from infra.telegram_logging_handler import app_logger
from technical_analysis.repositories.daily_candle_repository import (
    DailyCandleRepository,
)
from technical_analysis.repositories.rsi_repository import (
    save_rsi_results,
)


def calculate_rsi(series, window=14):
    """Calculate RSI using simple moving averages.

    Args:
        series: pandas Series of prices (typically close prices)
        window: Period for RSI calculation (default 14)

    Returns:
        pandas Series of RSI values (0-100)

    """
    delta = series.diff()

    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_rsi_using_ema(series, period=14):
    """Calculate RSI using exponential moving averages.

    Args:
        series: pandas Series of prices (typically close prices)
        period: Period for RSI calculation (default 14)

    Returns:
        pandas Series of RSI values (0-100)

    """
    # Calculate price changes
    delta = series.diff()

    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Calculate EMA of gains and losses
    avg_gain = calculate_ema(gain, period)
    avg_loss = calculate_ema(loss, period)

    # Calculate RS
    rs = avg_gain / avg_loss

    # Calculate RSI
    return 100 - (100 / (1 + rs))


def calculate_ema(series, period):
    """Calculate exponential moving average.

    Args:
        series: pandas Series of values
        period: Period for EMA calculation

    Returns:
        pandas Series of EMA values

    """
    # 'com' stands for center of mass; with com = period - 1, alpha becomes 1/period
    return series.ewm(com=period - 1, adjust=False).mean()


def calculate_rsi_using_rma(series, periods=14):
    """Calculate RSI using Wilder's smoothing (RMA - Relative Moving Average).

    This is the standard RSI calculation method used by TradingView and most platforms.

    The calculation:
    1. Calculate price changes (delta)
    2. Separate into gains and losses
    3. Use Wilder's smoothing: First average is SMA, then smooth with formula:
       new_avg = (old_avg * (n-1) + current_value) / n

    Args:
        series: pandas Series of prices (typically close prices)
        periods: RSI period (default 14, standard for RSI)

    Returns:
        pandas Series of RSI values (0-100)

    """
    delta = series.diff()

    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Initialize series for average gain/loss
    avg_gain = pd.Series(index=gain.index, dtype=float)
    avg_loss = pd.Series(index=loss.index, dtype=float)

    # Need at least 'periods + 1' data points for RSI calculation
    if len(series) <= periods:
        # Return NaN series if insufficient data
        return pd.Series([float("nan")] * len(series), index=series.index)

    # Calculate initial SMA for the first 'periods' values
    avg_gain.iloc[periods] = gain.iloc[1 : periods + 1].mean()
    avg_loss.iloc[periods] = loss.iloc[1 : periods + 1].mean()

    # Use Wilder's smoothing for subsequent values
    # Formula: new_avg = (old_avg * (n-1) + current_value) / n
    for i in range(periods + 1, len(series)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (periods - 1) + gain.iloc[i]) / periods
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (periods - 1) + loss.iloc[i]) / periods

    # Calculate RS and RSI
    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


def calculate_all_rsi_for_symbol(conn, symbol):
    """Calculate and save RSI for all daily candles of a symbol for the current year."""
    # Fetch all daily candles for the symbol
    daily_candle_repository = DailyCandleRepository(conn)
    all_daily_candles = daily_candle_repository.get_all_candles(symbol)

    if not all_daily_candles:
        app_logger.error(f"No daily candles found for {symbol.symbol_name}")
        return

    # Create DataFrame from candles: assumes each candle has attributes 'end_date' and 'close'
    df = pd.DataFrame(
        [
            {
                "Date": candle.end_date,
                "close": candle.close,
                "daily_candle_id": candle.id,  # Make sure Candle object includes ID
            }
            for candle in all_daily_candles
        ]
    )
    df = df.set_index("Date")
    df = df.sort_index()

    # Calculate RSI for entire series using your EMA based method
    df["RSI"] = calculate_rsi_using_rma(df["close"])

    # Save RSI results for each day in the current year
    for _, row in df.iterrows():
        rsi_val = row["RSI"]
        daily_candle_id: int = int(row["daily_candle_id"])

        # Skip if RSI is NaN
        if pd.isna(rsi_val):
            app_logger.error(f"Invalid RSI value for candle_id {daily_candle_id}")
            continue

        try:
            save_rsi_results(conn=conn, daily_candle_id=daily_candle_id, rsi=float(rsi_val))
            app_logger.info(
                f"Saved RSI for {symbol.symbol_name} candle {daily_candle_id}: RSI={rsi_val:.2f}"
            )
        except Exception as e:
            app_logger.error(f"Failed to save RSI results for candle {daily_candle_id}: {e!s}")


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import fetch_symbols

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)
    # symbols = [symbol for symbol in symbols if symbol.symbol_name == "XRP"]
    # Define start and end dates for January 2025
    # for symbol in symbols:
    # calculate_all_rsi_for_symbol(conn, symbol=symbol)
    # create_rsi_table(symbols, conn)
