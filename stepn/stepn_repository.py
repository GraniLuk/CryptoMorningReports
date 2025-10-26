import math
import os
from datetime import UTC, date
from typing import Any

import pyodbc

from infra.telegram_logging_handler import app_logger


def _is_sqlite() -> bool:
    """Check if we're using SQLite database"""
    return os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"


def _sanitize_float(value: Any) -> float | None:
    """Coerce incoming numeric-like values to a finite float or return None.

    This defends against values that SQL Server rejects (e.g. NaN, inf, empty strings,
    objects) which can surface as the generic ODBC error about invalid float instance.
    """
    if value is None:
        return None
    try:
        # Reject empty strings / whitespace
        if isinstance(value, str) and value.strip() == "":
            return None
        f = float(value)
        if not math.isfinite(f):  # NaN, inf, -inf -> store NULL
            return None
        return f
    except (ValueError, TypeError):
        return None


def _sanitize_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def save_stepn_results(
    conn,
    gmt_price: float,
    gst_price: float,
    ratio: float,
    ema: float,
    min_24h: float,
    max_24h: float,
    range_24h: float,
    rsi: float,
    transactions_count: int,
) -> None:
    """
    Saves STEPN results to the database

    Args:
        conn: Database connection
        gmt_price (float): Current GMT price
        gst_price (float): Current GST price
        ratio (float): GMT/GST ratio
        EMA14 (float): EMA14 value
        min_24h (float, optional): Minimum value in the last 24 hours
        max_24h (float, optional): Maximum value in the last 24 hours
        range_24h (float, optional): Range in the last 24 hours
        rsi (float, optional): RSI calculated based on EMA
        transactions_count (int, optional): Number of transactions from previous day
    """
    try:
        if conn:
            cursor = conn.cursor()

            # Sanitize all incoming numeric parameters
            sanitized_params = {
                "gmt_price": _sanitize_float(gmt_price),
                "gst_price": _sanitize_float(gst_price),
                "ratio": _sanitize_float(ratio),
                "ema": _sanitize_float(ema),
                "min_24h": _sanitize_float(min_24h),
                "max_24h": _sanitize_float(max_24h),
                "range_24h": _sanitize_float(range_24h),
                "rsi": _sanitize_float(rsi),
                "transactions_count": _sanitize_int(transactions_count),
            }

            app_logger.debug(
                "Prepared STEPN params: %s",
                ", ".join(f"{k}={v}" for k, v in sanitized_params.items()),
            )

            if _is_sqlite():
                # SQLite version - use INSERT OR REPLACE
                from datetime import datetime

                today = datetime.now(UTC).date().isoformat()

                query = """
                    INSERT OR REPLACE INTO StepNResults
                    (GMTPrice, GSTPrice, Ratio, Date, EMA14, Min24Value, Max24Value, Range24, RSI, TransactionsCount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(
                    query,
                    (
                        sanitized_params["gmt_price"],
                        sanitized_params["gst_price"],
                        sanitized_params["ratio"],
                        today,
                        sanitized_params["ema"],
                        sanitized_params["min_24h"],
                        sanitized_params["max_24h"],
                        sanitized_params["range_24h"],
                        sanitized_params["rsi"],
                        sanitized_params["transactions_count"],
                    ),
                )
            else:
                # SQL Server version - use MERGE
                query = """
                    MERGE INTO StepNResults AS target
                    USING (
                        SELECT ? AS GMTPrice, ? AS GSTPrice, ? AS Ratio,
                               CAST(GETDATE() AS DATE) AS Date, ? AS EMA14,
                               ? AS Min24Value, ? AS Max24Value, ? AS Range24,
                               ? AS RSI, ? AS TransactionsCount
                    ) AS source (GMTPrice, GSTPrice, Ratio, Date, EMA14, Min24Value, Max24Value, Range24, RSI, TransactionsCount)
                    ON target.Date = source.Date
                    WHEN MATCHED THEN
                        UPDATE SET
                            GMTPrice = source.GMTPrice,
                            GSTPrice = source.GSTPrice,
                            Ratio = source.Ratio,
                            EMA14 = source.EMA14,
                            Min24Value = source.Min24Value,
                            Max24Value = source.Max24Value,
                            Range24 = source.Range24,
                            RSI = source.RSI,
                            TransactionsCount = source.TransactionsCount
                    WHEN NOT MATCHED THEN
                        INSERT (GMTPrice, GSTPrice, Ratio, Date, EMA14, Min24Value, Max24Value, Range24, RSI, TransactionsCount)
                        VALUES (source.GMTPrice, source.GSTPrice, source.Ratio, source.Date,
                                source.EMA14, source.Min24Value, source.Max24Value, source.Range24, source.RSI, source.TransactionsCount);
                """
                cursor.execute(
                    query,
                    (
                        sanitized_params["gmt_price"],
                        sanitized_params["gst_price"],
                        sanitized_params["ratio"],
                        sanitized_params["ema"],
                        sanitized_params["min_24h"],
                        sanitized_params["max_24h"],
                        sanitized_params["range_24h"],
                        sanitized_params["rsi"],
                        sanitized_params["transactions_count"],
                    ),
                )

            conn.commit()
            cursor.close()
            app_logger.info("Successfully upserted STEPN results to database")
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving STEPN results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving STEPN results: {e!s}")
        raise


def fetch_stepn_results_last_14_days(
    conn,
) -> list[tuple[float, float, float, date]] | None:
    """
    Fetches STEPN results from the last 14 days from the database.

    Args:
        conn: Database connection

    Returns:
        list of tuples: Each tuple contains the columns from the StepNResults table.
    """
    try:
        if conn:
            cursor = conn.cursor()

            if _is_sqlite():
                # SQLite version - use date() function
                query = """
                    SELECT GMTPrice, GSTPrice, Ratio, Date
                    FROM StepNResults
                    WHERE Date >= date('now', '-14 days')
                    ORDER BY Date DESC;
                """
            else:
                # SQL Server version - use DATEADD
                query = """
                    SELECT GMTPrice, GSTPrice, Ratio, Date
                    FROM StepNResults
                    WHERE Date >= DATEADD(DAY, -14, CAST(GETDATE() AS DATE))
                    ORDER BY Date DESC;
                """

            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            app_logger.info("Successfully fetched STEPN results from the last 14 days")
            return results
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while fetching STEPN results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error fetching STEPN results: {e!s}")
        raise
