from datetime import date, timedelta
from typing import Optional

import pyodbc

from infra.telegram_logging_handler import app_logger


def save_rsi_results(conn, daily_candle_id: int, rsi: float) -> None:
    """
    Saves RSI results to the database

    Args:
        conn: Database connection
        daily_candle_id (int): DailyCandle ID from DailyCandles table
        rsi (float): Calculated RSI value
    """
    try:
        if conn:
            cursor = conn.cursor()
            query = """
                MERGE INTO RSI AS target
                USING (SELECT ? AS DailyCandleID, ? AS RSI) 
                    AS source (DailyCandleID, RSI)
                ON target.DailyCandleID = source.DailyCandleID
                WHEN MATCHED THEN
                    UPDATE SET RSI = source.RSI
                WHEN NOT MATCHED THEN
                    INSERT (DailyCandleID, RSI)
                    VALUES (source.DailyCandleID, source.RSI);
            """
            cursor.execute(query, (daily_candle_id, rsi))
            conn.commit()
            cursor.close()
            app_logger.info(
                f"Successfully saved RSI results to database for daily_candle_id {daily_candle_id}"
            )
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving RSI results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving RSI results: {str(e)}")
        raise


def save_rsi_by_timeframe(
    conn, candle_id: int, rsi: float, timeframe: str = "daily"
) -> None:
    """
    Saves RSI results to the database for different timeframes

    Args:
        conn: Database connection
        candle_id (int): Candle ID from the respective candles table
        rsi (float): Calculated RSI value
        timeframe (str): Timeframe type ("daily", "hourly", "fifteen_min")
    """
    try:
        if conn:
            cursor = conn.cursor()

            # Map timeframe to the correct table
            table_map = {
                "daily": "RSI",
                "hourly": "HourlyRSI",
                "fifteen_min": "FifteenMinRSI",
            }

            # Map timeframe to the correct ID column name
            id_column_map = {
                "daily": "DailyCandleID",
                "hourly": "HourlyCandleID",
                "fifteen_min": "FifteenMinCandleID",
            }

            table_name = table_map.get(timeframe.lower())
            id_column = id_column_map.get(timeframe.lower())

            if not table_name or not id_column:
                raise ValueError(f"Invalid timeframe: {timeframe}")

            query = f"""
                MERGE INTO {table_name} AS target
                USING (SELECT ? AS {id_column}, ? AS RSI) 
                    AS source ({id_column}, RSI)
                ON target.{id_column} = source.{id_column}
                WHEN MATCHED THEN
                    UPDATE SET RSI = source.RSI
                WHEN NOT MATCHED THEN
                    INSERT ({id_column}, RSI)
                    VALUES (source.{id_column}, source.RSI);
            """
            cursor.execute(query, (candle_id, rsi))
            conn.commit()
            cursor.close()
            app_logger.info(
                f"Successfully saved {timeframe} RSI results to database for candle_id {candle_id}"
            )
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving {timeframe} RSI results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving {timeframe} RSI results: {str(e)}")
        raise


def get_candles_with_rsi(
    conn, symbol_id: int, from_date, timeframe: str = "daily"
) -> Optional[list]:
    """
    Fetches candle data with RSI for a specific symbol,
    only returning records on or after the specified date.

    Args:
        conn: Database connection
        symbol_id (int): Symbol ID to filter the data
        from_date: The start date to filter the candles (inclusive)
        timeframe (str): Timeframe type ("daily", "hourly", "fifteen_min")

    Returns:
        list: List of dictionaries containing the candle and RSI data
    """
    try:
        if conn:
            cursor = conn.cursor()

            # Map timeframe to the correct tables
            table_map = {
                "daily": ("DailyCandles", "RSI", "DailyCandleID"),
                "hourly": ("HourlyCandles", "HourlyRSI", "HourlyCandleID"),
                "fifteen_min": (
                    "FifteenMinCandles",
                    "FifteenMinRSI",
                    "FifteenMinCandleID",
                ),
            }

            candle_table, rsi_table, id_column = table_map.get(
                timeframe.lower(), table_map["daily"]
            )

            query = f"""
                SELECT 
                    dc.SymbolId,
                    dc.EndDate as date,
                    r.RSI,
                    dc.[Close],
                    dc.[Open],
                    dc.High,
                    dc.Low
                FROM {candle_table} dc
                LEFT JOIN {rsi_table} r ON dc.ID = r.{id_column}
                WHERE dc.SymbolId = ? AND dc.EndDate >= ?
                ORDER BY dc.EndDate DESC
            """
            cursor.execute(query, symbol_id, from_date)

            # Fetch column names
            columns = [column[0] for column in cursor.description]

            # Fetch all rows and convert to list of dictionaries
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            cursor.close()
            app_logger.info(
                f"Successfully fetched {timeframe} candle data with RSI for symbol_id {symbol_id} starting from {from_date}"
            )
            return results

    except pyodbc.Error as e:
        app_logger.error(
            f"ODBC Error while fetching {timeframe} candle data with RSI: {e}"
        )
        raise
    except Exception as e:
        app_logger.error(f"Error fetching {timeframe} candle data with RSI: {str(e)}")
        raise


def get_historical_rsi(
    conn, symbol_id: int, date: date, timeframe: str = "daily"
) -> dict:
    """
    Fetches RSI values for current date, yesterday, and week ago for a symbol

    Args:
        conn: Database connection
        symbol_id (int): Symbol ID to fetch RSI for
        date: The current date to compare from
        timeframe (str): Timeframe type ("daily", "hourly", "fifteen_min")

    Returns:
        dict: Dictionary containing current, yesterday and week ago RSI values
    """
    results = {}  # Initialize empty results dictionary
    
    try:
        if conn:
            cursor = conn.cursor()

            # Map timeframe to the correct tables and time intervals
            table_map = {
                "daily": ("DailyCandles", "RSI", "DailyCandleID", 1, 7),
                "hourly": ("HourlyCandles", "HourlyRSI", "HourlyCandleID", 1, 24),
                "fifteen_min": (
                    "FifteenMinCandles",
                    "FifteenMinRSI",
                    "FifteenMinCandleID",
                    4,
                    4 * 24,
                ),
            }

            candle_table, rsi_table, id_column, previous_interval, week_interval = (
                table_map.get(timeframe.lower(), table_map["daily"])
            )

            # Adjust interval keywords based on timeframe
            interval_keyword = (
                "day"
                if timeframe.lower() == "daily"
                else "hour"
                if timeframe.lower() == "hourly"
                else "minute"
            )

            # Adjust multiplier for fifteen_min (as we need to multiply by 15)
            if timeframe.lower() == "fifteen_min":
                previous_interval *= 15
                week_interval *= 15

            query = f"""
                SELECT 
                    dc.EndDate as IndicatorDate,
                    r.RSI
                FROM {candle_table} dc
                LEFT JOIN {rsi_table} r ON dc.ID = r.{id_column}
                WHERE dc.SymbolID = ? 
                AND dc.EndDate IN (
                    DATEADD({interval_keyword}, -{previous_interval}, ?),  -- Previous interval
                    DATEADD({interval_keyword}, -{week_interval}, ?)   -- Week equivalent
                )
                ORDER BY dc.EndDate DESC
            """
            cursor.execute(query, (symbol_id, date, date))

            for row in cursor.fetchall():
                # Handle case where RSI might be None
                if row[1] is not None:
                    interval_description = (
                        "yesterday" if timeframe.lower() == "daily" else "previous"
                    )
                    week_description = (
                        "week_ago" if timeframe.lower() == "daily" else "period_ago"
                    )

                    if timeframe.lower() == "daily":
                        if row[0] == date - timedelta(days=1):
                            results[interval_description] = float(row[1])
                        elif row[0] == date - timedelta(days=7):
                            results[week_description] = float(row[1])
                    elif timeframe.lower() == "hourly":
                        if row[0] == date - timedelta(hours=1):
                            results[interval_description] = float(row[1])
                        elif row[0] == date - timedelta(hours=24):
                            results[week_description] = float(row[1])
                    elif timeframe.lower() == "fifteen_min":
                        if row[0] == date - timedelta(minutes=15):
                            results[interval_description] = float(row[1])
                        elif row[0] == date - timedelta(minutes=24 * 15):
                            results[week_description] = float(row[1])

            cursor.close()
        
        return results  # Return results dictionary (empty if conn is None or exception occurs)

    except pyodbc.Error as e:
        app_logger.error(
            f"ODBC Error while fetching historical {timeframe} RSI for symbol {symbol_id}: {e}"
        )
        raise
    except Exception as e:
        app_logger.error(
            f"Error fetching historical {timeframe} RSI for symbol {symbol_id}: {str(e)}"
        )
        raise
