"""Add CVDHourlySnapshots table to existing SQLite database.

This migration adds support for hourly CVD snapshots that accumulate over time,
allowing accurate 1h/4h/24h CVD aggregation from stored hourly data.
"""

import sqlite3
from pathlib import Path

from infra.telegram_logging_handler import app_logger


def migrate_add_cvd_hourly_snapshots(db_path: str = "./local_crypto.db") -> bool:
    """Add CVDHourlySnapshots table to existing database.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        True if migration succeeded, False otherwise.
    """
    if not Path(db_path).exists():
        app_logger.error(f"Database not found: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='CVDHourlySnapshots'
        """)

        if cursor.fetchone():
            app_logger.info("CVDHourlySnapshots table already exists, skipping migration")
            conn.close()
            return True

        app_logger.info("Creating CVDHourlySnapshots table...")

        # Create CVDHourlySnapshots table
        cursor.execute("""
            CREATE TABLE CVDHourlySnapshots (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                SymbolID INTEGER NOT NULL,
                HourTimestamp TEXT NOT NULL,
                CVD REAL NOT NULL DEFAULT 0,
                BuyVolume REAL NOT NULL DEFAULT 0,
                SellVolume REAL NOT NULL DEFAULT 0,
                TradeCount INTEGER NOT NULL DEFAULT 0,
                LargeBuyCount INTEGER NOT NULL DEFAULT 0,
                LargeSellCount INTEGER NOT NULL DEFAULT 0,
                AvgTradeSize REAL,
                LastTradeId INTEGER,
                CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
                UpdatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (SymbolID) REFERENCES Symbols(SymbolID),
                UNIQUE(SymbolID, HourTimestamp)
            )
        """)

        app_logger.info("Creating index on CVDHourlySnapshots...")

        # Create index for efficient time-range queries
        cursor.execute("""
            CREATE INDEX idx_cvd_hourly_symbol_time
            ON CVDHourlySnapshots(SymbolID, HourTimestamp)
        """)

        conn.commit()
        conn.close()

    except sqlite3.Error:
        app_logger.exception("Migration failed")
        return False
    else:
        app_logger.info("CVDHourlySnapshots table created successfully")
        return True


if __name__ == "__main__":
    import sys

    db_path = sys.argv[1] if len(sys.argv) > 1 else "./local_crypto.db"
    success = migrate_add_cvd_hourly_snapshots(db_path)
    sys.exit(0 if success else 1)
