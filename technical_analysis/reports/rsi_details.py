from datetime import date, timedelta

import pandas as pd
from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from sharedCode.priceChecker import fetch_daily_candles
from source_repository import Symbol
from technical_analysis.repositories.rsi_repository import get_historical_rsi
from technical_analysis.rsi import calculate_rsi_using_RMA


def create_rsi_table_for_symbol(
    symbol: Symbol, conn, target_date: date = None
) -> PrettyTable:
    """
    Creates RSI table for a given symbol using daily candles data,
    identifies divergences, and checks for RSI trendline breakouts.
    """
    target_date = target_date or date.today()
    all_values = pd.DataFrame()

    try:
        # Get 30 days of data for divergence analysis
        start_date = target_date - timedelta(days=30)
        candles = fetch_daily_candles(symbol, start_date, target_date, conn)

        if not candles:
            return None

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
            # Calculate RSI
            df["RSI"] = calculate_rsi_using_RMA(df["close"])

            # Identify Divergences
            df["bullish_divergence"] = detect_bullish_divergence(df)
            df["bearish_divergence"] = detect_bearish_divergence(df)

            # Check RSI Trendline Breakouts
            df["rsi_breakout"] = detect_rsi_breakout(df)

            # Create a proper copy of the latest row
            latest_row = df.iloc[[-1]].copy()
            latest_date = latest_row.index[-1]

            # Fetch historical RSI values
            historical_rsi = get_historical_rsi(conn, symbol.symbol_id, latest_date)

            # Calculate RSI changes
            rsi_value = float(latest_row["RSI"].iloc[-1])
            latest_row.loc[:, "rsi_daily_change"] = rsi_value - historical_rsi.get(
                "yesterday", rsi_value
            )
            latest_row.loc[:, "rsi_weekly_change"] = rsi_value - historical_rsi.get(
                "week_ago", rsi_value
            )

            all_values = pd.concat([all_values, latest_row])

            app_logger.info(
                "%s: Price=%f, RSI=%f",
                symbol.symbol_name,
                latest_row["close"].iloc[-1],
                latest_row["RSI"].iloc[-1],
            )
    except Exception as e:
        app_logger.error(f"Error processing {symbol.symbol_name}: {str(e)}")

    # Create PrettyTable output
    rsi_table = PrettyTable()
    rsi_table.field_names = [
        "Symbol",
        "Current Price",
        "RSI",
        "24h Change",
        "7d Change",
        "Bullish Divergence",
        "Bearish Divergence",
        "RSI Breakout",
    ]

    for _, row in all_values.iterrows():
        symbol = row["symbol"]
        price = float(row["close"])
        rsi = float(row["RSI"])
        daily_change = float(row["rsi_daily_change"])
        weekly_change = float(row["rsi_weekly_change"])
        bullish_divergence = bool(row["bullish_divergence"])
        bearish_divergence = bool(row["bearish_divergence"])
        rsi_breakout = bool(row["rsi_breakout"])

        rsi_table.add_row(
            [
                symbol,
                f"${price:,.2f}",
                f"{rsi:.2f}",
                f"{daily_change:+.2f}",
                f"{weekly_change:+.2f}",
                bullish_divergence,
                bearish_divergence,
                rsi_breakout,
            ]
        )

    return rsi_table


def detect_bullish_divergence(df):
    """
    Detects bullish divergence: RSI forms higher lows while price forms lower lows.
    """
    bullish_divergence_flags = []
    for i in range(1, len(df) - 1):
        # Compare current and previous RSI values (higher lows)
        if (
            df["RSI"].iloc[i] > df["RSI"].iloc[i - 1]
            and df["close"].iloc[i] < df["close"].iloc[i - 1]
        ):
            bullish_divergence_flags.append(True)
        else:
            bullish_divergence_flags.append(False)

    return (
        [False] + bullish_divergence_flags + [False]
    )  # Add False for first and last rows


def detect_bearish_divergence(df):
    """
    Detects bearish divergence: RSI forms lower highs while price forms higher highs.
    """
    bearish_divergence_flags = []
    for i in range(1, len(df) - 1):
        # Compare current and previous RSI values (lower highs)
        if (
            df["RSI"].iloc[i] < df["RSI"].iloc[i - 1]
            and df["close"].iloc[i] > df["close"].iloc[i - 1]
        ):
            bearish_divergence_flags.append(True)
        else:
            bearish_divergence_flags.append(False)

    return (
        [False] + bearish_divergence_flags + [False]
    )  # Add False for first and last rows


def detect_rsi_breakout(df):
    """
    Detects RSI trendline breakout by checking if the current RSI value breaks above/below key levels.
    """
    breakout_flags = []

    # Draw trendlines based on recent peaks/troughs (simple implementation)
    recent_rsis = df["RSI"].tail(5)  # Consider last 5 days of RSI values
    resistance_level = max(
        recent_rsis
    )  # Resistance is the highest value in the last 5 days
    support_level = min(recent_rsis)  # Support is the lowest value in the last 5 days

    for i in range(len(df)):
        if i >= len(df) - 5:  # Only check breakouts in the last few rows
            if df["RSI"].iloc[i] > resistance_level:
                breakout_flags.append(True)  # Breakout above resistance level
            elif df["RSI"].iloc[i] < support_level:
                breakout_flags.append(True)  # Breakdown below support level
            else:
                breakout_flags.append(False)
        else:
            breakout_flags.append(False)

    return breakout_flags


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import Symbol, fetch_symbols

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)
    symbol = [symbol for symbol in symbols if symbol.symbol_name == "BTC"][0]
    print(create_rsi_table_for_symbol(symbol, conn))
