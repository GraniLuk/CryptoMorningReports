"""Repository for managing Open Interest data in the database."""

import os
from datetime import datetime

from infra.telegram_logging_handler import app_logger


class OpenInterestRepository:
    """Repository for Open Interest data."""

    def __init__(self, conn):
        """Initialize the open interest repository with a database connection."""
        self.conn = conn
        self.is_sqlite = os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"

    def save_open_interest(
        self,
        symbol_id: int,
        open_interest: float,
        open_interest_value: float,
        indicator_date: datetime,
    ):
        """Save open interest data to database."""
        cursor = self.conn.cursor()

        try:
            if self.is_sqlite:
                # SQLite: Use INSERT OR REPLACE
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO OpenInterest
                    (SymbolID, OpenInterest, OpenInterestValue, IndicatorDate)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        symbol_id,
                        open_interest,
                        open_interest_value,
                        indicator_date.isoformat(),
                    ),
                )
            else:
                # Azure SQL: Use MERGE
                cursor.execute(
                    """
                    MERGE INTO OpenInterest AS target
                    USING (SELECT ? AS SymbolID, ? AS IndicatorDate) AS source
                    ON target.SymbolID = source.SymbolID AND target.IndicatorDate
                       = source.IndicatorDate
                    WHEN MATCHED THEN
                        UPDATE SET OpenInterest = ?, OpenInterestValue = ?
                    WHEN NOT MATCHED THEN
                        INSERT (SymbolID, OpenInterest, OpenInterestValue, IndicatorDate)
                        VALUES (?, ?, ?, ?);
                    """,
                    (
                        symbol_id,
                        indicator_date,
                        open_interest,
                        open_interest_value,
                        symbol_id,
                        open_interest,
                        open_interest_value,
                        indicator_date,
                    ),
                )

            self.conn.commit()
            app_logger.info(
                f"Saved Open Interest for SymbolID {symbol_id}: OI={open_interest}, "
                f"Value=${open_interest_value:,.0f}"
            )

        except Exception as e:
            app_logger.error(f"Error saving open interest: {e!s}")
            self.conn.rollback()
            raise

    def get_latest_open_interest(self, symbol_id: int):
        """Get the most recent open interest for a symbol."""
        cursor = self.conn.cursor()

        try:
            query = """
                SELECT OpenInterest, OpenInterestValue, IndicatorDate
                FROM OpenInterest
                WHERE SymbolID = ?
                ORDER BY IndicatorDate DESC
                LIMIT 1
            """

            if not self.is_sqlite:
                query = """
                    SELECT TOP 1 OpenInterest, OpenInterestValue, IndicatorDate
                    FROM OpenInterest
                    WHERE SymbolID = ?
                    ORDER BY IndicatorDate DESC
                """

            cursor.execute(query, (symbol_id,))
            row = cursor.fetchone()

            if row:
                return {
                    "open_interest": row[0],
                    "open_interest_value": row[1],
                    "indicator_date": row[2],
                }
            return None

        except Exception as e:
            app_logger.error(f"Error fetching open interest: {e!s}")
            raise
