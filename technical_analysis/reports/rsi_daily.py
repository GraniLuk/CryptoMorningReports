from datetime import date, timedelta
from typing import List, Optional

import pandas as pd
from prettytable import PrettyTable

from infra.telegram_logging_handler import app_logger
from sharedCode.priceChecker import fetch_daily_candles
from source_repository import Symbol
from technical_analysis.repositories.rsi_repository import (
    get_historical_rsi,
    save_rsi_results,
)
from technical_analysis.rsi import calculate_rsi_using_RMA


def create_rsi_table_for_symbol(
    symbol: Symbol, conn, target_date: date
) -> Optional[PrettyTable]:
    """
    Creates RSI table for a given symbol using daily candles data
    """
    all_values = pd.DataFrame()

    try:
        # Get 15 days of data for 14-period RSI calculation
        start_date = target_date - timedelta(days=15)
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
        
        # Normalize index to timezone-naive date objects (handle mixed datetime/date/timezone types)
        df.index = pd.to_datetime(df.index, utc=True).tz_localize(None).date
        
        df.sort_index(inplace=True)

        if not df.empty:
            df["RSI"] = calculate_rsi_using_RMA(df["close"])
            # Create a proper copy of the latest row
            latest_row = df.iloc[[-1]].copy()
            # Get the date from the index
            latest_date = latest_row.index[-1]
            
            # Convert to date object for comparison (handle both datetime and date types)
            if hasattr(latest_date, 'date'):
                latest_date_for_query = latest_date.date()
            else:
                latest_date_for_query = latest_date

            # Fetch historical RSI values
            historical_rsi = get_historical_rsi(conn, symbol.symbol_id, latest_date_for_query)

            # Calculate RSI changes
            rsi_value = float(latest_row["RSI"].iloc[-1])
            # Safely get historical values with defaults
            yesterday_rsi = historical_rsi.get("yesterday")
            week_ago_rsi = historical_rsi.get("week_ago")

            # Use .loc for assignments with safe defaults
            latest_row.loc[:, "rsi_daily_change"] = (
                rsi_value - yesterday_rsi if yesterday_rsi is not None else 0.0
            )
            latest_row.loc[:, "rsi_weekly_change"] = (
                rsi_value - week_ago_rsi if week_ago_rsi is not None else 0.0
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

    rsi_table = PrettyTable()
    rsi_table.field_names = [
        "Symbol",
        "Current Price",
        "RSI",
        "24h Change",
        "7d Change",
    ]

    for _, row in all_values.iterrows():
        symbol = row["symbol"]
        price = float(row["close"])
        rsi = float(row["RSI"])
        daily_change = float(row["rsi_daily_change"])
        weekly_change = float(row["rsi_weekly_change"])

        rsi_table.add_row(
            [
                symbol,
                f"${price:,.2f}",
                f"{rsi:.2f}",
                f"{daily_change:+.2f}",
                f"{weekly_change:+.2f}",
            ]
        )

    return rsi_table


def create_rsi_table(symbols: List[Symbol], conn, target_date: date) -> PrettyTable:
    """
    Creates RSI table for given symbols using daily candles data
    """
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
            
            # Normalize index to timezone-naive date objects (handle mixed datetime/date/timezone types)
            df.index = pd.to_datetime(df.index, utc=True).tz_localize(None).date
            
            df.sort_index(inplace=True)

            if not df.empty:
                df["RSI"] = calculate_rsi_using_RMA(df["close"])
                # Create a proper copy of the latest row
                latest_row = df.iloc[[-1]].copy()
                # Get the date from the index
                latest_date = latest_row.index[-1]
                
                # Convert to date object for comparison (handle both datetime and date types)
                if hasattr(latest_date, 'date'):
                    latest_date_for_query = latest_date.date()
                else:
                    latest_date_for_query = latest_date

                # Fetch historical RSI values
                historical_rsi = get_historical_rsi(conn, symbol.symbol_id, latest_date_for_query)

                # Calculate RSI changes
                rsi_value = float(latest_row["RSI"].iloc[-1])
                # Safely get historical values with defaults
                yesterday_rsi = historical_rsi.get("yesterday")
                week_ago_rsi = historical_rsi.get("week_ago")

                # Use .loc for assignments with safe defaults
                latest_row.loc[:, "rsi_daily_change"] = (
                    rsi_value - yesterday_rsi if yesterday_rsi is not None else 0.0
                )
                latest_row.loc[:, "rsi_weekly_change"] = (
                    rsi_value - week_ago_rsi if week_ago_rsi is not None else 0.0
                )

                all_values = pd.concat([all_values, latest_row])
                # Save to database if connection is available
                if conn:
                    try:
                        save_rsi_results(
                            conn=conn,
                            daily_candle_id=candles[-1].id,
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

    # Sort by RSI descending only if we have data
    if not all_values.empty and "RSI" in all_values.columns:
        all_values = all_values.sort_values("RSI", ascending=False)
    else:
        app_logger.warning(
            "No RSI values calculated - all_values DataFrame is empty or missing RSI column"
        )

    # Create table with new columns
    rsi_table = PrettyTable()
    rsi_table.field_names = [
        "Symbol",
        "Current Price",
        "RSI",
        "24h Change",
        "7d Change",
    ]

    for _, row in all_values.iterrows():
        symbol = row["symbol"]
        price = float(row["close"])
        rsi = float(row["RSI"])
        daily_change = float(row["rsi_daily_change"])
        weekly_change = float(row["rsi_weekly_change"])

        rsi_table.add_row(
            [
                symbol,
                f"${price:,.2f}",
                f"{rsi:.2f}",
                f"{daily_change:+.2f}",
                f"{weekly_change:+.2f}",
            ]
        )

    return rsi_table


def save_rsi_for_candle(conn, daily_candle_id: int, rsi: float) -> None:
    """Helper function to save RSI value for a specific daily candle"""
    try:
        save_rsi_results(conn=conn, daily_candle_id=daily_candle_id, rsi=rsi)
    except Exception as e:
        app_logger.error(
            f"Failed to save RSI results for candle {daily_candle_id}: {str(e)}"
        )


if __name__ == "__main__":
    from dotenv import load_dotenv

    from infra.sql_connection import connect_to_sql
    from source_repository import Symbol, fetch_symbols

    load_dotenv()
    conn = connect_to_sql()
    symbols = fetch_symbols(conn)
    symbol = [symbol for symbol in symbols if symbol.symbol_name == "LINK"][0]
    print(create_rsi_table_for_symbol(symbol, conn, target_date=date.today()))
