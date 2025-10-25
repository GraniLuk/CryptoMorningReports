import os
from datetime import date

import pyodbc

from infra.telegram_logging_handler import app_logger


def save_price_range_results(
    conn, symbol_id: int, low_price: float, high_price: float, range_percent: float
) -> None:
    """
    Saves price range results to the database

    Args:
        conn: Database connection
        symbol_id (int): Symbol ID from Symbols table
        low_price (float): 24h low price
        high_price (float): 24h high price
        range_percent (float): Price range percentage
    """
    try:
        if conn:
            cursor = conn.cursor()

            # Check if we're using SQLite or SQL Server
            is_sqlite = os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"

            # Get current date
            today = date.today()

            if is_sqlite:
                # SQLite uses INSERT OR REPLACE
                query = """
                    INSERT OR REPLACE INTO PriceRange 
                    (SymbolID, IndicatorDate, LowPrice, HighPrice, RangePercent)
                    VALUES (?, ?, ?, ?, ?)
                """
                cursor.execute(query, (symbol_id, today.isoformat(), low_price, high_price, range_percent))
            else:
                # SQL Server uses MERGE
                query = """
                    MERGE INTO PriceRange AS target
                    USING (SELECT ? AS SymbolID, CAST(GETDATE() AS DATE) AS IndicatorDate, 
                                 ? AS LowPrice, ? AS HighPrice, ? AS RangePercent) 
                        AS source (SymbolID, IndicatorDate, LowPrice, HighPrice, RangePercent)
                    ON target.SymbolID = source.SymbolID AND target.IndicatorDate = source.IndicatorDate
                    WHEN MATCHED THEN
                        UPDATE SET LowPrice = source.LowPrice, 
                                 HighPrice = source.HighPrice, 
                                 RangePercent = source.RangePercent
                    WHEN NOT MATCHED THEN
                        INSERT (SymbolID, IndicatorDate, LowPrice, HighPrice, RangePercent)
                        VALUES (source.SymbolID, source.IndicatorDate, source.LowPrice, 
                               source.HighPrice, source.RangePercent);
                """
                cursor.execute(query, (symbol_id, low_price, high_price, range_percent))
            
            conn.commit()
            cursor.close()
            app_logger.info(
                f"Successfully saved price range results to database for symbol_id {symbol_id}"
            )
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving price range results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving price range results: {str(e)}")
        raise
