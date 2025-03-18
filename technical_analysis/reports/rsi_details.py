from datetime import date, timedelta

import pandas as pd
from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from source_repository import Symbol
from technical_analysis.repositories.rsi_repository import get_candles_with_rsi


def create_rsi_table_for_symbol(
    symbol: Symbol, conn, target_date: date = None
) -> PrettyTable:
    """
    Creates RSI table for a symbol using daily candles data for the last 30 days,
    identifies divergences, and checks for RSI trendline breakouts.
    """
    target_date = target_date or date.today()
    all_values = pd.DataFrame()

    try:
        # Get 30 days of data with RSI values
        start_date = target_date - timedelta(days=30)
        candles_with_rsi = get_candles_with_rsi(conn, symbol.symbol_id, start_date)
        print(candles_with_rsi[0])

        if not candles_with_rsi:
            return None

        # Create DataFrame from candles
        df = pd.DataFrame(candles_with_rsi)
        df.set_index("date", inplace=True)
        df.sort_index(inplace=True)
        df["symbol"] = symbol.symbol_name

        if not df.empty:
            # Identify Divergences
            df["bullish_divergence"] = detect_bullish_divergence(df)
            df["bearish_divergence"] = detect_bearish_divergence(df)

            # Check RSI Trendline Breakouts
            df["rsi_breakout"] = detect_rsi_breakout(df)

            # Calculate daily and weekly RSI changes
            df["rsi_daily_change"] = df["RSI"].diff()
            df["rsi_weekly_change"] = df["RSI"] - df["RSI"].shift(7)

            all_values = df

            app_logger.info(
                "%s: Last Price=%f, RSI=%f",
                symbol.symbol_name,
                df["Close"].iloc[-1],
                df["RSI"].iloc[-1],
            )
    except Exception as e:
        app_logger.error(f"Error processing {symbol.symbol_name}: {str(e)}")

    # Create PrettyTable output
    rsi_table = PrettyTable()
    rsi_table.field_names = [
        "Date",
        "Symbol",
        "Price",
        "RSI",
        "24h Change",
        "7d Change",
        "Bullish Div",
        "Bearish Div",
        "RSI Breakout",
    ]

    for date_idx, row in all_values.iterrows():
        rsi_table.add_row(
            [
                date_idx.strftime("%Y-%m-%d"),
                row["symbol"],
                f"${float(row['Close']):,.2f}",
                f"{float(row['RSI']):.2f}",
                f"{row['rsi_daily_change']:+.2f}"
                if pd.notna(row["rsi_daily_change"])
                else "N/A",
                f"{row['rsi_weekly_change']:+.2f}"
                if pd.notna(row["rsi_weekly_change"])
                else "N/A",
                bool(row["bullish_divergence"]),
                bool(row["bearish_divergence"]),
                bool(row["rsi_breakout"]),
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
            and df["Close"].iloc[i] < df["Close"].iloc[i - 1]
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
            and df["Close"].iloc[i] > df["Close"].iloc[i - 1]
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
