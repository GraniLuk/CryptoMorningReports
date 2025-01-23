from dataclasses import dataclass
from typing import List
import pyodbc
from telegram_logging_handler import app_logger

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