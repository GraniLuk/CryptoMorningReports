"""
Fetch live cryptocurrency data from Binance and populate local SQLite database.
This fetches real market data for local development without Azure SQL.
"""

import logging
import os
import sqlite3
from datetime import datetime, timezone

from binance.client import Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_sqlite_connection(db_path=None):
    """Get SQLite database connection."""
    if db_path is None:
        db_path = os.getenv("SQLITE_DB_PATH", "./local_crypto.db")

    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"Database not found: {db_path}\nPlease run: python database/init_sqlite.py"
        )

    return sqlite3.connect(db_path)


def fetch_binance_klines(symbol, interval, limit=100):
    """
    Fetch candle data from Binance.

    Args:
        symbol: Trading pair (e.g., "BTCUSDT")
        interval: Candle interval (e.g., Client.KLINE_INTERVAL_1HOUR)
        limit: Number of candles to fetch
    """
    try:
        client = Client()  # No API key needed for public data
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)

        candles = []
        for k in klines:
            candle = {
                "open_time": datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc),
                "end_time": datetime.fromtimestamp(k[6] / 1000, tz=timezone.utc),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            }
            candles.append(candle)

        return candles

    except Exception as e:
        logger.error(f"Error fetching {symbol} {interval}: {e}")
        return []


def populate_hourly_candles(conn, hours=168):  # 7 days
    """Fetch and store hourly candles for all symbols."""
    cursor = conn.cursor()

    # Get all symbols (using Azure SQL compatible column names)
    cursor.execute("SELECT SymbolID, SymbolName FROM Symbols WHERE IsActive = 1")
    symbols = cursor.fetchall()

    logger.info(f"Fetching hourly candles for {len(symbols)} symbols...")

    for symbol_id, symbol_name in symbols:
        trading_pair = f"{symbol_name}USDT"
        logger.info(f"  Fetching {trading_pair}...")

        candles = fetch_binance_klines(
            trading_pair, Client.KLINE_INTERVAL_1HOUR, limit=min(hours, 1000)
        )

        if not candles:
            logger.warning(f"    No data for {trading_pair}")
            continue

        # Insert candles (using Azure SQL compatible column names)
        for candle in candles:
            cursor.execute(
                """
                INSERT OR REPLACE INTO HourlyCandles 
                (SymbolID, SourceID, OpenTime, EndDate, Open, High, Low, Close, Last, Volume, VolumeQuote)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    symbol_id,
                    1,  # SourceID = 1 (BINANCE)
                    candle["open_time"].isoformat(),
                    candle["end_time"].isoformat(),
                    candle["open"],
                    candle["high"],
                    candle["low"],
                    candle["close"],
                    candle["close"],  # Last = Close for simplicity
                    candle["volume"],
                    candle.get("quote_volume", 0),  # VolumeQuote
                ),
            )

        conn.commit()
        logger.info(f"    ✓ Inserted {len(candles)} hourly candles")


def populate_fifteen_min_candles(conn, hours=24):  # 1 day
    """Fetch and store 15-minute candles for all symbols."""
    cursor = conn.cursor()

    cursor.execute("SELECT SymbolID, SymbolName FROM Symbols WHERE IsActive = 1")
    symbols = cursor.fetchall()

    logger.info(f"Fetching 15-min candles for {len(symbols)} symbols...")

    for symbol_id, symbol_name in symbols:
        trading_pair = f"{symbol_name}USDT"
        logger.info(f"  Fetching {trading_pair}...")

        # Calculate number of 15-min candles needed
        limit = min(hours * 4, 1000)

        candles = fetch_binance_klines(
            trading_pair, Client.KLINE_INTERVAL_15MINUTE, limit=limit
        )

        if not candles:
            logger.warning(f"    No data for {trading_pair}")
            continue

        for candle in candles:
            cursor.execute(
                """
                INSERT OR REPLACE INTO FifteenMinCandles 
                (SymbolID, SourceID, OpenTime, EndDate, Open, High, Low, Close, Last, Volume, VolumeQuote)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    symbol_id,
                    1,  # SourceID = 1 (BINANCE)
                    candle["open_time"].isoformat(),
                    candle["end_time"].isoformat(),
                    candle["open"],
                    candle["high"],
                    candle["low"],
                    candle["close"],
                    candle["close"],  # Last = Close
                    candle["volume"],
                    candle.get("quote_volume", 0),  # VolumeQuote
                ),
            )

        conn.commit()
        logger.info(f"    ✓ Inserted {len(candles)} 15-min candles")


def populate_daily_candles(conn, days=200):  # ~6-7 months
    """Fetch and store daily candles for all symbols."""
    cursor = conn.cursor()

    cursor.execute("SELECT SymbolID, SymbolName FROM Symbols WHERE IsActive = 1")
    symbols = cursor.fetchall()

    logger.info(f"Fetching daily candles for {len(symbols)} symbols...")

    for symbol_id, symbol_name in symbols:
        trading_pair = f"{symbol_name}USDT"
        logger.info(f"  Fetching {trading_pair}...")

        candles = fetch_binance_klines(
            trading_pair, Client.KLINE_INTERVAL_1DAY, limit=min(days, 1000)
        )

        if not candles:
            logger.warning(f"    No data for {trading_pair}")
            continue

        for candle in candles:
            cursor.execute(
                """
                INSERT OR REPLACE INTO DailyCandles 
                (SymbolID, SourceID, Date, EndDate, Open, High, Low, Close, Last, Volume, VolumeQuote)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    symbol_id,
                    1,  # SourceID = 1 (BINANCE)
                    candle["end_time"].date().isoformat(),
                    candle["end_time"].isoformat(),
                    candle["open"],
                    candle["high"],
                    candle["low"],
                    candle["close"],
                    candle["close"],  # Last = Close
                    candle["volume"],
                    candle.get("quote_volume", 0),  # VolumeQuote
                ),
            )

        conn.commit()
        logger.info(f"    ✓ Inserted {len(candles)} daily candles")


def populate_all_data(db_path=None):
    """Fetch and populate all candle data."""
    conn = get_sqlite_connection(db_path)

    try:
        logger.info("=" * 60)
        logger.info("Fetching live data from Binance...")
        logger.info("=" * 60)

        # Populate all timeframes
        populate_daily_candles(conn, days=200)
        populate_hourly_candles(conn, hours=168)  # 7 days
        populate_fifteen_min_candles(conn, hours=24)  # 1 day

        logger.info("=" * 60)
        logger.info("✅ Database populated successfully!")
        logger.info("=" * 60)

        # Show summary
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM HourlyCandles")
        hourly = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM FifteenMinCandles")
        fifteen = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM DailyCandles")
        daily = cursor.fetchone()[0]

        logger.info(f"\n📊 Data Summary:")
        logger.info(f"   Daily candles: {daily}")
        logger.info(f"   Hourly candles: {hourly}")
        logger.info(f"   15-min candles: {fifteen}")
        logger.info(f"\n🎉 Ready to use! Run your reports now.")

    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "quick":
            # Quick mode - less data for fast testing
            conn = get_sqlite_connection()
            try:
                logger.info("Quick mode: fetching last 24 hours only...")
                populate_hourly_candles(conn, hours=24)
                populate_fifteen_min_candles(conn, hours=24)
                populate_daily_candles(conn, days=7)
            finally:
                conn.close()
        else:
            logger.info(f"Unknown option: {sys.argv[1]}")
            logger.info("Usage:")
            logger.info("  python database/fetch_live_data.py        # Full data")
            logger.info("  python database/fetch_live_data.py quick  # Quick test")
    else:
        populate_all_data()
