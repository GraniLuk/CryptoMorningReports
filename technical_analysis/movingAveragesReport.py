from collections import namedtuple
from datetime import date, timedelta
from typing import List

import pandas as pd
from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from sharedCode.priceChecker import fetch_daily_candles
from source_repository import Symbol
from technical_analysis.repositories.moving_averages_repository import (
    fetch_yesterday_moving_averages,
    save_moving_averages_results,
)


def calculate_indicators(
    symbols: List[Symbol], conn, target_date: date
) -> tuple[PrettyTable, PrettyTable]:
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
    yesterdayValues = fetch_yesterday_moving_averages(conn, target_date)

    for symbol in symbols:
        try:
            app_logger.info(
                "Processing symbol: %s for date %s", symbol.symbol_name, target_date
            )

            # Get historical data from database
            start_date = target_date - timedelta(days=200)
            candles = fetch_daily_candles(symbol, start_date, target_date, conn)

            if not candles:
                app_logger.warning(
                    f"No data available for {symbol.symbol_name} on {target_date}"
                )
                continue

            # Create DataFrame from candles
            df = pd.DataFrame(
                [{"Close": candle.close, "Date": candle.end_date} for candle in candles]
            )
            df.set_index("Date", inplace=True)

            if df.empty:
                app_logger.warning(
                    f"No data available for {symbol.symbol_name} up to {target_date}"
                )
                continue

            app_logger.info(
                "Retrieved %d data points for %s", len(df), symbol.symbol_name
            )

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
            target_MA50 = df["MA50"].iloc[-1]
            target_MA200 = df["MA200"].iloc[-1]
            target_EMA50 = df["EMA50"].iloc[-1]
            target_EMA200 = df["EMA200"].iloc[-1]

            # Add warning indicator if using shorter periods
            period_warning = ""
            if available_periods < 200:
                period_warning = "⚠️"  # Add warning emoji for shortened periods
                app_logger.warning(
                    f"{symbol.symbol_name} using shortened periods due to limited history: {available_periods} days"
                )

            # Initialize status indicators
            ma50_status = (
                f"🟢{period_warning}"
                if target_price > target_MA50
                else f"🔴{period_warning}"
            )
            ma200_status = (
                f"🟢{period_warning}"
                if target_price > target_MA200
                else f"🔴{period_warning}"
            )
            ema50_status = (
                f"🟢{period_warning}"
                if target_price > target_EMA50
                else f"🔴{period_warning}"
            )
            ema200_status = (
                f"🟢{period_warning}"
                if target_price > target_EMA200
                else f"🔴{period_warning}"
            )

            # Initialize cross status
            ma_cross_status = ""
            ema_cross_status = ""

            # Check for crossovers if we have previous day's data
            if not yesterdayValues.empty:
                yesterday_data = yesterdayValues[
                    yesterdayValues["SymbolName"] == symbol.symbol_name
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

                    # MA Crossovers
                    if yesterday_price < yesterday_ma50 and target_price > target_MA50:
                        ma50_status = "🚨🟢"
                        app_logger.info(f"{symbol.symbol_name} crossed above MA50")
                    elif (
                        yesterday_price > yesterday_ma50 and target_price < target_MA50
                    ):
                        ma50_status = "🚨🔴"
                        app_logger.info(f"{symbol.symbol_name} crossed below MA50")

                    if (
                        yesterday_price < yesterday_ma200
                        and target_price > target_MA200
                    ):
                        ma200_status = "🚨🟢"
                        app_logger.info(f"{symbol.symbol_name} crossed above MA200")
                    elif (
                        yesterday_price > yesterday_ma200
                        and target_price < target_MA200
                    ):
                        ma200_status = "🚨🔴"
                        app_logger.info(f"{symbol.symbol_name} crossed below MA200")

                    # EMA Crossovers
                    if (
                        yesterday_price < yesterday_ema50
                        and target_price > target_EMA50
                    ):
                        ema50_status = "🚨🟢"
                        app_logger.info(f"{symbol.symbol_name} crossed above EMA50")
                    elif (
                        yesterday_price > yesterday_ema50
                        and target_price < target_EMA50
                    ):
                        ema50_status = "🚨🔴"
                        app_logger.info(f"{symbol.symbol_name} crossed below EMA50")

                    if (
                        yesterday_price < yesterday_ema200
                        and target_price > target_EMA200
                    ):
                        ema200_status = "🚨🟢"
                        app_logger.info(f"{symbol.symbol_name} crossed above EMA200")
                    elif (
                        yesterday_price > yesterday_ema200
                        and target_price < target_EMA200
                    ):
                        ema200_status = "🚨🔴"
                        app_logger.info(f"{symbol.symbol_name} crossed below EMA200")

                    # Add Golden/Death Cross detection for MA
                    if yesterday_ma50 < yesterday_ma200 and target_MA50 > target_MA200:
                        ma_cross_status = "⚡️🟡"  # Golden Cross
                        app_logger.info(
                            f"{symbol.symbol_name} MA Golden Cross detected"
                        )
                    elif (
                        yesterday_ma50 > yesterday_ma200 and target_MA50 < target_MA200
                    ):
                        ma_cross_status = "💀"  # Death Cross
                        app_logger.info(f"{symbol.symbol_name} MA Death Cross detected")

                    # Add Golden/Death Cross detection for EMA
                    if (
                        yesterday_ema50 < yesterday_ema200
                        and target_EMA50 > target_EMA200
                    ):
                        ema_cross_status = "⚡️🟡"  # Golden Cross
                        app_logger.info(
                            f"{symbol.symbol_name} EMA Golden Cross detected"
                        )
                    elif (
                        yesterday_ema50 > yesterday_ema200
                        and target_EMA50 < target_EMA200
                    ):
                        ema_cross_status = "💀"  # Death Cross
                        app_logger.info(
                            f"{symbol.symbol_name} EMA Death Cross detected"
                        )

            # Store the results
            ma_values.append(
                MAData(
                    symbol=symbol.symbol_name,
                    current_price=target_price,
                    ma50=target_MA50,
                    ma200=target_MA200,
                    ma50_status=ma50_status,
                    ma200_status=ma200_status,
                    cross_status=ma_cross_status,
                )
            )

            ema_values.append(
                EMAData(
                    symbol=symbol.symbol_name,
                    current_price=target_price,
                    ema50=target_EMA50,
                    ema200=target_EMA200,
                    ema50_status=ema50_status,
                    ema200_status=ema200_status,
                    cross_status=ema_cross_status,
                )
            )

            # Save to database
            if conn:
                try:
                    save_moving_averages_results(
                        conn=conn,
                        symbol_id=symbol.symbol_id,
                        current_price=target_price,
                        ma50=target_MA50,
                        ma200=target_MA200,
                        ema50=target_EMA50,
                        ema200=target_EMA200,
                        indicator_date=target_date,
                    )
                except Exception as e:
                    app_logger.error(
                        f"Failed to save moving averages results for {symbol.symbol_name}: {str(e)}"
                    )

        except Exception as e:
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
        # Count total digits excluding decimal point
        total_digits = sum(c.isdigit() for c in str_price)

        if total_digits > 6:
            # If more than 6 digits, round to appropriate decimal places
            decimal_idx = str_price.find(".")
            if decimal_idx == -1:
                return str(round(price))[:6]  # No decimal point
            else:
                before_decimal = decimal_idx
                allowed_after_decimal = 6 - before_decimal
                return f"{price:.{max(0, allowed_after_decimal)}f}"
        return str_price

    # Fill both tables
    for ma_row, ema_row in zip(ma_values, ema_values):
        ma_table.add_row(
            [
                ma_row.symbol,
                format_price(ma_row.current_price),
                f"{format_price(ma_row.ma50)} {ma_row.ma50_status}",
                f"{format_price(ma_row.ma200)} {ma_row.ma200_status}",
                ma_row.cross_status,
            ]
        )

        ema_table.add_row(
            [
                ema_row.symbol,
                format_price(ema_row.current_price),
                f"{format_price(ema_row.ema50)} {ema_row.ema50_status}",
                f"{format_price(ema_row.ema200)} {ema_row.ema200_status}",
                ema_row.cross_status,
            ]
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
    calculate_indicators(symbols, conn, target_date=date.today())
