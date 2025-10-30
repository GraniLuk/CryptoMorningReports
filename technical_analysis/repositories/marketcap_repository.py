import os
from datetime import UTC, datetime

import pyodbc

from infra.telegram_logging_handler import app_logger


def save_marketcap_results(conn, sorted_results):
    """Saves market cap results to the database once per day.

    Args:
        conn: Database connection
        sorted_results: List of dictionaries containing market cap data

    """
    try:
        if conn:
            cursor = conn.cursor()

            # Check if we're using SQLite or SQL Server
            is_sqlite = os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"

            # Get current date
            today = datetime.now(UTC).date()

            if is_sqlite:
                # SQLite uses INSERT OR REPLACE
                query = """
                    INSERT OR REPLACE INTO MarketCapHistory
                    (SymbolID, MarketCap, IndicatorDate)
                    VALUES (?, ?, ?)
                """
                for result in sorted_results:
                    cursor.execute(
                        query,
                        (result["symbol_id"], result["market_cap"], today.isoformat()),
                    )
            else:
                # SQL Server uses MERGE
                query = """
                    MERGE INTO MarketCapHistory AS target
                    USING (SELECT ? AS SymbolID, ? AS MarketCap,
                           CAST(GETDATE() AS DATE) AS IndicatorDate)
                        AS source (SymbolID, MarketCap, IndicatorDate)
                    ON target.SymbolID = source.SymbolID
                       AND target.IndicatorDate = source.IndicatorDate
                    WHEN NOT MATCHED THEN
                        INSERT (SymbolID, MarketCap, IndicatorDate)
                        VALUES (source.SymbolID, source.MarketCap, source.IndicatorDate);
                """
                for result in sorted_results:
                    cursor.execute(query, (result["symbol_id"], result["market_cap"]))

            conn.commit()
            cursor.close()
            app_logger.info("Successfully saved market cap results to database")

    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving market cap results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving market cap results: {e!s}")
        raise
