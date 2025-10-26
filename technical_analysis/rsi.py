import pandas as pd

from infra.telegram_logging_handler import app_logger
from technical_analysis.repositories.daily_candle_repository import (
    DailyCandleRepository,
)
from technical_analysis.repositories.rsi_repository import (
    save_rsi_results,
)


def calculate_rsi(series, window=14):
    delta = series.diff()

    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_rsi_using_EMA(series, period=14):
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
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_ema(series, period):
    # 'com' stands for center of mass; with com = period - 1, alpha becomes 1/period
    return series.ewm(com=period - 1, adjust=False).mean()


def calculate_rsi_using_RMA(series, periods=14):
    delta = series.diff()

    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    alpha = 1.0 / periods

    avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = (
        100
        if avg_loss.iloc[-1] == 0
        else 0
        if avg_gain.iloc[-1] == 0
        else 100 - (100 / (1 + rs))
    )

    return rsi


def calculate_all_rsi_for_symbol(conn, symbol):
    """
    Calculate RSI using calculate_rsi_using_EMA for all days in the current year
    for the given symbol and save the results using save_rsi_results.
    """
    # Fetch all daily candles for the symbol
    dailyCandleRepository = DailyCandleRepository(conn)
    all_daily_candles = dailyCandleRepository.get_all_candles(symbol)

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
    df.set_index("Date", inplace=True)
    df.sort_index(inplace=True)

    # Calculate RSI for entire series using your EMA based method
    df["RSI"] = calculate_rsi_using_RMA(df["close"])

    # Save RSI results for each day in the current year
    for _, row in df.iterrows():
        rsi_val = row["RSI"]
        daily_candle_id: int = int(row["daily_candle_id"])

        # Skip if RSI is NaN
        if pd.isna(rsi_val):
            app_logger.error(f"Invalid RSI value for candle_id {daily_candle_id}")
            continue

        try:
            save_rsi_results(
                conn=conn, daily_candle_id=daily_candle_id, rsi=float(rsi_val)
            )
            app_logger.info(
                f"Saved RSI for {symbol.symbol_name} candle {daily_candle_id}: RSI={rsi_val:.2f}"
            )
        except Exception as e:
            app_logger.error(
                f"Failed to save RSI results for candle {daily_candle_id}: {e!s}"
            )


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
