import pyodbc
from telegram_logging_handler import app_logger

def save_stepn_results(conn, gmt_price: float, gst_price: float, ratio: float, ema: float) -> None:
    """
    Saves STEPN results to the database
    
    Args:
        conn: Database connection
        gmt_price (float): Current GMT price
        gst_price (float): Current GST price
        ratio (float): GMT/GST ratio
        EMA14 (float): EMA14 value
    """
    try:
        if conn:
            cursor = conn.cursor()
            query = """
                MERGE INTO StepNResults AS target
                USING (SELECT ? AS GMTPrice, ? AS GSTPrice, ? AS Ratio, CAST(GETDATE() AS DATE) AS Date), ? AS EMA14
                    AS source (GMTPrice, GSTPrice, Ratio, Date, EMA14)
                ON target.Date = source.Date
                WHEN NOT MATCHED THEN
                    INSERT (GMTPrice, GSTPrice, Ratio, Date, EMA14)
                    VALUES (source.GMTPrice, source.GSTPrice, source.Ratio, source.Date, source.EMA14);
            """
            cursor.execute(query, (gmt_price, gst_price, ratio, ema))
            conn.commit()
            cursor.close()
            app_logger.info("Successfully saved STEPN results to database")
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving STEPN results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving STEPN results: {str(e)}")
        raise

def fetch_stepn_results_last_14_days(conn):
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
        app_logger.error(f"Error fetching STEPN results: {str(e)}")
        raise