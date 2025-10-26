from datetime import datetime

from sharedCode.commonPrice import Candle
from source_repository import Symbol


class CandleRepository:
    def __init__(self, conn, table_name: str):
        self.conn = conn
        self.table_name = table_name

    def save_candle(self, symbol: Symbol, candle: Candle, source: int) -> None:
        # Check if we're using SQLite or SQL Server
        import os

        is_sqlite = os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"

        if is_sqlite:
            # SQLite uses INSERT OR REPLACE
            sql = f"""
            INSERT OR REPLACE INTO {self.table_name} 
            (SymbolID, SourceID, EndDate, [Open], [Close], High, Low, Last, Volume, VolumeQuote)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
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
                INSERT (SymbolID, SourceID, EndDate, [Open], [Close], High, Low, Last, Volume, VolumeQuote)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """
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
        """
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
        """
        rows = self.conn.execute(sql, (symbol.symbol_id, start_date, end_date)).fetchall()
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
        """
        Fetches the earliest date from the candles table
        Returns None if table is empty
        """
        sql = f"""
        SELECT MIN(EndDate)
        FROM {self.table_name}
        """
        row = self.conn.execute(sql).fetchone()
        return row[0] if row and row[0] else None

    def get_all_candles(self, symbol: Symbol) -> list[Candle]:
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
        """
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
