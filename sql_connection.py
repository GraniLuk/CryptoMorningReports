import pyodbc
import pandas as pd
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv
import os
from azure import identity
import logging
import time
import subprocess
from telegram_logging_handler import app_logger
import struct

load_dotenv()  # Load environment variables from .env file

@dataclass
class Symbol:
    symbol_id: int
    symbol_name: str
    full_name: str
    
    @property
    def kucoin_name(self) -> str:
        return f"{self.symbol_name}-USDT"
    
    @property
    def binance_name(self) -> str:
        return f"{self.symbol_name}USDT"
    
    @property
    def yf_name(self) -> str:
        return f"{self.symbol_name}-USD"

    @staticmethod
    def get_symbol_names(symbols: List['Symbol']) -> List[str]:
        """Convert List of Symbols to List of symbol names"""
        return [symbol.symbol_name for symbol in symbols]

    @staticmethod
    def get_symbol_names_usd(symbols: List['Symbol']) -> List[str]:
        """Convert List of Symbols to List of symbol names with USD suffix"""
        return [f"{symbol.symbol_name}-USD" for symbol in symbols]

def connect_to_sql(max_retries=3):
    conn = None
    for attempt in range(max_retries):
        try:
            # Connection parameters
            server = 'crypto-alerts.database.windows.net'
            database = 'Crypto'
            username = 'grani'
            password = os.getenv('SQL_PASSWORD')
            # Enhanced logging
            environment = os.getenv("AZURE_FUNCTIONS_ENVIRONMENT")
            is_azure = environment is not None and environment.lower() != "development"
            logging.info(f"Attempt {attempt + 1}/{max_retries}")
            logging.info(f"Environment: {environment}")
            logging.info(f"Is Azure: {is_azure}")
            
            if is_azure:
                try:
                    connection_string = os.environ["AZURE_SQL_CONNECTIONSTRING"]
                    credential = identity.DefaultAzureCredential(exclude_interactive_browser_credential=False)
                    token = credential.get_token("https://database.windows.net/.default").token
                    logging.info(f"Access token: {token}")
                    token_bytes = token.encode("UTF-16-LE")
                    token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
                    SQL_COPT_SS_ACCESS_TOKEN = 1256  # This connection option is defined by microsoft in msodbcsql.h
                    
                    logging.info(f"Azure connection string (without token): {connection_string}")
                    conn = pyodbc.connect(connection_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
                    logging.info("Successfully connected to the database.")
                    return conn
                except pyodbc.Error as e:
                    app_logger.warning(f"ODBC Error: {e}")
                    raise
                except Exception as e:
                    app_logger.warning(f"Unexpected error: {str(e)}")
                    raise
            else:
                try:
                    connection_string = (
                    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                    f"SERVER={server};"
                    f"DATABASE={database};"
                    f"UID={username};"
                    "Connection Timeout=120;"
                    "Login Timeout=120;"  # Add Login Timeout
                    "Encrypt=yes;"
                    "TrustServerCertificate=no"
                    )
                    logging.info(f"Local connection string (without password): {connection_string}")
                    conn = pyodbc.connect(connection_string + f";PWD={password}")
                    logging.info("Successfully connected to the database.")
                    return conn
                except pyodbc.Error as e:
                    app_logger.warning(f"ODBC Error: {e}")
                except Exception as e:
                    app_logger.warning(f"Failed to connect to the database: {str(e)}")
                
            logging.info("Connection successful")
            return conn
            
        except pyodbc.Error as e:
            app_logger.warning(f"Attempt {attempt + 1} failed:")
            app_logger.warning(f"Error state: {e.args[0] if e.args else 'No state'}")
            if attempt < max_retries - 1:
                time.sleep(45 ** attempt)  # Exponential backoff
                continue
            else:
                app_logger.error(f"Error message: {str(e)}")
                raise RuntimeError("Failed to connect to the database after maximum retries")

    if conn is None:
        raise RuntimeError("Failed to connect to the database after maximum retries")
    
def fetch_symbols(conn) -> List[Symbol]:
    """
    Fetches all symbols from the database and returns them as a list of Symbol objects
    
    Returns:
        List[Symbol]: List of cryptocurrency symbols
    """
    try:
        if conn:
            try:
                cursor = conn.cursor()
                query = "SELECT SymbolID, SymbolName, FullName FROM Symbols"
                
                symbols = []
                for row in cursor.execute(query):
                    symbol = Symbol(
                        symbol_id=row[0],
                        symbol_name=row[1],
                        full_name=row[2]
                    )
                    symbols.append(symbol)
                    
                cursor.close()
                return symbols
            except pyodbc.Error as e:
                app_logger.error(f"ODBC Error while fetching symbols: {e}")
            except Exception as e:
                app_logger.error(f"Error fetching symbols: {str(e)}")
        else:
            app_logger.error("Database connection was not established.")
    except Exception as e:
        app_logger.error(f"Error fetching symbols: {str(e)}")
        raise

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

def save_rsi_results(conn, symbol_id: int, closed_price: float, rsi: float) -> None:
    """
    Saves RSI results to the database
    
    Args:
        conn: Database connection
        symbol_id (int): Symbol ID from Symbols table
        closed_price (float): Current closing price
        rsi (float): Calculated RSI value
    """
    try:
        if conn:
            cursor = conn.cursor()
            query = """
                MERGE INTO RSI AS target
                USING (SELECT ? AS SymbolID, CAST(GETDATE() AS DATE) AS IndicatorDate, ? AS ClosedPrice, ? AS RSI) 
                    AS source (SymbolID, IndicatorDate, ClosedPrice, RSI)
                ON target.SymbolID = source.SymbolID AND target.IndicatorDate = source.IndicatorDate
                WHEN MATCHED THEN
                    UPDATE SET ClosedPrice = source.ClosedPrice, RSI = source.RSI
                WHEN NOT MATCHED THEN
                    INSERT (SymbolID, IndicatorDate, ClosedPrice, RSI)
                    VALUES (source.SymbolID, source.IndicatorDate, source.ClosedPrice, source.RSI);
            """
            cursor.execute(query, (symbol_id, closed_price, rsi))
            conn.commit()
            cursor.close()
            app_logger.info(f"Successfully saved RSI results to database for symbol_id {symbol_id}")
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving RSI results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving RSI results: {str(e)}")
        raise

def save_price_range_results(conn, symbol_id: int, low_price: float, high_price: float, range_percent: float) -> None:
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
            app_logger.info(f"Successfully saved price range results to database for symbol_id {symbol_id}")
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while saving price range results: {e}")
        raise
    except Exception as e:
        app_logger.error(f"Error saving price range results: {str(e)}")
        raise

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