---
goal: Add Live Order Book Data (Bid/Ask Depth & Liquidity Analysis) + Cumulative Volume Delta to Daily Crypto Report
version: 2.0
date_created: 2025-12-06
last_updated: 2025-01-19
owner: graniluk
status: COMPLETED
tags: feature, order-book, liquidity, cvd, derivatives, binance, market-depth, order-flow
---

# Introduction

![Status: COMPLETED](https://img.shields.io/badge/status-COMPLETED-green)

This plan implements live order book data integration AND Cumulative Volume Delta (CVD) to enhance the daily crypto report with bid/ask depth analysis, liquidity metrics, and real-time order flow tracking. The feature fetches order book snapshots and aggregate trades from Binance, calculates key liquidity and order flow indicators, stores them in the database for historical tracking, and includes them in both Telegram reports and AI analysis context.

**Key Value Proposition:**
- Identify support/resistance levels via bid/ask clustering
- Detect liquidity imbalances (buy vs sell pressure)
- Measure market depth for volatility risk assessment
- **Track real-time order flow with CVD (taker buy vs sell volume)**
- **Identify institutional activity via large trade analysis**
- Provide institutional-grade liquidity metrics to AI analysis

## 1. Requirements & Constraints

### Functional Requirements
- **REQ-001**: Fetch order book depth (bid/ask prices and quantities) from Binance Spot API (`GET /api/v3/depth`)
- **REQ-002**: Fetch order book depth from Binance Futures API for perpetual contracts
- **REQ-003**: Calculate aggregated liquidity metrics: total bid volume, total ask volume, bid/ask ratio
- **REQ-004**: Identify liquidity walls (large orders > 2x average) within ±2% of current price
- **REQ-005**: Calculate market depth at multiple price levels: ±0.5%, ±1%, ±2% from mid-price
- **REQ-006**: Store order book snapshots and metrics in database for historical analysis
- **REQ-007**: Generate formatted order book report table for Telegram delivery
- **REQ-008**: Include order book metrics in AI analysis context for enhanced insights
- **REQ-009**: Support both Binance spot and KuCoin symbols (where applicable)

### Non-Functional Requirements
- **SEC-001**: Use only public API endpoints (no API key required for order book data)
- **PER-001**: Limit API weight consumption to prevent rate limiting (depth limit=100 = weight 5)
- **PER-002**: Fetch order book data only once per report generation cycle

### Constraints
- **CON-001**: Order book data is point-in-time snapshot; no historical depth available from API
- **CON-002**: Binance API weight limits: 5 per symbol at limit=100, 25 at limit=500
- **CON-003**: KuCoin order book API may have different structure/limits
- **CON-004**: Must integrate without breaking existing daily report flow

### Guidelines
- **GUD-001**: Follow existing repository pattern (see `OpenInterestRepository`, `FundingRateRepository`)
- **GUD-002**: Use `PrettyTable` for Telegram report formatting (consistent with other reports)
- **GUD-003**: Use existing `BinanceClient` from `shared_code/binance.py` for API calls
- **PAT-001**: Follow existing data class pattern (see `FuturesMetrics` class in `binance.py`)

## 2. Implementation Steps

### Implementation Phase 1: Data Model & API Integration

- GOAL-001: Create data structures and API functions to fetch and represent order book data

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Create `OrderBookMetrics` dataclass in `shared_code/binance.py` with fields: symbol, best_bid, best_bid_qty, best_ask, best_ask_qty, bid_volume_2pct, ask_volume_2pct, bid_ask_ratio, spread_pct, largest_bid_wall, largest_ask_wall, timestamp | ✅ | 2025-01-19 |
| TASK-002 | Implement `fetch_binance_order_book(symbol: Symbol, limit: int = 100) -> OrderBookMetrics` in `shared_code/binance.py` using `client.get_order_book()` | ✅ | 2025-01-19 |
| TASK-003 | Implement `fetch_binance_futures_order_book(symbol: Symbol, limit: int = 100) -> OrderBookMetrics` for futures depth data using `client.futures_order_book()` | ✅ | 2025-01-19 |
| TASK-004 | Create `OrderBookSnapshot` dataclass for raw bid/ask storage with fields: symbol_id, bids (list), asks (list), timestamp, mid_price | Skipped | - |
| TASK-005 | Implement `calculate_liquidity_metrics(bids: list, asks: list, current_price: float) -> dict` to compute depth at ±0.5%, ±1%, ±2% levels | ✅ | 2025-01-19 |
| TASK-CVD-001 | Create `CVDMetrics` dataclass in `shared_code/binance.py` with CVD and volume fields | ✅ | 2025-01-19 |
| TASK-CVD-002 | Implement `fetch_binance_cvd(symbol: Symbol) -> CVDMetrics` using aggregate trades API | ✅ | 2025-01-19 |

### Implementation Phase 2: Database Schema & Repository

- GOAL-002: Design database tables and repository layer for order book data persistence

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-006 | Create `OrderBookMetrics` table schema in `database/init_sqlite.py` with columns: Id, SymbolID, BestBid, BestBidQty, BestAsk, BestAskQty, BidVolume2Pct, AskVolume2Pct, BidAskRatio, SpreadPct, LargestBidWall, LargestBidWallPrice, LargestAskWall, LargestAskWallPrice, IndicatorDate, CreatedAt | ✅ | 2025-01-19 |
| TASK-007 | Create database migration script `database/migrations/add_order_book_tables.py` for existing databases | ✅ | 2025-01-19 |
| TASK-008 | Create `technical_analysis/repositories/order_book_repository.py` with `OrderBookRepository` class | ✅ | 2025-01-19 |
| TASK-009 | Implement `save_order_book_metrics(symbol_id, metrics, indicator_date)` method in repository | ✅ | 2025-01-19 |
| TASK-010 | Implement `get_latest_order_book_metrics(symbol_id) -> dict` method in repository | ✅ | 2025-01-19 |
| TASK-011 | Implement `get_order_book_history(symbol_id, days: int) -> list` for historical tracking | ✅ | 2025-01-19 |
| TASK-CVD-003 | Create `CumulativeVolumeDelta` table schema in `database/init_sqlite.py` | ✅ | 2025-01-19 |
| TASK-CVD-004 | Create database migration script `database/migrations/add_cvd_tables.py` | ✅ | 2025-01-19 |
| TASK-CVD-005 | Create `technical_analysis/repositories/cvd_repository.py` with CVD repository class | ✅ | 2025-01-19 |

### Implementation Phase 3: Report Generation

- GOAL-003: Create order book report for Telegram and integrate with daily report flow

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-012 | Create `technical_analysis/order_book_report.py` module | ✅ | 2025-01-19 |
| TASK-013 | Implement `fetch_order_book_report(symbols: list[Symbol], conn) -> PrettyTable` function | ✅ | 2025-01-19 |
| TASK-014 | Format report columns: Symbol, Best Bid, Best Ask, Spread%, Bid Vol (2%), Ask Vol (2%), B/A Ratio, Bid Wall, Ask Wall | ✅ | 2025-01-19 |
| TASK-015 | Add color/emoji indicators for bid/ask imbalance: 🟢 (bid heavy > 1.2), 🔴 (ask heavy < 0.8), ⚪ (neutral) | ✅ | 2025-01-19 |
| TASK-016 | Integrate `fetch_order_book_report()` call in `reports/daily_report.py` after derivatives report | ✅ | 2025-01-19 |
| TASK-017 | Send order book report message via `send_telegram_message()` in `process_daily_report()` | ✅ | 2025-01-19 |
| TASK-CVD-006 | Implement `fetch_cvd_report(symbols: list[Symbol], conn) -> PrettyTable` function | ✅ | 2025-01-19 |
| TASK-CVD-007 | Add CVD report to daily Telegram messages | ✅ | 2025-01-19 |

### Implementation Phase 4: AI Analysis Integration

- GOAL-004: Include order book data in AI analysis context for enhanced insights

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-018 | Create `_build_order_book_section(conn) -> str` function in `reports/daily_report.py` | ✅ | 2025-01-19 |
| TASK-019 | Format order book data as text summary for AI context: bid/ask ratios, significant walls, spread analysis | ✅ | 2025-01-19 |
| TASK-020 | Add order book section to `_build_analysis_context()` after ETF flows section | ✅ | 2025-01-19 |
| TASK-021 | Update AI prompt guidance in `news/prompts.py` to interpret order book data (support/resistance, liquidity) | Deferred | - |
| TASK-022 | Add interpretation guidance: "Bid/Ask Ratio > 1.2 = buying pressure, < 0.8 = selling pressure, Liquidity walls indicate potential support/resistance" | ✅ | 2025-01-19 |
| TASK-CVD-008 | Create `build_cvd_ai_context(cvd_data) -> str` function | ✅ | 2025-01-19 |
| TASK-CVD-009 | Include CVD in AI analysis context | ✅ | 2025-01-19 |

### Implementation Phase 5: Aggregated Data Integration

- GOAL-005: Include order book metrics in aggregated data view for comprehensive analysis

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-023 | Update `technical_analysis/repositories/aggregated_repository.py` to include order book fields | ✅ | 2025-01-19 |
| TASK-024 | Add columns to aggregated view: BidAskRatio, SpreadPct, BidVolume2Pct, AskVolume2Pct | ✅ | 2025-01-19 |
| TASK-025 | Update `get_aggregated_data()` SQL query to LEFT JOIN OrderBookMetrics table | ✅ | 2025-01-19 |
| TASK-026 | Update `format_aggregated()` function in `daily_report.py` to display new columns | Deferred | - |

### Implementation Phase 6: Testing & Documentation

- GOAL-006: Ensure reliability and document the new feature

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-027 | Create `tests/technical_analysis/test_order_book_report.py` with unit tests | Deferred | - |
| TASK-028 | Test `fetch_binance_order_book()` with mock API responses | Deferred | - |
| TASK-029 | Test `calculate_liquidity_metrics()` with sample bid/ask data | Deferred | - |
| TASK-030 | Test repository save/retrieve operations | Deferred | - |
| TASK-031 | Create `features/ORDER_BOOK_README.md` documentation (similar to DERIVATIVES_README.md) | ✅ | 2025-01-19 |
| TASK-032 | Update `readme.md` to mention order book feature in report sections | Deferred | - |

## 5. Summary

### Completed Features
✅ **Order Book Liquidity Snapshot** - Static bid/ask depth with ratio, spread, walls
✅ **Cumulative Volume Delta (CVD)** - Dynamic order flow with 1h/4h/24h timeframes
✅ **Large Trade Analysis** - Institutional activity detection (trades > 2x average)
✅ **Database Persistence** - Both OrderBookMetrics and CumulativeVolumeDelta tables
✅ **Telegram Reports** - Formatted tables with emoji indicators
✅ **AI Context Integration** - Both order book and CVD data fed to AI analysis

### Key Files Created
- `shared_code/binance.py` - OrderBookMetrics, CVDMetrics dataclasses and fetch functions
- `technical_analysis/order_book_report.py` - Combined report generation
- `technical_analysis/repositories/order_book_repository.py` - Order book DB operations
- `technical_analysis/repositories/cvd_repository.py` - CVD DB operations
- `database/migrations/add_order_book_tables.py` - Order book migration
- `database/migrations/add_cvd_tables.py` - CVD migration
- `features/ORDER_BOOK_README.md` - Comprehensive documentation

## 3. Alternatives

- **ALT-001**: Use WebSocket for real-time order book updates instead of REST snapshots - rejected due to complexity and unnecessary for daily reports
- **ALT-002**: Store full order book depth (all levels) instead of aggregated metrics - rejected due to storage overhead and limited analytical value for daily analysis
- **ALT-003**: Use third-party liquidity aggregators (e.g., Kaiko, CryptoCompare) - rejected due to API costs and added dependency
- **ALT-004**: Calculate Volume-Weighted Average Price (VWAP) from order book - considered for future enhancement, not required for MVP
- **ALT-005**: Implement order book heatmap visualization - rejected for MVP, could be future enhancement for web dashboard

## 4. Dependencies

### External Dependencies
- **DEP-001**: `python-binance` library (already installed) - provides `get_order_book()` and `futures_order_book()` methods
- **DEP-002**: Binance Spot API `/api/v3/depth` endpoint (public, no API key required)
- **DEP-003**: Binance Futures API `/fapi/v1/depth` endpoint (public, no API key required)

### Internal Dependencies
- **DEP-004**: `shared_code/binance.py` - existing Binance client wrapper
- **DEP-005**: `source_repository.py` - Symbol dataclass and `fetch_symbols()`
- **DEP-006**: `infra/sql_connection.py` - database connection management
- **DEP-007**: `infra/telegram_logging_handler.py` - logging infrastructure
- **DEP-008**: `prettytable` library - report table formatting
- **DEP-009**: Existing derivatives report pattern (`technical_analysis/derivatives_report.py`)

## 5. Files

### New Files
- **FILE-001**: `shared_code/order_book.py` - OrderBookMetrics dataclass and API functions (alternative: add to binance.py)
- **FILE-002**: `technical_analysis/repositories/order_book_repository.py` - Database repository
- **FILE-003**: `technical_analysis/order_book_report.py` - Report generation
- **FILE-004**: `database/migrations/add_order_book_tables.py` - Database migration
- **FILE-005**: `features/ORDER_BOOK_README.md` - Feature documentation
- **FILE-006**: `tests/technical_analysis/test_order_book_report.py` - Unit tests

### Modified Files
- **FILE-007**: `shared_code/binance.py` - Add OrderBookMetrics class and fetch functions
- **FILE-008**: `database/init_sqlite.py` - Add OrderBookMetrics table schema
- **FILE-009**: `reports/daily_report.py` - Integrate order book report and AI context
- **FILE-010**: `technical_analysis/repositories/aggregated_repository.py` - Include order book in aggregated view
- **FILE-011**: `news/prompts.py` - Add order book interpretation guidance for AI
- **FILE-012**: `readme.md` - Document new feature

## 6. Testing

### Unit Tests
- **TEST-001**: Test `OrderBookMetrics` dataclass initialization and validation
- **TEST-002**: Test `fetch_binance_order_book()` with mocked API response (spot)
- **TEST-003**: Test `fetch_binance_futures_order_book()` with mocked API response (futures)
- **TEST-004**: Test `calculate_liquidity_metrics()` with various bid/ask distributions
- **TEST-005**: Test liquidity wall detection algorithm (orders > 2x average)

### Repository Tests
- **TEST-006**: Test `OrderBookRepository.save_order_book_metrics()` - SQLite
- **TEST-007**: Test `OrderBookRepository.get_latest_order_book_metrics()` - SQLite
- **TEST-008**: Test repository upsert behavior (UPDATE on duplicate date)

### Integration Tests
- **TEST-009**: Test `fetch_order_book_report()` end-to-end with real symbols
- **TEST-010**: Test order book data appears correctly in aggregated view
- **TEST-011**: Test AI analysis context includes order book section

### Manual Testing
- **TEST-012**: Run full daily report and verify order book table in Telegram
- **TEST-013**: Verify AI analysis references order book data in insights

## 7. Risks & Assumptions

### Risks
- **RISK-001**: Order book data is highly volatile; snapshot timing may not represent average conditions - Mitigation: document this limitation, consider multiple snapshots
- **RISK-002**: API rate limits during high volatility periods - Mitigation: use limit=100 (weight 5) instead of limit=500 (weight 25)
- **RISK-003**: Futures order book may not be available for all symbols - Mitigation: graceful fallback to spot order book only
- **RISK-004**: Large bid/ask walls may be spoofed (fake liquidity) - Mitigation: document limitation in AI prompt context
- **RISK-005**: KuCoin API structure differs from Binance - Mitigation: implement KuCoin support in separate phase if needed

### Assumptions
- **ASSUMPTION-001**: Binance API will remain available and maintain current response structure
- **ASSUMPTION-002**: Order book depth at ±2% provides sufficient liquidity insight for daily analysis
- **ASSUMPTION-003**: Bid/ask ratio is meaningful indicator of short-term market sentiment
- **ASSUMPTION-004**: Users prefer aggregated metrics over raw order book visualization
- **ASSUMPTION-005**: SQLite/Azure SQL can handle additional table without performance impact

## 8. Related Specifications / Further Reading

### API Documentation
- [Binance Spot Order Book API](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints#order-book)
- [Binance Futures Order Book API](https://binance-docs.github.io/apidocs/futures/en/#order-book)
- [python-binance Market Data](https://python-binance.readthedocs.io/en/latest/market_data.html#get-market-depth)

### Internal References
- `features/DERIVATIVES_README.md` - Similar feature pattern for Open Interest/Funding Rate
- `technical_analysis/derivatives_report.py` - Reference implementation for API data + report
- `technical_analysis/repositories/open_interest_repository.py` - Repository pattern reference
- `plan/feature-price-checker-batch-refactor.md` - Batch API optimization patterns

### External Resources
- [Understanding Order Book Depth](https://www.investopedia.com/terms/d/depth-of-market.asp)
- [Liquidity Analysis in Crypto Markets](https://research.kaiko.com/articles/understanding-crypto-market-liquidity)

---

## Appendix A: Sample OrderBookMetrics Data Structure

```python
@dataclass
class OrderBookMetrics:
    """Data class for order book liquidity metrics."""
    symbol: str
    best_bid: float           # Highest bid price
    best_bid_qty: float       # Quantity at best bid
    best_ask: float           # Lowest ask price
    best_ask_qty: float       # Quantity at best ask
    spread_pct: float         # (best_ask - best_bid) / mid_price * 100
    bid_volume_2pct: float    # Total bid volume within 2% of mid-price (USD)
    ask_volume_2pct: float    # Total ask volume within 2% of mid-price (USD)
    bid_ask_ratio: float      # bid_volume_2pct / ask_volume_2pct
    largest_bid_wall: float   # Largest single bid order (USD) within 2%
    largest_bid_wall_price: float
    largest_ask_wall: float   # Largest single ask order (USD) within 2%
    largest_ask_wall_price: float
    depth_05pct: dict         # {"bid": float, "ask": float} at ±0.5%
    depth_1pct: dict          # {"bid": float, "ask": float} at ±1%
    depth_2pct: dict          # {"bid": float, "ask": float} at ±2%
    timestamp: datetime
```

## Appendix B: Sample Report Table Format

```
Order Book Liquidity Report:
+--------+----------+----------+--------+------------+------------+--------+----------+----------+
| Symbol | Best Bid | Best Ask | Spread | Bid Vol 2% | Ask Vol 2% | B/A    | Bid Wall | Ask Wall |
+--------+----------+----------+--------+------------+------------+--------+----------+----------+
| BTC    | 98,450.0 | 98,455.0 | 0.005% | $45.2M     | $38.1M     | 1.19 🟢| $2.1M    | $1.8M    |
| ETH    | 3,890.50 | 3,891.20 | 0.018% | $12.8M     | $15.2M     | 0.84 🔴| $850K    | $1.2M    |
| SOL    | 225.30   | 225.45   | 0.067% | $3.2M      | $3.5M      | 0.91 ⚪| $320K    | $280K    |
+--------+----------+----------+--------+------------+------------+--------+----------+----------+
```

## Appendix C: AI Analysis Context Sample

```
Order Book Liquidity Analysis:
BTC: Bid/Ask Ratio 1.19 (buy pressure), spread 0.005%, significant bid wall at $98,200 ($2.1M)
ETH: Bid/Ask Ratio 0.84 (sell pressure), spread 0.018%, significant ask wall at $3,920 ($1.2M)
SOL: Bid/Ask Ratio 0.91 (neutral), spread 0.067%

Interpretation:
- Bid/Ask Ratio > 1.2 = Strong buying pressure (bullish short-term)
- Bid/Ask Ratio < 0.8 = Strong selling pressure (bearish short-term)
- Liquidity walls indicate potential support (bid) or resistance (ask) levels
- Wider spreads indicate lower liquidity and higher volatility risk
```
