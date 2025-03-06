from datetime import date, timedelta

import pyodbc

from infra.telegram_logging_handler import app_logger


def save_rsi_results(
    conn, symbol_id: int, indicator_date, closed_price: float, rsi: float
) -> None:
    """
    Saves RSI results to the database

    Args:
        conn: Database connection
        symbol_id (int): Symbol ID from Symbols table
        indicator_date: The date for the RSI indicator
        closed_price (float): Current closing price
        rsi (float): Calculated RSI value
    """
    try:
        if conn:
            cursor = conn.cursor()
            query = """
                MERGE INTO RSI AS target
                USING (SELECT ? AS SymbolID, ? AS IndicatorDate, ? AS ClosedPrice, ? AS RSI) 
                    AS source (SymbolID, IndicatorDate, ClosedPrice, RSI)
                ON target.SymbolID = source.SymbolID AND target.IndicatorDate = source.IndicatorDate
                WHEN MATCHED THEN
                    UPDATE SET ClosedPrice = source.ClosedPrice, RSI = source.RSI
                WHEN NOT MATCHED THEN
                    INSERT (SymbolID, IndicatorDate, ClosedPrice, RSI)
                    VALUES (source.SymbolID, source.IndicatorDate, source.ClosedPrice, source.RSI);
            """
            cursor.execute(query, (symbol_id, indicator_date, closed_price, rsi))
            conn.commit()
            cursor.close()
            app_logger.info(
                f"Successfully saved RSI results to database for symbol_id {symbol_id}"
            )
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving RSI results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving RSI results: {str(e)}")
        raise


def get_candles_with_rsi(conn, symbol_id: int, from_date) -> list:
    """
    Fetches candle data with RSI for a specific symbol from the CandleWithRsiView,
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
                    SymbolId,
                    date,
                    RSI,
                    [Close],
                    [Open],
                    High,
                    Low
                FROM CandleWithRsiView
                WHERE SymbolId = ? AND date >= ?
                ORDER BY date DESC
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
                    IndicatorDate,
                    RSI
                FROM RSI
                WHERE SymbolID = ? 
                AND IndicatorDate IN (
                    ?,              -- Current date
                    DATEADD(day, -1, ?),  -- Yesterday
                    DATEADD(day, -7, ?)   -- Week ago
                )
                ORDER BY IndicatorDate DESC
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
