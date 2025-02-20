from datetime import datetime
from typing import Optional

from sharedCode.commonPrice import Candle
from source_repository import Symbol


class DailyCandleRepository:
    def __init__(self, conn):
        self.conn = conn

    def save_candle(self, symbol: Symbol, candle: Candle, source: int) -> None:
        sql = """
        MERGE DailyCandles AS target
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

    def get_candle(self, symbol: Symbol, end_date: datetime) -> Optional[Candle]:
        sql = """
        SELECT [SymbolID]
      ,[SourceID]
      ,[EndDate]
      ,[Open]
      ,[Close]
      ,[High]
      ,[Low]
      ,[Last]
      ,[Volume]
      ,[VolumeQuote]
        FROM DailyCandles
        WHERE SymbolID = ? AND EndDate = ?
        """
        row = self.conn.execute(sql, (symbol.symbol_id, end_date)).fetchone()
        if row:
            return Candle(
                symbol=symbol.symbol_name,
                source=row[1],
                end_date=row[2],
                open=row[3],
                close=row[4],
                high=row[5],
                low=row[6],
                last=row[7],
                volume=row[8],
                volume_quote=row[9],
            )
        return None

    def get_candles(
        self, symbol: Symbol, start_date: datetime, end_date: datetime
    ) -> list[Candle]:
        sql = """
        SELECT [SymbolID]
          ,[SourceID]
          ,[EndDate]
          ,[Open]
          ,[Close]
          ,[High]
          ,[Low]
          ,[Last]
          ,[Volume]
          ,[VolumeQuote]
        FROM DailyCandles
        WHERE SymbolID = ? 
        AND EndDate >= ? 
        AND EndDate <= ?
        ORDER BY EndDate
        """
        rows = self.conn.execute(
            sql, (symbol.symbol_id, start_date, end_date)
        ).fetchall()
        return [
            Candle(
                symbol=symbol.symbol_name,
                source=row[1],
                end_date=row[2],
                open=row[3],
                close=row[4],
                high=row[5],
                low=row[6],
                last=row[7],
                volume=row[8],
                volume_quote=row[9],
            )
            for row in rows
        ]

    def get_min_candle_date(self) -> Optional[datetime]:
        """
        Fetches the earliest date from DailyCandles table
        Returns None if table is empty
        """
        sql = """
        SELECT MIN(EndDate)
        FROM DailyCandles
        """
        row = self.conn.execute(sql).fetchone()
        return row[0] if row and row[0] else None

    def get_all_candles(
        self, symbol: Symbol) -> list[Candle]:
        sql = """
        SELECT [SymbolID]
          ,[SourceID]
          ,[EndDate]
          ,[Open]
          ,[Close]
          ,[High]
          ,[Low]
          ,[Last]
          ,[Volume]
          ,[VolumeQuote]
        FROM DailyCandles
        WHERE SymbolID = ?
        ORDER BY EndDate
        """
        rows = self.conn.execute(
            sql, (symbol.symbol_id)
        ).fetchall()
        return [
            Candle(
                symbol=symbol.symbol_name,
                source=row[1],
                end_date=row[2],
                open=row[3],
                close=row[4],
                high=row[5],
                low=row[6],
                last=row[7],
                volume=row[8],
                volume_quote=row[9],
            )
            for row in rows
        ]