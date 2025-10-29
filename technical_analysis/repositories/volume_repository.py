import os
from datetime import UTC, datetime

import pyodbc

from infra.telegram_logging_handler import app_logger


def save_volume_results(conn, sorted_results):
    """
    Saves volume results to the database once per day

    Args:
        conn: Database connection
        sorted_results: List of dictionaries containing volume data
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
                    INSERT OR REPLACE INTO VolumeHistory
                    (SymbolID, Volume, IndicatorDate)
                    VALUES (?, ?, ?)
                """
                for result in sorted_results:
                    cursor.execute(query, (result["symbol_id"], result["total"], today.isoformat()))
            else:
                # SQL Server uses MERGE
                query = """
                    MERGE INTO VolumeHistory AS target
                    USING (SELECT ? AS SymbolID, ? AS Volume,
                           CAST(GETDATE() AS DATE) AS IndicatorDate)
                        AS source (SymbolID, Volume, IndicatorDate)
                    ON target.SymbolID = source.SymbolID
                       AND target.IndicatorDate = source.IndicatorDate
                    WHEN NOT MATCHED THEN
                        INSERT (SymbolID, Volume, IndicatorDate)
                        VALUES (source.SymbolID, source.Volume, source.IndicatorDate);
                """
                for result in sorted_results:
                    cursor.execute(query, (result["symbol_id"], result["total"]))

            conn.commit()
            cursor.close()
            app_logger.info("Successfully saved volume results to database")

    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving volume results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving volume results: {e!s}")
        raise


def get_combined_market_cap_and_volume_data(self):
    """
    Fetch data from CombinedMarketCapAndVolumeView
    Returns: List of dictionaries containing market cap and volume data
    """
    try:
        with pyodbc.connect(self.connection_string) as conn:
            cursor = conn.cursor()

            query = """
                SELECT TOP (1000) [SymbolName]
                    ,[IndicatorDate]
                    ,[Volume]
                    ,[MarketCap]
                    ,[VolumeToMarketCapRatio]
                    ,[RatioPercentage]
                    ,[VolumeRank]
                    ,[MarketCapRank]
                    ,[RatioRank]
                FROM [dbo].[CombinedMarketCapAndVolumeView]
            """

            cursor.execute(query)

            # Convert rows to list of dictionaries
            columns = [column[0] for column in cursor.description]
            results = []

            for row in cursor.fetchall():
                results.append(dict(zip(columns, row, strict=False)))

            cursor.close()
            app_logger.info("Successfully fetched combined market cap and volume data")

            return results

    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while fetching combined data: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error fetching combined data: {e!s}")
        raise
