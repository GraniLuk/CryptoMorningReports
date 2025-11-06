"""Moving averages analysis and reporting for cryptocurrency markets."""

from collections import namedtuple
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

import pandas as pd
from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from shared_code.price_checker import fetch_daily_candles
from source_repository import Symbol
from technical_analysis.repositories.moving_averages_repository import (
    fetch_yesterday_moving_averages,
    save_moving_averages_results,
)


if TYPE_CHECKING:
    import logging

    import pyodbc

    from infra.sql_connection import SQLiteConnectionWrapper


def _detect_crossover(
    yesterday_price: float,
    target_price: float,
    yesterday_ma: float,
    target_ma: float,
    symbol_name: str,
    logger: "logging.Logger",
) -> str:
    """Detect crossover and return updated status."""
    if yesterday_price < yesterday_ma and target_price > target_ma:
        logger.info("%s crossed above MA", symbol_name)
        return "🚨🟢"
    if yesterday_price > yesterday_ma and target_price < target_ma:
        logger.info("%s crossed below MA", symbol_name)
        return "🚨🔴"

    return "🟢" if target_price > target_ma else "🔴"


def _detect_golden_death_cross(
    yesterday_short: float,
    target_short: float,
    yesterday_long: float,
    target_long: float,
    symbol_name: str,
    indicator_type: str,
    logger: "logging.Logger",
) -> str:
    """Detect golden or death cross."""
    if yesterday_short < yesterday_long and target_short > target_long:
        logger.info("%s %s Golden Cross detected", symbol_name, indicator_type)
        return "⚡️🟡"  # Golden Cross
    if yesterday_short > yesterday_long and target_short < target_long:
        logger.info("%s %s Death Cross detected", symbol_name, indicator_type)
        return "💀"  # Death Cross
    return ""


def calculate_indicators(
    symbols: list[Symbol],
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None",
    target_date: date,
) -> tuple[PrettyTable, PrettyTable]:
    """Calculate moving averages and RSI indicators for cryptocurrency symbols."""
    # If no date provided, use today's date
    ma_values = []
    ema_values = []
    MAData = namedtuple(
        "MAData",
        [
            "symbol",
            "current_price",
            "ma50",
            "ma200",
            "ma50_status",
            "ma200_status",
            "cross_status",
        ],
    )
    EMAData = namedtuple(
        "EMAData",
        [
            "symbol",
            "current_price",
            "ema50",
            "ema200",
            "ema50_status",
            "ema200_status",
            "cross_status",
        ],
    )

    # Fetch previous day's values (relative to target_date)
    yesterday_values = fetch_yesterday_moving_averages(conn, target_date)

    for symbol in symbols:
        try:
            app_logger.info("Processing symbol: %s for date %s", symbol.symbol_name, target_date)

            # Get historical data from database
            start_date = target_date - timedelta(days=200)
            candles = fetch_daily_candles(symbol, start_date, target_date, conn)

            if not candles:
                app_logger.warning(f"No data available for {symbol.symbol_name} on {target_date}")
                continue

            # Create DataFrame from candles
            df = pd.DataFrame(
                [{"Close": candle.close, "Date": candle.end_date} for candle in candles],
            )
            df = df.set_index("Date")

            if df.empty:
                app_logger.warning(
                    f"No data available for {symbol.symbol_name} up to {target_date}",
                )
                continue

            app_logger.info("Retrieved %d data points for %s", len(df), symbol.symbol_name)

            # For new symbols (VIRTUAL, TON), adjust the MA/EMA periods based on available data
            available_periods = len(df)
            ma50_period = min(50, available_periods)
            ma200_period = min(200, available_periods)

            # Calculate indicators with adjusted periods
            df["MA50"] = df["Close"].rolling(window=ma50_period).mean()
            df["MA200"] = df["Close"].rolling(window=ma200_period).mean()
            df["EMA50"] = df["Close"].ewm(span=ma50_period, adjust=False).mean()
            df["EMA200"] = df["Close"].ewm(span=ma200_period, adjust=False).mean()

            # Get values for target date (last row of filtered DataFrame)
            target_price = df["Close"].iloc[-1]
            target_ma50 = df["MA50"].iloc[-1]
            target_ma200 = df["MA200"].iloc[-1]
            target_ema50 = df["EMA50"].iloc[-1]
            target_ema200 = df["EMA200"].iloc[-1]

            # Add warning indicator if using shorter periods
            min_recommended_periods = 200
            period_warning = ""
            if available_periods < min_recommended_periods:
                period_warning = "⚠️"  # Add warning emoji for shortened periods
                app_logger.warning(
                    f"{symbol.symbol_name} using shortened periods due to "
                    f"limited history: {available_periods} days",
                )

            # Initialize status indicators
            ma50_status = (
                f"🟢{period_warning}" if target_price > target_ma50 else f"🔴{period_warning}"
            )
            ma200_status = (
                f"🟢{period_warning}" if target_price > target_ma200 else f"🔴{period_warning}"
            )
            ema50_status = (
                f"🟢{period_warning}" if target_price > target_ema50 else f"🔴{period_warning}"
            )
            ema200_status = (
                f"🟢{period_warning}" if target_price > target_ema200 else f"🔴{period_warning}"
            )

            # Initialize cross status
            ma_cross_status = ""
            ema_cross_status = ""

            # Check for crossovers if we have previous day's data
            if not yesterday_values.empty:
                yesterday_data = yesterday_values[
                    yesterday_values["SymbolName"] == symbol.symbol_name
                ]
                if not yesterday_data.empty:
                    # Extract series with explicit type annotations to help type checker
                    price_series: pd.Series = yesterday_data["CurrentPrice"]
                    ma50_series: pd.Series = yesterday_data["MA50"]
                    ma200_series: pd.Series = yesterday_data["MA200"]
                    ema50_series: pd.Series = yesterday_data["EMA50"]
                    ema200_series: pd.Series = yesterday_data["EMA200"]

                    yesterday_price = price_series.iloc[0]
                    yesterday_ma50 = ma50_series.iloc[0]
                    yesterday_ma200 = ma200_series.iloc[0]
                    yesterday_ema50 = ema50_series.iloc[0]
                    yesterday_ema200 = ema200_series.iloc[0]

                    # MA Crossovers using helper functions
                    ma50_status = _detect_crossover(
                        yesterday_price,
                        target_price,
                        yesterday_ma50,
                        target_ma50,
                        symbol.symbol_name,
                        app_logger,
                    )
                    ma200_status = _detect_crossover(
                        yesterday_price,
                        target_price,
                        yesterday_ma200,
                        target_ma200,
                        symbol.symbol_name,
                        app_logger,
                    )

                    # EMA Crossovers using helper functions
                    ema50_status = _detect_crossover(
                        yesterday_price,
                        target_price,
                        yesterday_ema50,
                        target_ema50,
                        symbol.symbol_name,
                        app_logger,
                    )
                    ema200_status = _detect_crossover(
                        yesterday_price,
                        target_price,
                        yesterday_ema200,
                        target_ema200,
                        symbol.symbol_name,
                        app_logger,
                    )

                    # Add Golden/Death Cross detection for MA and EMA
                    ma_cross_status = _detect_golden_death_cross(
                        yesterday_ma50,
                        target_ma50,
                        yesterday_ma200,
                        target_ma200,
                        symbol.symbol_name,
                        "MA",
                        app_logger,
                    )
                    ema_cross_status = _detect_golden_death_cross(
                        yesterday_ema50,
                        target_ema50,
                        yesterday_ema200,
                        target_ema200,
                        symbol.symbol_name,
                        "EMA",
                        app_logger,
                    )

            # Store the results
            ma_values.append(
                MAData(
                    symbol=symbol.symbol_name,
                    current_price=target_price,
                    ma50=target_ma50,
                    ma200=target_ma200,
                    ma50_status=ma50_status,
                    ma200_status=ma200_status,
                    cross_status=ma_cross_status,
                ),
            )

            ema_values.append(
                EMAData(
                    symbol=symbol.symbol_name,
                    current_price=target_price,
                    ema50=target_ema50,
                    ema200=target_ema200,
                    ema50_status=ema50_status,
                    ema200_status=ema200_status,
                    cross_status=ema_cross_status,
                ),
            )

            # Save to database
            if conn:
                try:
                    save_moving_averages_results(
                        conn=conn,
                        symbol_id=symbol.symbol_id,
                        current_price=target_price,
                        ma50=target_ma50,
                        ma200=target_ma200,
                        ema50=target_ema50,
                        ema200=target_ema200,
                        indicator_date=target_date,
                    )
                except (KeyError, ValueError, TypeError, OSError) as e:
                    app_logger.error(
                        f"Failed to save moving averages results for {symbol.symbol_name}: {e!s}",
                    )

        except (KeyError, ValueError, TypeError, IndexError, AttributeError) as e:
            app_logger.error(
                "Error processing moving average for symbol %s: %s",
                symbol.symbol_name,
                str(e),
            )

    # Create MA table
    ma_table = PrettyTable()
    ma_table.field_names = ["Symbol", "Current", "MA50", "MA200", "Cross"]

    # Create EMA table
    ema_table = PrettyTable()
    ema_table.field_names = ["Symbol", "Current", "EMA50", "EMA200", "Cross"]

    # Format numbers just before displaying in table
    def format_price(price):
        # Convert to string with standard notation (no scientific)
        str_price = f"{price:.10f}"
        # Remove trailing zeros after decimal
        str_price = str_price.rstrip("0").rstrip(".")
        # Count total digits in the price (excluding decimal point)
        total_digits = sum(c.isdigit() for c in str_price)

        max_significant_digits = 6
        if total_digits > max_significant_digits:
            # If more than 6 digits, round to appropriate decimal places
            decimal_idx = str_price.find(".")
            if decimal_idx == -1:
                return str(round(price))[:6]  # No decimal point
            before_decimal = decimal_idx
            allowed_after_decimal = 6 - before_decimal
            return f"{price:.{max(0, allowed_after_decimal)}f}"
        return str_price

    # Fill both tables
    for ma_row, ema_row in zip(ma_values, ema_values, strict=False):
        ma_table.add_row(
            [
                ma_row.symbol,
                format_price(ma_row.current_price),
                f"{format_price(ma_row.ma50)} {ma_row.ma50_status}",
                f"{format_price(ma_row.ma200)} {ma_row.ma200_status}",
                ma_row.cross_status,
            ],
        )

        ema_table.add_row(
            [
                ema_row.symbol,
                format_price(ema_row.current_price),
                f"{format_price(ema_row.ema50)} {ema_row.ema50_status}",
                f"{format_price(ema_row.ema200)} {ema_row.ema200_status}",
                ema_row.cross_status,
            ],
        )

    return ma_table, ema_table


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
        coingecko_name="bitcoin",  # Added required field
    )

    symbols = [symbol]
    calculate_indicators(symbols, conn, target_date=datetime.now(UTC).date())
