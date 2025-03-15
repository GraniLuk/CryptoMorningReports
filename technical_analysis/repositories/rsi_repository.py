from datetime import date, timedelta

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


def get_candles_with_rsi(conn, symbol_id: int, from_date) -> list:
    """
    Fetches candle data with RSI for a specific symbol,
    only returning records on or after the specified date.

    Args:
        conn: Database connection
        symbol_id (int): Symbol ID to filter the data
        from_date: The start date to filter the candles (inclusive)

    Returns:
        list: List of dictionaries containing the candle and RSI data
    """
    try:
        if conn:
            cursor = conn.cursor()
            query = """
                SELECT 
                    dc.SymbolId,
                    dc.EndDate as date,
                    r.RSI,
                    dc.[Close],
                    dc.[Open],
                    dc.High,
                    dc.Low
                FROM DailyCandles dc
                LEFT JOIN RSI r ON dc.ID = r.DailyCandleID
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
                f"Successfully fetched candle data with RSI for symbol_id {symbol_id} starting from {from_date}"
            )
            return results

    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while fetching candle data with RSI: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error fetching candle data with RSI: {str(e)}")
        raise


def get_historical_rsi(conn, symbol_id: int, date: date) -> dict:
    """
    Fetches RSI values for current date, yesterday, and week ago for a symbol

    Args:
        conn: Database connection
        symbol_id (int): Symbol ID to fetch RSI for
        date: The current date to compare from

    Returns:
        dict: Dictionary containing current, yesterday and week ago RSI values
    """
    try:
        if conn:
            cursor = conn.cursor()
            query = """
                SELECT 
                    dc.EndDate as IndicatorDate,
                    r.RSI
                FROM DailyCandles dc
                LEFT JOIN RSI r ON dc.ID = r.DailyCandleID
                WHERE dc.SymbolID = ? 
                AND dc.EndDate IN (
                    ?,              -- Current date
                    DATEADD(day, -1, ?),  -- Yesterday
                    DATEADD(day, -7, ?)   -- Week ago
                )
                ORDER BY dc.EndDate DESC
            """
            cursor.execute(query, (symbol_id, date, date, date))

            results = {}
            for row in cursor.fetchall():
                if row[0] == date:
                    results["current"] = float(row[1])
                elif row[0] == date - timedelta(days=1):
                    results["yesterday"] = float(row[1])
                elif row[0] == date - timedelta(days=7):
                    results["week_ago"] = float(row[1])

            cursor.close()
            return results

    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while fetching historical RSI: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error fetching historical RSI: {str(e)}")
        raise
