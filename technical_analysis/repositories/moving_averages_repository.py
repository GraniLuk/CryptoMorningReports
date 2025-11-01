"""Moving averages data repository for cryptocurrency markets."""

import os
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

import pandas as pd
import pyodbc

from infra.telegram_logging_handler import app_logger


if TYPE_CHECKING:
    from infra.sql_connection import SQLiteConnectionWrapper


def save_moving_averages_results(
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None",
    symbol_id: int,
    current_price: float,
    ma50: float,
    ma200: float,
    ema50: float,
    ema200: float,
    indicator_date: date,
) -> None:
    """Save moving averages results to the database.

    Args:
        conn: Database connection
        symbol_id (int): Symbol ID from Symbols table
        current_price (float): Current price
        ma50 (float): 50-day moving average
        ma200 (float): 200-day moving average
        ema50 (float): 50-day exponential moving average
        ema200 (float): 200-day exponential moving average
        indicator_date (date): Date of the moving averages

    """
    try:
        if conn:
            indicator_date = indicator_date or datetime.now(UTC).date()
            cursor = conn.cursor()

            # Check if we're using SQLite or SQL Server
            is_sqlite = os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"

            if is_sqlite:
                # SQLite uses INSERT OR REPLACE
                query = """
                    INSERT OR REPLACE INTO MovingAverages
                    (SymbolID, IndicatorDate, CurrentPrice, MA50, MA200, EMA50, EMA200)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """
            else:
                # SQL Server uses MERGE
                query = """
                    MERGE INTO MovingAverages AS target
                    USING (SELECT ? AS SymbolID, ? AS IndicatorDate,
                                 ? AS CurrentPrice, ? AS MA50, ? AS MA200,
                                 ? AS EMA50, ? AS EMA200)
                        AS source (SymbolID, IndicatorDate, CurrentPrice,
                                   MA50, MA200, EMA50, EMA200)
                    ON target.SymbolID = source.SymbolID AND target.IndicatorDate
                       = source.IndicatorDate
                    WHEN MATCHED THEN
                        UPDATE SET CurrentPrice = source.CurrentPrice,
                                 MA50 = source.MA50,
                                 MA200 = source.MA200,
                                 EMA50 = source.EMA50,
                                 EMA200 = source.EMA200
                    WHEN NOT MATCHED THEN
                        INSERT (SymbolID, IndicatorDate, CurrentPrice, MA50, MA200, EMA50, EMA200)
                        VALUES (source.SymbolID, source.IndicatorDate, source.CurrentPrice,
                               source.MA50, source.MA200, source.EMA50, source.EMA200);
                """

            cursor.execute(
                query,
                (symbol_id, indicator_date, current_price, ma50, ma200, ema50, ema200),
            )
            conn.commit()
            cursor.close()
            app_logger.info(
                f"Successfully saved moving averages results to database for symbol_id {symbol_id}",
            )
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving moving averages results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving moving averages results: {e!s}")
        raise


def fetch_yesterday_moving_averages(
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None",
    target_date: date,
) -> pd.DataFrame:
    """Fetch all moving averages records from yesterday.

    Args:
        conn: Database connection
        target_date (date): Date of the moving averages

    Returns:
        pd.DataFrame: DataFrame containing yesterday's moving averages data with columns:
            SymbolID, IndicatorDate, CurrentPrice, MA50, MA200, EMA50, EMA200

    """
    try:
        if conn:
            target_date = target_date or datetime.now(UTC).date()
            yesterday = target_date - timedelta(days=1)

            query = """
                SELECT ma.SymbolID, s.SymbolName, ma.IndicatorDate, ma.CurrentPrice,
                       ma.MA50, ma.MA200, ma.EMA50, ma.EMA200
                FROM MovingAverages ma
                JOIN Symbols s ON ma.SymbolID = s.SymbolID
                WHERE ma.IndicatorDate = ?
            """

            df = pd.read_sql(query, conn, params=[yesterday])
            app_logger.info(
                f"Successfully fetched {len(df)} moving averages records for {yesterday}",
            )
            return df
        return pd.DataFrame()
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while fetching yesterday's moving averages: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error fetching yesterday's moving averages: {e!s}")
        raise


def fetch_moving_averages_for_symbol(
    conn: "pyodbc.Connection | SQLiteConnectionWrapper | None",
    symbol_id: int,
    lookback_days: int = 7,
) -> pd.DataFrame:
    """Fetch moving averages records for a specific symbol for the past N days.

    Args:
        conn: Database connection
        symbol_id (int): Symbol ID from Symbols table
        lookback_days (int): Number of days to look back for data

    Returns:
        pd.DataFrame: DataFrame containing moving averages data for the specified
            symbol with columns: SymbolID, SymbolName, IndicatorDate, CurrentPrice,
            MA50, MA200, EMA50, EMA200

    """
    try:
        if conn:
            target_date = datetime.now(UTC).date()
            start_date = target_date - timedelta(days=lookback_days)

            query = """
                SELECT ma.SymbolID, s.SymbolName, ma.IndicatorDate, ma.CurrentPrice,
                       ma.MA50, ma.MA200, ma.EMA50, ma.EMA200
                FROM MovingAverages ma
                JOIN Symbols s ON ma.SymbolID = s.SymbolID
                WHERE ma.SymbolID = ? AND ma.IndicatorDate >= ?
                ORDER BY ma.IndicatorDate
            """

            df = pd.read_sql(query, conn, params=[symbol_id, start_date])
            app_logger.info(
                f"Successfully fetched {len(df)} moving averages records for symbol_id {symbol_id}",
            )
            return df
        return pd.DataFrame()
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while fetching moving averages for symbol: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error fetching moving averages for symbol: {e!s}")
        raise
