from datetime import datetime

from sharedCode.commonPrice import Candle
from source_repository import Symbol
from technical_analysis.repositories.candle_repository import CandleRepository


class DailyCandleRepository(CandleRepository):
    def __init__(self, conn):
        super().__init__(conn, table_name="DailyCandles")

    def save_candle(self, symbol: Symbol, candle: Candle, source: int) -> None:
        """
        Override save_candle for DailyCandles table which has both Date and EndDate columns.
        Date is the date portion only, EndDate is the full datetime.
        """
        import os

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
            (SymbolID, SourceID, Date, EndDate, [Open], [Close], High, Low, Last, Volume, VolumeQuote)
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
                INSERT (SymbolID, SourceID, Date, EndDate, [Open], [Close], High, Low, Last, Volume, VolumeQuote)
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
