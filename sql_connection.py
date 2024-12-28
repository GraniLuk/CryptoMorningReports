import pyodbc
import pandas as pd
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv
import os
from azure.identity import ManagedIdentityCredential
import logging
import time

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
    for attempt in range(max_retries):
        try:
            # Connection parameters
            server = 'tcp:crypto-alerts.database.windows.net,1433'
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
                user_assigned_client_id = os.getenv("USER_ASSIGNED_CLIENT_ID")
                logging.info(f"Using Managed Identity with client ID: {user_assigned_client_id}")
                credential = ManagedIdentityCredential(client_id=user_assigned_client_id)
                access_token = credential.get_token("https://database.windows.net/.default").token
                connection_string = (
                    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                    f"SERVER={server};"
                    f"DATABASE={database};"
                    "Connection Timeout=60;"
                    "Encrypt=yes;"
                    "TrustServerCertificate=no"
                )
                logging.info(f"Azure connection string (without token): {connection_string}")
                conn = pyodbc.connect(connection_string, attrs_before={"AccessToken": access_token})
            else:
                connection_string = (
                    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                    f"SERVER={server};"
                    f"DATABASE={database};"
                    f"UID={username};"
                    "Connection Timeout=30;"
                    "Encrypt=yes;"
                    "TrustServerCertificate=no"
                )
                logging.info(f"Local connection string (without password): {connection_string}")
                conn = pyodbc.connect(connection_string + f";PWD={password}")
                
            logging.info("Connection successful")
            return conn
            
        except pyodbc.Error as e:
            logging.error(f"Attempt {attempt + 1} failed:")
            logging.error(f"Error state: {e.args[0] if e.args else 'No state'}")
            logging.error(f"Error message: {str(e)}")
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise

def fetch_symbols() -> List[Symbol]:
    """
    Fetches all symbols from the database and returns them as a list of Symbol objects
    
    Returns:
        List[Symbol]: List of cryptocurrency symbols
    """
    try:
        conn = connect_to_sql()
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
        conn.close()
        return symbols
    
    except Exception as e:
        print(f"Error fetching symbols: {str(e)}")
        raise