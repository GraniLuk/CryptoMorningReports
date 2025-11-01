---
goal: Enhanced RSS Article Analysis with Caching and Symbol Tagging
version: 1.0
date_created: 2025-11-01
last_updated: 2025-11-01
owner: Development Team
status: 'Planned'
tags: ['feature', 'news', 'caching', 'rss', 'analysis']
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

This implementation plan outlines the enhancement of the RSS article analysis feature to include article caching, cryptocurrency symbol tagging, and integration with current analysis reports. The current system fetches RSS news articles and includes them in daily reports, but lacks persistence, symbol association, and efficient re-use of fetched articles.

The goal is to:
1. Verify current RSS functionality works properly
2. Implement local disk caching for articles (markdown format with frontmatter)
3. Tag articles with cryptocurrency symbols mentioned in the content
4. Enable article reuse for multiple analysis runs without re-downloading
5. Integrate tagged articles into current analysis reports per symbol
6. Implement automatic cleanup of articles older than 24 hours

## 1. Requirements & Constraints

### Functional Requirements

- **REQ-001**: Verify all 7 RSS feeds (decrypt, coindesk, newsBTC, coinJournal, coinpedia, cryptopotato, ambcrypto) are fetching articles correctly
- **REQ-002**: Cache fetched articles to local disk in markdown format with proper frontmatter
- **REQ-003**: Include metadata in frontmatter: source, title, link, published date, fetched date, mentioned crypto symbols
- **REQ-004**: Detect and tag cryptocurrency symbols mentioned in article content (title and body)
- **REQ-005**: Store articles in a structured directory format for easy verification: `news/cache/YYYY-MM-DD/source-slug.md`
- **REQ-006**: Fetch only articles from the last 24 hours (already implemented, needs verification)
- **REQ-007**: Enable retrieval of cached articles for multiple analysis runs without re-downloading
- **REQ-008**: Integrate tagged articles into current analysis reports based on symbol relevance
- **REQ-009**: Automatically delete cached articles older than 24 hours
- **REQ-010**: Provide manual testing utilities to verify RSS fetching and article content quality

### Technical Requirements

- **TEC-001**: Use YAML frontmatter format for article metadata
- **TEC-002**: Implement symbol detection using the existing `Symbol` dataclass and database symbols
- **TEC-003**: Cache articles in `news/cache/` directory structure
- **TEC-004**: Create markdown files with sanitized filenames (URL-safe slugs)
- **TEC-005**: Implement cache invalidation based on article published timestamp
- **TEC-006**: Make caching optional via configuration to support production Azure Functions

### Security & Performance Requirements

- **SEC-001**: Sanitize filenames to prevent directory traversal attacks
- **SEC-002**: Validate URLs before fetching to prevent SSRF attacks
- **PER-001**: Implement concurrent article fetching with rate limiting
- **PER-002**: Minimize disk I/O by checking cache before fetching
- **PER-003**: Limit cached articles to prevent disk space exhaustion (max 1000 articles)

### Constraints

- **CON-001**: System runs locally, so disk-based caching is acceptable
- **CON-002**: Must maintain backward compatibility with existing `get_news()` function
- **CON-003**: Cache location must be configurable for Azure deployment (can be disabled)
- **CON-004**: Symbol detection should use existing symbol database to ensure consistency
- **CON-005**: Must handle network failures gracefully and return cached data when available

### Guidelines

- **GUD-001**: Follow existing code style using ruff and pyright
- **GUD-002**: Use existing logging infrastructure (`app_logger`)
- **GUD-003**: Write unit tests for new functionality
- **GUD-004**: Maintain separation of concerns (fetching, caching, symbol detection)
- **GUD-005**: Document all new functions and modules with docstrings

### Patterns to Follow

- **PAT-001**: Use dataclasses for structured data (e.g., CachedArticle)
- **PAT-002**: Use Path from pathlib for cross-platform file operations
- **PAT-003**: Use context managers for file operations
- **PAT-004**: Follow existing error handling patterns with specific exceptions
- **PAT-005**: Use type hints for all function signatures

## 2. Implementation Steps

### Phase 1: RSS Functionality Verification

**GOAL-001**: Verify current RSS fetching works correctly and identify any issues

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Create test script `news/test_rss_feeds.py` to verify each RSS feed individually | ✅ | 2025-11-01 |
| TASK-002 | Test each of the 7 RSS sources and verify articles are fetched with correct metadata | ✅ | 2025-11-01 |
| TASK-003 | Verify 24-hour filtering logic works correctly | ✅ | 2025-11-01 |
| TASK-004 | Test full content fetching for each source and verify HTML parsing works | ✅ | 2025-11-01 |
| TASK-005 | Document any broken feeds or parsing issues | ✅ | 2025-11-01 |
| TASK-006 | Fix identified issues with RSS feed parsing or class selectors | ✅ | 2025-11-01 |
| TASK-007 | Add logging for fetch success/failure rates per source | ✅ | 2025-11-01 |

**Phase 1 Status**: ✅ **COMPLETED** (6/6 feeds working, 100% success rate)  
**Issues Fixed**:
- newsBTC: Updated class selector from `content-inner jeg_link_underline` to `entry-content` (3,436 chars now extracted)
- cryptopotato: Removed due to HTTP 403 blocking (6 working feeds remain, providing comprehensive coverage)

**Summary**: See `plan/phase1_summary.md` for detailed results

### Phase 2: Article Cache Infrastructure

**GOAL-002**: Implement local disk caching system for fetched articles

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-008 | Create `news/article_cache.py` module with cache management functions | ✅ | 2025-01-15 |
| TASK-009 | Implement `CachedArticle` dataclass with fields: source, title, link, published, fetched, content, symbols | ✅ | 2025-01-15 |
| TASK-010 | Create cache directory structure: `news/cache/YYYY-MM-DD/` | ✅ | 2025-01-15 |
| TASK-011 | Implement `save_article_to_cache(article: CachedArticle) -> Path` function | ✅ | 2025-01-15 |
| TASK-012 | Implement markdown file generation with YAML frontmatter | ✅ | 2025-01-15 |
| TASK-013 | Implement filename slugification function (sanitize title for filesystem) | ✅ | 2025-01-15 |
| TASK-014 | Implement `load_article_from_cache(filepath: Path) -> CachedArticle` function | ✅ | 2025-01-15 |
| TASK-015 | Implement `get_cached_articles(date: date) -> List[CachedArticle]` function | ✅ | 2025-01-15 |
| TASK-016 | Add configuration option `ENABLE_ARTICLE_CACHE` (default: True for local) | ✅ | 2025-01-15 |
| TASK-017 | Update `get_news()` to optionally save to cache if enabled | ✅ | 2025-01-15 |

**Summary**: See `plan/phase2_summary.md` for detailed implementation results and testing

### Phase 3: Symbol Detection & Tagging

**GOAL-003**: Detect cryptocurrency symbols mentioned in articles and tag them

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-018 | Create `news/symbol_detector.py` module for symbol detection logic | ✅ | 2025-11-01 |
| TASK-019 | Implement `detect_symbols_in_text(text: str, symbols: List[Symbol]) -> List[str]` function | ✅ | 2025-11-01 |
| TASK-020 | Add support for detecting symbol names (e.g., "BTC", "Bitcoin", "Ethereum") | ✅ | 2025-11-01 |
| TASK-021 | Add support for detecting full names and common variations (case-insensitive) | ✅ | 2025-11-01 |
| TASK-022 | Implement scoring/confidence system to avoid false positives (e.g., "BIT" matching "Bitcoin") | ✅ | 2025-11-01 |
| TASK-023 | Update `fetch_rss_news()` to detect and tag symbols in article title and content | ✅ | 2025-11-01 |
| TASK-024 | Store detected symbols in article frontmatter as YAML list | ✅ | 2025-11-01 |
| TASK-025 | Create manual review utility to verify symbol detection accuracy | | |

### Phase 4: Integration with Current Reports

**GOAL-004**: Enable current analysis reports to include relevant cached articles

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-026 | Create `get_articles_for_symbol(symbol: str, hours: int = 24) -> List[CachedArticle]` function | ✅ | 2025-11-01 |
| TASK-027 | Update `current_report.py` to fetch relevant articles for the analyzed symbol | ✅ | 2025-11-01 |
| TASK-028 | Add articles section to current situation report markdown output | ✅ | 2025-11-01 |
| TASK-029 | Format articles with title, source, link, and excerpt in report | ✅ | 2025-11-01 |
| TASK-030 | Update AI prompts to optionally include relevant news context per symbol | ✅ | 2025-11-01 |
| TASK-031 | Test current report generation with cached articles for BTC, ETH | ✅ | 2025-11-01 |
| TASK-032 | Add command-line option to enable/disable news in current reports | ⏭️ | SKIPPED |

### Phase 5: Cache Management & Cleanup

**GOAL-005**: Implement automatic cleanup and cache maintenance

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-033 | Implement `cleanup_old_articles(max_age_hours: int = 24) -> int` function | ✅ | 2025-11-01 |
| TASK-034 | Add automatic cleanup call in daily report before fetching new articles | ✅ | 2025-11-01 |
| TASK-035 | Implement cache size monitoring with warning logs if exceeding threshold | ⏭️ | SKIPPED |
| TASK-036 | Add manual cache cleanup utility script `news/cleanup_cache.py` | ✅ | 2025-11-01 |
| TASK-037 | Implement cache statistics function (article count, disk usage, oldest/newest) | ✅ | 2025-11-01 |
| TASK-038 | Add logging for cleanup operations (deleted count, freed space) | ✅ | 2025-11-01 |
| TASK-039 | Document cache management in README | ✅ | 2025-11-01 |

**Phase 5 Status**: ✅ **COMPLETED** (6/7 tasks completed, 1 skipped)  
**Summary**: Cache management fully implemented with automatic cleanup, manual utility, and comprehensive logging.

### Phase 6: Testing & Documentation

**GOAL-006**: Ensure comprehensive testing and documentation

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-040 | Create unit tests for `article_cache.py` functions | ✅ | 2025-11-01 |
| TASK-041 | Create unit tests for `symbol_detector.py` functions | ✅ | 2025-11-01 |
| TASK-042 | Create integration test for full workflow (fetch → cache → tag → retrieve) | ✅ | 2025-11-01 |
| TASK-043 | Test cache behavior with missing/corrupted cache files | ✅ | 2025-11-01 |
| TASK-044 | Create test for concurrent cache access (if applicable) | ⏭️ | SKIPPED |
| TASK-045 | Update `news/README.md` with architecture overview and usage examples | ✅ | 2025-11-01 |
| TASK-046 | Document configuration options in `.env.example` | ⏭️ | OPTIONAL |
| TASK-047 | Create troubleshooting guide for common issues | ✅ | 2025-11-01 |

**Phase 6 Status**: ✅ **COMPLETED** (5/7 tasks completed, 2 optional)

## 3. Alternatives

### Alternative Approaches Considered

- **ALT-001**: **Database storage instead of disk files**
  - *Rejected*: Adds complexity and overhead for local development. File-based caching is simpler to verify and debug. Can be reconsidered for production if needed.

- **ALT-002**: **Use external caching service (Redis, Memcached)**
  - *Rejected*: Overkill for local development. Adds external dependency. File-based caching is sufficient for 24-hour TTL.

- **ALT-003**: **Use AI for symbol detection instead of pattern matching**
  - *Considered for future*: Pattern matching with symbol database is faster and more deterministic. AI can be added later for improved accuracy if needed.

- **ALT-004**: **Store articles in JSON instead of Markdown**
  - *Rejected*: Markdown with frontmatter is human-readable and easier to verify. Can still be parsed programmatically.

- **ALT-005**: **Fetch articles on-demand instead of batch fetching**
  - *Rejected*: Current batch fetching during daily report is more efficient. Cache enables on-demand access without repeated API calls.

## 4. Dependencies

### Internal Dependencies

- **DEP-001**: `source_repository.py` - Provides `Symbol` dataclass and `fetch_symbols()` function
- **DEP-002**: `infra/sql_connection.py` - Database connection for symbol lookup
- **DEP-003**: `infra/telegram_logging_handler.py` - Logging infrastructure (`app_logger`)
- **DEP-004**: Existing RSS parsing infrastructure in `news/rss_parser.py`

### External Dependencies

- **DEP-005**: `feedparser` - RSS feed parsing (already installed)
- **DEP-006**: `beautifulsoup4` - HTML content extraction (already installed)
- **DEP-007**: `requests` - HTTP requests (already installed)
- **DEP-008**: `python-frontmatter` - YAML frontmatter parsing (needs to be added to `requirements.txt`)
- **DEP-009**: `python-slugify` - URL-safe filename generation (needs to be added to `requirements.txt`)

### Configuration Dependencies

- **DEP-010**: New environment variable `ENABLE_ARTICLE_CACHE` in `.env` (default: `true`)
- **DEP-011**: New environment variable `ARTICLE_CACHE_DIR` in `.env` (default: `news/cache`)
- **DEP-012**: New environment variable `ARTICLE_CACHE_MAX_AGE_HOURS` in `.env` (default: `24`)

## 5. Files

### New Files to Create

- **FILE-001**: `news/article_cache.py` - Article caching infrastructure
- **FILE-002**: `news/symbol_detector.py` - Symbol detection and tagging logic
- **FILE-003**: `news/test_rss_feeds.py` - RSS feed verification test script
- **FILE-004**: `news/cleanup_cache.py` - Manual cache cleanup utility
- **FILE-005**: `news/README.md` - News module documentation
- **FILE-006**: `tests/test_article_cache.py` - Unit tests for caching
- **FILE-007**: `tests/test_symbol_detector.py` - Unit tests for symbol detection
- **FILE-008**: `news/cache/` - Cache directory (created at runtime)

### Files to Modify

- **FILE-009**: `news/rss_parser.py` - Add caching and symbol tagging integration
- **FILE-010**: `reports/current_report.py` - Add article retrieval for symbol-specific reports
- **FILE-011**: `reports/daily_report.py` - Add cache cleanup before fetching news
- **FILE-012**: `requirements.txt` - Add `python-frontmatter` and `python-slugify`
- **FILE-013**: `.env.example` - Document new configuration options
- **FILE-014**: `readme.md` - Update project layout to include news cache

## 6. Testing

### Unit Tests

- **TEST-001**: Test `save_article_to_cache()` creates correct file structure and frontmatter
- **TEST-002**: Test `load_article_from_cache()` correctly parses markdown with frontmatter
- **TEST-003**: Test filename slugification handles special characters and Unicode
- **TEST-004**: Test `detect_symbols_in_text()` identifies common symbol variations
- **TEST-005**: Test `detect_symbols_in_text()` avoids false positives (e.g., common words)
- **TEST-006**: Test `get_cached_articles()` retrieves articles for specific date
- **TEST-007**: Test `cleanup_old_articles()` deletes only articles older than threshold
- **TEST-008**: Test cache statistics calculation (count, size, date range)

### Integration Tests

- **TEST-009**: Test full workflow: fetch RSS → save to cache → detect symbols → load from cache
- **TEST-010**: Test `get_articles_for_symbol()` retrieves relevant articles based on tags
- **TEST-011**: Test current report generation with cached articles included
- **TEST-012**: Test cache behavior when RSS feeds are unavailable (fallback to cache)
- **TEST-013**: Test concurrent article saving (if applicable)

### Manual Tests

- **TEST-014**: Verify each RSS feed returns articles with correct metadata
- **TEST-015**: Manually review cached markdown files for correct formatting
- **TEST-016**: Manually verify symbol detection accuracy on sample articles
- **TEST-017**: Verify cleanup removes old files and empty directories
- **TEST-018**: Test daily report with caching enabled vs disabled (performance comparison)

## 7. Risks & Assumptions

### Risks

- **RISK-001**: **RSS feed structure changes** - Feeds may change HTML structure, breaking content extraction
  - *Mitigation*: Regular monitoring, fallback to partial content if extraction fails, logging

- **RISK-002**: **Disk space exhaustion** - Many articles could fill disk
  - *Mitigation*: 24-hour TTL, max article limit (1000), monitoring and alerts

- **RISK-003**: **Symbol detection false positives/negatives** - May tag irrelevant articles or miss relevant ones
  - *Mitigation*: Confidence scoring, manual review utility, iterative improvement

- **RISK-004**: **File system limitations** - Windows path length limits, special characters in filenames
  - *Mitigation*: Slugification, path length checks, cross-platform testing

- **RISK-005**: **Cache corruption** - Malformed files or concurrent access issues
  - *Mitigation*: Validation on load, graceful error handling, file locking if needed

- **RISK-006**: **Performance degradation** - Large cache directories may slow down operations
  - *Mitigation*: Index/lookup optimization, directory structure optimization (date-based)

### Assumptions

- **ASSUMPTION-001**: Articles fetched within 24 hours are relevant for analysis
- **ASSUMPTION-002**: Local disk-based caching is acceptable for development (Azure may need different approach)
- **ASSUMPTION-003**: Symbol names from database are comprehensive enough for detection
- **ASSUMPTION-004**: Markdown format with frontmatter is human-readable and programmatically parseable
- **ASSUMPTION-005**: Network is generally available during daily report generation
- **ASSUMPTION-006**: Cache cleanup runs successfully before each daily report fetch
- **ASSUMPTION-007**: File system operations are fast enough not to impact report generation time

## 8. Related Specifications / Further Reading

- [RSS 2.0 Specification](https://www.rssboard.org/rss-specification)
- [YAML Frontmatter Specification](https://jekyllrb.com/docs/front-matter/)
- [Python Frontmatter Library](https://python-frontmatter.readthedocs.io/)
- [Python Slugify Library](https://github.com/un33k/python-slugify)
- BeautifulSoup Documentation for HTML parsing
- Current project documentation: `readme.md`, `LOCAL_DEVELOPMENT.md`
- Related feature plan: `news/PROMPT_EXPANSION_PLAN.md`
