import pyodbc

from infra.telegram_logging_handler import app_logger


def save_sopr_results(conn, metrics: dict) -> None:
    """
    Saves SOPR metrics to the database

    Args:
        conn: Database connection
        metrics (dict): Dictionary containing SOPR metrics (SOPR, STH-SOPR, LTH-SOPR)
    """
    try:
        if conn:
            cursor = conn.cursor()

            # Check if we're using SQLite or SQL Server
            import os

            is_sqlite = os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"

            if is_sqlite:
                # SQLite uses INSERT OR REPLACE
                query = """
                    INSERT OR REPLACE INTO SOPR
                    (IndicatorDate, SOPR, STH_SOPR, LTH_SOPR)
                    VALUES (DATE('now'), ?, ?, ?)
                """
            else:
                # SQL Server uses MERGE
                query = """
                    MERGE INTO SOPR AS target
                    USING (
                        SELECT
                            CAST(GETDATE() AS DATE) AS IndicatorDate,
                            ? AS SOPR,
                            ? AS STH_SOPR,
                            ? AS LTH_SOPR
                    ) AS source (IndicatorDate, SOPR, STH_SOPR, LTH_SOPR)
                    ON target.IndicatorDate = source.IndicatorDate
                    WHEN MATCHED THEN
                        UPDATE SET
                            SOPR = source.SOPR,
                            STH_SOPR = source.STH_SOPR,
                            LTH_SOPR = source.LTH_SOPR
                    WHEN NOT MATCHED THEN
                        INSERT (IndicatorDate, SOPR, STH_SOPR, LTH_SOPR)
                        VALUES (
                            source.IndicatorDate,
                            source.SOPR,
                            source.STH_SOPR,
                            source.LTH_SOPR
                        );
                """

            sopr = float(metrics["SOPR"].get("sopr", 0))
            sth_sopr = float(metrics["STH-SOPR"].get("sthSopr", 0))
            lth_sopr = float(metrics["LTH-SOPR"].get("lthSopr", 0))

            cursor.execute(query, (sopr, sth_sopr, lth_sopr))
            conn.commit()
            cursor.close()
            app_logger.info("Successfully saved SOPR metrics to database")

    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving SOPR metrics: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving SOPR metrics: {e!s}")
        raise
