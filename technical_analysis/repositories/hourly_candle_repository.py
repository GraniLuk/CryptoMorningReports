import os
from datetime import datetime, timedelta

from shared_code.common_price import Candle
from source_repository import Symbol
from technical_analysis.repositories.candle_repository import CandleRepository


class HourlyCandleRepository(CandleRepository):
    def __init__(self, conn):
        super().__init__(conn, table_name="HourlyCandles")

    def save_candle(self, symbol: Symbol, candle: Candle, source: int) -> None:
        """Override to handle OpenTime column for SQLite"""
        is_sqlite = os.getenv("DATABASE_TYPE", "azuresql").lower() == "sqlite"

        if is_sqlite:
            # Calculate OpenTime as 1 hour before EndDate
            end_date = candle.end_date
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

            open_time = end_date - timedelta(hours=1)

            # SQLite: Insert both OpenTime and EndDate
            sql = f"""
            INSERT OR REPLACE INTO {self.table_name}
            (SymbolID, SourceID, OpenTime, EndDate, [Open], [Close], High, Low,
             Last, Volume, VolumeQuote)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.conn.execute(
                sql,
                (
                    symbol.symbol_id,
                    source,
                    open_time.isoformat(),
                    end_date.isoformat() if hasattr(end_date, "isoformat") else end_date,
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
        else:
            # SQL Server doesn't need OpenTime override
            super().save_candle(symbol, candle, source)
