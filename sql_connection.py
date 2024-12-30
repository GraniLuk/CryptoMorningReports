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
            is_azure = environment is None or environment.lower() != "development"
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
                    app_logger.error(f"ODBC Error: {e}")
                    raise
                except Exception as e:
                    app_logger.error(f"Unexpected error: {str(e)}")
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
                    app_logger.error(f"ODBC Error: {e}")
                except Exception as e:
                    app_logger.error(f"Failed to connect to the database: {str(e)}")
                
            logging.info("Connection successful")
            return conn
            
        except pyodbc.Error as e:
            app_logger.error(f"Attempt {attempt + 1} failed:")
            app_logger.error(f"Error state: {e.args[0] if e.args else 'No state'}")
            app_logger.error(f"Error message: {str(e)}")
            
            if attempt < max_retries - 1:
                time.sleep(30 ** attempt)  # Exponential backoff
                continue
            else:
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
                logging.error(f"ODBC Error while fetching symbols: {e}")
            except Exception as e:
                logging.error(f"Error fetching symbols: {str(e)}")
        else:
            logging.error("Database connection was not established.")
    except Exception as e:
        logging.error(f"Error fetching symbols: {str(e)}")
        raise