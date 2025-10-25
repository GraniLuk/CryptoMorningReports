"""
Repository for managing Funding Rate data in the database.
"""

import os
from datetime import datetime

from infra.telegram_logging_handler import app_logger


class FundingRateRepository:
    """Repository for Funding Rate data."""

    def __init__(self, conn):
        self.conn = conn
        self.is_sqlite = os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"

    def save_funding_rate(
        self, symbol_id: int, funding_rate: float, funding_time: datetime, indicator_date: datetime
    ):
        """Save funding rate data to database."""
        cursor = self.conn.cursor()

        try:
            if self.is_sqlite:
                # SQLite: Use INSERT OR REPLACE
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO FundingRate 
                    (SymbolID, FundingRate, FundingTime, IndicatorDate)
                    VALUES (?, ?, ?, ?)
                    """,
                    (symbol_id, funding_rate, funding_time.isoformat(), indicator_date.isoformat()),
                )
            else:
                # Azure SQL: Use MERGE
                cursor.execute(
                    """
                    MERGE INTO FundingRate AS target
                    USING (SELECT ? AS SymbolID, ? AS IndicatorDate) AS source
                    ON target.SymbolID = source.SymbolID AND target.IndicatorDate = source.IndicatorDate
                    WHEN MATCHED THEN
                        UPDATE SET FundingRate = ?, FundingTime = ?
                    WHEN NOT MATCHED THEN
                        INSERT (SymbolID, FundingRate, FundingTime, IndicatorDate)
                        VALUES (?, ?, ?, ?);
                    """,
                    (
                        symbol_id,
                        indicator_date,
                        funding_rate,
                        funding_time,
                        symbol_id,
                        funding_rate,
                        funding_time,
                        indicator_date,
                    ),
                )

            self.conn.commit()
            app_logger.info(
                f"Saved Funding Rate for SymbolID {symbol_id}: {funding_rate:.6f}%, Next: {funding_time}"
            )

        except Exception as e:
            app_logger.error(f"Error saving funding rate: {str(e)}")
            self.conn.rollback()
            raise

    def get_latest_funding_rate(self, symbol_id: int):
        """Get the most recent funding rate for a symbol."""
        cursor = self.conn.cursor()

        try:
            query = """
                SELECT FundingRate, FundingTime, IndicatorDate
                FROM FundingRate
                WHERE SymbolID = ?
                ORDER BY IndicatorDate DESC
                LIMIT 1
            """

            if not self.is_sqlite:
                query = """
                    SELECT TOP 1 FundingRate, FundingTime, IndicatorDate
                    FROM FundingRate
                    WHERE SymbolID = ?
                    ORDER BY IndicatorDate DESC
                """

            cursor.execute(query, (symbol_id,))
            row = cursor.fetchone()

            if row:
                return {
                    "funding_rate": row[0],
                    "funding_time": row[1],
                    "indicator_date": row[2],
                }
            return None

        except Exception as e:
            app_logger.error(f"Error fetching funding rate: {str(e)}")
            raise
