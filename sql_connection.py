import pyodbc
import pandas as pd
from dataclasses import dataclass
from typing import List

@dataclass
class Symbol:
    symbol_id: int
    symbol_name: str
    full_name: str

def connect_to_sql():
    try:
        # Connection parameters
        server = 'tcp:crypto-alerts.database.windows.net,1433'
        database = 'Crypto'
        username = 'grani'
        password = '{your_password_here}'  # Replace with actual password
        
        # Create connection string
        conn_str = (
            f'DRIVER={{ODBC Driver 18 for SQL Server}};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'UID={username};'
            f'PWD={password};'
            'Encrypt=yes;'
            'TrustServerCertificate=no;'
        )
        
        # Create connection
        conn = pyodbc.connect(conn_str)
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