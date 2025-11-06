"""Daily candle data repository for cryptocurrency markets."""

import os
from datetime import datetime
from typing import TYPE_CHECKING

from shared_code.common_price import Candle
from source_repository import Symbol
from technical_analysis.repositories.candle_repository import CandleRepository


if TYPE_CHECKING:
    import pyodbc

    from infra.sql_connection import SQLiteConnectionWrapper


class DailyCandleRepository(CandleRepository):
    """Repository for managing daily candlestick data."""

    def __init__(self, conn: "pyodbc.Connection | SQLiteConnectionWrapper") -> None:
        """Initialize the repository with a database connection."""
        super().__init__(conn, table_name="DailyCandles")

    def save_candle(self, symbol: Symbol, candle: Candle, source: int) -> None:
        """Override save_candle for DailyCandles table which has both Date and EndDate columns.

        Date is the date portion only, EndDate is the full datetime.
        """
        is_sqlite = os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"

        # Extract date portion from end_date
        if isinstance(candle.end_date, datetime):
            date_value = candle.end_date.date().isoformat()
        else:
            # If it's already a string, try to parse it
            date_value = (
                candle.end_date.split("T")[0]
                if "T" in str(candle.end_date)
                else str(candle.end_date).split()[0]
            )

        if is_sqlite:
            # SQLite: Use INSERT ... ON CONFLICT DO UPDATE to preserve row ID
            # This prevents orphaning RSI/indicator records that reference DailyCandleID
            sql = f"""
            INSERT INTO {self.table_name}
            (SymbolID, SourceID, Date, EndDate, [Open], [Close], High, Low,
             Last, Volume, VolumeQuote)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(SymbolID, Date)
            DO UPDATE SET
                SourceID = excluded.SourceID,
                EndDate = excluded.EndDate,
                [Open] = excluded.[Open],
                [Close] = excluded.[Close],
                High = excluded.High,
                Low = excluded.Low,
                Last = excluded.Last,
                Volume = excluded.Volume,
                VolumeQuote = excluded.VolumeQuote
            """
            self.conn.execute(
                sql,
                (
                    symbol.symbol_id,
                    source,
                    date_value,
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
            USING (SELECT ? as SymbolID, ? as SourceID, ? as Date, ? as EndDate) AS source
            ON (target.SymbolID = source.SymbolID
                AND target.SourceID = source.SourceID
                AND target.Date = source.Date)
            WHEN NOT MATCHED THEN
                INSERT (SymbolID, SourceID, Date, EndDate, [Open], [Close],
                        High, Low, Last, Volume, VolumeQuote)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """
            self.conn.execute(
                sql,
                (
                    symbol.symbol_id,
                    source,
                    date_value,
                    candle.end_date,  # For the USING clause
                    symbol.symbol_id,
                    source,
                    date_value,
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
        """Override get_candle for DailyCandles table to query by Date column."""
        # Extract date portion for comparison
        date_value = (
            end_date.date().isoformat() if isinstance(end_date, datetime) else str(end_date)
        )

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
        WHERE SymbolID = ? AND Date = ?
        """
        row = self.conn.execute(sql, (symbol.symbol_id, date_value)).fetchone()
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
