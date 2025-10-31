"""Add StepNResults table to existing SQLite database.

This migration adds support for STEPN token metrics tracking.
"""

import logging
import sqlite3
from pathlib import Path


def migrate_add_stepn_table(db_path="./local_crypto.db"):
    """Add StepNResults table to existing database."""
    if not Path(db_path).exists():
        logging.error(f"Database not found: {db_path}")
        return False


    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='StepNResults'
        """)

        if cursor.fetchone():
            conn.close()
            return True

        # Create StepNResults table
        cursor.execute("""
            CREATE TABLE StepNResults (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                GMTPrice REAL,
                GSTPrice REAL,
                Ratio REAL,
                Date TEXT NOT NULL UNIQUE,
                EMA14 REAL,
                Min24Value REAL,
                Max24Value REAL,
                Range24 REAL,
                RSI REAL,
                TransactionsCount INTEGER,
                CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index for date queries
        cursor.execute("""
            CREATE INDEX idx_stepn_date ON StepNResults(Date)
        """)

        conn.commit()
        conn.close()

        return True

    except sqlite3.Error as e:
        logging.error(f"Migration failed: {e}")
        return False


if __name__ == "__main__":

    success = migrate_add_stepn_table()

    if success:
        pass
    else:
        logging.error("Migration failed. Please check the error above.")
