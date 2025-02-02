from datetime import date
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
            query = """
                MERGE INTO VolumeHistory AS target
                USING (SELECT ? AS SymbolID, ? AS Volume, CAST(GETDATE() AS DATE) AS IndicatorDate)
                    AS source (SymbolID, Volume, IndicatorDate)
                ON target.SymbolID = source.SymbolID 
                   AND target.IndicatorDate = source.IndicatorDate
                WHEN NOT MATCHED THEN
                    INSERT (SymbolID, Volume, IndicatorDate)
                    VALUES (source.SymbolID, source.Volume, source.IndicatorDate);
            """
            
            for result in sorted_results:
                cursor.execute(query, (result['symbol_id'], result['total']))
                
            conn.commit()
            cursor.close()
            app_logger.info("Successfully saved volume results to database")
            
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving volume results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving volume results: {str(e)}")
        raise