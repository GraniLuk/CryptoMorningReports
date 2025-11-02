---
goal: Centralized Batch Candle Fetching with Source-Aware Optimization
version: 1.0
date_created: 2025-11-02
last_updated: 2025-11-02
owner: Development Team
status: 'Planned'
tags: ['feature', 'refactoring', 'price-checker', 'performance', 'api-optimization']
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

This implementation plan outlines the refactoring of the candle fetching mechanism to centralize all logic in `price_checker.py`, implement source-aware batch fetching, and ensure consistent behavior across daily and current reports. The current system has scattered batch fetching logic with source-specific code in multiple files, leading to inconsistency and inefficiency.

The goal is to:
1. Centralize all candle fetching logic in `price_checker.py` as the single source of truth
2. Implement intelligent batch fetching that respects `symbol.source_id` from the database
3. Use batch API calls for BINANCE (efficient), fall back to individual calls for KUCOIN
4. Ensure consistent behavior between `daily_report.py` and `current_report.py`
5. Simplify `update_latest_data.py` by removing source-specific logic
6. Maintain backward compatibility with existing functions
7. Optionally add KuCoin batch functions if the API supports it

## 1. Requirements & Constraints

### Functional Requirements

- **REQ-001**: All candle fetching (individual and batch) must go through `price_checker.py`
- **REQ-002**: Batch functions must check database first and only fetch missing candles
- **REQ-003**: Source detection must use `symbol.source_id` property from the Symbol dataclass
- **REQ-004**: BINANCE symbols must use batch API calls (fetch up to 1000 candles in one request)
- **REQ-005**: KUCOIN symbols must fall back to individual API calls (no batch support currently)
- **REQ-006**: All fetched candles must be saved to database automatically
- **REQ-007**: Both `daily_report.py` and `current_report.py` must use update functions before analysis
- **REQ-008**: `update_latest_data.py` must delegate to `price_checker.py` batch functions
- **REQ-009**: Existing `fetch_*_candles()` functions must remain functional (backward compatibility)
- **REQ-010**: Support for daily, hourly, and 15-minute candle timeframes

### Technical Requirements

- **TEC-001**: Create `fetch_daily_candles_batch()` function in `price_checker.py`
- **TEC-002**: Create `fetch_hourly_candles_batch()` function in `price_checker.py`
- **TEC-003**: Create `fetch_fifteen_min_candles_batch()` function in `price_checker.py`
- **TEC-004**: Create `fetch_binance_daily_klines_batch()` function in `binance.py`
- **TEC-005**: Refactor existing `fetch_*_candles()` to use batch functions internally
- **TEC-006**: Update `update_latest_data.py` to use `price_checker` batch functions
- **TEC-007**: Update `current_report.py` to call update functions before analysis

### Performance Requirements

- **PER-001**: Reduce API calls by using batch fetching (1 call for 500 candles vs 500 individual calls)
- **PER-002**: Minimize database queries by checking for missing candles before fetching
- **PER-003**: Avoid rate limiting issues by consolidating API requests
- **PER-004**: Enable concurrent symbol processing where beneficial
- **PER-005**: Commit database transactions after all symbols are updated

### Constraints

- **CON-001**: Must maintain backward compatibility with existing code
- **CON-002**: BINANCE API limit: 1000 candles per request
- **CON-003**: KUCOIN currently has no batch API (individual calls only)
- **CON-004**: Database connection must be passed to all batch functions
- **CON-005**: Must handle timezone-aware datetime objects consistently (UTC)

### Guidelines

- **GUD-001**: Follow existing code style using ruff and pyright
- **GUD-002**: Use existing logging infrastructure (`app_logger`)
- **GUD-003**: Write unit tests for new batch functions
- **GUD-004**: Maintain separation of concerns (fetching vs saving vs analysis)
- **GUD-005**: Document all new functions with comprehensive docstrings

### Patterns to Follow

- **PAT-001**: Check database first, fetch missing data only
- **PAT-002**: Dispatch to source-specific functions based on `symbol.source_id`
- **PAT-003**: Use timezone-aware datetime objects (UTC) consistently
- **PAT-004**: Save candles to database immediately after fetching
- **PAT-005**: Return sorted lists of Candle objects
- **PAT-006**: Use type hints for all function signatures

## 2. Implementation Steps

### Phase 1: Create Binance Daily Batch Function

**GOAL-001**: Implement missing batch function for Binance daily candles

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Create `fetch_binance_daily_klines_batch()` in `binance.py` | ✅ | 2025-11-02 |
| TASK-002 | Implement date range validation and timezone handling | ✅ | 2025-11-02 |
| TASK-003 | Add support for fetching up to 1000 daily candles in one API call | ✅ | 2025-11-02 |
| TASK-004 | Convert Binance API response to list of Candle objects | ✅ | 2025-11-02 |
| TASK-005 | Add comprehensive error handling and logging | ✅ | 2025-11-02 |
| TASK-006 | Test with various date ranges (7 days, 30 days, 180 days) | ✅ | 2025-11-02 |
| TASK-007 | Verify API response format matches hourly/15-min batch functions | ✅ | 2025-11-02 |

**Phase 1 Status**: ✅ **COMPLETED** (7/7 tasks completed)  
**Summary**: Successfully implemented `fetch_binance_daily_klines_batch()` function with full timezone support, error handling, and API limit enforcement (1000 candles max). All tests passed for various date ranges (7, 30, 180, 1000 days).

### Phase 2: Refactor Existing price_checker.py Functions for Batch Fetching

**GOAL-002**: Modify existing functions to use intelligent batch fetching internally

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-008 | Refactor `fetch_daily_candles()` to use batch fetching | ✅ | 2025-11-02 |
| TASK-009 | Implement database check for existing daily candles in range | ✅ | 2025-11-02 |
| TASK-010 | Generate list of expected dates between start_date and end_date | ✅ | 2025-11-02 |
| TASK-011 | Identify missing dates by comparing DB results with expected dates | ✅ | 2025-11-02 |
| TASK-012 | Add source detection: dispatch to BINANCE batch or KUCOIN loop | ✅ | 2025-11-02 |
| TASK-013 | Save fetched candles to database using DailyCandleRepository | ✅ | 2025-11-02 |
| TASK-014 | Return combined list of cached + newly fetched candles (sorted) | ✅ | 2025-11-02 |
| TASK-015 | Refactor `fetch_hourly_candles()` to use batch fetching | ✅ | 2025-11-02 |
| TASK-016 | Implement hourly timestamp generation and DB checking | ✅ | 2025-11-02 |
| TASK-017 | Add source-aware dispatch for hourly candles (BINANCE batch vs KUCOIN loop) | ✅ | 2025-11-02 |
| TASK-018 | Refactor `fetch_fifteen_min_candles()` to use batch fetching | ✅ | 2025-11-02 |
| TASK-019 | Implement 15-minute timestamp generation and DB checking | ✅ | 2025-11-02 |
| TASK-020 | Add source-aware dispatch for 15-minute candles | ✅ | 2025-11-02 |
| TASK-021 | Update docstrings to document batch fetching behavior | ✅ | 2025-11-02 |
| TASK-022 | Add comprehensive logging for batch operations (count, source, duration) | ⏳ | |

**Phase 2 Status**: 🔄 **IN PROGRESS** (14/15 tasks completed - 93%)  
**Summary**: Successfully refactored all three candle fetching functions (`fetch_daily_candles()`, `fetch_hourly_candles()`, `fetch_fifteen_min_candles()`) to use intelligent batch fetching for BINANCE and individual fetching for KUCOIN. Updated all docstrings to document the new behavior. Added helper function `_parse_candle_date()` to handle timezone-aware date parsing. All functions now use the same pattern: check DB → identify missing → batch fetch (BINANCE) or individual fetch (KUCOIN) → save to DB → return sorted list. Remaining task: add comprehensive logging.

**Note**: This phase modifies existing functions rather than creating new ones. This is a breaking change approach that simplifies the API and automatically provides batch performance to all existing code.

### Phase 3: Simplify update_latest_data.py

**GOAL-003**: Remove source-specific logic and use refactored price_checker functions

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-023 | Refactor `update_latest_daily_candles()` to use modified `fetch_daily_candles()` | | |
| TASK-024 | Remove hardcoded `if symbol.source_id == SourceID.BINANCE` logic | | |
| TASK-025 | Simplify function to: check last date, call fetch_daily_candles with range | | |
| TASK-026 | Refactor `update_latest_hourly_candles()` to use modified `fetch_hourly_candles()` | | |
| TASK-027 | Remove individual fetch fallback logic (now handled in price_checker) | | |
| TASK-028 | Remove direct imports of `fetch_binance_*_klines_batch()` functions | | |
| TASK-029 | Refactor `update_latest_fifteen_min_candles()` to use modified function | | |
| TASK-030 | Update logging to reflect simplified flow | | |
| TASK-031 | Remove helper functions `_fetch_hourly_candles_individually()` etc. | | |

### Phase 4: Update current_report.py

**GOAL-004**: Ensure current_report uses update functions before analysis (Option A)

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-032 | Add imports for `update_latest_*_candles()` functions | | |
| TASK-033 | Call `update_latest_daily_candles()` before fetching daily candles | | |
| TASK-034 | Call `update_latest_hourly_candles()` before fetching hourly candles | | |
| TASK-035 | Call `update_latest_fifteen_min_candles()` before fetching 15-min candles | | |
| TASK-036 | Adjust update parameters based on analysis requirements (180 days, 48 hours, etc.) | | |
| TASK-037 | Add database commit after all updates complete | | |
| TASK-038 | Verify reports use fresh data from database | | |
| TASK-039 | Add logging to indicate data refresh step | | |

### Phase 5: Testing & Validation

**GOAL-005**: Comprehensive testing of refactored batch functionality

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-040 | Test `fetch_daily_candles()` with BINANCE symbol (batch path) | | |
| TASK-041 | Test `fetch_daily_candles()` with KUCOIN symbol (individual path) | | |
| TASK-042 | Test `fetch_hourly_candles()` with both sources | | |
| TASK-043 | Test `fetch_fifteen_min_candles()` with both sources | | |
| TASK-044 | Verify database correctly stores all fetched candles | | |
| TASK-045 | Test with empty database (first run scenario) | | |
| TASK-046 | Test with partially filled database (resume scenario) | | |
| TASK-047 | Test with fully updated database (no fetch scenario) | | |
| TASK-048 | Measure API call reduction (before vs after refactoring) | | |
| TASK-049 | Test error handling for API failures | | |
| TASK-050 | Test timezone handling across different timeframes | | |
| TASK-051 | Verify both daily_report and current_report work correctly | | |

### Phase 6: Optional - KuCoin Batch Functions

**GOAL-006**: Add batch fetching for KuCoin if API supports it (optional)

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-052 | Research KuCoin API documentation for batch kline endpoints | | |
| TASK-053 | Verify KuCoin API rate limits and batch capabilities | | |
| TASK-054 | Implement `fetch_kucoin_daily_klines_batch()` if supported | | |
| TASK-055 | Implement `fetch_kucoin_hourly_klines_batch()` if supported | | |
| TASK-056 | Implement `fetch_kucoin_fifteen_min_klines_batch()` if supported | | |
| TASK-057 | Update price_checker.py to use KuCoin batch when available | | |
| TASK-058 | Test KuCoin batch functions with various date ranges | | |
| TASK-059 | Measure performance improvement for KuCoin symbols | | |

### Phase 7: Documentation & Cleanup

**GOAL-007**: Update documentation and remove obsolete code

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-060 | Update `price_checker.py` docstrings with batch behavior | | |
| TASK-061 | Document source-aware dispatching in comments | | |
| TASK-062 | Update `readme.md` with architecture changes | | |
| TASK-063 | Document recommended usage patterns (update functions first) | | |
| TASK-064 | Remove obsolete helper functions from update_latest_data.py | | |
| TASK-065 | Clean up unused imports | | |
| TASK-066 | Add performance metrics to daily report logs | | |
| TASK-067 | Create troubleshooting guide for common issues | | |

## 3. Alternatives

### Alternative Approaches Considered

- **ALT-001**: **Keep source-specific logic in update_latest_data.py**
  - *Rejected*: Scatters candle fetching logic across multiple files. Makes it harder to add new sources. Violates single responsibility principle.

- **ALT-002**: **Create separate batch functions in technical_analysis modules**
  - *Rejected*: Creates redundancy. price_checker.py is already the canonical place for fetching logic.

- **ALT-003**: **Use existing fetch_*_candles() without refactoring**
  - *Rejected*: Current functions fetch one-by-one which is inefficient for BINANCE. Missing optimization opportunity.

- **ALT-004**: **Always fetch from API, ignore database cache**
  - *Rejected*: Wasteful of API calls. Hits rate limits. Slower performance.

- **ALT-005**: **Option B: Use batch functions directly in current_report**
  - *Considered but not chosen*: Option A (call update functions first) ensures consistency with daily_report and reuses proven update logic. More maintainable.

- **ALT-006**: **Implement generic batch interface for all sources**
  - *Deferred*: Would require significant changes to source-specific code. Can be considered after KuCoin batch research.

## 4. Dependencies

### Internal Dependencies

- **DEP-001**: `source_repository.py` - Provides `Symbol` dataclass with `source_id` property
- **DEP-002**: `shared_code/binance.py` - BINANCE-specific API functions
- **DEP-003**: `shared_code/kucoin.py` - KUCOIN-specific API functions
- **DEP-004**: `shared_code/common_price.py` - `Candle` and `TickerPrice` dataclasses
- **DEP-005**: `technical_analysis/repositories/daily_candle_repository.py` - Database operations
- **DEP-006**: `technical_analysis/repositories/hourly_candle_repository.py` - Database operations
- **DEP-007**: `technical_analysis/repositories/fifteen_min_candle_repository.py` - Database operations
- **DEP-008**: `infra/sql_connection.py` - Database connection management
- **DEP-009**: `infra/telegram_logging_handler.py` - Logging infrastructure

### External Dependencies

- **DEP-010**: `python-binance` - Binance API client (already installed)
- **DEP-011**: `python-kucoin` - KuCoin API client (already installed)
- **DEP-012**: `pyodbc` - Database connectivity (already installed)

### Configuration Dependencies

- **DEP-013**: No new environment variables needed
- **DEP-014**: Existing database configuration sufficient

## 5. Files

### Files to Create

- **None** - All changes are modifications to existing files

### Files to Modify

- **FILE-001**: `shared_code/price_checker.py` - Add batch functions, refactor existing functions
- **FILE-002**: `shared_code/binance.py` - Add `fetch_binance_daily_klines_batch()`
- **FILE-003**: `database/update_latest_data.py` - Simplify by delegating to price_checker
- **FILE-004**: `reports/current_report.py` - Add update function calls before analysis
- **FILE-005**: `shared_code/kucoin.py` - Optionally add batch functions (Phase 7)
- **FILE-006**: `readme.md` - Update architecture documentation

### Files Potentially Affected (Testing)

- **FILE-007**: `technical_analysis/daily_candle.py` - Wrapper functions may need testing
- **FILE-008**: `technical_analysis/hourly_candle.py` - Wrapper functions may need testing
- **FILE-009**: `technical_analysis/fifteen_min_candle.py` - Wrapper functions may need testing
- **FILE-010**: `reports/daily_report.py` - Should continue working without changes

## 6. Testing

### Unit Tests

- **TEST-001**: Test `fetch_binance_daily_klines_batch()` with valid date range
- **TEST-002**: Test `fetch_binance_daily_klines_batch()` with date range > 1000 days (API limit)
- **TEST-003**: Test `fetch_daily_candles_batch()` with BINANCE symbol (batch path)
- **TEST-004**: Test `fetch_daily_candles_batch()` with KUCOIN symbol (individual path)
- **TEST-005**: Test `fetch_hourly_candles_batch()` with empty database
- **TEST-006**: Test `fetch_hourly_candles_batch()` with partially filled database
- **TEST-007**: Test `fetch_fifteen_min_candles_batch()` with timestamp generation
- **TEST-008**: Test database save operations for batch-fetched candles
- **TEST-009**: Test timezone handling (UTC conversion and consistency)
- **TEST-010**: Test error handling when API returns empty results
- **TEST-011**: Test error handling when API returns malformed data

### Integration Tests

- **TEST-012**: Test full update_latest_daily_candles() flow with multiple symbols
- **TEST-013**: Test full update_latest_hourly_candles() flow with BINANCE and KUCOIN mix
- **TEST-014**: Test current_report generation after data updates
- **TEST-015**: Test daily_report continues to work correctly
- **TEST-016**: Test backward compatibility of existing fetch_*_candles() functions
- **TEST-017**: Test database commit after batch updates
- **TEST-018**: Test RSI calculation uses correct candles after batch update

### Performance Tests

- **TEST-019**: Measure API call count before refactoring (baseline)
- **TEST-020**: Measure API call count after refactoring (should be significantly reduced)
- **TEST-021**: Measure time to update 10 symbols with 180 days of data
- **TEST-022**: Measure time to update 10 symbols with 24 hours of hourly data
- **TEST-023**: Compare BINANCE batch vs KUCOIN individual performance
- **TEST-024**: Test concurrent symbol processing (if implemented)

### Manual Tests

- **TEST-025**: Run daily_report.py locally and verify correct operation
- **TEST-026**: Run current_report.py for BTC and verify articles + fresh data
- **TEST-027**: Check database after updates to verify all candles saved
- **TEST-028**: Review logs for batch operation metrics
- **TEST-029**: Test with network failure simulation
- **TEST-030**: Test with database connection failure

## 7. Risks & Assumptions

### Risks

- **RISK-001**: **API response format changes** - Binance/KuCoin may change API response structure
  - *Mitigation*: Comprehensive error handling, version pinning, monitoring

- **RISK-002**: **Rate limiting** - Batch calls may still hit rate limits with many symbols
  - *Mitigation*: Add rate limiting logic, exponential backoff, respect API limits

- **RISK-003**: **Database deadlocks** - Concurrent updates may cause locking issues
  - *Mitigation*: Sequential processing, proper transaction management, retry logic

- **RISK-004**: **Backward compatibility breaks** - Refactoring may break existing code
  - *Mitigation*: Comprehensive testing, gradual rollout, version control

- **RISK-005**: **Timezone bugs** - Incorrect timezone handling may cause missing/duplicate candles
  - *Mitigation*: Consistent UTC usage, thorough timezone testing, validation

- **RISK-006**: **Performance regression** - Batch logic complexity may slow down simple cases
  - *Mitigation*: Performance benchmarking, optimization, caching strategies

### Assumptions

- **ASSUMPTION-001**: BINANCE API supports batch fetching for all timeframes (1d, 1h, 15m)
- **ASSUMPTION-002**: Database can handle bulk insert operations efficiently
- **ASSUMPTION-003**: Network is generally reliable during update operations
- **ASSUMPTION-004**: Symbol source_id is correctly set in database for all symbols
- **ASSUMPTION-005**: Existing candle repositories (daily, hourly, 15-min) work correctly
- **ASSUMPTION-006**: Database connection is maintained throughout batch operations
- **ASSUMPTION-007**: UTC timezone handling is consistent across all modules

## 8. Architecture Overview

### Current Architecture (Before Refactoring)

```
daily_report.py
    ├─> update_latest_data.py
    │       ├─> if BINANCE: fetch_binance_hourly_klines_batch() [shared_code/binance.py]
    │       └─> else: fetch_hourly_candle() [shared_code/price_checker.py]
    └─> Reports read from database

current_report.py
    ├─> fetch_hourly_candles_for_all_symbols() [technical_analysis/hourly_candle.py]
    │       └─> fetch_hourly_candles() [shared_code/price_checker.py]
    │               └─> fetch individual candles one-by-one
    └─> No database update step
```

**Issues:**
- ❌ Source-specific logic in update_latest_data.py
- ❌ current_report fetches individually (slow)
- ❌ Batch logic scattered across files
- ❌ Inconsistent behavior between reports

### Target Architecture (After Refactoring)

```
daily_report.py
    ├─> update_latest_data.py
    │       └─> fetch_hourly_candles_batch() [shared_code/price_checker.py]
    │               ├─> if BINANCE: fetch_binance_hourly_klines_batch()
    │               └─> else: fetch_kucoin_hourly_kline() loop
    └─> Reports read from database

current_report.py
    ├─> update_latest_data.py (same as daily_report)
    │       └─> fetch_hourly_candles_batch() [shared_code/price_checker.py]
    └─> Reports read from database
```

**Benefits:**
- ✅ Single source of truth (price_checker.py)
- ✅ Source-aware dispatching centralized
- ✅ Consistent behavior across reports
- ✅ Batch optimization for all reports
- ✅ Easier to maintain and extend

## 9. Success Criteria

### Performance Metrics

- **METRIC-001**: API calls reduced by at least 90% for BINANCE symbols
- **METRIC-002**: Daily report execution time reduced by at least 30%
- **METRIC-003**: Current report data freshness guaranteed (always up-to-date)
- **METRIC-004**: Database storage efficiency maintained (no duplicate candles)

### Code Quality Metrics

- **METRIC-005**: All new functions have comprehensive docstrings
- **METRIC-006**: All new functions have type hints
- **METRIC-007**: Code coverage for price_checker.py > 80%
- **METRIC-008**: No pylint/ruff errors introduced
- **METRIC-009**: No pyright type errors introduced

### Functional Metrics

- **METRIC-010**: daily_report.py runs successfully with refactored code
- **METRIC-011**: current_report.py runs successfully with refactored code
- **METRIC-012**: All existing tests pass without modification
- **METRIC-013**: Both BINANCE and KUCOIN symbols fetch correctly
- **METRIC-014**: Database contains correct candles after batch updates

## 10. Related Specifications / Further Reading

- [Binance API Documentation - Klines/Candlestick Data](https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-data)
- [KuCoin API Documentation - Get Klines](https://docs.kucoin.com/#get-klines)
- Current project documentation: `readme.md`, `LOCAL_DEVELOPMENT.md`
- Related files: `shared_code/price_checker.py`, `database/update_latest_data.py`
- Python `datetime` and timezone handling best practices
- Database transaction management patterns
