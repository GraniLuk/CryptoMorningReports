import pandas as pd
import pyodbc
from telegram_logging_handler import app_logger

def save_moving_averages_results(conn, symbol_id: int, current_price: float, ma50: float, ma200: float) -> None:
    """
    Saves moving averages results to the database
    
    Args:
        conn: Database connection
        symbol_id (int): Symbol ID from Symbols table
        current_price (float): Current price
        ma50 (float): 50-day moving average
        ma200 (float): 200-day moving average
    """
    try:
        if conn:
            cursor = conn.cursor()
            query = """
                MERGE INTO MovingAverages AS target
                USING (SELECT ? AS SymbolID, CAST(GETDATE() AS DATE) AS IndicatorDate, 
                             ? AS CurrentPrice, ? AS MA50, ? AS MA200) 
                    AS source (SymbolID, IndicatorDate, CurrentPrice, MA50, MA200)
                ON target.SymbolID = source.SymbolID AND target.IndicatorDate = source.IndicatorDate
                WHEN MATCHED THEN
                    UPDATE SET CurrentPrice = source.CurrentPrice,
                             MA50 = source.MA50,
                             MA200 = source.MA200
                WHEN NOT MATCHED THEN
                    INSERT (SymbolID, IndicatorDate, CurrentPrice, MA50, MA200)
                    VALUES (source.SymbolID, source.IndicatorDate, source.CurrentPrice, 
                           source.MA50, source.MA200);
            """
            cursor.execute(query, (symbol_id, current_price, ma50, ma200))
            conn.commit()
            cursor.close()
            app_logger.info(f"Successfully saved moving averages results to database for symbol_id {symbol_id}")
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving moving averages results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving moving averages results: {str(e)}")
        raise

def fetch_yesterday_moving_averages(conn) -> pd.DataFrame:
    """
    Fetches all moving averages records from yesterday
    
    Args:
        conn: Database connection
        
    Returns:
        pd.DataFrame: DataFrame containing yesterday's moving averages data with columns:
            SymbolID, IndicatorDate, CurrentPrice, MA50, MA200
    """
    try:
        if conn:
            query = """
                SELECT ma.SymbolID, s.SymbolName, ma.IndicatorDate, ma.CurrentPrice, ma.MA50, ma.MA200
                FROM MovingAverages ma
                JOIN Symbols s ON ma.SymbolID = s.SymbolID
                WHERE ma.IndicatorDate = DATEADD(day, -1, CAST(GETDATE() AS DATE))
            """
            
            df = pd.read_sql(query, conn)
            app_logger.info(f"Successfully fetched {len(df)} moving averages records from yesterday")
            return df
            
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while fetching yesterday's moving averages: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error fetching yesterday's moving averages: {str(e)}")
        raise