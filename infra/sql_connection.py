import logging
import os
import sqlite3
import struct
import time
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

import pyodbc
from azure import identity
from dotenv import load_dotenv

from infra.telegram_logging_handler import app_logger


load_dotenv()  # Load environment variables from .env file


class SQLiteRow:
    """
    Custom row class that mimics pyodbc.Row behavior.
    Supports both index and name-based access, and converts date strings to datetime objects.
    """

    def __init__(self, cursor, row):
        self._data = []
        self._names = {}

        for idx, col in enumerate(cursor.description):
            col_name = col[0]
            value = row[idx]

            # Convert string dates to datetime objects
            date_format_length = 10
            expected_dashes = 2
            if value is not None and isinstance(value, str):
                # Try to parse as datetime (ISO format: YYYY-MM-DD HH:MM:SS or YYYY-MM-DDTHH:MM:SS)
                if "T" in value or " " in value:
                    with suppress(ValueError, AttributeError):
                        # Handle both formats: "2025-10-23T20:00:00" and "2025-10-23 20:00:00"
                        value = datetime.fromisoformat(value.replace(" ", "T"))
                # Try to parse as date only (YYYY-MM-DD)
                elif len(value) == date_format_length and value.count("-") == expected_dashes:
                    with suppress(ValueError, AttributeError):
                        value = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC).date()

            self._data.append(value)
            self._names[col_name] = idx

    def __getitem__(self, key):
        """Support both index and name-based access."""
        if isinstance(key, int):
            return self._data[key]
        return self._data[self._names[key]]

    def __iter__(self):
        """Support iteration."""
        return iter(self._data)

    def __len__(self):
        """Support len()."""
        return len(self._data)

    def keys(self):
        """Return column names."""
        return self._names.keys()


def dict_factory(cursor, row):
    """Row factory that returns SQLiteRow objects with date conversion."""
    return SQLiteRow(cursor, row)


class SQLiteConnectionWrapper:
    """
    Wrapper for SQLite connection to make it compatible with pyodbc-style code.
    Provides a cursor() method that supports context manager protocol.
    Also supports direct execute() calls like pyodbc.
    Automatically converts date strings to datetime objects.
    """

    def __init__(self, sqlite_conn):
        self._conn = sqlite_conn
        # Use custom row factory that converts dates and supports column access by name
        self._conn.row_factory = dict_factory

    def cursor(self):
        """Return a cursor that supports context manager."""
        return SQLiteCursorWrapper(self._conn.cursor())

    def execute(self, sql, params=None):
        """
        Execute SQL directly on the connection (pyodbc compatibility).
        Returns a cursor with the results.
        """
        cursor = self._conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False


class SQLiteCursorWrapper:
    """Wrapper for SQLite cursor to support context manager protocol."""

    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self._cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cursor.close()
        return False

    def __getattr__(self, name):
        return getattr(self._cursor, name)


def connect_to_sql_sqlite(db_path=None):
    """
    Connect to local SQLite database.
    Returns a connection compatible with the existing codebase.
    """
    if db_path is None:
        db_path = os.getenv("SQLITE_DB_PATH", "./local_crypto.db")

    if not Path(db_path).exists():
        logging.error(f"SQLite database not found: {db_path}")
        logging.error("Please run: python database/init_sqlite.py")
        raise FileNotFoundError(f"Database not found: {db_path}")

    logging.info(f"Connecting to SQLite database: {db_path}")

    # Create SQLite connection with optimized settings
    sqlite_conn = sqlite3.connect(
        db_path,
        timeout=30.0,  # Increase timeout to 30 seconds (default is 5)
        check_same_thread=False,  # Allow connection to be used across threads
    )

    # Enable WAL mode for better concurrency
    sqlite_conn.execute("PRAGMA journal_mode=WAL")

    # Optimize for performance
    sqlite_conn.execute("PRAGMA synchronous=NORMAL")  # Faster, still safe in WAL mode
    sqlite_conn.execute("PRAGMA cache_size=-64000")  # Use 64MB cache
    sqlite_conn.execute("PRAGMA temp_store=MEMORY")  # Keep temp tables in memory

    wrapped_conn = SQLiteConnectionWrapper(sqlite_conn)

    logging.info("✅ Connected to SQLite database (WAL mode enabled, 30s timeout)")
    return wrapped_conn


def connect_to_sql(max_retries=3):
    """
    Connect to database based on DATABASE_TYPE environment variable.
    Supports both SQLite (local) and Azure SQL (cloud).
    """
    database_type = os.getenv("DATABASE_TYPE", "azuresql").lower()

    if database_type == "sqlite":
        return connect_to_sql_sqlite()

    # Original Azure SQL connection code
    conn = None
    for attempt in range(max_retries):
        try:
            # Connection parameters
            server = "crypto-alerts.database.windows.net"
            database = "Crypto"
            username = "grani"
            password = os.getenv("SQL_PASSWORD")
            # Enhanced logging
            environment = os.getenv("AZURE_FUNCTIONS_ENVIRONMENT")
            is_azure = environment is not None and environment.lower() != "development"
            logging.info(f"Attempt {attempt + 1}/{max_retries}")
            logging.info(f"Environment: {environment}")
            logging.info(f"Is Azure: {is_azure}")

            if is_azure:
                try:
                    connection_string = os.environ["AZURE_SQL_CONNECTIONSTRING"]
                    credential = identity.DefaultAzureCredential(
                        exclude_interactive_browser_credential=False
                    )
                    token = credential.get_token("https://database.windows.net/.default").token
                    logging.info(f"Access token: {token}")
                    token_bytes = token.encode("UTF-16-LE")
                    token_struct = struct.pack(
                        f"<I{len(token_bytes)}s", len(token_bytes), token_bytes
                    )
                    sql_copt_ss_access_token = (
                        1256  # This connection option is defined by microsoft in msodbcsql.h
                    )

                    logging.info(f"Azure connection string (without token): {connection_string}")
                    conn = pyodbc.connect(
                        connection_string,
                        attrs_before={sql_copt_ss_access_token: token_struct},
                    )
                    logging.info("Successfully connected to the database.")
                    return conn
                except pyodbc.Error as e:
                    app_logger.warning(f"ODBC Error: {e}")
                    raise
                except Exception as e:
                    app_logger.warning(f"Unexpected error: {e!s}")
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
                    app_logger.warning(f"Failed to connect to the database: {e!s}")

            logging.info("Connection successful")
            return conn

        except pyodbc.Error as e:
            app_logger.warning(f"Attempt {attempt + 1} failed:")
            app_logger.warning(f"Error state: {e.args[0] if e.args else 'No state'}")
            if attempt < max_retries - 1:
                time.sleep(55**attempt)  # Exponential backoff
                continue
            app_logger.error(f"Error message: {e!s}")
            msg = "Failed to connect to the database after maximum retries"
            raise RuntimeError(msg) from e

    # This should never be reached, but added for type checking
    msg = "Failed to connect to the database after maximum retries"
    raise RuntimeError(msg)
