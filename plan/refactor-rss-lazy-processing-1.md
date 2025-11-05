---
goal: Optimize RSS News Processing with Lazy Evaluation and Cross-Feed Sorting
version: 1.0
date_created: 2025-11-05
last_updated: 2025-11-05
owner: CryptoMorningReports Team
status: 'Phase 4 Complete'
tags: ['refactor', 'performance', 'news', 'ollama', 'rss']
---

# Introduction

![Status: Phase 4 Complete](https://img.shields.io/badge/status-Phase%204%20Complete-brightgreen)

This plan addresses a critical performance bottleneck in the RSS news processing pipeline. Currently, the system processes up to 60 articles with Ollama (10 per feed × 6 feeds) even though only 10 relevant articles are needed for final Gemini analysis. Articles are not sorted by date across feeds, leading to potential processing of older articles while newer ones are ignored.

**Current Problem (Evidence from Production Logs):**
```
2025-11-05 15:47:57 - 17:13:04 (1 hour 25 minutes total processing)
- Processed 26 articles across 4 different feeds
- Article 1: 461.07s (7.7 minutes) - relevant: True (0.80)
- Article 2: 578.84s (9.6 minutes) - relevant: False (0.30) ❌ WASTED
- Article 3: 347.89s (5.8 minutes) - relevant: True (0.70)
- Article 4: 640.85s (10.7 minutes) - relevant: False (0.30) ❌ WASTED
- Article 5: 663.92s (11.1 minutes) - relevant: False (0.20) ❌ WASTED
- Article 6: 282.28s (4.7 minutes) - relevant: True (0.70)
... and 20 more articles (many irrelevant)

Total: ~85 minutes spent, only 10 relevant articles found
Wasted: ~60% of processing time on irrelevant articles
```

**Issues Identified:**
- Ollama processes up to 10 articles per feed independently (6 feeds = 60 articles max)
- Articles are NOT sorted by date across all feeds before processing
- No early stopping when enough relevant articles are found
- Processing time: 26 articles × ~3-11 minutes each = 85+ minutes of Ollama processing
- User only needs 10 articles (`NEWS_ARTICLE_LIMIT=10`)
- Many irrelevant articles processed (relevance: 0.00-0.30) that are never used

**Desired Behavior:**
- Fetch all RSS entries from all feeds
- Sort ALL articles by published date (newest first) across all sources
- Process articles ONE BY ONE with Ollama until 10 RELEVANT articles are found
- Stop immediately when target is reached
- Expected savings: Process 10-15 articles instead of 26-60 (40-75% time reduction)
- Estimated time: 30-60 minutes instead of 85+ minutes

## 1. Requirements & Constraints

### Requirements

#### Daily Report Requirements

- **REQ-001**: System must fetch RSS entries from all feeds before any Ollama processing
- **REQ-002**: All unprocessed articles must be sorted by published date (newest first) across all feeds
- **REQ-003**: Ollama processing must stop when `NEWS_ARTICLE_LIMIT` relevant articles are found
- **REQ-004**: Already-cached articles must be skipped (preserve existing behavior)
- **REQ-005**: Articles older than 24 hours must be filtered out (preserve existing behavior)
- **REQ-006**: Each processed article must be cached immediately (preserve existing behavior)
- **REQ-007**: System must maintain backward compatibility with existing cache structure
- **REQ-008**: Processing progress must be logged with relevant/target counts (enhance existing behavior)
- **REQ-009**: Must support configurable target for relevant articles via `NEWS_ARTICLE_LIMIT` environment variable (default: 10)
- **REQ-010**: Must handle feed parsing failures gracefully without blocking other feeds

#### Current Report Requirements (Symbol-Specific)

- **REQ-011**: Current report must use symbol-specific filtering when fetching articles
- **REQ-012**: Articles for current report must be filtered by symbols mentioned in article
- **REQ-013**: Current report must support a separate article limit via `CURRENT_REPORT_ARTICLE_LIMIT` environment variable (default: 3-5)
- **REQ-014**: Symbol-specific article fetching must still benefit from the cross-feed sorted cache
- **REQ-015**: `fetch_and_cache_articles_for_symbol()` must use the optimized lazy processing pipeline
- **REQ-016**: Current report must only show articles where the symbol is explicitly mentioned in `symbols` list
- **REQ-017**: Symbol-specific filtering should happen AFTER articles are cached (not during Ollama processing)

### Constraints

- **CON-001**: Must not break existing article caching mechanism
- **CON-002**: Must preserve all existing article metadata (source, symbols, relevance_score, etc.)
- **CON-003**: Cannot change the `CachedArticle` dataclass structure (used by other modules)
- **CON-004**: Must maintain existing error handling and logging patterns
- **CON-005**: RSS parsing and HTTP requests are synchronous (cannot parallelize easily)
- **CON-006**: Ollama processing is slow (3-11 minutes per article) - must minimize calls

### Guidelines

- **GUD-001**: Minimize code duplication - extract reusable functions
- **GUD-002**: Use descriptive variable names for clarity
- **GUD-003**: Add comprehensive logging at key decision points
- **GUD-004**: Preserve type hints for all function signatures
- **GUD-005**: Follow existing code style (dataclasses, error handling patterns)
- **GUD-006**: Log progress with format: `"🔄 Processing article {current}/{total} | {relevant_found}/{target} relevant found"`

### Patterns to Follow

- **PAT-001**: Use dataclasses for structured data (e.g., `RSSEntry`, `ProcessingResult`)
- **PAT-002**: Early return pattern for filtering logic
- **PAT-003**: Progress logging with `app_logger.info(f"🔄 Processing {index}/{total}...")`
- **PAT-004**: Environment variable configuration via `os.environ.get()` with defaults
- **PAT-005**: Generator pattern for lazy evaluation where applicable
- **PAT-006**: Per-feed error handling to prevent cascade failures

## 2. Implementation Steps

### Implementation Phase 1: Data Structure Preparation

- GOAL-001: Create intermediate data structures for cross-feed article aggregation

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Create `RSSEntry` dataclass in `rss_parser.py` to hold parsed RSS entry data (source, title, link, published_time, published_str, class_name, raw_entry) | ✅ | 2025-11-05 |
| TASK-002 | Add helper function `_parse_rss_entry()` to extract and normalize entry fields with published datetime | ✅ | 2025-11-05 |
| TASK-003 | Add helper function `_is_entry_processable()` to check if entry should be processed (not cached, within 24h) | ✅ | 2025-11-05 |
| TASK-004 | Add unit tests for `RSSEntry` creation and entry filtering logic | ✅ | 2025-11-05 |

### Implementation Phase 2: Cross-Feed Aggregation

- GOAL-002: Refactor RSS fetching to collect all entries before processing

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-005 | Refactor `get_news()` to use two-stage processing: (1) collect entries, (2) process sorted entries | ✅ | 2025-11-05 |
| TASK-006 | Create `_collect_all_rss_entries()` function that fetches from all feeds and returns list of `RSSEntry` objects | ✅ | 2025-11-05 |
| TASK-007 | Implement per-feed error handling in `_collect_all_rss_entries()` to prevent one feed failure from blocking others | ✅ | 2025-11-05 |
| TASK-008 | Sort collected entries by `published_time` (newest first) before processing | ✅ | 2025-11-05 |
| TASK-009 | Add logging to show total entries collected and how many from each source | ✅ | 2025-11-05 |

### Implementation Phase 3: Lazy Processing with Early Stopping

- GOAL-003: Implement incremental processing that stops when target relevant articles are found

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-010 | Add `TARGET_RELEVANT_ARTICLES` configuration via environment variable `NEWS_ARTICLE_LIMIT` (default: 10 for daily reports) | ✅ | 2025-11-05 |
| TASK-011 | Create `_process_entries_until_target()` function that iterates sorted entries and stops at target | ✅ | 2025-11-05 |
| TASK-012 | Update `_process_feed_entry()` to work with `RSSEntry` dataclass instead of raw feedparser entry | ✅ | 2025-11-05 |
| TASK-013 | Implement counter for relevant articles found and exit loop when target reached | ✅ | 2025-11-05 |
| TASK-014 | Add enhanced progress logging: `"🔄 Processing article {current}/{total_processed} ({current_source}) | {relevant_found}/{target} relevant found | Elapsed: {elapsed}s"` | ✅ | 2025-11-05 |
| TASK-015 | Add final summary logging: `"✅ Completed: Processed {total_processed}/{total_available} articles in {total_time}s, found {relevant_count}/{target} relevant (saved {time_saved}s)"` | ✅ | 2025-11-05 |

### Implementation Phase 4: Current Report Integration

- GOAL-004: Integrate symbol-specific filtering for current reports

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-016 | Add `CURRENT_REPORT_ARTICLE_LIMIT` environment variable configuration (default: 3) | ✅ | 2025-11-05 |
| TASK-017 | Update `fetch_and_cache_articles_for_symbol()` in `article_cache.py` to leverage optimized `get_news()` pipeline | ✅ | 2025-11-05 |
| TASK-018 | Ensure symbol-specific filtering happens AFTER cache lookup (filter from already-processed articles) | ✅ | 2025-11-05 |
| TASK-019 | Update `current_report.py` to respect `CURRENT_REPORT_ARTICLE_LIMIT` when formatting articles | |  |
| TASK-020 | Add logging in `current_report.py`: `"Found {total} cached articles for {symbol}, using top {limit}"` | |  |
| TASK-021 | Test that current report gets newest relevant articles for requested symbol from the shared cache | ✅ | 2025-11-05 |

### Implementation Phase 5: Optimization and Cleanup

- GOAL-005: Remove obsolete code and optimize remaining functions

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-022 | Remove `MAX_RELEVANT_ARTICLES` constant (replaced by `NEWS_ARTICLE_LIMIT` config) | |  |
| TASK-023 | Refactor `fetch_rss_news()` to use new architecture or mark as deprecated | |  |
| TASK-024 | Update `get_news()` return value documentation to clarify it returns JSON of newly-cached relevant articles | |  |
| TASK-025 | Review and update all docstrings to reflect new behavior | |  |
| TASK-026 | Add performance timing logs (total time, avg time per article, estimated time saved) | |  |
| TASK-027 | Document `NEWS_ARTICLE_LIMIT` and `CURRENT_REPORT_ARTICLE_LIMIT` in `LOCAL_DEVELOPMENT.md` | |  |

### Implementation Phase 6: Testing and Validation

- GOAL-006: Ensure refactored system works correctly and achieves performance goals

### Implementation Phase 6: Testing and Validation

- GOAL-006: Ensure refactored system works correctly and achieves performance goals

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-028 | Create test fixture with mock RSS feeds containing 60 articles across 6 sources | |  |
| TASK-029 | Test that articles are sorted by date across all feeds (newest first) | |  |
| TASK-030 | Test early stopping: verify processing stops after finding target relevant articles | |  |
| TASK-031 | Test that cached articles are properly skipped | |  |
| TASK-032 | Test that articles older than 24h are filtered out | |  |
| TASK-033 | Test symbol-specific filtering for current report (articles with symbol in symbols list) | |  |
| TASK-034 | Test `CURRENT_REPORT_ARTICLE_LIMIT` configuration for current report | |  |
| TASK-035 | Test that current report gets articles from shared optimized cache | |  |
| TASK-036 | Measure and log actual performance improvement (articles processed before/after) | |  |
| TASK-037 | Integration test: Run full daily report generation and verify Gemini receives correct articles | |  |
| TASK-038 | Integration test: Run current report for multiple symbols and verify symbol-specific filtering | |  |
| TASK-039 | Performance regression test: Verify worst-case (all articles irrelevant) doesn't exceed current performance | |  |

## 3. Alternatives

### Alternative Approaches Considered

- **ALT-001**: **Parallel Processing with Async Ollama Calls**
  - **Description**: Use `asyncio` to process multiple articles in parallel with Ollama
  - **Pros**: Could speed up total processing time significantly if Ollama supports concurrency
  - **Cons**: Ollama client is synchronous; would require major refactoring; potential resource exhaustion; complexity increase; may overwhelm Ollama server
  - **Reason Not Chosen**: Lazy evaluation provides better performance gains with less complexity; current logs show 3-11 min per article suggests I/O or model bottleneck, not CPU

- **ALT-002**: **Pre-filter Articles by Keywords Before Ollama Processing**
  - **Description**: Use simple keyword matching (e.g., coin names, "price", "trading") to filter articles before calling Ollama
  - **Pros**: Very fast pre-filtering; reduces Ollama calls dramatically; could filter out 50%+ articles
  - **Cons**: May miss relevant articles with unconventional terminology; hard to maintain keyword list; less accurate than AI analysis
  - **Reason Not Chosen**: AI-based relevance scoring is more accurate; lazy evaluation achieves similar performance gains without accuracy loss

- **ALT-003**: **Process All Articles but Cache Irrelevant Ones with Lower Priority**
  - **Description**: Continue processing all articles but cache them with priority flags for future reuse
  - **Pros**: Builds comprehensive cache for future analysis; no articles "missed"
  - **Cons**: Doesn't solve the performance problem; still processes 26-60 articles unnecessarily; 85+ minutes wasted
  - **Reason Not Chosen**: Doesn't address the core issue of processing too many articles

- **ALT-004**: **Use Cheaper/Faster Model for Initial Relevance Filtering**
  - **Description**: Use a smaller Ollama model (e.g., llama3.2-1b) for first pass relevance check, then detailed model for selected articles
  - **Pros**: Could reduce total processing time with faster initial filtering
  - **Cons**: Requires managing multiple models; two-pass approach adds complexity; still processes many articles; may miss nuanced relevance
  - **Reason Not Chosen**: Lazy evaluation with date-sorting is simpler and more effective; adds model management overhead

- **ALT-005**: **Increase Ollama Performance with Model Caching/Quantization**
  - **Description**: Optimize Ollama configuration (quantization, caching, GPU acceleration)
  - **Pros**: Could reduce per-article processing time from 3-11 minutes to 1-3 minutes
  - **Cons**: Still processes too many articles; infrastructure changes required; doesn't address root cause
  - **Reason Not Chosen**: Should be done in addition to lazy evaluation, not instead of; doesn't solve "processing irrelevant articles" problem

## 4. Dependencies

### External Dependencies

- **DEP-001**: `feedparser` library - No changes required, existing usage sufficient
- **DEP-002**: `requests` library - No changes required, existing usage sufficient
- **DEP-003**: `beautifulsoup4` library - No changes required, existing usage sufficient

### Internal Dependencies

- **DEP-004**: `news/article_processor.py` - `process_article_with_ollama()` function (no changes needed)
- **DEP-005**: `news/article_cache.py` - `article_exists_in_cache()`, `save_article_to_cache()` (no changes needed)
- **DEP-006**: `news/symbol_detector.py` - `detect_symbols_in_text()` function (no changes needed)
- **DEP-007**: `shared_code/ollama_client.py` - Ollama client (no changes needed, but consider optimization separately)
- **DEP-008**: `infra/configuration.py` - May need to add `get_target_relevant_articles()` helper

### Configuration Dependencies

- **DEP-009**: `NEWS_ARTICLE_LIMIT` environment variable - Used in `daily_report.py` for daily report article limit (default: 10)
- **DEP-010**: `CURRENT_REPORT_ARTICLE_LIMIT` environment variable - NEW: Used in `current_report.py` for symbol-specific report article limit (default: 3)
- **DEP-011**: `ARTICLE_CACHE_ENABLED` environment variable - Existing, controls caching behavior (no changes)

## 5. Files

### Files to Modify

- **FILE-001**: `news/rss_parser.py`
  - Add `RSSEntry` dataclass
  - Refactor `get_news()` for two-stage processing
  - Add `_collect_all_rss_entries()` function
  - Add `_process_entries_until_target()` function
  - Update helper functions to work with `RSSEntry`
  - Remove/deprecate `MAX_RELEVANT_ARTICLES` constant
  - Enhance logging with progress tracking
  - Support configurable target via `NEWS_ARTICLE_LIMIT` env var

- **FILE-002**: `news/article_cache.py`
  - Update `fetch_and_cache_articles_for_symbol()` to leverage optimized `get_news()` pipeline
  - Ensure symbol filtering happens efficiently after cache lookup
  - Add support for `CURRENT_REPORT_ARTICLE_LIMIT` when returning symbol-specific articles
  - Document that function now benefits from cross-feed sorted cache

- **FILE-003**: `reports/daily_report.py`
  - No structural changes required
  - Verify that `get_news()` is called correctly (line 90)
  - Ensure `NEWS_ARTICLE_LIMIT` is properly used in `_collect_relevant_news()` (line 252)
  - Consider adding timing logs around `get_news()` call
  - Verify behavior with new optimized processing

- **FILE-004**: `reports/current_report.py`
  - Add `CURRENT_REPORT_ARTICLE_LIMIT` configuration reading (default: 3)
  - Update article fetching to respect the new limit (around line 450)
  - Add logging to show how many articles found vs limit applied
  - Update `format_articles_for_prompt()` to truncate to limit if needed
  - Document that it now benefits from shared optimized cache

- **FILE-005**: `infra/configuration.py` (optional)
  - Add `get_news_article_limit()` helper function (returns int from `NEWS_ARTICLE_LIMIT`, default: 10)
  - Add `get_current_report_article_limit()` helper function (returns int from `CURRENT_REPORT_ARTICLE_LIMIT`, default: 3)
  - Centralize configuration reading for article limits

- **FILE-006**: `LOCAL_DEVELOPMENT.md`
  - Document `NEWS_ARTICLE_LIMIT` environment variable (default: 10, used for daily report)
  - Document `CURRENT_REPORT_ARTICLE_LIMIT` environment variable (default: 3, used for current report per symbol)
  - Explain the difference and when each is used
  - Returns `int(os.environ.get("NEWS_ARTICLE_LIMIT", "10"))`

### Files to Review (No Changes Expected)

- **FILE-007**: `news/article_processor.py` - Verify Ollama processing works with new flow
- **FILE-008**: `news/news_agent.py` - Verify `get_relevant_cached_articles()` still works correctly
- **FILE-009**: `shared_code/telegram/formatting_utils.py` - Verify article formatting functions work correctly

### New Files (if needed)

- **FILE-010**: `tests/test_rss_lazy_processing.py` - Unit tests for new lazy processing logic
- **FILE-011**: `tests/test_symbol_filtering.py` - Unit tests for symbol-specific article filtering
- **FILE-012**: `tests/fixtures/mock_rss_feeds.json` - Test data with 60+ mock articles

## 6. Testing

### Unit Tests

- **TEST-001**: Test `RSSEntry` dataclass creation with various RSS entry formats
- **TEST-002**: Test `_parse_rss_entry()` with valid and invalid RSS entries
- **TEST-003**: Test `_is_entry_processable()` filters cached articles correctly
- **TEST-004**: Test `_is_entry_processable()` filters articles older than 24h
- **TEST-005**: Test `_collect_all_rss_entries()` aggregates entries from multiple feeds
- **TEST-006**: Test `_collect_all_rss_entries()` handles feed parsing errors gracefully
- **TEST-007**: Test articles are sorted by published date (newest first) across all feeds
- **TEST-008**: Test `_process_entries_until_target()` stops after finding target relevant articles
- **TEST-009**: Test `_process_entries_until_target()` processes all articles if target not reached
- **TEST-010**: Test progress logging includes correct counts and elapsed time

### Integration Tests

- **TEST-011**: Test full `get_news()` flow with mock RSS feeds (60 articles, mixed relevance)
- **TEST-012**: Verify only newest articles are processed when target is reached early
- **TEST-013**: Verify all processed articles are cached correctly
- **TEST-014**: Test that `get_relevant_cached_articles()` returns correct articles after processing
- **TEST-015**: Test `daily_report.py` integration - verify Gemini receives correct article count
- **TEST-016**: Test with mixed scenarios: some feeds failing, some succeeding

### Performance Tests

- **TEST-017**: Measure articles processed before refactor (baseline: 26-60 articles from logs)
- **TEST-018**: Measure articles processed after refactor (target: 10-15 articles)
- **TEST-019**: Measure total processing time before/after refactor (baseline: 85+ minutes)
- **TEST-020**: Verify performance improvement is at least 40% reduction in Ollama calls
- **TEST-021**: Benchmark worst-case scenario (all articles irrelevant, must process all)

## 7. Risks & Assumptions

### Risks

- **RISK-001**: **Breaking existing cache compatibility**
  - **Likelihood**: Low
  - **Impact**: High
  - **Mitigation**: Preserve `CachedArticle` structure; extensive testing; gradual rollout

- **RISK-002**: **Date parsing inconsistencies across different RSS feeds**
  - **Likelihood**: Medium
  - **Impact**: Medium
  - **Mitigation**: Use existing `_resolve_published_time()` logic; add fallback handling; test with all 6 feeds

- **RISK-003**: **Not finding enough relevant articles**
  - **Likelihood**: Low (logs show ~40% relevance rate)
  - **Impact**: Medium
  - **Mitigation**: Process all available articles if target not reached; log warning; adjust target if needed

- **RISK-004**: **Performance regression if most articles are irrelevant**
  - **Likelihood**: Low (current logs show 40% relevance)
  - **Impact**: Low
  - **Mitigation**: Worst case matches current behavior (process up to 60 articles); benchmark worst-case

- **RISK-005**: **Feed failures causing empty article lists**
  - **Likelihood**: Medium
  - **Impact**: Low
  - **Mitigation**: Per-feed error handling; graceful degradation; logging; at least one feed usually succeeds

- **RISK-006**: **Missing newest articles due to incorrect sorting**
  - **Likelihood**: Low
  - **Impact**: High
  - **Mitigation**: Comprehensive sorting tests; validate published_time extraction; log sort order

### Assumptions

- **ASSUMPTION-001**: Most relevant articles are among the newest 20-30 articles across all feeds (validated by logs showing recent articles are more relevant)
- **ASSUMPTION-002**: Ollama processing time (3-11 minutes per article) is the primary bottleneck, not RSS fetching or content scraping (validated by logs)
- **ASSUMPTION-003**: Relevance scoring from Ollama is consistent enough to stop early (logs show clear differentiation: 0.00-0.30 vs 0.60-0.80)
- **ASSUMPTION-004**: 10 relevant articles is sufficient for quality Gemini analysis (current system configuration)
- **ASSUMPTION-005**: RSS feed publish dates are reasonably accurate and consistent (needs validation)
- **ASSUMPTION-006**: Article cache cleanup (24h) runs regularly to prevent stale data
- **ASSUMPTION-007**: ~40% relevance rate observed in logs is typical (means ~15-25 articles needed to find 10 relevant)

## 8. Related Specifications / Further Reading

- **[Original RSS Caching Feature Plan](./feature-rss-article-caching-1.md)** - Initial article caching implementation
- **[Article Summarization Feature Plan](./feature-article-summarization-1.md)** - Ollama integration for article processing
- **[NEWS_ARTICLE_LIMIT Configuration](../LOCAL_DEVELOPMENT.md)** - Environment variable documentation
- **[Article Cache README](../news/README.md)** - Article caching architecture overview
- **[Ollama Client Documentation](../shared_code/ollama_client.py)** - Ollama integration details

---

## Implementation Notes

### Performance Expectations (Based on Production Logs)

**Current State (Baseline from 2025-11-05 logs):**
- 26 articles processed across 4 feeds in 85+ minutes
- Relevance rate: ~40% (10-11 relevant out of 26 processed)
- Per-article time: 44s - 664s (avg ~200s or 3.3 minutes)
- Total Ollama time: ~85 minutes for 26 articles
- Wasted time on irrelevant articles: ~51 minutes (60% of total)

**Expected State (After Refactor):**
- Process articles sorted by date until 10 relevant found
- With 40% relevance rate, expect to process ~15-25 articles total
- Estimated time: 15 articles × 3.3 min avg = ~50 minutes
- Or with early stopping optimization: 10-15 articles × 3.3 min = 33-50 minutes
- **Expected Improvement: 40-60% reduction in processing time**
- **Time saved: 35-52 minutes per daily report**

### Detailed Time Analysis from Logs

```
Feed 1 (6 articles): 2,974.03s (49.6 min) - 3 relevant, 3 irrelevant
Feed 2 (10 articles): 1,070.02s (17.8 min) - 2 relevant, 8 irrelevant
Feed 3 (4 articles): 867.58s (14.5 min) - 3 relevant, 1 irrelevant
Feed 4 (6 articles): Processing continues...

Problems visible:
- Feed 2 wasted 856s (14.3 min) on 8 irrelevant articles
- Feed 1 wasted 1,587s (26.5 min) on 3 irrelevant articles
- No cross-feed sorting (newer articles from Feed 4 processed after older ones from Feed 1-3)
```

### Migration Strategy

This is a refactoring task with no data migration required. The implementation should be:

1. **Phase 1-2 (Days 1-2)**: Implement new functions alongside existing code
   - Add `RSSEntry` dataclass and helper functions
   - Test individually without changing `get_news()` flow

2. **Phase 3 (Days 3-4)**: Implement lazy processing logic
   - Add `_process_entries_until_target()` function
   - Add configuration and logging

3. **Phase 4 (Day 5)**: Switch to new processing flow
   - Refactor `get_news()` to use new functions
   - Test in development environment
   - Monitor performance metrics

4. **Phase 5 (Days 6-7)**: Testing and validation
   - Run integration tests
   - Compare performance with baseline logs
   - Deploy to production with monitoring

5. **Phase 6 (Day 8)**: Cleanup and optimization
   - Remove deprecated code after validation
   - Monitor production performance for 24-48 hours

### Rollback Plan

If issues arise after deployment:

1. **Immediate Rollback** (< 5 minutes):
   - Revert changes to `news/rss_parser.py`
   - System will fall back to original behavior (process 10 per feed)
   - No data loss - cached articles remain intact

2. **Gradual Rollback** (if partial issues):
   - Keep new sorting logic but disable early stopping
   - Adjust `TARGET_RELEVANT_ARTICLES` to higher value
   - Monitor and tune

3. **Validation After Rollback**:
   - Check daily report still generates correctly
   - Verify Gemini receives expected articles
   - Monitor Ollama processing times

### Current Report Integration Notes

The current report (`current_report.py`) uses `fetch_and_cache_articles_for_symbol()` which:

**Current Behavior:**
- Line 450: Calls `fetch_and_cache_articles_for_symbol(symbol_name, hours=24)`
- This internally calls `get_news()` to refresh RSS feeds
- Then filters cached articles by symbol
- Returns ALL articles mentioning the symbol (no limit)

**New Behavior After Refactor:**
- `get_news()` will use optimized lazy processing (stop at 10 relevant articles globally)
- Symbol-specific filtering happens AFTER articles are cached
- Current report respects `CURRENT_REPORT_ARTICLE_LIMIT` (default: 3 articles per symbol)
- Benefits from shared cache without re-processing articles

**Key Advantages:**
1. Current report no longer triggers expensive Ollama processing (uses shared cache)
2. Symbol-specific reports get newest relevant articles for that symbol
3. Configurable limit prevents overwhelming AI with too many articles
4. Multiple current reports can run without duplicating Ollama work

**Example Flow:**
```
Daily Report (morning):
  get_news() → Process 15 articles → Find 10 relevant → Cache all 15

Current Report for BTC (afternoon):
  fetch_and_cache_articles_for_symbol("BTC") →
    Check cache (15 articles already processed) →
    Filter by symbol (5 mention BTC) →
    Apply limit (return top 3 newest for BTC) →
    NO Ollama processing needed!

Current Report for ETH (afternoon):
  fetch_and_cache_articles_for_symbol("ETH") →
    Check cache (same 15 articles) →
    Filter by symbol (4 mention ETH) →
    Apply limit (return top 3 newest for ETH) →
    NO Ollama processing needed!
```

### Success Criteria

The refactoring is considered successful if:

1. ✅ Processing time reduced by at least 40% (from 85 min to < 50 min)
2. ✅ Only 10-25 articles processed (vs 26-60 currently)
3. ✅ Articles sorted by date across all feeds
4. ✅ Processing stops when 10 relevant articles found for daily report
5. ✅ Current report gets up to 3 newest articles per symbol from shared cache
6. ✅ No breaking changes to article caching or Gemini analysis
7. ✅ All existing tests pass
8. ✅ Production logs show improvement within 24 hours
9. ✅ Current reports run faster (cache hits instead of Ollama processing)

### Monitoring and Metrics

After deployment, monitor:

**Daily Report Metrics:**
- **Articles processed per run**: Target 10-25 (vs 26-60 baseline)
- **Total processing time**: Target < 50 min (vs 85+ min baseline)
- **Relevant article ratio**: Should remain ~40%
- **Cache hit rate**: Should increase (reusing recent articles)
- **Error rate**: Should remain low (< 5%)
- **Early stop triggers**: Count how often target is reached before processing all articles

**Current Report Metrics:**
- **Cache hit rate**: Target > 95% (should rarely trigger new Ollama processing)
- **Articles returned per symbol**: Should respect `CURRENT_REPORT_ARTICLE_LIMIT` (default: 3)
- **Response time**: Target < 5 seconds (just cache lookup + filtering)
- **Symbol filtering accuracy**: Verify only articles with requested symbol are returned
- **Freshness**: Verify articles are from the newest processed batch

**Configuration Monitoring:**
- `NEWS_ARTICLE_LIMIT`: Default 10, track if users adjust this
- `CURRENT_REPORT_ARTICLE_LIMIT`: Default 3, track if users adjust this
- Correlation between limits and AI analysis quality