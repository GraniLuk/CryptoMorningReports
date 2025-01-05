import pyodbc
from telegram_logging_handler import app_logger

def save_stepn_results(conn, gmt_price: float, gst_price: float, ratio: float) -> None:
    """
    Saves STEPN results to the database
    
    Args:
        conn: Database connection
        gmt_price (float): Current GMT price
        gst_price (float): Current GST price
        ratio (float): GMT/GST ratio
    """
    try:
        if conn:
            cursor = conn.cursor()
            query = """
                MERGE INTO StepNResults AS target
                USING (SELECT ? AS GMTPrice, ? AS GSTPrice, ? AS Ratio, CAST(GETDATE() AS DATE) AS Date) 
                    AS source (GMTPrice, GSTPrice, Ratio, Date)
                ON target.Date = source.Date
                WHEN NOT MATCHED THEN
                    INSERT (GMTPrice, GSTPrice, Ratio, Date)
                    VALUES (source.GMTPrice, source.GSTPrice, source.Ratio, source.Date);
            """
            cursor.execute(query, (gmt_price, gst_price, ratio))
            conn.commit()
            cursor.close()
            app_logger.info("Successfully saved STEPN results to database")
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving STEPN results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving STEPN results: {str(e)}")
        raise