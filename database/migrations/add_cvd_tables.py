"""Add CumulativeVolumeDelta table to existing SQLite database.

This migration adds support for Cumulative Volume Delta (order flow) tracking.
"""

import sqlite3
from pathlib import Path

from infra.telegram_logging_handler import app_logger


def migrate_add_cvd_table(db_path: str = "./local_crypto.db") -> bool:
    """Add CumulativeVolumeDelta table to existing database.

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
            WHERE type='table' AND name='CumulativeVolumeDelta'
        """)

        if cursor.fetchone():
            app_logger.info("CumulativeVolumeDelta table already exists, skipping migration")
            conn.close()
            return True

        app_logger.info("Creating CumulativeVolumeDelta table...")

        # Create CumulativeVolumeDelta table
        cursor.execute("""
            CREATE TABLE CumulativeVolumeDelta (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                SymbolID INTEGER NOT NULL,
                CVD1h REAL,
                CVD4h REAL,
                CVD24h REAL,
                BuyVolume1h REAL,
                SellVolume1h REAL,
                BuyVolume24h REAL,
                SellVolume24h REAL,
                TradeCount1h INTEGER,
                TradeCount24h INTEGER,
                AvgTradeSize REAL,
                LargeBuyCount INTEGER,
                LargeSellCount INTEGER,
                IndicatorDate TEXT NOT NULL,
                CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (SymbolID) REFERENCES Symbols(SymbolID),
                UNIQUE(SymbolID, IndicatorDate)
            )
        """)

        app_logger.info("Creating index on CumulativeVolumeDelta...")

        # Create index for efficient queries
        cursor.execute("""
            CREATE INDEX idx_cvd_symbol_date
            ON CumulativeVolumeDelta(SymbolID, IndicatorDate)
        """)

        conn.commit()
        conn.close()

        app_logger.info("CumulativeVolumeDelta table created successfully")

    except sqlite3.Error:
        app_logger.exception("Migration failed")
        return False
    else:
        return True


if __name__ == "__main__":
    import sys

    # Allow custom db path from command line
    db_path = sys.argv[1] if len(sys.argv) > 1 else "./local_crypto.db"

    success = migrate_add_cvd_table(db_path)

    if success:
        app_logger.info("✅ CVD Migration completed successfully")
    else:
        app_logger.error("❌ CVD Migration failed. Please check the logs above.")
        sys.exit(1)
