"""Data models and source definitions for the Crypto Morning Reports application."""

from dataclasses import dataclass
from enum import Enum

import pyodbc

from infra.telegram_logging_handler import app_logger


class SourceID(Enum):
    """Enumeration of supported cryptocurrency data sources."""

    BINANCE = 1
    KUCOIN = 2
    COINGECKO = 3
    COINMARKETCAP = 4
    BYBIT = 5


@dataclass
class Symbol:
    """Represents a cryptocurrency symbol with its properties and exchange-specific names."""

    symbol_id: int
    symbol_name: str
    full_name: str
    source_id: SourceID  # Use enum for SourceID
    coingecko_name: str

    @property
    def kucoin_name(self) -> str:
        """Return the KuCoin-specific name for this symbol."""
        return f"{self.symbol_name}-USDT"

    @property
    def binance_name(self) -> str:
        """Return the Binance-specific name for this symbol."""
        return f"{self.symbol_name}USDT"

    @staticmethod
    def get_symbol_names(symbols: list["Symbol"]) -> list[str]:
        """Convert List of Symbols to List of symbol names."""
        return [symbol.symbol_name for symbol in symbols]

    @staticmethod
    def get_symbol_names_usd(symbols: list["Symbol"]) -> list[str]:
        """Convert List of Symbols to List of symbol names with USD suffix."""
        return [f"{symbol.symbol_name}-USD" for symbol in symbols]


class NoSymbolsFoundError(Exception):
    """Exception raised when no symbols are found in the database."""


class SymbolNotFoundError(Exception):
    """Exception raised when a specific symbol is not found in the database."""


def fetch_symbols(conn) -> list[Symbol]:
    """Fetch all symbols from the database and return them as a list of Symbol objects.

    Raises:
        NoSymbolsFoundError: If no active symbols are found in the database
        Exception: For other errors during symbol retrieval

    Returns:
        List[Symbol]: List of cryptocurrency symbols

    """
    symbols = []
    if not conn:
        msg = "Database connection was not established."
        raise ConnectionError(msg)

    try:
        query = (
            "SELECT SymbolID, SymbolName, FullName, SourceID, CoinGeckoName "
            "FROM Symbols WHERE IsActive = 1"
        )

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

    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while fetching symbols: {e}")
        msg = f"Database error while fetching symbols: {e}"
        raise Exception(msg) from e
    except Exception as e:
        app_logger.error(f"Error fetching symbols: {e!s}")
        raise

    if not symbols:
        app_logger.error("No active symbols found in the database")
        msg = "No active symbols found in the database"
        raise NoSymbolsFoundError(msg)

    return symbols


def fetch_symbol_by_name(conn, symbol_name: str) -> Symbol:
    """Fetch a specific symbol by name from the database.

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
    if not conn:
        msg = "Database connection was not established."
        raise ConnectionError(msg)

    try:
        query = (
            "SELECT SymbolID, SymbolName, FullName, SourceID, CoinGeckoName "
            "FROM Symbols WHERE SymbolName = ? AND IsActive = 1"
        )

        with conn.cursor() as cursor:
            row = cursor.execute(query, (symbol_name,)).fetchone()

    except pyodbc.Error as e:
        app_logger.error(f"ODBC Error while fetching symbol {symbol_name}: {e}")
        msg = f"Database error while fetching symbol {symbol_name}: {e}"
        raise Exception(msg) from e
    except ConnectionError:
        # Re-raise connection errors
        raise
    except Exception as e:
        app_logger.error(f"Error fetching symbol {symbol_name}: {e!s}")
        raise

    if row is None:
        msg = f"Symbol '{symbol_name}' not found in the database"
        raise SymbolNotFoundError(msg)

    return Symbol(
        symbol_id=row[0],
        symbol_name=row[1],
        full_name=row[2],
        source_id=SourceID(row[3]),
        coingecko_name=row[4],
    )
