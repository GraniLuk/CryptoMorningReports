"""Detailed RSI analysis and reporting for cryptocurrency markets."""

from datetime import date, timedelta

import pandas as pd
from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from source_repository import Symbol
from technical_analysis.repositories.rsi_repository import get_candles_with_rsi


def create_rsi_table_for_symbol(symbol: Symbol, conn, target_date: date) -> PrettyTable | None:
    """Create RSI table for a symbol using daily candles data for the last 30 days.

    identifies divergences, and checks for RSI trendline breakouts.
    """
    all_values = pd.DataFrame()

    try:
        # Get 30 days of data with RSI values
        start_date = target_date - timedelta(days=30)
        candles_with_rsi = get_candles_with_rsi(conn, symbol.symbol_id, start_date)

        if not candles_with_rsi:
            return None

        # Create DataFrame from candles
        df = pd.DataFrame(candles_with_rsi)
        df = df.set_index("date")
        df = df.sort_index()
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
    except Exception as e:  # noqa: BLE001
        app_logger.error(f"Error processing {symbol.symbol_name}: {e!s}")

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
        if isinstance(date_idx, pd.Timestamp):
            date_str = date_idx.strftime("%Y-%m-%d")
        else:
            date_str = str(date_idx)

        rsi_table.add_row(
            [
                date_str,
                row["symbol"],
                f"${float(row['Close']):,.2f}",
                f"{float(row['RSI']):.2f}",
                f"{row['rsi_daily_change']:+.2f}" if pd.notna(row["rsi_daily_change"]) else "N/A",
                f"{row['rsi_weekly_change']:+.2f}" if pd.notna(row["rsi_weekly_change"]) else "N/A",
                bool(row["bullish_divergence"]),
                bool(row["bearish_divergence"]),
                bool(row["rsi_breakout"]),
            ],
        )

    return rsi_table


def detect_bullish_divergence(df):
    """Detect bullish divergence: RSI forms higher lows while price forms lower lows.

    Looks for pattern over a 5-day window.
    """
    window = 5
    bullish_divergence_flags = []

    for i in range(window, len(df)):
        # Get the window of data to analyze
        price_window = df["Close"].iloc[i - window : i + 1]
        rsi_window = df["RSI"].iloc[i - window : i + 1]

        # Find local minima
        price_min_idx = price_window.idxmin()
        rsi_min_idx = rsi_window.idxmin()

        # Check if price made lower low but RSI made higher low
        if (
            price_window.iloc[-1] < price_window.min()
            and rsi_window.iloc[-1] > rsi_window.min()
            and price_min_idx < rsi_min_idx
        ):  # Ensure price bottom came before RSI bottom
            bullish_divergence_flags.append(True)
        else:
            bullish_divergence_flags.append(False)

    # Add False for the initial window periods where we couldn't calculate divergence
    return [False] * window + bullish_divergence_flags


def detect_bearish_divergence(df):
    """Detect bearish divergence: RSI forms lower highs while price forms higher highs.

    Looks for pattern over a 5-day window.
    """
    window = 5
    bearish_divergence_flags = []

    for i in range(window, len(df)):
        # Get the window of data to analyze
        price_window = df["Close"].iloc[i - window : i + 1]
        rsi_window = df["RSI"].iloc[i - window : i + 1]

        # Find local maxima
        price_max_idx = price_window.idxmax()
        rsi_max_idx = rsi_window.idxmax()

        # Check if price made higher high but RSI made lower high
        if (
            price_window.iloc[-1] > price_window.max()
            and rsi_window.iloc[-1] < rsi_window.max()
            and price_max_idx < rsi_max_idx
        ):  # Ensure price peak came before RSI peak
            bearish_divergence_flags.append(True)
        else:
            bearish_divergence_flags.append(False)

    # Add False for the initial window periods where we couldn't calculate divergence
    return [False] * window + bearish_divergence_flags


def detect_rsi_breakout(df):
    """Detect RSI trendline breakout by checking if the current RSI value.

    breaks above/below key levels.
    """
    breakout_flags = []

    # Draw trendlines based on recent peaks/troughs (simple implementation)
    recent_rsis = df["RSI"].tail(5)  # Consider last 5 days of RSI values
    resistance_level = max(recent_rsis)  # Resistance is the highest value in the last 5 days
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
    for _symbol in symbols:
        pass
