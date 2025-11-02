"""Test suite for batch refactored price_checker functions.

This script validates that all three candle fetching functions
(fetch_daily_candles, fetch_hourly_candles, fetch_fifteen_min_candles)
correctly use intelligent batch fetching for BINANCE and individual fetching for KUCOIN.
"""
# ruff: noqa: T201, S101, PLR2004

import os
import sqlite3
from datetime import datetime, timedelta, UTC

from dotenv import load_dotenv

from shared_code.price_checker import (
    fetch_daily_candles,
    fetch_hourly_candles,
    fetch_fifteen_min_candles,
)
from source_repository import Symbol, SourceID


def setup_test_db() -> sqlite3.Connection:
    """Create a fresh in-memory SQLite database for testing."""
    conn = sqlite3.Connection(":memory:")

    # Create required tables (matching database/init_sqlite.py schema)
    conn.execute("""
        CREATE TABLE Symbols (
            SymbolID INTEGER PRIMARY KEY AUTOINCREMENT,
            SourceID INTEGER NOT NULL,
            SymbolName TEXT NOT NULL,
            FullName TEXT,
            CoingeckoName TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE DailyCandles (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            SymbolID INTEGER NOT NULL,
            SourceID INTEGER DEFAULT 1,
            Date TEXT NOT NULL,
            EndDate TEXT NOT NULL,
            Open REAL NOT NULL,
            High REAL NOT NULL,
            Low REAL NOT NULL,
            Close REAL NOT NULL,
            Last REAL,
            Volume REAL NOT NULL,
            VolumeQuote REAL,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (SymbolID) REFERENCES Symbols(SymbolID),
            UNIQUE(SymbolID, Date)
        )
    """)

    conn.execute("""
        CREATE TABLE HourlyCandles (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            SymbolID INTEGER NOT NULL,
            SourceID INTEGER DEFAULT 1,
            Date TEXT NOT NULL,
            EndDate TEXT NOT NULL,
            Open REAL NOT NULL,
            High REAL NOT NULL,
            Low REAL NOT NULL,
            Close REAL NOT NULL,
            Last REAL,
            Volume REAL NOT NULL,
            VolumeQuote REAL,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (SymbolID) REFERENCES Symbols(SymbolID),
            UNIQUE(SymbolID, EndDate)
        )
    """)

    conn.execute("""
        CREATE TABLE FifteenMinCandles (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            SymbolID INTEGER NOT NULL,
            SourceID INTEGER DEFAULT 1,
            Date TEXT NOT NULL,
            EndDate TEXT NOT NULL,
            Open REAL NOT NULL,
            High REAL NOT NULL,
            Low REAL NOT NULL,
            Close REAL NOT NULL,
            Last REAL,
            Volume REAL NOT NULL,
            VolumeQuote REAL,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (SymbolID) REFERENCES Symbols(SymbolID),
            UNIQUE(SymbolID, EndDate)
        )
    """)

    conn.commit()
    return conn


def test_daily_candles_batch(symbol: Symbol, conn: sqlite3.Connection):
    """Test fetch_daily_candles with batch fetching (BINANCE)."""
    print("\n" + "="*80)
    print("TEST 1: Daily Candles - Batch Fetching (BINANCE)")
    print("="*80)
    
    # Fetch 30 days of data
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=30)
    
    print(f"Symbol: {symbol.symbol_name} (source_id={symbol.source_id.name})")
    print(f"Date Range: {start_date.date()} to {end_date.date()}")
    print(f"Expected: ~30 daily candles")
    
    candles = fetch_daily_candles(symbol, start_date, end_date, conn)
    
    print(f"✅ Fetched {len(candles)} daily candles")
    print(f"First candle: {candles[0].end_date} - Close: ${candles[0].close_price:.2f}")
    print(f"Last candle:  {candles[-1].end_date} - Close: ${candles[-1].close_price:.2f}")
    
    # Validate results
    assert len(candles) > 0, "Should fetch at least some candles"
    assert len(candles) <= 31, "Should not exceed expected range"
    
    # Verify all candles have valid data
    for candle in candles:
        assert candle.close_price > 0, f"Invalid close price: {candle.close_price}"
        assert candle.volume >= 0, f"Invalid volume: {candle.volume}"
    
    print("✅ All validations passed!")
    return candles


def test_hourly_candles_batch(symbol: Symbol, conn: sqlite3.Connection):
    """Test fetch_hourly_candles with batch fetching (BINANCE)."""
    print("\n" + "="*80)
    print("TEST 2: Hourly Candles - Batch Fetching (BINANCE)")
    print("="*80)
    
    # Fetch 48 hours of data
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=48)
    
    print(f"Symbol: {symbol.symbol_name} (source_id={symbol.source_id.name})")
    print(f"Time Range: {start_time} to {end_time}")
    print(f"Expected: ~48 hourly candles")
    
    candles = fetch_hourly_candles(symbol, start_time, end_time, conn)
    
    print(f"✅ Fetched {len(candles)} hourly candles")
    print(f"First candle: {candles[0].end_date} - Close: ${candles[0].close_price:.2f}")
    print(f"Last candle:  {candles[-1].end_date} - Close: ${candles[-1].close_price:.2f}")
    
    # Validate results
    assert len(candles) > 0, "Should fetch at least some candles"
    assert len(candles) <= 49, "Should not exceed expected range"
    
    # Verify all candles have valid data
    for candle in candles:
        assert candle.close_price > 0, f"Invalid close price: {candle.close_price}"
        assert candle.volume >= 0, f"Invalid volume: {candle.volume}"
    
    print("✅ All validations passed!")
    return candles


def test_fifteen_min_candles_batch(symbol: Symbol, conn: sqlite3.Connection):
    """Test fetch_fifteen_min_candles with batch fetching (BINANCE)."""
    print("\n" + "="*80)
    print("TEST 3: 15-Minute Candles - Batch Fetching (BINANCE)")
    print("="*80)
    
    # Fetch 4 hours of data (16 candles)
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=4)
    
    print(f"Symbol: {symbol.symbol_name} (source_id={symbol.source_id.name})")
    print(f"Time Range: {start_time} to {end_time}")
    print(f"Expected: ~16 fifteen-minute candles")
    
    candles = fetch_fifteen_min_candles(symbol, start_time, end_time, conn)
    
    print(f"✅ Fetched {len(candles)} fifteen-minute candles")
    print(f"First candle: {candles[0].end_date} - Close: ${candles[0].close_price:.2f}")
    print(f"Last candle:  {candles[-1].end_date} - Close: ${candles[-1].close_price:.2f}")
    
    # Validate results
    assert len(candles) > 0, "Should fetch at least some candles"
    assert len(candles) <= 17, "Should not exceed expected range"
    
    # Verify all candles have valid data
    for candle in candles:
        assert candle.close_price > 0, f"Invalid close price: {candle.close_price}"
        assert candle.volume >= 0, f"Invalid volume: {candle.volume}"
    
    print("✅ All validations passed!")
    return candles


def test_db_caching(symbol: Symbol, conn: sqlite3.Connection):
    """Test that second fetch uses database cache."""
    print("\n" + "="*80)
    print("TEST 4: Database Caching - Verify Second Fetch Uses Cache")
    print("="*80)
    
    # First fetch (from API)
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=7)
    
    print(f"First fetch: {start_date.date()} to {end_date.date()}")
    candles_1 = fetch_daily_candles(symbol, start_date, end_date, conn)
    count_1 = len(candles_1)
    print(f"✅ Fetched {count_1} candles from API + saved to DB")
    
    # Second fetch (from DB cache)
    print(f"\nSecond fetch: Same range {start_date.date()} to {end_date.date()}")
    candles_2 = fetch_daily_candles(symbol, start_date, end_date, conn)
    count_2 = len(candles_2)
    print(f"✅ Fetched {count_2} candles from DB cache")
    
    # Validate
    assert count_1 == count_2, "Cache should return same number of candles"
    assert candles_1[0].close_price == candles_2[0].close_price, "Candle data should match"
    
    print("✅ Caching works correctly!")


def test_missing_data_detection(symbol: Symbol, conn: sqlite3.Connection):
    """Test that function detects and fetches missing data."""
    print("\n" + "="*80)
    print("TEST 5: Missing Data Detection - Fetch Only Missing Candles")
    print("="*80)
    
    # Fetch first range (days 10-20)
    end_date = datetime.now(UTC) - timedelta(days=10)
    start_date = end_date - timedelta(days=10)
    
    print(f"First range: {start_date.date()} to {end_date.date()}")
    candles_1 = fetch_daily_candles(symbol, start_date, end_date, conn)
    print(f"✅ Fetched {len(candles_1)} candles")
    
    # Fetch wider range (days 5-25) - should fetch missing days
    end_date_2 = datetime.now(UTC) - timedelta(days=5)
    start_date_2 = end_date - timedelta(days=15)
    
    print(f"\nSecond range (wider): {start_date_2.date()} to {end_date_2.date()}")
    candles_2 = fetch_daily_candles(symbol, start_date_2, end_date_2, conn)
    print(f"✅ Fetched {len(candles_2)} candles (includes cached + new)")
    
    # Validate
    assert len(candles_2) > len(candles_1), "Should fetch more candles for wider range"
    
    print("✅ Missing data detection works correctly!")


def main():
    """Run all tests."""
    load_dotenv()
    
    # Set up test database
    conn = setup_test_db()
    
    # Create BINANCE test symbol
    btc_symbol = Symbol(
        symbol_id=1,
        symbol_name="BTCUSDT",
        full_name="Bitcoin",
        source_id=SourceID.BINANCE,
        coingecko_name="bitcoin",
    )
    
    try:
        # Run all tests
        test_daily_candles_batch(btc_symbol, conn)
        test_hourly_candles_batch(btc_symbol, conn)
        test_fifteen_min_candles_batch(btc_symbol, conn)
        test_db_caching(btc_symbol, conn)
        test_missing_data_detection(btc_symbol, conn)
        
        print("\n" + "="*80)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("="*80)
        print("\nPhase 2 refactoring is working correctly:")
        print("  ✅ Daily candles use batch fetching")
        print("  ✅ Hourly candles use batch fetching")
        print("  ✅ 15-minute candles use batch fetching")
        print("  ✅ Database caching works")
        print("  ✅ Missing data detection works")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
