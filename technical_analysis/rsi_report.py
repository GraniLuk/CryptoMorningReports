from datetime import date, timedelta
from typing import List

import pandas as pd
from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from sharedCode.priceChecker import fetch_daily_candles
from source_repository import Symbol
from technical_analysis.repositories.rsi_repository import save_rsi_results


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
                all_values = pd.concat([all_values, latest_row])

                # Save to database if connection is available
                if conn:
                    try:
                        save_rsi_results(
                            conn=conn,
                            symbol_id=symbol.symbol_id,
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


def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import SourceID, Symbol

    load_dotenv()
    conn = connect_to_sql()
    symbol = Symbol(
        symbol_id=1,  # Added required field
        symbol_name="BTC",
        full_name="Bitcoin",  # Added required field
        source_id=SourceID.BINANCE,
    )

    symbols = [symbol]
    create_rsi_table(symbols, conn)
