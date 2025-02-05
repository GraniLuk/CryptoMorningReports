import pandas as pd
import pyodbc
from infra.telegram_logging_handler import app_logger
from datetime import date, timedelta

def save_macd_results(conn, symbol_id: int, current_price: float, macd: float, 
                     signal: float, histogram: float, indicator_date: date = None) -> None:
    """
    Saves MACD results to the database
    
    Args:
        conn: Database connection
        symbol_id (int): Symbol ID from Symbols table
        current_price (float): Current price
        macd (float): MACD line value
        signal (float): Signal line value
        histogram (float): MACD histogram value
        indicator_date (date): Date of the indicators
    """
    try:
        if conn:
            indicator_date = indicator_date or date.today()
            cursor = conn.cursor()
            query = """
                MERGE INTO MACD AS target
                USING (SELECT ? AS SymbolID, ? AS IndicatorDate, 
                             ? AS CurrentPrice, ? AS MACD, ? AS Signal, ? AS Histogram) 
                    AS source (SymbolID, IndicatorDate, CurrentPrice, MACD, Signal, Histogram)
                ON target.SymbolID = source.SymbolID AND target.IndicatorDate = source.IndicatorDate
                WHEN MATCHED THEN
                    UPDATE SET CurrentPrice = source.CurrentPrice,
                             MACD = source.MACD,
                             Signal = source.Signal,
                             Histogram = source.Histogram
                WHEN NOT MATCHED THEN
                    INSERT (SymbolID, IndicatorDate, CurrentPrice, MACD, Signal, Histogram)
                    VALUES (source.SymbolID, source.IndicatorDate, source.CurrentPrice, 
                           source.MACD, source.Signal, source.Histogram);
            """
            cursor.execute(query, (symbol_id, indicator_date, current_price, macd, signal, histogram))
            conn.commit()
            cursor.close()
            app_logger.info(f"Successfully saved MACD results to database for symbol_id {symbol_id}")
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving MACD results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving MACD results: {str(e)}")
        raise

def fetch_yesterday_macd(conn, target_date: date = None) -> pd.DataFrame:
    """
    Fetches all MACD records from yesterday
    
    Args:
        conn: Database connection
        target_date (date): Target date for MACD data
        
    Returns:
        pd.DataFrame: DataFrame containing yesterday's MACD data
    """
    try:
        if conn:
            target_date = target_date or date.today()
            yesterday = target_date - timedelta(days=1)
            
            query = """
                SELECT m.SymbolID, s.SymbolName, m.IndicatorDate, m.CurrentPrice, 
                       m.MACD, m.Signal, m.Histogram
                FROM MACD m
                JOIN Symbols s ON m.SymbolID = s.SymbolID
                WHERE m.IndicatorDate = ?
            """
            
            df = pd.read_sql(query, conn, params=[yesterday])
            app_logger.info(f"Successfully fetched {len(df)} MACD records for {yesterday}")
            return df
            
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while fetching yesterday's MACD: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error fetching yesterday's MACD: {str(e)}")
        raise

def get_macd_with_crossover_data(self):
    """
    Fetch data from MACDWithCrossoverView
    Returns: List of dictionaries containing MACD data with crossover signals
    """
    try:
        with pyodbc.connect(self.connection_string) as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT TOP (1000) [ID]
                    ,[SymbolName]
                    ,[IndicatorDate]
                    ,[CurrentPrice]
                    ,[MACD]
                    ,[Signal]
                    ,[Histogram]
                    ,[HistogramCrossover]
                FROM [dbo].[MACDWithCrossoverView]
            """
            
            cursor.execute(query)
            
            # Convert rows to list of dictionaries
            columns = [column[0] for column in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
                
            cursor.close()
            app_logger.info("Successfully fetched MACD with crossover data")
            
            return results
            
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while fetching MACD data: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error fetching MACD data: {str(e)}")
        raise