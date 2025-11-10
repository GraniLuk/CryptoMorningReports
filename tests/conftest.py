"""Pytest configuration for tests.

Sets up test environment to use SQLite database instead of Azure SQL.
"""

import os
from pathlib import Path

import pytest

from database.init_sqlite import create_sqlite_database


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Configure test environment to use SQLite database.

    This fixture runs automatically before all tests and ensures that:
    1. DATABASE_TYPE is set to 'sqlite'
    2. A test SQLite database is used (or created if it doesn't exist)
    """
    # Force SQLite for all tests
    os.environ["DATABASE_TYPE"] = "sqlite"

    # Use the local database if it exists, otherwise try to create it
    local_db = Path("./local_crypto.db")

    if not local_db.exists():
        # Create the database using the init script
        print(f"\n📦 Creating test database at {local_db.absolute()}")
        conn = create_sqlite_database(str(local_db))
        conn.close()
        print("✅ Test database created successfully\n")

    # Set the database path for tests
    os.environ["SQLITE_DB_PATH"] = str(local_db.absolute())

    # Cleanup is optional - we can keep the test database for inspection
