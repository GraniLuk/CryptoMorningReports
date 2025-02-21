from datetime import date, timedelta
from typing import List

import pandas as pd
from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from sharedCode.priceChecker import fetch_daily_candles
from source_repository import Symbol
from technical_analysis.repositories.rsi_repository import save_rsi_results
from technical_analysis.repositories.daily_candle_repository import DailyCandleRepository


def create_rsi_table(
    symbols: List[Symbol], conn, target_date: date = None
) -> PrettyTable:
    """
    Creates RSI table for given symbols using daily candles data
    """
    target_date = target_date or date.today()
    all_values = pd.DataFrame()

    for symbol in symbols:
        try:
            # Get 15 days of data for 14-period RSI calculation
            start_date = target_date - timedelta(days=15)
            candles = fetch_daily_candles(symbol, start_date, target_date, conn)

            if not candles:
                continue

            # Create DataFrame from candles
            df = pd.DataFrame(
                [
                    {
                        "Date": candle.end_date,
                        "close": candle.close,
                        "symbol": symbol.symbol_name,
                    }
                    for candle in candles
                ]
            )
            df.set_index("Date", inplace=True)
            df.sort_index(inplace=True)

            if not df.empty:
                df["RSI"] = calculate_rsi_using_EMA(df["close"])
                # Take only latest row
                latest_row = df.iloc[-1:]
                # Get the date from the index
                latest_date = latest_row.index[-1]
                all_values = pd.concat([all_values, latest_row])

                # Save to database if connection is available
                if conn:
                    try:
                        save_rsi_results(
                            conn=conn,
                            symbol_id=symbol.symbol_id,
                            indicator_date=latest_date,
                            closed_price=float(latest_row["close"].iloc[-1]),
                            rsi=float(latest_row["RSI"].iloc[-1]),
                        )
                    except Exception as e:
                        app_logger.error(
                            f"Failed to save RSI results for {symbol.symbol_name}: {str(e)}"
                        )

                app_logger.info(
                    "%s: Price=%f, RSI=%f",
                    symbol.symbol_name,
                    latest_row["close"].iloc[-1],
                    latest_row["RSI"].iloc[-1],
                )
        except Exception as e:
            app_logger.error(f"Error processing {symbol.symbol_name}: {str(e)}")

    # Sort by RSI descending
    all_values = all_values.sort_values("RSI", ascending=False)

    # Create table
    rsi_table = PrettyTable()
    rsi_table.field_names = ["Symbol", "Current Price", "RSI"]

    for _, row in all_values.iterrows():
        symbol = row["symbol"]
        price = float(row["close"])
        rsi = float(row["RSI"])
        rsi_table.add_row([symbol, f"${price:,.2f}", f"{rsi:.2f}"])

    return rsi_table


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
    return series.ewm(com=period-1, adjust=False).mean()

def calculate_rsi_using_RMA(series, periods=14):
    delta = series.diff()

    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    alpha = 1.0 / periods

    avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

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
            {"Date": candle.end_date, "close": candle.close} 
            for candle in all_daily_candles
        ]
    )
    df.set_index("Date", inplace=True)
    df.sort_index(inplace=True)

# Calculate RSI for entire series using your EMA based method
    df["RSI"] = calculate_rsi_using_EMA(df["close"])

    # Save RSI results for each day in the current year
    for day, row in df.iterrows():
        close_val = row["close"]
        rsi_val = row["RSI"]

        # Skip if RSI or close price is NaN
        if pd.isna(close_val) or pd.isna(rsi_val):
            app_logger.error(
                f"Invalid values for {symbol.symbol_name} on {day}: close={close_val}, RSI={rsi_val}"
            )
            continue

        try:
            save_rsi_results(
                conn=conn,
                symbol_id=symbol.symbol_id,
                indicator_date=day,
                closed_price=float(close_val),
                rsi=float(rsi_val),
            )
            app_logger.info(
                f"Saved RSI for {symbol.symbol_name} on {day}: Price=${close_val:.2f}, RSI={rsi_val:.2f}"
            )
        except Exception as e:
            app_logger.error(
                f"Failed to save RSI results for {symbol.symbol_name} on {day}: {str(e)}"
            )


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import Symbol, fetch_symbols, SourceID

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)
    # Define start and end dates for January 2025
    for symbol in symbols:
        calculate_all_rsi_for_symbol(conn, symbol=symbol)


