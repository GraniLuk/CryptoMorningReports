from technical_analysis.repositories.candle_repository import CandleRepository


class DailyCandleRepository(CandleRepository):
    def __init__(self, conn):
        super().__init__(conn, table_name="DailyCandles")
