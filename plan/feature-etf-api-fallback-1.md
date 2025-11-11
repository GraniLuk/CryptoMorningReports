---
goal: Implement API Fallback Strategy for ETF Data Reliability
version: 1.0
date_created: 2025-01-11
last_updated: 2025-01-11
owner: Engineering Team
status: 'Planned'
tags: [feature, etf, api, reliability, refactor]
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

This implementation plan addresses the critical reliability issues with the current ETF data fetching system. YFinance API frequently rate-limits requests and does NOT provide ETF AUM (Assets Under Management) or inflow/outflow data, which are the core metrics for ETF tracking. This plan implements a fallback API strategy to ensure daily ETF data availability while addressing the fundamental data gap.

**Core Problem**: The system currently relies solely on YFinance, which:
1. Frequently returns "429 Too Many Requests" errors
2. Does NOT provide AUM or flows data (returns None for these critical fields)
3. Only provides price and volume data

**Solution Strategy**: Implement multi-tier API fallback with Alpha Vantage, document data limitations, and prepare for future premium data integration.

## 1. Requirements & Constraints

### Data Requirements
- **REQ-001**: System must fetch ETF data at least once per day without failure
- **REQ-002**: Primary data: ticker, coin, issuer, price, volume (available from free APIs)
- **REQ-003**: Secondary data: AUM, flows, flows_change (NOT available from free APIs)
- **REQ-004**: Database schema must remain compatible (existing ETFFlows table)
- **REQ-005**: Report must gracefully handle missing AUM/flows data

### API Constraints
- **CON-001**: YFinance: Rate-limited, no AUM/flows data, batch download supported
- **CON-002**: Alpha Vantage: Free tier = 25 requests/day, TIME_SERIES_DAILY for ETFs
- **CON-003**: Alpha Vantage: Does NOT provide ETF-specific AUM/flows data
- **CON-004**: FMP (Financial Modeling Prep): Has ETF data but requires paid plan, no explicit flows data
- **CON-005**: ETF flows data is typically premium data (Bloomberg Terminal, Morningstar, etc.)

### Technical Constraints
- **CON-006**: Must work with existing TDD tests (22 passing tests)
- **CON-007**: Must maintain backward compatibility with existing repository methods
- **CON-008**: Must log which API succeeded for debugging
- **CON-009**: API keys must be stored in local.settings.json (not committed)

### Business Logic
- **GUD-001**: Repository only returns TODAY's data (no old data fallback)
- **GUD-002**: When both APIs fail, show "Data unavailable" in reports
- **GUD-003**: Prefer YFinance (batch mode) when available due to single API call efficiency
- **GUD-004**: Fall back to Alpha Vantage only when YFinance fails

### Security & Configuration
- **SEC-001**: API keys must be stored in environment variables/settings file
- **SEC-002**: Never commit API keys to source control
- **SEC-003**: Log API failures without exposing keys

### Future Considerations
- **PAT-001**: Architecture must support adding premium ETF data sources later
- **PAT-002**: Separate fetching logic from data source to enable easy swapping
- **PAT-003**: Consider implementing estimated flows calculation from price/AUM changes

## 2. Implementation Steps

### Implementation Phase 1: Alpha Vantage Integration

- GOAL-001: Implement Alpha Vantage as fallback API for ETF price/volume data

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Register for Alpha Vantage API key (free tier) | |  |
| TASK-002 | Add `alpha-vantage` package to requirements.txt | |  |
| TASK-003 | Add ALPHA_VANTAGE_API_KEY to local.settings.json template | |  |
| TASK-004 | Create `fetch_alphavantage_etf_data()` function in etf_fetcher.py | |  |
| TASK-005 | Implement rate limit handling for Alpha Vantage (25 calls/day) | |  |
| TASK-006 | Parse Alpha Vantage TIME_SERIES_DAILY response to ETF format | |  |
| TASK-007 | Add logging to track which API is being used | |  |
| TASK-008 | Test Alpha Vantage fetcher independently | |  |

### Implementation Phase 2: Fallback Logic Implementation

- GOAL-002: Implement primary → fallback → fail gracefully pattern

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-009 | Refactor fetch_yfinance_etf_data() to return error codes on failure | |  |
| TASK-010 | Create `fetch_etf_data_with_fallback()` orchestrator function | |  |
| TASK-011 | Implement try YFinance → try Alpha Vantage → return None logic | |  |
| TASK-012 | Add retry logic with exponential backoff for transient failures | |  |
| TASK-013 | Log which API succeeded/failed for each fetch attempt | |  |
| TASK-014 | Update etf_repository.py to use new fallback function | |  |

### Implementation Phase 3: Data Limitations Documentation

- GOAL-003: Clearly document that AUM/flows data is NOT available from free APIs

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-015 | Add WARNING comments in etf_fetcher.py about missing AUM/flows | |  |
| TASK-016 | Update ETF README documenting free API limitations | |  |
| TASK-017 | Add log warnings when storing None for AUM/flows fields | |  |
| TASK-018 | Update etf_report.py to show "AUM/flows data unavailable" message | |  |

### Implementation Phase 4: Testing & Validation

- GOAL-004: Ensure all existing tests pass and add fallback-specific tests

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-019 | Create test_etf_api_fallback.py with mock responses | |  |
| TASK-020 | Test scenario: YFinance succeeds (no fallback triggered) | |  |
| TASK-021 | Test scenario: YFinance fails → Alpha Vantage succeeds | |  |
| TASK-022 | Test scenario: Both APIs fail → graceful None return | |  |
| TASK-023 | Test scenario: Rate limit handling (Alpha Vantage 25/day limit) | |  |
| TASK-024 | Verify all 22 existing TDD tests still pass | |  |
| TASK-025 | Run full test suite (pytest) | |  |

### Implementation Phase 5: Configuration & Deployment

- GOAL-005: Configure API keys and deploy fallback system

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-026 | Add Alpha Vantage API key to local.settings.json (local dev) | |  |
| TASK-027 | Add Alpha Vantage API key to Azure Function App Settings (production) | |  |
| TASK-028 | Update deployment documentation with new API key requirement | |  |
| TASK-029 | Test fallback in local development environment | |  |
| TASK-030 | Test fallback in Azure production environment | |  |
| TASK-031 | Monitor logs for API success/failure patterns | |  |

## 3. Alternatives

Alternative approaches considered and why they were not chosen:

- **ALT-001**: Use Financial Modeling Prep (FMP) as fallback
  - Reason rejected: Requires paid plan for reliable access; free tier very limited
  - Why not chosen: Alpha Vantage has more generous free tier (25/day vs FMP's 250/day total across all endpoints)

- **ALT-002**: Implement web scraping for ETF data from public websites
  - Reason rejected: Fragile, violates ToS, legally questionable
  - Why not chosen: APIs provide stable, legal access to data

- **ALT-003**: Calculate estimated flows from AUM changes
  - Reason rejected (for now): Requires historical AUM data which free APIs don't provide
  - Why not chosen: Will consider this as future enhancement once we have consistent AUM data

- **ALT-004**: Pay for premium ETF flows data (Bloomberg, Morningstar)
  - Reason rejected: Cost prohibitive for personal project
  - Why not chosen: Current budget constraints; may revisit if project scales

- **ALT-005**: Use multiple fallback APIs (3+ tiers)
  - Reason rejected: Complexity increases exponentially with diminishing returns
  - Why not chosen: Two APIs (YFinance + Alpha Vantage) provide sufficient reliability

- **ALT-006**: Cache ETF data for multiple days to reduce API calls
  - Reason rejected: Defeats purpose of daily fresh data requirement
  - Why not chosen: Repository already implements "today only" logic per TDD

## 4. Dependencies

External dependencies required for implementation:

- **DEP-001**: Alpha Vantage API free account (https://www.alphavantage.co/support/#api-key)
  - Status: Must create account
  - Limit: 25 API calls per day
  - Required for: Fallback ETF data fetching

- **DEP-002**: Python package `alpha-vantage` or `requests`
  - Status: Need to add to requirements.txt
  - Version: Latest stable
  - Required for: Alpha Vantage API integration

- **DEP-003**: YFinance API (existing)
  - Status: Already integrated
  - Version: 0.2.49
  - Required for: Primary ETF data source

- **DEP-004**: Local.settings.json with API keys
  - Status: Needs ALPHA_VANTAGE_API_KEY added
  - Required for: API authentication

- **DEP-005**: Azure Function App Settings
  - Status: Needs ALPHA_VANTAGE_API_KEY configured
  - Required for: Production deployment

## 5. Files

Files that will be created or modified during implementation:

### Files to Modify

- **FILE-001**: `etf/etf_fetcher.py`
  - Changes: Add `fetch_alphavantage_etf_data()`, `fetch_etf_data_with_fallback()`
  - Impact: Core fetching logic enhanced with fallback
  - Lines: ~100-150 new lines

- **FILE-002**: `requirements.txt`
  - Changes: Add `requests` or `alpha-vantage` package
  - Impact: New dependency for Alpha Vantage API

- **FILE-003**: `local.settings.json`
  - Changes: Add ALPHA_VANTAGE_API_KEY configuration
  - Impact: API key management (not committed)

- **FILE-004**: `etf/etf_repository.py`
  - Changes: Update to use new fallback function
  - Impact: Repository uses fallback fetcher

- **FILE-005**: `etf/etf_report.py`
  - Changes: Add messaging for missing AUM/flows data
  - Impact: User-facing report clarity

### Files to Create

- **FILE-006**: `etf/README.md`
  - Purpose: Document ETF data limitations and API usage
  - Content: API constraints, data gaps, future enhancements

- **FILE-007**: `tests/test_etf_api_fallback.py`
  - Purpose: Test fallback logic with mocked API responses
  - Content: 5+ test scenarios for fallback behavior

- **FILE-008**: `.env.example`
  - Purpose: Template for environment variables
  - Content: ALPHA_VANTAGE_API_KEY=your_key_here

## 6. Testing

Test coverage required for fallback implementation:

### Unit Tests

- **TEST-001**: `test_yfinance_success()`
  - Purpose: Verify YFinance fetcher works when API is available
  - Expected: Returns valid ETF data list, no fallback triggered

- **TEST-002**: `test_yfinance_rate_limit_triggers_fallback()`
  - Purpose: Mock YFinance 429 error, verify Alpha Vantage is called
  - Expected: Alpha Vantage fetcher called, returns data

- **TEST-003**: `test_alphavantage_success()`
  - Purpose: Verify Alpha Vantage fetcher works independently
  - Expected: Returns valid ETF data list with correct schema

- **TEST-004**: `test_both_apis_fail_gracefully()`
  - Purpose: Mock both APIs failing, verify None returned
  - Expected: Returns None, logs both failures, no exception raised

- **TEST-005**: `test_alphavantage_rate_limit_handling()`
  - Purpose: Verify Alpha Vantage 25/day limit is respected
  - Expected: After 25 calls, returns appropriate error

- **TEST-006**: `test_api_selection_logging()`
  - Purpose: Verify logs clearly show which API was used
  - Expected: Log contains "Using YFinance" or "Falling back to Alpha Vantage"

- **TEST-007**: `test_data_schema_consistency()`
  - Purpose: Ensure both APIs return same data structure
  - Expected: YFinance and Alpha Vantage data have identical keys

### Integration Tests

- **TEST-008**: `test_repository_integration_with_fallback()`
  - Purpose: Test full flow from fetcher → repository → database
  - Expected: Data stored correctly regardless of API used

- **TEST-009**: `test_report_with_missing_flows_data()`
  - Purpose: Verify report handles None AUM/flows gracefully
  - Expected: Report shows "Data unavailable" message

### Existing Tests Validation

- **TEST-010**: Run all 22 existing TDD tests
  - Purpose: Ensure no regression from fallback implementation
  - Expected: All tests pass (test_etf_no_old_data_tdd.py, test_etf_repository.py)

## 7. Risks & Assumptions

Potential risks and underlying assumptions:

### Risks

- **RISK-001**: Alpha Vantage free tier limit (25/day) may be insufficient
  - Impact: HIGH - Fetching 15 ETF tickers = 15 API calls
  - Mitigation: Implement daily quota tracking, warn when approaching limit
  - Probability: MEDIUM - Depends on how often YFinance fails

- **RISK-002**: Alpha Vantage may not provide real-time data (15-min delay)
  - Impact: LOW - Daily reports don't require real-time data
  - Mitigation: Document delay in README
  - Probability: HIGH - Free tier often has delayed data

- **RISK-003**: Both APIs may fail simultaneously
  - Impact: HIGH - No ETF data in daily report
  - Mitigation: Graceful degradation (show "unavailable" message)
  - Probability: LOW - Unlikely both fail on same day

- **RISK-004**: Missing AUM/flows data makes reports less useful
  - Impact: MEDIUM - Core ETF tracking feature incomplete
  - Mitigation: Document limitation, plan future premium integration
  - Probability: CERTAIN - Free APIs don't provide this data

- **RISK-005**: API provider policy changes
  - Impact: MEDIUM - May require code changes
  - Mitigation: Monitor API documentation, have flexible architecture
  - Probability: LOW - Rare but possible

### Assumptions

- **ASSUMPTION-001**: YFinance will remain free and accessible
  - Validation: Check YFinance GitHub and documentation quarterly
  - Risk if wrong: Need to find alternative primary source

- **ASSUMPTION-002**: Alpha Vantage TIME_SERIES_DAILY provides ETF price data
  - Validation: Test with actual API calls during development
  - Risk if wrong: Need different Alpha Vantage endpoint or alternative API

- **ASSUMPTION-003**: 15 API calls/day is acceptable for Alpha Vantage free tier
  - Validation: Monitor actual usage in production
  - Risk if wrong: May hit rate limits frequently

- **ASSUMPTION-004**: Price and volume data alone is sufficient for basic reports
  - Validation: Review report requirements with stakeholders
  - Risk if wrong: May need premium data source sooner than planned

- **ASSUMPTION-005**: Current database schema can accommodate None values for AUM/flows
  - Validation: Schema allows NULL values (already tested)
  - Risk if wrong: Minimal - schema already handles this

## 8. Related Specifications / Further Reading

### Related Plans
- [Daily ETF Inflows](./daily-etf-inflows.md) - Original ETF feature specification
- [TDD Phase 1 Summary](./phase1_summary.md) - Testing approach
- [TDD Phase 2 Summary](./phase2_summary.md) - Repository fix implementation

### External Documentation
- [Alpha Vantage API Documentation](https://www.alphavantage.co/documentation/)
- [YFinance Documentation](https://github.com/ranaroussi/yfinance)
- [Financial Modeling Prep ETF API](https://site.financialmodelingprep.com/developer/docs/etf-asset-exposure) (for future reference)

### Technical References
- [Python Requests Library](https://requests.readthedocs.io/) - For Alpha Vantage integration
- [Azure Function App Settings](https://learn.microsoft.com/en-us/azure/azure-functions/functions-app-settings) - For API key management
- [ETF Data Sources Comparison](https://github.com/topics/etf-data) - Research on data sources

### Data Source Research
- **Bloomberg Terminal** - Premium ETF flows data (enterprise pricing)
- **Morningstar Direct** - ETF flows and AUM data (paid subscription)
- **ETF.com** - Free ETF data but no API
- **State Street SPDR ETF Flow Data** - Limited free data for SPDR ETFs

### Future Enhancements
- Consider implementing estimated flows calculation from price/AUM changes
- Evaluate Financial Modeling Prep premium tier if budget allows
- Research if any free sources provide even partial ETF flows data
- Consider aggregating data from multiple free sources to fill gaps
