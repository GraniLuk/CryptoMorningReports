---
goal: Implement ETF Daily Inflows/Outflows Tracking for BTC and ETH
version: 1.0
date_created: 2025-11-06
last_updated: 2025-11-06
owner: CryptoMorningReports Team
status: Planned
tags: [feature, etf, data-integration, telegram, ai-analysis]
---

# ETF Inflows/Outflows Feature Implementation Plan

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

This plan outlines the implementation of ETF (Exchange-Traded Fund) daily inflows and outflows tracking for Bitcoin and Ethereum using the DefiLlama ETF API. The feature will integrate seamlessly with the existing daily report infrastructure, providing institutional sentiment indicators through ETF flow data.

## 1. Requirements & Constraints

### Requirements

- **REQ-001**: Fetch ETF data from DefiLlama API endpoint `https://defillama.com/api/etfs`
- **REQ-002**: Track daily inflows/outflows for both BTC and ETH ETFs
- **REQ-003**: Store ETF flow data in a dedicated database table with proper schema
- **REQ-004**: Display today's inflows and 7-day aggregated values in the daily report
- **REQ-005**: Send ETF data as a formatted table in Telegram messages
- **REQ-006**: Integrate ETF flow data into Gemini AI analysis with updated prompts
- **REQ-007**: Follow existing architectural patterns (etf_report.py, etf_repository.py similar to stepn/launchpool)
- **REQ-008**: Support both SQLite (local) and Azure SQL (production) databases
- **REQ-009**: Handle API failures gracefully with proper error logging
- **REQ-010**: Include issuer-level breakdown (BlackRock, Fidelity, Grayscale, etc.)

### Security Requirements

- **SEC-001**: Validate API response data types before database insertion
- **SEC-002**: Sanitize all ETF data to prevent SQL injection (use parameterized queries)
- **SEC-003**: Handle sensitive float values (NaN, Infinity) properly before storage

### Constraints

- **CON-001**: Must maintain compatibility with existing database connection patterns (pyodbc/SQLiteConnectionWrapper)
- **CON-002**: Database schema must support both date-based and datetime-based queries
- **CON-003**: Telegram message formatting must comply with HTML parse mode limitations
- **CON-004**: API calls should be rate-limited to avoid overwhelming DefiLlama service
- **CON-005**: Maximum 30-second timeout for API requests

### Guidelines

- **GUD-001**: Use PrettyTable for consistent table formatting across reports
- **GUD-002**: Follow existing naming conventions: lowercase with underscores for functions/modules
- **GUD-003**: Log all significant operations using app_logger from telegram_logging_handler
- **GUD-004**: Include type hints for all function parameters and return values
- **GUD-005**: Write defensive code with try-except blocks for external API calls

### Patterns to Follow

- **PAT-001**: Repository pattern for database operations (see stepn_repository.py, funding_rate_repository.py)
- **PAT-002**: Report generation pattern returning formatted strings/tables (see stepn_report.py)
- **PAT-003**: Database table schema with Id, CreatedAt, and proper foreign keys (see init_sqlite.py)
- **PAT-004**: SQLite/Azure SQL compatibility checks using `os.getenv("DATABASE_TYPE")`
- **PAT-005**: Integration into daily_report.py with async send_telegram_message calls

## 2. Implementation Steps

### Phase 1: Database Infrastructure

**GOAL-001**: Create database schema and repository layer for ETF data storage

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Create ETFFlows table in `database/init_sqlite.py` with columns: Id (PK), Ticker (TEXT), Coin (TEXT), Issuer (TEXT), Price (REAL), AUM (REAL), Flows (REAL), FlowsChange (REAL), Volume (REAL), FetchDate (TEXT/DATE), CreatedAt (TEXT/TIMESTAMP) | | |
| TASK-002 | Add UNIQUE constraint on (Ticker, FetchDate) to prevent duplicate entries | | |
| TASK-003 | Create indexes on Coin and FetchDate columns for query performance | | |
| TASK-004 | Update database migration/initialization script to create table on fresh deployments | | |
| TASK-005 | Test table creation in both SQLite and Azure SQL environments | | |

### Phase 2: ETF Repository Layer

**GOAL-002**: Implement data access layer for ETF operations following repository pattern

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-006 | Create `etf/etf_repository.py` module with ETFRepository class | | |
| TASK-007 | Implement `save_etf_flow()` method with parameterized INSERT/UPDATE logic | | |
| TASK-008 | Implement `get_latest_etf_flows(coin: str)` to fetch today's data for BTC or ETH | | |
| TASK-009 | Implement `get_weekly_etf_flows(coin: str, days: int = 7)` to aggregate 7-day flows | | |
| TASK-010 | Implement `get_etf_flows_by_issuer(coin: str, date: str)` for issuer breakdown | | |
| TASK-011 | Add SQLite/Azure SQL compatibility handling using `self.is_sqlite` pattern | | |
| TASK-012 | Add proper error handling and logging for all database operations | | |

### Phase 3: API Integration

**GOAL-003**: Fetch and parse ETF data from DefiLlama API

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-013 | Create `etf/etf_fetcher.py` module for API communication | | |
| TASK-014 | Implement `fetch_defillama_etf_data()` function with requests library (30s timeout) | | |
| TASK-015 | Add response validation: check HTTP 200, valid JSON, expected fields present | | |
| TASK-016 | Parse JSON response and convert to structured ETF data objects | | |
| TASK-017 | Filter results by Coin field to separate BTC and ETH ETFs | | |
| TASK-018 | Add retry logic with exponential backoff for transient failures (max 3 retries) | | |
| TASK-019 | Log API response statistics (total ETFs fetched, BTC count, ETH count) | | |

### Phase 4: ETF Report Generation

**GOAL-004**: Create report module to format ETF data for display

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-020 | Create `etf/etf_report.py` module following stepn_report.py pattern | | |
| TASK-021 | Implement `fetch_etf_report(conn, coin: str)` returning PrettyTable | | |
| TASK-022 | Add table columns: Ticker, Issuer, Price, Daily Flows, 7-Day Total Flows, AUM | | |
| TASK-023 | Format currency values with proper thousands separators and +/- indicators | | |
| TASK-024 | Calculate aggregate BTC/ETH totals for daily and weekly flows | | |
| TASK-025 | Add summary row showing NET INFLOW/OUTFLOW with directional arrows (↑/↓) | | |
| TASK-026 | Handle edge cases: no data available, API failures, missing issuers | | |

### Phase 5: Daily Report Integration

**GOAL-005**: Integrate ETF reports into the existing daily report workflow

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-027 | Import etf_report functions in `reports/daily_report.py` | | |
| TASK-028 | Call `fetch_etf_report()` for both BTC and ETH in main report generation | | |
| TASK-029 | Format ETF tables for Telegram HTML with `<pre>` tags | | |
| TASK-030 | Add ETF report sections after derivatives report, before launchpool | | |
| TASK-031 | Create separate Telegram messages for BTC and ETH ETF flows | | |
| TASK-032 | Add await send_telegram_message() calls with proper error handling | | |
| TASK-033 | Test Telegram message formatting with real data | | |

### Phase 6: AI Prompt Integration

**GOAL-006**: Extend AI analysis to include ETF flow sentiment

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-034 | Update `news/prompts.py` SYSTEM_PROMPT_ANALYSIS_NEWS to include ETF flow interpretation | | |
| TASK-035 | Add ETF section to prompt: "Analyze institutional sentiment via ETF flows (inflows=bullish, outflows=bearish)" | | |
| TASK-036 | Update USER_PROMPT_ANALYSIS_NEWS template to include ETF data placeholder | | |
| TASK-037 | Modify `_process_ai_analysis()` in daily_report.py to include ETF data in context | | |
| TASK-038 | Format ETF data for AI consumption: "BTC ETF Flows: +$XM daily, +$YM weekly" | | |
| TASK-039 | Test AI analysis output to ensure ETF flows are mentioned in market sentiment section | | |

### Phase 7: Data Population & Scheduling

**GOAL-007**: Automate ETF data fetching and storage

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-040 | Create `etf/fetch_etf_data.py` standalone script for data population | | |
| TASK-041 | Implement main() function that fetches API data and saves to database | | |
| TASK-042 | Add command-line arguments for date range and coin selection | | |
| TASK-043 | Integrate ETF data fetching into daily report execution flow | | |
| TASK-044 | Add ETF fetch step to `run-daily-task.ps1` or equivalent scheduler | | |
| TASK-045 | Test end-to-end: fetch → store → report → Telegram → AI analysis | | |

### Phase 8: Testing & Documentation

**GOAL-008**: Ensure reliability and maintainability

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-046 | Create unit tests for etf_repository methods in `tests/test_etf_repository.py` | | |
| TASK-047 | Create integration tests for API fetcher with mock responses | | |
| TASK-048 | Test database schema with sample ETF data (10+ issuers) | | |
| TASK-049 | Document ETF feature in README.md with usage examples | | |
| TASK-050 | Create ETF_README.md in etf/ folder with API details and data schema | | |
| TASK-051 | Add error handling test cases: API timeout, invalid JSON, missing fields | | |
| TASK-052 | Verify backward compatibility: ensure reports work if ETF table is empty | | |

## 3. Alternatives

- **ALT-001**: Use CoinGecko or alternative ETF data providers instead of DefiLlama (rejected: DefiLlama has comprehensive ETF coverage and free API)
- **ALT-002**: Store only aggregated daily totals instead of per-issuer data (rejected: issuer breakdown provides valuable institutional insights)
- **ALT-003**: Create separate tables for BTC and ETH ETFs (rejected: single table with Coin column is more maintainable and follows DRY principle)
- **ALT-004**: Embed ETF data in existing indicators table (rejected: ETF data has different structure and update frequency)
- **ALT-005**: Use REST API polling instead of batch daily fetch (rejected: daily batch is sufficient for morning reports and reduces API load)

## 4. Dependencies

- **DEP-001**: DefiLlama ETF API availability and stability (external dependency)
- **DEP-002**: requests library for HTTP communication (already in requirements.txt)
- **DEP-003**: PrettyTable library for table formatting (already in requirements.txt)
- **DEP-004**: Database migration completion before production deployment
- **DEP-005**: Telegram bot token and chat_id configuration for message delivery
- **DEP-006**: AI API (Gemini/Perplexity) access for enhanced analysis

## 5. Files

### New Files to Create

- **FILE-001**: `etf/__init__.py` - Module initialization
- **FILE-002**: `etf/etf_repository.py` - Database access layer (class ETFRepository)
- **FILE-003**: `etf/etf_fetcher.py` - DefiLlama API integration
- **FILE-004**: `etf/etf_report.py` - Report generation (function fetch_etf_report)
- **FILE-005**: `etf/fetch_etf_data.py` - Standalone data population script
- **FILE-006**: `etf/ETF_README.md` - Feature documentation
- **FILE-007**: `tests/test_etf_repository.py` - Unit tests
- **FILE-008**: `tests/test_etf_fetcher.py` - Integration tests

### Files to Modify

- **FILE-009**: `database/init_sqlite.py` - Add ETFFlows table creation
- **FILE-010**: `reports/daily_report.py` - Import and integrate ETF reports
- **FILE-011**: `news/prompts.py` - Update AI prompts with ETF context
- **FILE-012**: `README.md` - Document ETF feature
- **FILE-013**: `requirements.txt` - Verify requests library is present

## 6. Testing

### Unit Tests

- **TEST-001**: Test `save_etf_flow()` inserts data correctly in SQLite
- **TEST-002**: Test `save_etf_flow()` handles duplicate (Ticker, FetchDate) with UPDATE
- **TEST-003**: Test `get_latest_etf_flows()` returns correct BTC/ETH data
- **TEST-004**: Test `get_weekly_etf_flows()` aggregates 7 days correctly
- **TEST-005**: Test float sanitization for NaN, Infinity, None values

### Integration Tests

- **TEST-006**: Test `fetch_defillama_etf_data()` with live API (or mocked response)
- **TEST-007**: Test end-to-end: fetch → save → retrieve → format → display
- **TEST-008**: Test Telegram message formatting with actual PrettyTable output
- **TEST-009**: Test AI prompt generation includes ETF data correctly
- **TEST-010**: Test database schema creation in both SQLite and Azure SQL

### Error Handling Tests

- **TEST-011**: Test API timeout (30s) handling
- **TEST-012**: Test invalid JSON response handling
- **TEST-013**: Test missing required fields in API response
- **TEST-014**: Test database connection failure scenarios
- **TEST-015**: Test empty ETF data (no flows available for date)

## 7. Risks & Assumptions

### Risks

- **RISK-001**: DefiLlama API may change structure or become unavailable (Mitigation: Add response validation, log schema changes)
- **RISK-002**: ETF data may not be available for all dates (Mitigation: Handle missing data gracefully, show "No data" message)
- **RISK-003**: Large number of ETFs may exceed Telegram message size limits (Mitigation: Paginate or summarize if >50 ETFs)
- **RISK-004**: API rate limiting may block requests (Mitigation: Add retry logic with exponential backoff)
- **RISK-005**: Database table creation may fail in Azure SQL (Mitigation: Test migration scripts thoroughly)

### Assumptions

- **ASSUMPTION-001**: DefiLlama API returns data in consistent JSON format as documented
- **ASSUMPTION-002**: ETF data updates at least once daily (suitable for morning reports)
- **ASSUMPTION-003**: Users are interested in both BTC and ETH ETF flows (not just BTC)
- **ASSUMPTION-004**: 7-day rolling window is sufficient for trend analysis
- **ASSUMPTION-005**: Existing database connection patterns (SQLiteConnectionWrapper) will continue to work
- **ASSUMPTION-006**: Telegram HTML formatting supports <pre> tags for monospaced tables
- **ASSUMPTION-007**: AI models (Gemini/Perplexity) can meaningfully interpret ETF flow data

## 8. Related Specifications / Further Reading

### Internal Documentation
- [STEPN Report Implementation](../stepn/stepn_report.py) - Similar report pattern
- [Funding Rate Repository](../technical_analysis/repositories/funding_rate_repository.py) - Repository pattern reference
- [SQLite Database Setup](../database/README_SQLITE.md) - Database architecture
- [Telegram Formatting Guide](../docs/TELEGRAM_FORMATTING.md) - Message formatting standards

### External Resources
- [DefiLlama API Documentation](https://api-docs.defillama.com/)
- [DefiLlama ETF Dashboard](https://defillama.com/etfs)
- [DefiLlama LLMs.txt](https://api-docs.defillama.com/llms.txt) - API usage guide

---

## DefiLlama ETF API - Complete JSON Response Breakdown

The API endpoint `https://defillama.com/api/etfs` returns a **JSON array** where each element represents one Bitcoin or Ethereum spot ETF. Here's exactly what you get:

## Complete JSON Response Example

json

`[   {     "Name": "iShares Bitcoin ETF",     "Ticker": "IBIT",     "Coin": "BTC",     "Issuer": "BlackRock",     "Symbol": "IBIT",     "Price": 42850.2,     "AUM": 45123456789,     "AUMChange": 250000000,     "Change": 2.44,     "Flows": 180000000,     "FlowsChange": 45000000,     "Date": 1730784000,     "Country": "USA",     "Volume": 890000000   },   {     "Name": "Fidelity Bitcoin Trust",     "Ticker": "FBTC",     "Coin": "BTC",     "Issuer": "Fidelity",     "Symbol": "FBTC",     "Price": 42851.5,     "AUM": 38456789012,     "AUMChange": 180000000,     "Change": 2.45,     "Flows": 142000000,     "FlowsChange": 28000000,     "Date": 1730784000,     "Country": "USA",     "Volume": 654000000   } ]`

## Field Meanings (for inflow/outflow monitoring)

|Field|Meaning|Your Use Case|
|---|---|---|
|**Ticker**|Stock symbol (IBIT, FBTC, ETHE, etc.)|Identify which ETF|
|**Coin**|"BTC" or "ETH"|Filter what you're monitoring|
|**Flows**|**Daily NET inflow/outflow in USD** ⭐|**THIS IS THE KEY METRIC**|
|**AUM**|Total assets in the ETF|Track if ETF is growing|
|**Price**|Current price per share|Track valuation|
|**Change**|Daily price change %|See if BTC/ETH went up/down|
|**Volume**|Trading volume in USD|See trading activity|
|**Issuer**|Who manages it (BlackRock, Fidelity, etc.)|Filter by provider|

## Key Insight: Understanding "Flows"

The **"Flows"** field is what you monitor for inflows/outflows:

- **Positive number** (e.g., `180000000`) = **$180M flowed INTO the ETF** ↑ (buying pressure)
    
- **Negative number** (e.g., `-50000000`) = **$50M flowed OUT of the ETF** ↓ (selling pressure)
    
- **Zero or small** = Balanced, no major institutional movement
    

This represents institutional investors moving money in or out, which is a strong indicator of sentiment.

## Practical Examples

**Example 1: Check today's Bitcoin ETF flows**

python

`import requests data = requests.get('https://defillama.com/api/etfs').json() # Sum all Bitcoin ETF flows btc_total_flows = sum(etf['Flows'] for etf in data if etf['Coin'] == 'BTC') if btc_total_flows > 0:     print(f"✓ Bitcoin ETFs: ${btc_total_flows:,.0f} INFLOW (Institutions BUYING)") else:     print(f"✗ Bitcoin ETFs: ${abs(btc_total_flows):,.0f} OUTFLOW (Institutions SELLING)")`

**Example 2: See each issuer's flows**

python

`data = requests.get('https://defillama.com/api/etfs').json() for etf in data:     if etf['Coin'] == 'BTC':         flows = etf['Flows']         status = "↑ IN" if flows > 0 else "↓ OUT"         print(f"{etf['Ticker']:8} ({etf['Issuer']:15}): {status} ${flows:>15,.0f}")`

**Output:**

text

`IBIT     (BlackRock      ): ↑ IN  $   180000000 FBTC     (Fidelity       ): ↑ IN  $   142000000 GBTC     (Grayscale      ): ↓ OUT $   -25000000`

## How to Set Up Daily Monitoring

I've created three complete scripts for you:

This script includes formatted output, daily logging, CSV tracking, and 7-day trend analysis.

Complete documentation with code examples showing how to parse flows and track trends.

A production-ready class-based monitor with methods for fetching, parsing, logging, and analyzing flows over time.

## Setting Up Automated Daily Runs

**On Windows (Task Scheduler):**

1. Open Task Scheduler
    
2. Create Basic Task → Set trigger to daily at desired time
    
3. Action: Run program → `C:\Python\python.exe -m etf_daily_monitor`
    

**On Linux/Mac (Cron):**

bash

`# Run daily at 5 PM 0 17 * * * /usr/bin/python3 /path/to/etf_daily_monitor.py >> /tmp/etf_monitor.log 2>&1`

The scripts will log data to:

- **JSONL format**: `etf_flows_daily.jsonl` (for trend analysis)
    
- **CSV format**: `etf_flows_tracking.csv` (for spreadsheet analysis)
    

After collecting 7+ days of data, you'll see meaningful trends showing whether institutions are accumulating or distributing Bitcoin and Ethereum.

1. [https://api-docs.defillama.com/llms.txt](https://api-docs.defillama.com/llms.txt)
2. [https://defillama.com](https://defillama.com/)
3. [https://docs.llama.fi/list-your-project/other-dashboards](https://docs.llama.fi/list-your-project/other-dashboards)
4. [https://github.com/Hati0x/defillama-api](https://github.com/Hati0x/defillama-api)
5. [https://defillama.com/protocol/dexfinance-etf](https://defillama.com/protocol/dexfinance-etf)
6. [https://www.youtube.com/watch?v=-fAinvExQHk](https://www.youtube.com/watch?v=-fAinvExQHk)
7. [https://www.youtube.com/watch?v=LEOrwRZzyWY](https://www.youtube.com/watch?v=LEOrwRZzyWY)
8. [https://www.jpmorgan.com/kinexys/documents/JPMC-Kinexys-Project-Epic-Whitepaper-2024.pdf](https://www.jpmorgan.com/kinexys/documents/JPMC-Kinexys-Project-Epic-Whitepaper-2024.pdf)
9. [https://defillama.com/etfs](https://defillama.com/etfs)
10. [https://api-docs.defillama.com](https://api-docs.defillama.com/)