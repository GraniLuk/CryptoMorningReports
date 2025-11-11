---
goal: Implement DefiLlama Web Scraping for Complete ETF Data
version: 2.0
date_created: 2025-01-11
last_updated: 2025-11-11
owner: Engineering Team
status: 'Planned'
tags: [feature, etf, web-scraping, defillama, reliability, refactor]
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

This implementation plan addresses the critical reliability issues with the current ETF data fetching system. YFinance API frequently rate-limits requests and does NOT provide ETF AUM (Assets Under Management) or inflow/outflow data, which are the core metrics for ETF tracking. This plan implements web scraping of DefiLlama's ETF dashboard to obtain complete ETF data including flows and AUM.

**Core Problem**: The system currently relies solely on YFinance, which:
1. Frequently returns "429 Too Many Requests" errors
2. Does NOT provide AUM or flows data (returns None for these critical fields)
3. Only provides price and volume data

**Solution Strategy**: Implement web scraping of DefiLlama ETF dashboard (https://defillama.com/etfs) which provides:
- Daily flows data for Bitcoin and Ethereum ETFs
- Total AUM (Assets Under Management) for both BTC and ETH
- Individual ETF details (ticker, issuer, coin, flows, AUM, volume)
- Data sourced from Farside (reputable ETF flow tracker)

## 1. Requirements & Constraints

### Data Requirements
- **REQ-001**: System must fetch ETF data at least once per day without failure
- **REQ-002**: Primary data: ticker, coin, issuer, flows, AUM, volume (available from DefiLlama)
- **REQ-003**: Database schema must remain compatible (existing ETFFlows table)
- **REQ-004**: Report must display AUM and flows data prominently
- **REQ-005**: Data must be from current day (Nov 10, 2025 example: BTC flows=$1.2M, AUM=$114.612B)

### Data Source Constraints
- **CON-001**: DefiLlama ETF dashboard: https://defillama.com/etfs
- **CON-002**: DefiLlama uses Cloudflare protection (must use Selenium or similar)
- **CON-003**: DefiLlama sources data from Farside (reputable ETF tracker)
- **CON-004**: YFinance: Keep as fallback for price/volume only
- **CON-005**: DefiLlama provides: Daily/Weekly/Monthly/Cumulative flows data
- **CON-006**: Individual ETF table has: Ticker, Issuer, Coin, Flows, AUM, Volume

### Technical Constraints
- **CON-007**: Must work with existing TDD tests (22 passing tests)
- **CON-008**: Must maintain backward compatibility with existing repository methods
- **CON-009**: Must bypass Cloudflare protection (use Selenium WebDriver or cloudscraper)
- **CON-010**: Scraping must be respectful (add delays, proper user agent)
- **CON-011**: Must handle scraping failures gracefully
- **CON-012**: Parse HTML table structure to extract ETF data

### Business Logic
- **GUD-001**: Repository only returns TODAY's data (no old data fallback)
- **GUD-002**: When scraping fails, show "Data unavailable" in reports
- **GUD-003**: Prefer DefiLlama scraping (complete data with flows/AUM)
- **GUD-004**: Fall back to YFinance only if scraping fails (price/volume only)

### Security & Configuration
- **SEC-001**: API keys must be stored in environment variables/settings file
- **SEC-002**: Never commit API keys to source control
- **SEC-003**: Log API failures without exposing keys

### Future Considerations
- **PAT-001**: Architecture must support adding premium ETF data sources later
- **PAT-002**: Separate fetching logic from data source to enable easy swapping
- **PAT-003**: Consider implementing estimated flows calculation from price/AUM changes

## 2. Implementation Steps

### Implementation Phase 1: DefiLlama Web Scraper Setup

- GOAL-001: Implement web scraper for DefiLlama ETF dashboard

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Add `selenium` and `beautifulsoup4` packages to requirements.txt | |  |
| TASK-002 | Add `webdriver-manager` for automatic ChromeDriver management | |  |
| TASK-003 | Install and test Selenium WebDriver with Chrome (headless mode) | |  |
| TASK-004 | Create `scrape_defillama_etf()` function in etf_fetcher.py | |  |
| TASK-005 | Implement Cloudflare bypass using Selenium with proper wait times | |  |
| TASK-006 | Parse HTML to extract daily stats (BTC/ETH flows and AUM) | |  |
| TASK-007 | Parse ETF table to extract individual ETF data (ticker, issuer, flows, AUM, volume) | |  |
| TASK-008 | Add respectful scraping delays (2-3 seconds) and proper User-Agent | |  |
| TASK-009 | Test scraper independently with live DefiLlama site | |  |

### Implementation Phase 2: Data Parsing & Transformation

- GOAL-002: Transform scraped HTML data into ETF data structure

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-010 | Parse "Daily Stats" section for BTC flows ($1.2M) and AUM ($114.612B) | |  |
| TASK-011 | Parse "Daily Stats" section for ETH flows ($0) and AUM ($17.183B) | |  |
| TASK-012 | Parse ETF table rows (IBIT, FBTC, ETHA, etc.) | |  |
| TASK-013 | Convert flow strings ("$1.2m", "$0") to numeric values | |  |
| TASK-014 | Convert AUM strings ("$114.612b", "$17.183b") to numeric values | |  |
| TASK-015 | Convert volume strings to numeric values | |  |
| TASK-016 | Map ticker to coin type (BTC/ETH) and issuer | |  |
| TASK-017 | Calculate flows_change if historical data available | |  |
| TASK-018 | Return standardized ETF data list matching database schema | |  |

### Implementation Phase 3: Fallback Logic Implementation

- GOAL-003: Implement DefiLlama → YFinance → fail gracefully pattern

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-019 | Create `fetch_etf_data_with_scraping()` orchestrator function | |  |
| TASK-020 | Implement try DefiLlama scraper → try YFinance → return None logic | |  |
| TASK-021 | Add retry logic with exponential backoff for transient failures | |  |
| TASK-022 | Log which data source succeeded/failed for each fetch attempt | |  |
| TASK-023 | Handle Cloudflare blocking gracefully (fall back to YFinance) | |  |
| TASK-024 | Update etf_repository.py to use new scraping function | |  |
| TASK-025 | Ensure scraper cleanup (close browser) even on errors | |  |

### Implementation Phase 4: Testing & Validation

- GOAL-004: Ensure all existing tests pass and add scraping-specific tests

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-026 | Create test_defillama_scraper.py with mocked HTML responses | |  |
| TASK-027 | Test scenario: DefiLlama succeeds (complete data with flows/AUM) | |  |
| TASK-028 | Test scenario: DefiLlama fails → YFinance succeeds (partial data) | |  |
| TASK-029 | Test scenario: Both sources fail → graceful None return | |  |
| TASK-030 | Test scenario: Parse error handling (malformed HTML) | |  |
| TASK-031 | Test scenario: Cloudflare challenge handling | |  |
| TASK-032 | Verify all 22 existing TDD tests still pass | |  |
| TASK-033 | Run full test suite (pytest) | |  |
| TASK-034 | Manual test with live DefiLlama site | |  |

### Implementation Phase 5: Configuration & Deployment

- GOAL-005: Configure scraper settings and deploy to production

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-035 | Add Chrome/ChromeDriver to Azure Function App dependencies | |  |
| TASK-036 | Configure headless browser settings for Azure environment | |  |
| TASK-037 | Add scraping timeout settings to local.settings.json | |  |
| TASK-038 | Update deployment documentation with Selenium requirements | |  |
| TASK-039 | Test scraping in local development environment | |  |
| TASK-040 | Test scraping in Azure production environment | |  |
| TASK-041 | Monitor logs for scraping success/failure patterns | |  |
| TASK-042 | Add alerting for consecutive scraping failures (3+ days) | |  |

## 3. Alternatives

Alternative approaches considered and why they were not chosen:

- **ALT-001**: Use Alpha Vantage API as fallback
  - Reason rejected: Does NOT provide AUM or flows data (same limitation as YFinance)
  - Why not chosen: User specifically needs AUM and flows data which are unavailable via free APIs

- **ALT-002**: Use Financial Modeling Prep (FMP) API
  - Reason rejected: Requires paid plan for reliable access; no explicit ETF flows data
  - Why not chosen: Cost prohibitive; uncertain if flows data available even with paid tier

- **ALT-003**: Pay for premium ETF flows data (Bloomberg, Morningstar)
  - Reason rejected: Costs $1000+/month for Bloomberg Terminal
  - Why not chosen: Current budget constraints; project is personal/non-commercial

- **ALT-004**: Calculate estimated flows from AUM changes
  - Reason rejected: Requires historical AUM data which free APIs don't consistently provide
  - Why not chosen: Less accurate than actual flow data; DefiLlama provides real data

- **ALT-005**: Use Farside Investors API directly
  - Reason rejected: Farside doesn't appear to have a public API
  - Why not chosen: DefiLlama aggregates Farside data and presents it accessibly

- **ALT-006**: Implement caching to reduce API calls
  - Reason rejected: Doesn't solve the data availability problem
  - Why not chosen: Repository already implements "today only" logic; need current data daily

- **ALT-007**: Use cloudscraper Python library instead of Selenium
  - Reason considered: Lighter weight, faster than Selenium
  - Risk: May not bypass Cloudflare reliably; Selenium more robust
  - Decision: Start with Selenium for reliability; can optimize later if needed

## 4. Dependencies

External dependencies required for implementation:

- **DEP-001**: Selenium WebDriver for Python
  - Status: Need to add to requirements.txt
  - Package: `selenium>=4.15.0`
  - Required for: Bypassing Cloudflare and scraping DefiLlama

- **DEP-002**: WebDriver Manager
  - Status: Need to add to requirements.txt
  - Package: `webdriver-manager>=4.0.0`
  - Required for: Automatic ChromeDriver installation and management

- **DEP-003**: BeautifulSoup4 (existing)
  - Status: Already in requirements.txt
  - Version: Current (>=4.12.0)
  - Required for: HTML parsing

- **DEP-004**: Google Chrome / Chromium
  - Status: Must be available in Azure Function App environment
  - Required for: Selenium WebDriver headless browser
  - Note: May need to use chrome-headless-shell Azure extension

- **DEP-005**: YFinance API (existing)
  - Status: Already integrated
  - Version: 0.2.49
  - Required for: Fallback data source (price/volume only)

- **DEP-006**: DefiLlama ETF Dashboard
  - Status: External website (https://defillama.com/etfs)
  - Availability: Public, but Cloudflare protected
  - Required for: Primary data source (flows, AUM, volume)
  - Source: Data from Farside Investors (reputable ETF tracker)

## 5. Files

Files that will be created or modified during implementation:

### Files to Modify

- **FILE-001**: `etf/etf_fetcher.py`
  - Changes: Add `scrape_defillama_etf()`, `fetch_etf_data_with_scraping()`
  - Impact: Core fetching logic enhanced with web scraping
  - Lines: ~200-250 new lines (scraping + parsing + fallback logic)

- **FILE-002**: `requirements.txt`
  - Changes: Add `selenium>=4.15.0`, `webdriver-manager>=4.0.0`
  - Impact: New dependencies for web scraping

- **FILE-003**: `local.settings.json`
  - Changes: Add SCRAPING_TIMEOUT, HEADLESS_BROWSER settings
  - Impact: Scraper configuration (not committed)

- **FILE-004**: `etf/etf_repository.py`
  - Changes: Update to use new scraping function
  - Impact: Repository uses scraping-based fetcher

- **FILE-005**: `etf/etf_report.py`
  - Changes: Update to prominently display AUM and flows data
  - Impact: User-facing report now shows complete ETF data

### Files to Create

- **FILE-006**: `etf/defillama_scraper.py`
  - Purpose: Dedicated module for DefiLlama scraping logic
  - Content: Selenium setup, HTML parsing, data extraction

- **FILE-007**: `etf/README.md`
  - Purpose: Document ETF data sources and scraping approach
  - Content: DefiLlama usage, fallback strategy, data schema

- **FILE-008**: `tests/test_defillama_scraper.py`
  - Purpose: Test scraping logic with mocked HTML responses
  - Content: 8+ test scenarios for scraping behavior

- **FILE-009**: `tests/fixtures/defillama_etf_page.html`
  - Purpose: Sample HTML for testing scraper
  - Content: Realistic DefiLlama ETF page structure

## 6. Testing

Test coverage required for web scraping implementation:

### Unit Tests

- **TEST-001**: `test_defillama_scraping_success()`
  - Purpose: Verify DefiLlama scraper works with valid HTML
  - Expected: Returns complete ETF data with flows and AUM

- **TEST-002**: `test_parse_daily_stats()`
  - Purpose: Test parsing of "Daily Stats" section (BTC/ETH flows and AUM)
  - Expected: Correctly extracts "$1.2M", "$114.612B", "$0", "$17.183B"

- **TEST-003**: `test_parse_etf_table()`
  - Purpose: Test parsing of individual ETF table rows
  - Expected: Extracts ticker, issuer, coin, flows, AUM, volume for each ETF

- **TEST-004**: `test_numeric_conversion()`
  - Purpose: Test string to numeric conversion ("$1.2m" → 1200000, "$114.612b" → 114612000000)
  - Expected: Correctly handles M (millions) and B (billions) suffixes

- **TEST-005**: `test_cloudflare_challenge_fallback()`
  - Purpose: Mock Cloudflare blocking, verify YFinance fallback triggered
  - Expected: YFinance fetcher called, returns data without flows/AUM

- **TEST-006**: `test_both_sources_fail_gracefully()`
  - Purpose: Mock both scraping and YFinance failing
  - Expected: Returns None, logs both failures, no exception raised

- **TEST-007**: `test_malformed_html_handling()`
  - Purpose: Test scraper with incomplete or malformed HTML
  - Expected: Graceful error handling, fallback to YFinance

- **TEST-008**: `test_browser_cleanup_on_error()`
  - Purpose: Verify Selenium WebDriver closes even when errors occur
  - Expected: Browser process terminated, no resource leaks

### Integration Tests

- **TEST-009**: `test_repository_integration_with_scraping()`
  - Purpose: Test full flow from scraper → repository → database
  - Expected: Complete data (with flows/AUM) stored correctly

- **TEST-010**: `test_report_with_complete_etf_data()`
  - Purpose: Verify report displays AUM and flows prominently
  - Expected: Report shows "BTC Flows: $1.2M, AUM: $114.612B"

- **TEST-011**: `test_live_defillama_scraping()` (manual/optional)
  - Purpose: Test with actual DefiLlama website
  - Expected: Successfully scrapes current day's data
  - Note: Skip in CI/CD, run manually before deployment

### Existing Tests Validation

- **TEST-012**: Run all 22 existing TDD tests
  - Purpose: Ensure no regression from scraping implementation
  - Expected: All tests pass (test_etf_no_old_data_tdd.py, test_etf_repository.py)

## 7. Risks & Assumptions

Potential risks and underlying assumptions:

### Risks

- **RISK-001**: DefiLlama may change their HTML structure
  - Impact: HIGH - Scraper would break completely
  - Mitigation: Regular monitoring, graceful fallback to YFinance, version scraper HTML selectors
  - Probability: MEDIUM - Websites update occasionally

- **RISK-002**: Cloudflare protection may be strengthened
  - Impact: HIGH - Selenium may no longer bypass protection
  - Mitigation: Consider cloudscraper library, implement rotating user agents, add delay randomization
  - Probability: MEDIUM - Cloudflare evolves continuously

- **RISK-003**: DefiLlama may implement rate limiting or blocking
  - Impact: MEDIUM - Could block scraper IP/user agent
  - Mitigation: Respectful scraping (delays, proper UA), fallback to YFinance
  - Probability: LOW - Once-daily scraping is minimal traffic

- **RISK-004**: Selenium/Chrome dependencies in Azure Functions
  - Impact: HIGH - May not work in Azure serverless environment
  - Mitigation: Use Azure Function Docker container, chrome-headless-shell extension, or Azure Container Instances
  - Probability: MEDIUM - Azure Functions has limited native support

- **RISK-005**: Scraping performance may be slow (10-15 seconds)
  - Impact: LOW - Daily report delayed by a few seconds
  - Mitigation: Run in background, implement timeout (30 sec max)
  - Probability: HIGH - Selenium/Chrome startup takes time

- **RISK-006**: Legal concerns about web scraping
  - Impact: MEDIUM - Potential ToS violation
  - Mitigation: Respectful scraping, proper attribution, use data for personal/non-commercial purposes only
  - Probability: LOW - Public data, educational use

### Assumptions

- **ASSUMPTION-001**: DefiLlama will continue providing free public ETF data
  - Validation: Monitor site availability monthly
  - Risk if wrong: Would need to find alternative source or revert to YFinance only

- **ASSUMPTION-002**: DefiLlama data from Farside is accurate and reliable
  - Validation: Compare with other sources (etf.com, yahoo finance)
  - Risk if wrong: Report data may be incorrect

- **ASSUMPTION-003**: Selenium can bypass Cloudflare protection reliably
  - Validation: Test during development phase
  - Risk if wrong: May need cloudscraper library or alternative approach

- **ASSUMPTION-004**: Chrome/Chromium can run in Azure Functions environment
  - Validation: Test in Azure staging environment before production
  - Risk if wrong: May need to use Azure Container Instances instead

- **ASSUMPTION-005**: Once-daily scraping won't trigger blocking
  - Validation: Monitor for HTTP 403/429 errors in production logs
  - Risk if wrong: May need to reduce frequency or add more delays

- **ASSUMPTION-006**: HTML parsing selectors remain stable
  - Validation: Version selectors, add fallback selectors for same data
  - Risk if wrong: Scraper breaks until selectors updated

- **ASSUMPTION-007**: Individual ETF data in table matches aggregated daily stats
  - Validation: Sum individual ETF flows, compare to daily stats total
  - Risk if wrong: Data inconsistency in reports

## 8. Related Specifications / Further Reading

### Related Plans
- [Daily ETF Inflows](./daily-etf-inflows.md) - Original ETF feature specification
- [TDD Phase 1 Summary](./phase1_summary.md) - Testing approach
- [TDD Phase 2 Summary](./phase2_summary.md) - Repository fix implementation

### External Documentation
- [DefiLlama ETF Dashboard](https://defillama.com/etfs) - Data source for scraping
- [Farside Investors](https://farside.co.uk/) - Original data provider for ETF flows
- [Selenium Documentation](https://www.selenium.dev/documentation/) - Web automation framework
- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) - HTML parsing

### Technical References
- [Selenium Python Bindings](https://selenium-python.readthedocs.io/) - Selenium with Python
- [WebDriver Manager](https://github.com/SergeyPirogov/webdriver_manager) - Auto ChromeDriver management
- [Cloudflare Bypass Techniques](https://github.com/VeNoMouS/cloudscraper) - Alternative to Selenium
- [Azure Functions with Chrome](https://github.com/Azure/azure-functions-docker) - Running Chrome in Functions

### Web Scraping Best Practices
- **Respectful Scraping**: Add 2-3 second delays between requests
- **User-Agent**: Use realistic browser user agent string
- **robots.txt**: Check site's robots.txt before scraping (DefiLlama allows crawling)
- **Error Handling**: Always have fallback when scraping fails
- **Legal Compliance**: Public data, non-commercial use, proper attribution

### Data Source Information
- **DefiLlama**: Open-source DeFi analytics platform
- **Farside Investors**: UK-based investment research firm specializing in ETF flow data
- **Data Frequency**: Updated daily (end of trading day)
- **Coverage**: US-listed Bitcoin and Ethereum ETFs
- **Accuracy**: Industry-standard source used by professional traders

### Azure Deployment Resources
- [Azure Functions Linux Containers](https://learn.microsoft.com/en-us/azure/azure-functions/functions-create-function-linux-custom-image)
- [Azure Container Instances](https://learn.microsoft.com/en-us/azure/container-instances/)
- [Chrome Headless Shell](https://github.com/Azure/azure-functions-docker/tree/dev/host/4/bullseye/amd64/python)

### Future Enhancements
- Consider using cloudscraper library for lighter-weight Cloudflare bypass
- Implement caching layer to reduce scraping frequency if needed
- Add data validation by comparing DefiLlama with alternative sources
- Explore DefiLlama API if they release official ETF endpoints
- Monitor ETF coverage expansion (DefiLlama may add more ETFs over time)
