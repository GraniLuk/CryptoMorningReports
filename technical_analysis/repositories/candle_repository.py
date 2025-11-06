"""Repository for managing candle data in the database."""

import os
from datetime import datetime
from typing import TYPE_CHECKING

from shared_code.common_price import Candle
from source_repository import Symbol


if TYPE_CHECKING:
    import pyodbc

    from infra.sql_connection import SQLiteConnectionWrapper


class CandleRepository:
    """Repository for managing candle data operations."""

    def __init__(
        self,
        conn: "pyodbc.Connection | SQLiteConnectionWrapper",
        table_name: str,
    ):
        """Initialize the candle repository.

        Args:
            conn: Database connection
            table_name: Name of the table to operate on

        """
        self.conn = conn
        self.table_name = table_name

    def save_candle(self, symbol: Symbol, candle: Candle, source: int) -> None:
        """Save a candle to the database.

        Args:
            symbol: Symbol object
            candle: Candle data to save
            source: Source identifier

        """
        # Check if we're using SQLite or SQL Server
        is_sqlite = os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"

        if is_sqlite:
            # SQLite uses INSERT OR REPLACE
            sql = f"""
            INSERT OR REPLACE INTO {self.table_name}
            (SymbolID, SourceID, EndDate, [Open], [Close], High, Low, Last, Volume, VolumeQuote)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """  # noqa: S608
            self.conn.execute(
                sql,
                (
                    symbol.symbol_id,
                    source,
                    candle.end_date,
                    candle.open,
                    candle.close,
                    candle.high,
                    candle.low,
                    candle.last,
                    candle.volume,
                    candle.volume_quote,
                ),
            )
        else:
            # SQL Server uses MERGE
            sql = f"""
            MERGE {self.table_name} AS target
            USING (SELECT ? as SymbolID, ? as SourceID, ? as EndDate) AS source
            ON (target.SymbolID = source.SymbolID
                AND target.SourceID = source.SourceID
                AND target.EndDate = source.EndDate)
            WHEN NOT MATCHED THEN
                INSERT (SymbolID, SourceID, EndDate, [Open], [Close], High, Low,
                        Last, Volume, VolumeQuote)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """  # noqa: S608
            self.conn.execute(
                sql,
                (
                    symbol.symbol_id,
                    source,
                    candle.end_date,  # For the USING clause
                    symbol.symbol_id,
                    source,
                    candle.end_date,  # For the INSERT clause
                    candle.open,
                    candle.close,
                    candle.high,
                    candle.low,
                    candle.last,
                    candle.volume,
                    candle.volume_quote,
                ),
            )
        self.conn.commit()

    def get_candle(self, symbol: Symbol, end_date: datetime) -> Candle | None:
        """Retrieve a single candle for the given symbol and end date."""
        sql = f"""
        SELECT [Id]
            ,[SymbolID]
            ,[SourceID]
            ,[EndDate]
            ,[Open]
            ,[Close]
            ,[High]
            ,[Low]
            ,[Last]
            ,[Volume]
            ,[VolumeQuote]
        FROM {self.table_name}
        WHERE SymbolID = ? AND EndDate = ?
        """  # noqa: S608
        row = self.conn.execute(sql, (symbol.symbol_id, end_date)).fetchone()
        if row:
            return Candle(
                id=row[0],
                symbol=symbol.symbol_name,
                source=row[2],
                end_date=row[3],
                open=row[4],
                close=row[5],
                high=row[6],
                low=row[7],
                last=row[8],
                volume=row[9],
                volume_quote=row[10],
            )
        return None

    def get_candles(self, symbol: Symbol, start_date: datetime, end_date: datetime) -> list[Candle]:
        """Retrieve candles for the given symbol within the date range."""
        # Convert datetime objects to ISO format strings for comparison since
        # EndDate is stored as text
        start_date_str = (
            start_date.isoformat() if isinstance(start_date, datetime) else str(start_date)
        )
        end_date_str = end_date.isoformat() if isinstance(end_date, datetime) else str(end_date)

        sql = f"""
        SELECT [Id]
            ,[SymbolID]
            ,[SourceID]
            ,[EndDate]
            ,[Open]
            ,[Close]
            ,[High]
            ,[Low]
            ,[Last]
            ,[Volume]
            ,[VolumeQuote]
        FROM {self.table_name}
        WHERE SymbolID = ?
        AND EndDate >= ?
        AND EndDate <= ?
        ORDER BY EndDate
        """  # noqa: S608
        rows = self.conn.execute(sql, (symbol.symbol_id, start_date_str, end_date_str)).fetchall()
        return [
            Candle(
                id=row[0],
                symbol=symbol.symbol_name,
                source=row[2],
                end_date=row[3],
                open=row[4],
                close=row[5],
                high=row[6],
                low=row[7],
                last=row[8],
                volume=row[9],
                volume_quote=row[10],
            )
            for row in rows
        ]

    def get_min_candle_date(self) -> datetime | None:
        """Fetch the earliest date from the candles table.

        Returns None if table is empty.
        """
        sql = f"""
        SELECT MIN(EndDate)
        FROM {self.table_name}
        """  # noqa: S608
        row = self.conn.execute(sql).fetchone()
        return row[0] if row and row[0] else None

    def get_all_candles(self, symbol: Symbol) -> list[Candle]:
        """Retrieve all candles for the given symbol."""
        sql = f"""
        SELECT [Id]
            ,[SymbolID]
            ,[SourceID]
            ,[EndDate]
            ,[Open]
            ,[Close]
            ,[High]
            ,[Low]
            ,[Last]
            ,[Volume]
            ,[VolumeQuote]
        FROM {self.table_name}
        WHERE SymbolID = ?
        ORDER BY EndDate
        """  # noqa: S608
        rows = self.conn.execute(sql, (symbol.symbol_id,)).fetchall()
        return [
            Candle(
                id=row[0],
                symbol=symbol.symbol_name,
                source=row[2],
                end_date=row[3],
                open=row[4],
                close=row[5],
                high=row[6],
                low=row[7],
                last=row[8],
                volume=row[9],
                volume_quote=row[10],
            )
            for row in rows
        ]
