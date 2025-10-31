"""Add StepNResults table to existing SQLite database.

This migration adds support for STEPN token metrics tracking.
"""

import sqlite3
from pathlib import Path


def migrate_add_stepn_table(db_path="./local_crypto.db"):
    """Add StepNResults table to existing database."""
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        print("   Please run: python -m database.init_sqlite")
        return False

    print(f"🔄 Adding StepNResults table to: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='StepNResults'
        """)

        if cursor.fetchone():
            print("✓ StepNResults table already exists")
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

        print("✅ StepNResults table created successfully!")
        print("   STEPN metrics tracking is now enabled")
        return True

    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        return False


if __name__ == "__main__":
    print("")
    print("═" * 60)
    print("  📊 STEPN Table Migration")
    print("═" * 60)
    print("")

    success = migrate_add_stepn_table()

    if success:
        print("")
        print("🎉 Migration complete! STEPN reporting is now available.")
        print("")
        print("Next steps:")
        print("  • Run daily report to start collecting STEPN data")
        print("  • Data will accumulate for RSI/EMA calculations")
        print("")
    else:
        print("")
        print("❌ Migration failed. Please check the error above.")
        print("")
