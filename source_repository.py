from dataclasses import dataclass
from enum import Enum

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
    coingecko_name: str

    @property
    def kucoin_name(self) -> str:
        return f"{self.symbol_name}-USDT"

    @property
    def binance_name(self) -> str:
        return f"{self.symbol_name}USDT"

    @staticmethod
    def get_symbol_names(symbols: list["Symbol"]) -> list[str]:
        """Convert List of Symbols to List of symbol names"""
        return [symbol.symbol_name for symbol in symbols]

    @staticmethod
    def get_symbol_names_usd(symbols: list["Symbol"]) -> list[str]:
        """Convert List of Symbols to List of symbol names with USD suffix"""
        return [f"{symbol.symbol_name}-USD" for symbol in symbols]


class NoSymbolsFoundError(Exception):
    """Exception raised when no symbols are found in the database."""


class SymbolNotFoundError(Exception):
    """Exception raised when a specific symbol is not found in the database."""


def fetch_symbols(conn) -> list[Symbol]:
    """
    Fetches all symbols from the database and returns them as a list of Symbol objects.

    Raises:
        NoSymbolsFoundError: If no active symbols are found in the database
        Exception: For other errors during symbol retrieval

    Returns:
        List[Symbol]: List of cryptocurrency symbols
    """
    symbols = []
    try:
        if not conn:
            msg = "Database connection was not established."
            raise ConnectionError(msg)

        query = "SELECT SymbolID, SymbolName, FullName, SourceID, CoinGeckoName FROM Symbols WHERE IsActive = 1"

        with conn.cursor() as cursor:
            for row in cursor.execute(query):
                symbol = Symbol(
                    symbol_id=row[0],
                    symbol_name=row[1],
                    full_name=row[2],
                    source_id=SourceID(row[3]),
                    coingecko_name=row[4],
                )
                symbols.append(symbol)

        if not symbols:
            app_logger.error("No active symbols found in the database")
            msg = "No active symbols found in the database"
            raise NoSymbolsFoundError(msg)

        return symbols
    except NoSymbolsFoundError:
        # Re-raise the NoSymbolsFoundError to be handled by the caller
        raise
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while fetching symbols: {e}")
        raise Exception(f"Database error while fetching symbols: {e}") from e
    except Exception as e:
        app_logger.error(f"Error fetching symbols: {e!s}")
        raise


def fetch_symbol_by_name(conn, symbol_name: str) -> Symbol:
    """
    Fetches a specific symbol by name from the database

    Args:
        conn: Database connection
        symbol_name: The symbol name to look up (e.g., "BTC", "ETH")

    Raises:
        SymbolNotFoundError: If the requested symbol is not found in the database
        ConnectionError: If the database connection is not established
        Exception: For other errors during symbol retrieval

    Returns:
        Symbol: The symbol object
    """
    try:
        if not conn:
            msg = "Database connection was not established."
            raise ConnectionError(msg)

        query = "SELECT SymbolID, SymbolName, FullName, SourceID, CoinGeckoName FROM Symbols WHERE SymbolName = ? AND IsActive = 1"

        with conn.cursor() as cursor:
            row = cursor.execute(query, (symbol_name,)).fetchone()
            if row is None:
                raise SymbolNotFoundError(f"Symbol '{symbol_name}' not found in the database")

        return Symbol(
            symbol_id=row[0],
            symbol_name=row[1],
            full_name=row[2],
            source_id=SourceID(row[3]),
            coingecko_name=row[4],
        )

    except SymbolNotFoundError:
        # Re-raise the SymbolNotFoundError to be handled by the caller
        raise
    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while fetching symbol {symbol_name}: {e}")
        raise Exception(f"Database error while fetching symbol {symbol_name}: {e}") from e
    except ConnectionError:
        # Re-raise connection errors
        raise
    except Exception as e:
        app_logger.error(f"Error fetching symbol {symbol_name}: {e!s}")
        raise
