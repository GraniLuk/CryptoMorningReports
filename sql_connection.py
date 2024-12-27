import pyodbc
import pandas as pd
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv
import os

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

def connect_to_sql():
    try:
        # Connection parameters
        server = 'tcp:crypto-alerts.database.windows.net,1433'
        database = 'Crypto'
        username = 'grani'
        password = os.getenv('SQL_PASSWORD')
        
       # Define the UMI client ID
        user_assigned_client_id = os.getenv("USER_ASSIGNED_CLIENT_ID")  # Set this in your app settings

        # Authenticate using ManagedIdentityCredential
        credential = ManagedIdentityCredential(client_id=user_assigned_client_id)
        access_token = credential.get_token("https://database.windows.net/.default").token

        # Define connection string
        connection_string = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};"

        # Connect using token
        conn = pyodbc.connect(connection_string, attrs_before={"AccessToken": access_token})
        return conn
    
    except pyodbc.Error as e:
        print(f"Error connecting to SQL Server: {str(e)}")
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