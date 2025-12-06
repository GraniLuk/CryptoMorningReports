# Order Book Liquidity & CVD Data Integration

## Overview
This feature adds **Order Book Depth**, **Liquidity Analysis**, and **Cumulative Volume Delta (CVD)** from Binance Spot and Futures markets to provide insights into market microstructure, bid/ask imbalances, large order walls, and real-time order flow dynamics.

## What's Included

### 1. Database Tables
- **OrderBookMetrics**: Tracks bid/ask ratios, spreads, volumes, and wall detection
- **CumulativeVolumeDelta**: Tracks taker buy/sell volume and net order flow

### 2. Data Fetching
- `fetch_binance_order_book()` - Fetches spot market order book (top 100 levels)
- `fetch_binance_futures_order_book()` - Fetches futures market order book (top 100 levels)
- `fetch_binance_cvd()` - Fetches aggregate trades and calculates CVD metrics
- `OrderBookMetrics` dataclass - Standardized format for order book data
- `CVDMetrics` dataclass - Standardized format for order flow data

### 3. Reports
- New **Order Book Liquidity** section in daily Telegram messages
- New **Cumulative Volume Delta (CVD)** section with order flow analysis
- Integrated into **AI Analysis Context** for enhanced market insights
- Shows: Bid/Ask Ratio, Spread %, Total Bid/Ask Volume, Largest Walls, CVD 24h, Buy/Sell Volume, Large Trade Imbalance

## Setup Instructions

### Step 1: Run Database Migrations
```powershell
python database/migrations/add_order_book_tables.py
python database/migrations/add_cvd_tables.py
```

This creates the `OrderBookMetrics` and `CumulativeVolumeDelta` tables in your database (SQLite or Azure SQL).

### Step 2: Test Data Fetching
```powershell
python technical_analysis/order_book_report.py
```

You should see output like:
```
📊 Order Book Liquidity (2025-01-19 10:30 UTC)
+--------+----------+---------+----------+----------+-----------+-----------+
| Symbol | Bid/Ask  | Spread% | Bid Vol  | Ask Vol  | Bid Wall  | Ask Wall  |
+--------+----------+---------+----------+----------+-----------+-----------+
|  BTC   |   🟢1.25 |  0.02%  |  1.23M   |  980.5K  |   250.0K  |   180.2K  |
|  ETH   |   🟢1.48 |  0.03%  |  1.14M   |  890.1K  |   125.5K  |   200.1K  |
|  SOL   |   ⚪1.02 |  0.05%  |  456.2K  |  447.8K  |    50.2K  |    48.9K  |
+--------+----------+---------+----------+----------+-----------+-----------+

📈 Cumulative Volume Delta (CVD)
+--------+------------+------------+------------+------------+-----------+
| Symbol |  CVD 24h   | Buy Vol 24h| Sell Vol 24| Lg Buys    | Lg Sells  |
+--------+------------+------------+------------+------------+-----------+
|  BTC   | 🔴-$21.7M  |  $21.5M    |  $43.2M    |    1340    |    2189   |
|  ETH   | 🔴-$9.0M   |  $12.3M    |  $21.3M    |     890    |    1456   |
|  DOT   | 🟢+$979.1K |  $2.1M     |  $1.1M     |     234    |     189   |
+--------+------------+------------+------------+------------+-----------+
```

### Step 3: Run Daily Report
The order book data will now be automatically included when you run:
```powershell
python function_app.py
```

Or locally:
```powershell
.\run-local.ps1
```

## What the Metrics Mean

### Bid/Ask Ratio
- **Definition**: Total bid volume divided by total ask volume
- **> 1.2** 🟢: Strong buy pressure (more buyers than sellers)
- **< 0.8** 🔴: Strong sell pressure (more sellers than buyers)
- **0.8 - 1.2** ⚪: Balanced/neutral market

### Spread Percentage
- **Definition**: Price difference between best bid and best ask as a percentage
- **Tight Spread** (< 0.05%): High liquidity, efficient market
- **Wide Spread** (> 0.1%): Lower liquidity, higher trading cost

### Total Bid/Ask Volume
- **Definition**: Aggregate volume across all price levels in the order book
- **High Volume**: Deep liquidity, can absorb large orders
- **Imbalanced**: Direction of imbalance may predict short-term price movement

### Largest Walls
- **Bid Wall**: Largest single buy order in the order book
- **Ask Wall**: Largest single sell order in the order book
- **Significance**: Large walls can act as support/resistance levels
- **Threshold**: Walls > $100,000 are considered significant

### Cumulative Volume Delta (CVD)
- **Definition**: Net volume = Buy Volume - Sell Volume (taker perspective)
- **> 0** 🟢: More aggressive buying than selling
- **< 0** 🔴: More aggressive selling than buying
- **Interpretation**: Shows true order flow pressure, not just price movement

### CVD Signals
- **Rising CVD + Rising Price**: Strong trend confirmation (buying driving price up)
- **Rising CVD + Falling Price**: Potential reversal (accumulation phase)
- **Falling CVD + Rising Price**: Potential reversal (distribution phase)
- **Falling CVD + Falling Price**: Strong downtrend confirmation

### Large Trade Imbalance
- **Definition**: Counts of trades > 2× average trade size
- **More Large Buys**: Institutional accumulation likely
- **More Large Sells**: Institutional distribution likely
- **Real example**: BTC with 2189 large sells vs 1340 large buys = bearish whale activity

### Combined Analysis
The AI analysis receives all metrics to identify:
- **Liquidity imbalances**: Strong bid/ask ratio indicates directional pressure
- **Support/Resistance**: Large walls suggest price levels where significant orders exist
- **Market depth**: Volume analysis helps assess slippage risk for large trades
- **Short-term momentum**: Order book imbalance often precedes price moves
- **Order flow confirmation**: CVD confirms or diverges from price movement
- **Institutional activity**: Large trade counts reveal whale behavior

## Database Schema

### OrderBookMetrics Table
```sql
CREATE TABLE OrderBookMetrics (
    Id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    SymbolID            INTEGER NOT NULL,
    BestBid             REAL,                   -- Best bid price
    BestBidQty          REAL,                   -- Quantity at best bid
    BestAsk             REAL,                   -- Best ask price
    BestAskQty          REAL,                   -- Quantity at best ask
    SpreadPct           REAL,                   -- (ask - bid) / mid * 100
    BidVolume2Pct       REAL,                   -- Bid volume within 2% of mid
    AskVolume2Pct       REAL,                   -- Ask volume within 2% of mid
    BidAskRatio         REAL,                   -- bid_volume / ask_volume
    LargestBidWall      REAL,                   -- Largest single bid order
    LargestBidWallPrice REAL,                   -- Price level of largest bid
    LargestAskWall      REAL,                   -- Largest single ask order
    LargestAskWallPrice REAL,                   -- Price level of largest ask
    IndicatorDate       TEXT NOT NULL,
    CreatedAt           TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (SymbolID) REFERENCES Symbols(SymbolID),
    UNIQUE(SymbolID, IndicatorDate)
);

CREATE INDEX idx_orderbook_symbol_date ON OrderBookMetrics(SymbolID, IndicatorDate);
```

### CumulativeVolumeDelta Table
```sql
CREATE TABLE CumulativeVolumeDelta (
    Id              INTEGER PRIMARY KEY AUTOINCREMENT,
    SymbolID        INTEGER NOT NULL,
    CVD1h           REAL,                   -- Cumulative Volume Delta for 1 hour
    CVD4h           REAL,                   -- Cumulative Volume Delta for 4 hours
    CVD24h          REAL,                   -- Cumulative Volume Delta for 24 hours
    BuyVolume1h     REAL,                   -- Taker buy volume in USD (1h)
    SellVolume1h    REAL,                   -- Taker sell volume in USD (1h)
    BuyVolume24h    REAL,                   -- Taker buy volume in USD (24h)
    SellVolume24h   REAL,                   -- Taker sell volume in USD (24h)
    TradeCount1h    INTEGER,                -- Number of trades in 1h
    TradeCount24h   INTEGER,                -- Number of trades in 24h
    AvgTradeSize    REAL,                   -- Average trade size in USD
    LargeBuyCount   INTEGER,                -- Trades > 2x average that were buys
    LargeSellCount  INTEGER,                -- Trades > 2x average that were sells
    IndicatorDate   TEXT NOT NULL,
    CreatedAt       TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (SymbolID) REFERENCES Symbols(SymbolID),
    UNIQUE(SymbolID, IndicatorDate)
);

CREATE INDEX idx_cvd_symbol_date ON CumulativeVolumeDelta(SymbolID, IndicatorDate);
```

## Files Created/Modified

### New Files
- `database/migrations/add_order_book_tables.py` - Order book database migration
- `database/migrations/add_cvd_tables.py` - CVD database migration
- `technical_analysis/order_book_report.py` - Report generation and AI context
- `technical_analysis/repositories/order_book_repository.py` - Order book data access layer
- `technical_analysis/repositories/cvd_repository.py` - CVD data access layer
- `features/ORDER_BOOK_README.md` - This file

### Modified Files
- `shared_code/binance.py` - Added `OrderBookMetrics`, `CVDMetrics` dataclasses, `fetch_binance_order_book()`, `fetch_binance_futures_order_book()`, and `fetch_binance_cvd()`
- `database/init_sqlite.py` - Added OrderBookMetrics and CumulativeVolumeDelta table schemas
- `reports/daily_report.py` - Added order book + CVD report generation and Telegram sending
- `technical_analysis/repositories/aggregated_repository.py` - Added BidAskRatio, SpreadPct to aggregated view

## API Endpoints Used

### Binance Spot API
- **Order Book**: `GET /api/v3/depth?symbol={symbol}&limit=100`
- **Weight**: 5 per request
- **Public**: No API key required

- **Aggregate Trades (CVD)**: `GET /api/v3/aggTrades?symbol={symbol}&limit=1000`
- **Weight**: 2 per request
- **Public**: No API key required
- **Note**: Maximum 1000 trades per request, paginated for 24h lookback

### Binance Futures API
- **Order Book**: `GET /fapi/v1/depth?symbol={symbol}&limit=100`
- **Weight**: 10 per request
- **Public**: No API key required

### Order Book Response Structure
```json
{
  "lastUpdateId": 1027024,
  "bids": [
    ["50000.00", "2.5"],    // [price, quantity]
    ["49999.00", "1.2"],
    ...
  ],
  "asks": [
    ["50001.00", "1.8"],
    ["50002.00", "0.9"],
    ...
  ]
}
```

### Aggregate Trades Response Structure
```json
[
  {
    "a": 26129,         // Aggregate trade ID
    "p": "50000.00",    // Price
    "q": "0.01000000",  // Quantity
    "f": 100,           // First trade ID
    "l": 105,           // Last trade ID
    "T": 1499865549590, // Timestamp
    "m": true,          // isBuyerMaker (true=seller was taker, false=buyer was taker)
    "M": true           // Best match
  }
]
```

**CVD Calculation**: 
- If `isBuyerMaker = false` → Taker was a buyer → Add to buy volume
- If `isBuyerMaker = true` → Taker was a seller → Add to sell volume
- CVD = Buy Volume - Sell Volume

## Constants and Thresholds

```python
# Volume formatting thresholds
VOLUME_BILLION = 1_000_000_000
VOLUME_MILLION = 1_000_000
VOLUME_THOUSAND = 1_000

# Bid/Ask ratio indicators
RATIO_BUY_PRESSURE = 1.2    # Above this = 🟢 (buy pressure)
RATIO_SELL_PRESSURE = 0.8   # Below this = 🔴 (sell pressure)
# Between 0.8-1.2 = ⚪ (neutral)

# CVD indicators
CVD_STRONG_THRESHOLD = 10   # % imbalance for strong signal
CVD_MODERATE_THRESHOLD = 5  # % imbalance for moderate signal

# Wall significance threshold
MIN_SIGNIFICANT_WALL = 100_000  # $100K USD equivalent

# Large trade detection
LARGE_TRADE_MULTIPLIER = 2.0  # Trades > 2x average size
```

## Troubleshooting

### "No order book data available"
- **Cause**: Symbol may not exist on Binance or API rate limit reached
- **Solution**: Verify symbol exists, check API rate limits

### "Order book empty or insufficient levels"
- **Cause**: Market has very low liquidity
- **Solution**: This is expected for low-volume tokens

### "CVD data limited - may not cover full 24h"
- **Cause**: Binance aggTrades API returns max 1000 trades per request
- **Note**: For high-volume coins like BTC (>50k trades/day), we hit the API limit
- **Solution**: This is logged as a warning but data is still useful for relative comparison

### Migration fails
- **SQLite**: Check file permissions on `local_crypto.db`
- **Azure SQL**: Verify connection string and database permissions

### Data not appearing in aggregated view
- Run the migrations first, then regenerate the data
- Check that `OrderBookMetrics` and `CumulativeVolumeDelta` tables exist and have data

## Interpreting Signals

### Bullish Signals
- Bid/Ask Ratio > 1.2 with increasing trend
- Large bid walls forming at key support levels
- Tight spreads indicating healthy liquidity
- **Positive CVD (taker buying > selling)**
- **More large buys than large sells**
- **Rising CVD with rising price (trend confirmation)**

### Bearish Signals
- Bid/Ask Ratio < 0.8 with decreasing trend
- Large ask walls forming at key resistance levels
- Widening spreads suggesting liquidity withdrawal
- **Negative CVD (taker selling > buying)**
- **More large sells than large buys**
- **Falling CVD with falling price (trend confirmation)**

### Divergence Signals (Watch Carefully)
- **Rising CVD + Falling Price**: Accumulation (bullish reversal potential)
- **Falling CVD + Rising Price**: Distribution (bearish reversal potential)
- **High bid/ask ratio but negative CVD**: Order book may be misleading

### Caution Signals
- Extremely high bid/ask ratios (> 2.0) may indicate manipulation
- Very large walls may be "spoofing" (fake orders)
- Sudden liquidity drops may precede volatility
- **Extreme CVD imbalance (> 80/20) may indicate exhaustion**

## Future Enhancements

Potential additions:
- **Order Book Depth Charts**: Visual heatmap of liquidity distribution
- **Historical Wall Tracking**: Monitor how walls form and dissolve over time
- **Liquidity Score**: Composite metric combining spread, depth, and imbalance
- **Cross-Exchange Analysis**: Compare order books across Binance, Coinbase, etc.
- **Real-time Alerts**: Notify on significant liquidity changes
- **Liquidation Heatmaps**: Track where forced liquidations cluster
- **Long/Short Ratio**: Futures positioning data from Binance Futures
- **Funding Rate Integration**: Combine with CVD for complete derivatives view
- **WebSocket Real-time Updates**: Live order book and trade stream monitoring

## References

- [Binance Spot API - Order Book](https://binance-docs.github.io/apidocs/spot/en/#order-book)
- [Binance Spot API - Aggregate Trades](https://binance-docs.github.io/apidocs/spot/en/#compressed-aggregate-trades-list)
- [Binance Futures API - Order Book](https://binance-docs.github.io/apidocs/futures/en/#order-book)
- [Understanding Order Book Dynamics](https://www.binance.com/en/blog/all/understanding-crypto-order-books-421499824684903893)
- [Cumulative Volume Delta Explained](https://www.tradingview.com/scripts/cumulativedelta/)
