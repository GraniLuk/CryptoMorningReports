import logging
import os
import struct
import time

import pyodbc
from azure import identity
from dotenv import load_dotenv

from infra.telegram_logging_handler import app_logger

load_dotenv()  # Load environment variables from .env file


def connect_to_sql(max_retries=3):
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
                    token = credential.get_token(
                        "https://database.windows.net/.default"
                    ).token
                    logging.info(f"Access token: {token}")
                    token_bytes = token.encode("UTF-16-LE")
                    token_struct = struct.pack(
                        f"<I{len(token_bytes)}s", len(token_bytes), token_bytes
                    )
                    SQL_COPT_SS_ACCESS_TOKEN = 1256  # This connection option is defined by microsoft in msodbcsql.h

                    logging.info(
                        f"Azure connection string (without token): {connection_string}"
                    )
                    conn = pyodbc.connect(
                        connection_string,
                        attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct},
                    )
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
                    logging.info(
                        f"Local connection string (without password): {connection_string}"
                    )
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
                time.sleep(55**attempt)  # Exponential backoff
                continue
            else:
                app_logger.error(f"Error message: {str(e)}")
                raise RuntimeError(
                    "Failed to connect to the database after maximum retries"
                )

    if conn is None:
        raise RuntimeError("Failed to connect to the database after maximum retries")
