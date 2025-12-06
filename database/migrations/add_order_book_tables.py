"""Add OrderBookMetrics table to existing SQLite database.

This migration adds support for order book depth and liquidity tracking.
"""

import sqlite3
from pathlib import Path

from infra.telegram_logging_handler import app_logger


def migrate_add_order_book_table(db_path: str = "./local_crypto.db") -> bool:
    """Add OrderBookMetrics table to existing database.

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
            WHERE type='table' AND name='OrderBookMetrics'
        """)

        if cursor.fetchone():
            app_logger.info("OrderBookMetrics table already exists, skipping migration")
            conn.close()
            return True

        app_logger.info("Creating OrderBookMetrics table...")

        # Create OrderBookMetrics table
        cursor.execute("""
            CREATE TABLE OrderBookMetrics (
                Id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                SymbolID            INTEGER NOT NULL,
                BestBid             REAL,
                BestBidQty          REAL,
                BestAsk             REAL,
                BestAskQty          REAL,
                SpreadPct           REAL,
                BidVolume2Pct       REAL,
                AskVolume2Pct       REAL,
                BidAskRatio         REAL,
                LargestBidWall      REAL,
                LargestBidWallPrice REAL,
                LargestAskWall      REAL,
                LargestAskWallPrice REAL,
                IndicatorDate       TEXT NOT NULL,
                CreatedAt           TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (SymbolID) REFERENCES Symbols(SymbolID),
                UNIQUE(SymbolID, IndicatorDate)
            )
        """)

        app_logger.info("Creating index on OrderBookMetrics...")

        # Create index for efficient queries
        cursor.execute("""
            CREATE INDEX idx_orderbook_symbol_date
            ON OrderBookMetrics(SymbolID, IndicatorDate)
        """)

        conn.commit()
        conn.close()

        app_logger.info("OrderBookMetrics table created successfully")

    except sqlite3.Error:
        app_logger.exception("Migration failed")
        return False
    else:
        return True


if __name__ == "__main__":
    import sys

    # Allow custom db path from command line
    db_path = sys.argv[1] if len(sys.argv) > 1 else "./local_crypto.db"

    success = migrate_add_order_book_table(db_path)

    if success:
        print("✅ Migration completed successfully")
    else:
        print("❌ Migration failed. Please check the logs above.")
        sys.exit(1)
