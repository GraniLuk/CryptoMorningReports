from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv

from infra.sql_connection import connect_to_sql
from shared_code.price_checker import fetch_daily_candles
from source_repository import SourceID, fetch_symbols

load_dotenv()
conn = connect_to_sql()
symbols = fetch_symbols(conn)
binance_symbol = next(s for s in symbols if s.source_id == SourceID.BINANCE)
today = datetime.now(UTC).date()
start_date = today - timedelta(days=2)
candles = fetch_daily_candles(binance_symbol, start_date, today, conn)

print(f"Total candles: {len(candles)}")
for i, c in enumerate(candles):
    is_datetime = isinstance(c.end_date, datetime)
    has_tz = c.end_date.tzinfo is not None if is_datetime else False
    print(f"{i}: type={type(c.end_date).__name__}, is_datetime={is_datetime}, has_tz={has_tz}")

# Test the all() condition
result = all(isinstance(c.end_date, datetime) and c.end_date.tzinfo is not None for c in candles)
print(f"\nall() condition result: {result}")
