from dataclasses import dataclass
from enum import Enum
from typing import List

import pyodbc

from infra.telegram_logging_handler import app_logger


class SourceID(Enum):
    BINANCE = 1
    KUCOIN = 2
    COINGECKO = 3
    COINMARKETCAP = 4
    BYBIT = 5


@dataclass
class Symbol:
    symbol_id: int
    symbol_name: str
    full_name: str
    source_id: SourceID  # Use enum for SourceID
    coingecko_name: str = None

    @property
    def kucoin_name(self) -> str:
        return f"{self.symbol_name}-USDT"

    @property
    def binance_name(self) -> str:
        return f"{self.symbol_name}USDT"

    @staticmethod
    def get_symbol_names(symbols: List["Symbol"]) -> List[str]:
        """Convert List of Symbols to List of symbol names"""
        return [symbol.symbol_name for symbol in symbols]

    @staticmethod
    def get_symbol_names_usd(symbols: List["Symbol"]) -> List[str]:
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
                query = "SELECT SymbolID, SymbolName, FullName, SourceID, CoinGeckoName FROM Symbols WHERE IsActive = 1"

                symbols = []
                for row in cursor.execute(query):
                    symbol = Symbol(
                        symbol_id=row[0],
                        symbol_name=row[1],
                        full_name=row[2],
                        source_id=SourceID(row[3]),  # Convert to SourceID enum
                        coingecko_name=row[4],
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


def fetch_symbol_by_name(conn, symbol_name: str) -> Symbol:
    """
    Fetches a specific symbol by name from the database

    Args:
        conn: Database connection
        symbol_name: The symbol name to look up (e.g., "BTC", "ETH")

    Returns:
        Symbol: The symbol object if found, None otherwise
    """
    try:
        if conn:
            try:
                cursor = conn.cursor()
                query = "SELECT SymbolID, SymbolName, FullName, SourceID, CoinGeckoName FROM Symbols WHERE SymbolName = ? AND IsActive = 1"

                row = cursor.execute(query, (symbol_name,)).fetchone()

                if row:
                    symbol = Symbol(
                        symbol_id=row[0],
                        symbol_name=row[1],
                        full_name=row[2],
                        source_id=SourceID(row[3]),  # Convert to SourceID enum
                        coingecko_name=row[4],
                    )
                    cursor.close()
                    return symbol
                else:
                    app_logger.warning(
                        f"Symbol '{symbol_name}' not found in the database"
                    )
                    cursor.close()
                    return None
            except pyodbc.Error as e:
                app_logger.error(f"ODBC Error while fetching symbol {symbol_name}: {e}")
                return None
            except Exception as e:
                app_logger.error(f"Error fetching symbol {symbol_name}: {str(e)}")
                return None
        else:
            app_logger.error("Database connection was not established.")
            return None
    except Exception as e:
        app_logger.error(f"Error fetching symbol {symbol_name}: {str(e)}")
        return None
