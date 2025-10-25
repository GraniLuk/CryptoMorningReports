# Derivatives Data Integration

## Overview
This feature adds **Open Interest** and **Funding Rate** tracking from Binance Futures to provide deeper market insights into leverage, sentiment, and positioning.

## What's Included

### 1. Database Tables
- **OpenInterest**: Tracks open interest values and USD equivalent
- **FundingRate**: Tracks funding rates and next funding times

### 2. Data Fetching
- `fetch_binance_futures_metrics()` - Fetches both OI and funding rate in a single call
- Automatically called during daily report generation
- Only processes Binance symbols (futures market)

### 3. Reports
- New **Derivatives Report** section in daily Telegram messages
- Integrated into **Aggregated Data** sent to AI analysis
- Shows: Open Interest, OI Value (USD), Funding Rate, Next Funding Time

## Setup Instructions

### Step 1: Run Database Migration
```powershell
.\run-derivatives-migration.ps1
```

Or manually:
```powershell
python database/migrations/add_derivatives_tables.py
```

This creates the `OpenInterest` and `FundingRate` tables in your database (SQLite or Azure SQL).

### Step 2: Test Data Fetching
```powershell
python technical_analysis/derivatives_report.py
```

You should see output like:
```
+--------+----------------+-----------------+------------------+--------------+
| Symbol | Open Interest  | OI Value (USD)  | Funding Rate (%) | Next Funding |
+--------+----------------+-----------------+------------------+--------------+
|  BTC   |   45,234.50    |  $2,034,567,890 |    0.0100%       |   16:00 UTC  |
|  ETH   |  234,567.80    |    $456,789,012 |    0.0085%       |   16:00 UTC  |
+--------+----------------+-----------------+------------------+--------------+
```

### Step 3: Run Daily Report
The derivatives data will now be automatically included when you run:
```powershell
python function_app.py
```

Or locally:
```powershell
.\run-local.ps1
```

## What the Metrics Mean

### Open Interest (OI)
- **Definition**: Total number of outstanding derivative contracts
- **High OI**: More leverage in the market, higher risk of volatility
- **Rising OI + Rising Price**: Strong bullish conviction
- **Rising OI + Falling Price**: Strong bearish conviction
- **Falling OI**: Positions closing, potential trend reversal

### Funding Rate
- **Definition**: Periodic payment between long and short positions
- **Positive Rate**: Longs pay shorts (bullish sentiment dominates)
- **Negative Rate**: Shorts pay longs (bearish sentiment dominates)
- **High Positive Rate** (>0.1%): Overleveraged longs, potential liquidation cascade
- **High Negative Rate** (<-0.1%): Overleveraged shorts, potential short squeeze

### Combined Analysis
The AI analysis receives both metrics to identify:
- **Leverage buildup**: Rising OI indicates more traders entering leveraged positions
- **Sentiment extremes**: Extreme funding rates suggest overcrowded trades
- **Liquidation zones**: High OI + extreme funding = potential cascade events
- **Trend confirmation**: OI + price movement direction validates trend strength

## Database Schema

### OpenInterest Table
```sql
CREATE TABLE OpenInterest (
    Id              INT IDENTITY(1,1) PRIMARY KEY,
    SymbolID        INT NOT NULL,
    OpenInterest    FLOAT NOT NULL,           -- Number of contracts
    OpenInterestValue FLOAT,                  -- USD value (OI * price)
    IndicatorDate   DATETIME NOT NULL,
    CreatedAt       DATETIME DEFAULT GETUTCDATE(),
    FOREIGN KEY (SymbolID) REFERENCES Symbols(SymbolID),
    UNIQUE(SymbolID, IndicatorDate)
)
```

### FundingRate Table
```sql
CREATE TABLE FundingRate (
    Id              INT IDENTITY(1,1) PRIMARY KEY,
    SymbolID        INT NOT NULL,
    FundingRate     FLOAT NOT NULL,           -- Rate as percentage
    FundingTime     DATETIME NOT NULL,        -- Next funding time
    IndicatorDate   DATETIME NOT NULL,
    CreatedAt       DATETIME DEFAULT GETUTCDATE(),
    FOREIGN KEY (SymbolID) REFERENCES Symbols(SymbolID),
    UNIQUE(SymbolID, IndicatorDate)
)
```

## Files Modified/Created

### New Files
- `database/migrations/add_derivatives_tables.py` - Database migration
- `technical_analysis/derivatives_report.py` - Report generation
- `technical_analysis/repositories/open_interest_repository.py` - OI data access
- `technical_analysis/repositories/funding_rate_repository.py` - Funding rate data access
- `run-derivatives-migration.ps1` - Migration runner script
- `DERIVATIVES_README.md` - This file

### Modified Files
- `sharedCode/binance.py` - Added `fetch_binance_futures_metrics()` and `FuturesMetrics` class
- `reports/daily_report.py` - Added derivatives report generation and Telegram sending
- `technical_analysis/repositories/aggregated_repository.py` - Added OI and funding rate to aggregated view

## API Endpoints Used

### Binance Futures API
- **Open Interest**: `GET /fapi/v1/openInterest`
- **Funding Rate**: `GET /fapi/v1/fundingRate`
- **Mark Price**: `GET /fapi/v1/premiumIndex` (for next funding time)
- **Ticker**: `GET /fapi/v1/ticker/24hr` (for price calculation)

All endpoints are public and don't require API keys.

## Troubleshooting

### "No futures data available"
- **Cause**: Symbol doesn't have a futures market on Binance
- **Solution**: Only symbols with `source_id = BINANCE` will have derivatives data

### Migration fails
- **SQLite**: Check file permissions on `local_crypto.db`
- **Azure SQL**: Verify connection string and database permissions

### Data not appearing in aggregated view
- Run the migration first, then regenerate the data
- Check that `OpenInterest` and `FundingRate` tables exist

## Future Enhancements

Potential additions (from `PROMPT_EXPANSION_PLAN.md`):
- **Liquidation Heatmap**: Cluster analysis of liquidation levels
- **Long/Short Ratio**: Exchange-specific positioning data
- **24h OI Delta**: Track rapid changes in open interest
- **Historical Funding Trends**: Rising/falling funding rate analysis

## References

- [Binance Futures API Documentation](https://binance-docs.github.io/apidocs/futures/en/)
- [Understanding Funding Rates](https://www.binance.com/en/support/faq/what-is-funding-rate-and-how-is-it-calculated-360033525031)
- [Open Interest Explained](https://www.binance.com/en/support/faq/what-is-open-interest-360033779452)
