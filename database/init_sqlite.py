"""
SQLite database schema and initialization for local development.
This creates a local database structure compatible with the Azure SQL schema.
"""

import os
import sqlite3
from datetime import datetime


def create_sqlite_database(db_path="./local_crypto.db"):
    """
    Create SQLite database with schema matching Azure SQL.
    Returns connection object.
    """
    # Remove existing database if present
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.rename(db_path, backup_path)
        print(f"📦 Backed up existing database to: {backup_path}")

    print(f"🗄️  Creating new SQLite database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create Symbols table (matching Azure SQL schema)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Symbols (
            SymbolID INTEGER PRIMARY KEY AUTOINCREMENT,
            SymbolName TEXT NOT NULL UNIQUE,
            FullName TEXT,
            SourceID INTEGER DEFAULT 1,
            CoinGeckoName TEXT,
            IsActive INTEGER DEFAULT 1,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create HourlyCandles table (matching Azure SQL schema)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS HourlyCandles (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            SymbolID INTEGER NOT NULL,
            SourceID INTEGER DEFAULT 1,
            OpenTime TEXT NOT NULL,
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

    # Create FifteenMinCandles table (matching Azure SQL schema)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS FifteenMinCandles (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            SymbolID INTEGER NOT NULL,
            SourceID INTEGER DEFAULT 1,
            OpenTime TEXT NOT NULL,
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

    # Create DailyCandles table (matching Azure SQL schema)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS DailyCandles (
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

    # Create RSI tables for different timeframes (matching Azure SQL schema)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS RSI (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            DailyCandleID INTEGER NOT NULL,
            RSI REAL NOT NULL,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (DailyCandleID) REFERENCES DailyCandles(Id),
            UNIQUE(DailyCandleID)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS HourlyRSI (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            HourlyCandleID INTEGER NOT NULL,
            RSI REAL NOT NULL,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (HourlyCandleID) REFERENCES HourlyCandles(Id),
            UNIQUE(HourlyCandleID)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS FifteenMinRSI (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            FifteenMinCandleID INTEGER NOT NULL,
            RSI REAL NOT NULL,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (FifteenMinCandleID) REFERENCES FifteenMinCandles(Id),
            UNIQUE(FifteenMinCandleID)
        )
    """)

    # Create MovingAverages table (matching Azure SQL schema)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS MovingAverages (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            SymbolID INTEGER NOT NULL,
            IndicatorDate TEXT NOT NULL,
            CurrentPrice REAL,
            MA50 REAL,
            MA200 REAL,
            EMA50 REAL,
            EMA200 REAL,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (SymbolID) REFERENCES Symbols(SymbolID),
            UNIQUE(SymbolID, IndicatorDate)
        )
    """)

    # Create MACD table (matching Azure SQL schema)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS MACD (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            SymbolID INTEGER NOT NULL,
            IndicatorDate TEXT NOT NULL,
            CurrentPrice REAL,
            MACD REAL,
            Signal REAL,
            Histogram REAL,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (SymbolID) REFERENCES Symbols(SymbolID),
            UNIQUE(SymbolID, IndicatorDate)
        )
    """)

    # Create VolumeHistory table (matching Azure SQL schema)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS VolumeHistory (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            SymbolID INTEGER NOT NULL,
            Volume REAL,
            IndicatorDate TEXT NOT NULL,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (SymbolID) REFERENCES Symbols(SymbolID),
            UNIQUE(SymbolID, IndicatorDate)
        )
    """)

    # Create SOPR table (matching Azure SQL schema)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS SOPR (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            IndicatorDate TEXT NOT NULL UNIQUE,
            SOPR REAL,
            STH_SOPR REAL,
            LTH_SOPR REAL,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create PriceRange table (matching Azure SQL schema)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PriceRange (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            SymbolID INTEGER NOT NULL,
            IndicatorDate TEXT NOT NULL,
            LowPrice REAL,
            HighPrice REAL,
            RangePercent REAL,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (SymbolID) REFERENCES Symbols(SymbolID),
            UNIQUE(SymbolID, IndicatorDate)
        )
    """)

    # Create MarketCapHistory table (matching Azure SQL schema)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS MarketCapHistory (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            SymbolID INTEGER NOT NULL,
            MarketCap REAL,
            IndicatorDate TEXT NOT NULL,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (SymbolID) REFERENCES Symbols(SymbolID),
            UNIQUE(SymbolID, IndicatorDate)
        )
    """)

    # Create StepNResults table for STEPN token metrics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS StepNResults (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            GMTPrice REAL,
            GSTPrice REAL,
            Ratio REAL,
            Date TEXT NOT NULL UNIQUE,
            EMA14 REAL,
            Min24Value REAL,
            Max24Value REAL,
            Range24 REAL,
            RSI REAL,
            TransactionsCount INTEGER,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes for better query performance
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_hourly_symbol_date ON HourlyCandles(SymbolID, EndDate)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_fifteen_symbol_date ON FifteenMinCandles(SymbolID, EndDate)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_daily_symbol_date ON DailyCandles(SymbolID, Date)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_rsi_daily_candle ON RSI(DailyCandleID)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_rsi_hourly_candle ON HourlyRSI(HourlyCandleID)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_rsi_fifteen_candle ON FifteenMinRSI(FifteenMinCandleID)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_ma_symbol_date ON MovingAverages(SymbolID, IndicatorDate)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_macd_symbol_date ON MACD(SymbolID, IndicatorDate)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_volume_symbol_date ON VolumeHistory(SymbolID, IndicatorDate)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sopr_date ON SOPR(IndicatorDate)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_pricerange_symbol_date ON PriceRange(SymbolID, IndicatorDate)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_marketcap_symbol_date ON MarketCapHistory(SymbolID, IndicatorDate)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_macd_symbol_date ON MACD(SymbolID, IndicatorDate)"
    )

    # Insert default symbols (with SourceID and CoinGeckoName for compatibility)
    default_symbols = [
        ("BTC", "Bitcoin", 1, "bitcoin"),
        ("ETH", "Ethereum", 1, "ethereum"),
        ("XRP", "Ripple", 1, "ripple"),
        ("SOL", "Solana", 1, "solana"),
        ("ATOM", "Cosmos", 1, "cosmos"),
        ("DOT", "Polkadot", 1, "polkadot"),
        ("LINK", "Chainlink", 1, "chainlink"),
        ("DOGE", "Dogecoin", 1, "dogecoin"),
        ("TON", "Toncoin", 1, "the-open-network"),
        ("HBAR", "Hedera", 1, "hedera-hashgraph"),
        ("OSMO", "Osmosis", 1, "osmosis"),
        ("VIRTUAL", "Virtual Protocol", 1, "virtual-protocol"),
    ]

    cursor.executemany(
        "INSERT OR IGNORE INTO Symbols (SymbolName, FullName, SourceID, CoinGeckoName) VALUES (?, ?, ?, ?)",
        default_symbols,
    )

    conn.commit()
    print(f"✅ Database schema created successfully!")
    print(f"   - Symbols: {len(default_symbols)} symbols added")
    print(f"   - Tables: Symbols, HourlyCandles, FifteenMinCandles, DailyCandles")

    return conn


def verify_database(db_path="./local_crypto.db"):
    """Verify database structure and content."""
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\n📊 Database Tables: {', '.join(tables)}")

    # Check symbols
    cursor.execute("SELECT SymbolID, SymbolName, FullName FROM Symbols")
    symbols = cursor.fetchall()
    print(f"\n💰 Symbols ({len(symbols)}):")
    for symbol_id, name, display_name in symbols:
        print(f"   {symbol_id}: {name} ({display_name})")

    # Check candle counts
    cursor.execute("SELECT COUNT(*) FROM HourlyCandles")
    hourly_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM FifteenMinCandles")
    fifteen_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM DailyCandles")
    daily_count = cursor.fetchone()[0]

    print(f"\n📈 Candle Data:")
    print(f"   Hourly: {hourly_count} candles")
    print(f"   15-min: {fifteen_count} candles")
    print(f"   Daily: {daily_count} candles")

    conn.close()
    return True


if __name__ == "__main__":
    import sys

    db_path = os.getenv("SQLITE_DB_PATH", "./local_crypto.db")

    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        verify_database(db_path)
    else:
        conn = create_sqlite_database(db_path)
        conn.close()
        print(f"\n🎉 SQLite database ready!")
        print(f"\nNext steps:")
        print(f"  1. Run: python database/init_sqlite.py verify")
        print(f"  2. Populate with data: python database/fetch_live_data.py")
