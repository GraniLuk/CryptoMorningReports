# 🗄️ Local SQLite Database Setup

## Why SQLite?

While your Azure subscription is offline, you can use **SQLite** - a file-based database that:
- ✅ Requires no server installation
- ✅ Works offline (no Azure needed)
- ✅ Contains **REAL price data** from Binance
- ✅ Compatible with your existing code
- ✅ Single file (`local_crypto.db`)

## Quick Start (5 minutes)

### 1. Set up the database with live data:

```powershell
.\setup-local-db.ps1 quick
```

This will:
1. Create the SQLite database schema
2. Fetch **real price data** from Binance (last 24 hours)
3. Populate hourly, 15-min, and daily candles

### 2. Update your `.env` file:

```env
DATABASE_TYPE=sqlite
SQLITE_DB_PATH=./local_crypto.db
OFFLINE_MODE=false
```

### 3. Run your reports with REAL data!

```powershell
.\run-local.ps1 daily
```

## What Data Do You Get?

### Quick Mode (Default - ~2 minutes):
- ✅ Last 24 hours of hourly candles
- ✅ Last 24 hours of 15-minute candles  
- ✅ Last 7 days of daily candles
- 📊 For all 12 symbols (BTC, ETH, XRP, SOL, etc.)

### Full Mode (~5 minutes):
```powershell
.\setup-local-db.ps1 full
```
- ✅ Last 7 days of hourly candles
- ✅ Last 24 hours of 15-minute candles
- ✅ Last 200 days of daily candles

## Manual Setup

If you prefer step-by-step:

### Step 1: Create database schema
```powershell
python database/init_sqlite.py
```

### Step 2: Fetch live data from Binance
```powershell
# Quick mode (24 hours)
python database/fetch_live_data.py quick

# Full mode (7 days hourly, 200 days daily)
python database/fetch_live_data.py
```

### Step 3: Verify database
```powershell
python database/init_sqlite.py verify
```

## Refreshing Data

The data in your local database gets stale over time. To refresh with latest prices:

```powershell
# Quick refresh (recommended daily)
python database/fetch_live_data.py quick

# Full refresh (when you need historical data)
python database/fetch_live_data.py
```

**Pro tip:** Add this to your daily routine or create a scheduled task!

## Database Schema

Your SQLite database contains:

```sql
Symbols              # Symbol definitions (BTC, ETH, etc.)
  ├── symbol_id
  ├── symbol_name
  └── display_name

HourlyCandles        # Hourly OHLCV data
  ├── symbol_id
  ├── end_date
  ├── open, high, low, close
  └── volume

FifteenMinCandles    # 15-minute OHLCV data
  └── (same structure)

DailyCandles         # Daily OHLCV data
  └── (same structure)
```

## Switching Between SQLite and Azure SQL

In your `.env` file:

```env
# Use local SQLite
DATABASE_TYPE=sqlite

# Use Azure SQL (when subscription is back)
DATABASE_TYPE=azuresql
```

No code changes needed! The connection layer handles both automatically.

## Troubleshooting

### "Database not found" error
```powershell
# Re-create the database
python database/init_sqlite.py
```

### "No data" or old data
```powershell
# Refresh from Binance
python database/fetch_live_data.py quick
```

### Binance API errors
- Check your internet connection
- Binance public API requires no authentication
- If blocked in your region, you may need a VPN

### "Symbol not found" errors
```powershell
# Check what symbols are in your database
python database/init_sqlite.py verify
```

## Comparing SQLite vs Azure SQL

| Feature | SQLite (Local) | Azure SQL |
|---------|----------------|-----------|
| Cost | Free | Requires subscription |
| Setup | 2 minutes | Already set up (when active) |
| Data source | Binance API | Your historical data |
| Performance | Very fast (local file) | Network latency |
| Data freshness | Manual refresh | Auto-updated by your functions |
| Best for | Development/Testing | Production |

## File Location

Your database file:
- **Location**: `./local_crypto.db` (in project root)
- **Size**: ~1-10 MB depending on data amount
- **Backup**: Automatically backed up when recreating

## Advanced: Custom Symbols

To add more symbols:

1. Edit `database/init_sqlite.py` and add to `default_symbols`
2. Make sure the symbol exists on Binance as `{SYMBOL}USDT`
3. Re-run: `python database/init_sqlite.py`
4. Fetch data: `python database/fetch_live_data.py quick`

## Benefits Over Mock Data

| Feature | Mock Data | SQLite Real Data |
|---------|-----------|------------------|
| Price accuracy | Randomized | Real from Binance |
| Technical indicators | Simulated | Calculated from real OHLCV |
| Historical patterns | Fake | Actual market behavior |
| AI analysis quality | Limited | Production-quality |
| Testing authenticity | Low | High |

## Next Steps

Once your SQLite database is set up:

1. ✅ Run daily reports with real data
2. ✅ Test your AI analysis pipeline
3. ✅ Develop new features
4. ✅ When Azure subscription returns, switch to `DATABASE_TYPE=azuresql`

**No code changes needed between SQLite and Azure SQL!** 🎉
