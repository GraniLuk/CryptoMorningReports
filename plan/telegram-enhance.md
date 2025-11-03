---
goal: Refactor and Unify Telegram Support Across All Reports with Format Abstraction
version: 1.0
date_created: 2025-11-03
last_updated: 2025-11-03
owner: Development Team
status: Planned
tags: [refactor, telegram, architecture, cleanup, feature]
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

This plan outlines the refactoring of Telegram messaging support across the CryptoMorningReports application. Currently, telegram-related code is scattered across multiple files with duplicated functionality, nested helper functions, and inconsistent formatting approaches. This refactor will:

- **Unify** all Telegram sending and formatting logic in `shared_code/telegram.py`
- **Abstract** format selection (HTML vs MarkdownV2) with easy switching via configuration
- **Eliminate** code duplication across daily, weekly, and current reports
- **Refactor** nested formatting functions to reusable module-level utilities
- **Standardize** message formatting with consistent emoji usage, article formatting, and indicator displays

The end result will be a clean, maintainable telegram module that all reports can use with a simple configuration flag to switch between HTML and MarkdownV2 formats.

## 1. Requirements & Constraints

**Requirements:**

- **REQ-001**: All reports (daily, weekly, current) must use the same telegram sending functions
- **REQ-002**: Support both HTML and MarkdownV2 parse modes with easy configuration switching
- **REQ-003**: Format selection must be controlled by a single configuration variable (e.g., `TELEGRAM_PARSE_MODE` env var)
- **REQ-004**: All telegram formatting utilities must be in `shared_code/telegram.py`
- **REQ-005**: Article formatting must be consistent across all reports that use news articles
- **REQ-006**: Technical indicator formatting (RSI, price, funding rate) must use consistent emojis and thresholds
- **REQ-007**: All existing tests must pass after refactoring
- **REQ-008**: Backward compatibility: existing reports should continue to work during migration

**Constraints:**

- **CON-001**: Telegram message length limit is 4096 characters (must respect `smart_split` logic)
- **CON-002**: Telegram HTML only supports specific tags: `<b>`, `<i>`, `<u>`, `<s>`, `<code>`, `<pre>`, `<a>`
- **CON-003**: MarkdownV2 requires escaping special characters: `_*[]()~``>#+-=|{}.!`
- **CON-004**: Cannot break existing daily report generation (it's in production)
- **CON-005**: Must maintain current logging and error handling behavior

**Guidelines:**

- **GUD-001**: Follow DRY principle - no duplicate telegram code
- **GUD-002**: Use type hints for all public functions
- **GUD-003**: Keep formatting functions pure (no side effects)
- **GUD-004**: Extract magic numbers to named constants
- **GUD-005**: Prefer composition over inheritance for formatters

**Patterns to Follow:**

- **PAT-001**: Strategy Pattern - Format selection via configuration
- **PAT-002**: Factory Pattern - Create formatters based on parse_mode
- **PAT-003**: Single Responsibility - Each formatter does one thing well
- **PAT-004**: Separation of Concerns - Formatting logic separate from report generation

## 2. Implementation Steps

### Phase 1: Preparation & Analysis

**GOAL-001**: Audit existing telegram usage and establish baseline tests

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Document all current telegram sending locations (daily_report.py, weekly_report.py, current_report.py, utils.py, send_current_report.py) | | |
| TASK-002 | Create snapshot tests for current telegram message outputs to verify no regressions | | |
| TASK-003 | Identify all nested formatting functions in current_report.py and current_data_table.py | | |
| TASK-004 | List all magic numbers and thresholds (RSI 70/30, article lengths 100/500) to be extracted | | |
| TASK-005 | Review existing test coverage in `tests/test_telegram_utils.py` | | |

### Phase 2: Create Core Formatting Abstraction Layer

**GOAL-002**: Build a format-agnostic interface for telegram message formatting

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-006 | Create `TelegramFormatter` base class/protocol in `telegram.py` with methods: `format_header()`, `format_bold()`, `format_italic()`, `format_code()`, `format_link()` | | |
| TASK-007 | Implement `HTMLFormatter` class that outputs Telegram-compatible HTML | | |
| TASK-008 | Implement `MarkdownV2Formatter` class that outputs properly escaped MarkdownV2 | | |
| TASK-009 | Create `get_formatter(parse_mode: str) -> TelegramFormatter` factory function | | |
| TASK-010 | Add `TELEGRAM_PARSE_MODE` environment variable support (default: "HTML") | | |
| TASK-011 | Write unit tests for both formatter implementations | | |

### Phase 3: Extract and Refactor Formatting Utilities

**GOAL-003**: Move all formatting functions to `telegram.py` as module-level reusable utilities

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-012 | Extract constants to top of `telegram.py`: `ARTICLE_TITLE_MAX_LENGTH=100`, `ARTICLE_CONTENT_PREVIEW_LENGTH=500`, `RSI_OVERBOUGHT=70`, `RSI_OVERSOLD=30`, `FUNDING_RATE_HIGH=0.01`, `FUNDING_RATE_LOW=-0.01` | | |
| TASK-013 | Move `convert_markdown_to_telegram_html()` from `current_report.py` to `telegram.py` (rename to `convert_ai_markdown_to_telegram_html()` for clarity) | | |
| TASK-014 | Extract `enforce_emoji_usage()` from `current_report.py` nested function to `telegram.py` as `enhance_text_with_emojis(text: str, emoji_map: dict) -> str` with configurable emoji map | | |
| TASK-015 | Move `format_articles_for_html()` from `current_report.py` to `telegram.py` as `format_articles_for_telegram(articles, formatter)` using formatter abstraction | | |
| TASK-016 | Extract `format_rsi_with_emoji()` from `current_data_table.py` nested function to `telegram.py` as module-level function | | |
| TASK-017 | Create `format_price_with_currency(price: float, decimals: int = 4) -> str` utility function | | |
| TASK-018 | Create `format_funding_rate_with_emoji(rate: float) -> str` utility function | | |
| TASK-019 | Write unit tests for all extracted formatting functions | | |

### Phase 4: Unify Sending Logic & Remove Duplicates

**GOAL-004**: Consolidate all telegram sending to use `shared_code/telegram.py` exclusively

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-020 | Delete duplicate `send_telegram_message()` from `utils.py` (lines 23-33) | | |
| TASK-021 | Update `send_telegram_message()` in `telegram.py` to use formatter abstraction internally | | |
| TASK-022 | Update `try_send_report_with_html_or_markdown()` to respect `TELEGRAM_PARSE_MODE` config instead of trying both | | |
| TASK-023 | Add optional `parse_mode_override` parameter to sending functions for testing flexibility | | |
| TASK-024 | Ensure all sending functions use consistent parameter names and signatures | | |

### Phase 5: Refactor Current Report

**GOAL-005**: Update `current_report.py` to use unified telegram utilities

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-025 | Remove `convert_markdown_to_telegram_html()` from `current_report.py` (now in telegram.py) | | |
| TASK-026 | Remove `format_articles_for_html()` from `current_report.py` (now in telegram.py) | | |
| TASK-027 | Remove `enforce_emoji_usage()` nested function from `generate_crypto_situation_report()` | | |
| TASK-028 | Update imports to use new telegram utilities: `from shared_code.telegram import convert_ai_markdown_to_telegram_html, format_articles_for_telegram, enhance_text_with_emojis` | | |
| TASK-029 | Replace direct `try_send_report_with_html_or_markdown()` call with new unified approach | | |
| TASK-030 | Update AI-generated markdown conversion to use formatter abstraction | | |
| TASK-031 | Keep `format_articles_for_prompt()` in current_report.py (AI-specific, not telegram formatting) | | |

### Phase 6: Refactor Technical Analysis Reports

**GOAL-006**: Update `current_data_table.py` to use unified telegram utilities

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-032 | Remove `format_rsi_with_emoji()` nested function from `format_current_data_for_telegram_html()` | | |
| TASK-033 | Import and use `format_rsi_with_emoji()` from `telegram.py` | | |
| TASK-034 | Import and use `format_price_with_currency()` from `telegram.py` | | |
| TASK-035 | Import and use `format_funding_rate_with_emoji()` from `telegram.py` | | |
| TASK-036 | Refactor `format_current_data_for_telegram_html()` to accept formatter parameter and be format-agnostic | | |
| TASK-037 | Rename to `format_current_data_for_telegram(symbol_data, formatter)` for clarity | | |

### Phase 7: Refactor Daily Report

**GOAL-007**: Update `daily_report.py` to use unified telegram utilities with format switching

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-038 | Review current HTML formatting in daily report sections (analyze_daily_rsi, analyze_moving_averages, analyze_derivatives, etc.) | | |
| TASK-039 | Update all `send_telegram_message()` calls to use formatter abstraction | | |
| TASK-040 | Replace hardcoded `parse_mode="HTML"` with `TELEGRAM_PARSE_MODE` config | | |
| TASK-041 | Refactor HTML building in report sections to use formatter methods instead of string concatenation | | |
| TASK-042 | Add format switching capability - test that MarkdownV2 output works correctly | | |
| TASK-043 | Update inline formatting (e.g., `<pre>` blocks) to use `formatter.format_code_block()` | | |

### Phase 8: Refactor Weekly Report

**GOAL-008**: Update `weekly_report.py` to use unified telegram utilities

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-044 | Update `send_telegram_message()` call to use formatter abstraction | | |
| TASK-045 | Replace hardcoded `parse_mode="HTML"` with `TELEGRAM_PARSE_MODE` config | | |
| TASK-046 | Verify weekly report formatting works with both HTML and MarkdownV2 | | |

### Phase 9: Configuration & Format Switching

**GOAL-009**: Implement easy format switching via configuration

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-047 | Add `TELEGRAM_PARSE_MODE` to `.env.example` with documentation | | |
| TASK-048 | Add `TELEGRAM_PARSE_MODE` to `local.settings.json` template | | |
| TASK-049 | Create helper function `get_telegram_config()` in `infra/configuration.py` that returns formatter, parse_mode, etc. | | |
| TASK-050 | Update all reports to call `get_telegram_config()` instead of hardcoding format | | |
| TASK-051 | Add logging to show which format is being used on startup | | |

### Phase 10: Testing & Validation

**GOAL-010**: Comprehensive testing to ensure no regressions and both formats work

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-052 | Run existing tests: `pytest tests/test_telegram_utils.py -v` | | |
| TASK-053 | Add integration tests for formatter abstraction layer | | |
| TASK-054 | Test current report with `TELEGRAM_PARSE_MODE=HTML` | | |
| TASK-055 | Test current report with `TELEGRAM_PARSE_MODE=MarkdownV2` | | |
| TASK-056 | Test daily report with both formats | | |
| TASK-057 | Test weekly report with both formats | | |
| TASK-058 | Verify message splitting still works correctly with both formats | | |
| TASK-059 | Test edge cases: very long messages, special characters, emojis | | |
| TASK-060 | Validate that all reports send successfully to actual Telegram (staging environment) | | |

### Phase 11: Documentation & Cleanup

**GOAL-011**: Document new architecture and clean up obsolete code

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-061 | Update `shared_code/telegram.py` module docstring with new architecture overview | | |
| TASK-062 | Add inline documentation for `TelegramFormatter` protocol/class | | |
| TASK-063 | Create `docs/TELEGRAM_FORMATTING.md` guide explaining format switching and formatter usage | | |
| TASK-064 | Update README.md with new `TELEGRAM_PARSE_MODE` configuration option | | |
| TASK-065 | Remove any leftover commented-out code from refactoring | | |
| TASK-066 | Run linters (ruff) and fix any new issues | | |
| TASK-067 | Run type checker (pyright) and fix any type issues | | |

## 3. Alternatives

**Alternative Approaches Considered:**

- **ALT-001**: Keep HTML and MarkdownV2 in separate modules (`telegram_html.py`, `telegram_markdown.py`)
  - **Rejected**: Would duplicate sending logic; harder to switch between formats; more files to maintain
  
- **ALT-002**: Use string template approach (Jinja2) for formatting
  - **Rejected**: Overkill for simple formatting; adds dependency; harder to test individual formatters
  
- **ALT-003**: Keep nested formatting functions as-is and just unify sending
  - **Rejected**: Doesn't solve code duplication; nested functions aren't reusable across reports
  
- **ALT-004**: Use markdown library (like `python-markdown`) for conversion
  - **Rejected**: Telegram markdown is non-standard; would still need custom converter; adds dependency
  
- **ALT-005**: Keep format hardcoded per report (some always HTML, some always Markdown)
  - **Rejected**: Doesn't allow easy A/B testing of formats; inconsistent user experience

## 4. Dependencies

**Internal Dependencies:**

- **DEP-001**: `infra/configuration.py` - Need to add `get_telegram_config()` helper
- **DEP-002**: `infra/telegram_logging_handler.py` - May need logging updates for format selection
- **DEP-003**: All report modules depend on `shared_code/telegram.py` refactor

**External Dependencies:**

- **DEP-004**: `requests` library - Already used for Telegram API calls
- **DEP-005**: Environment variable system (.env, local.settings.json) - For `TELEGRAM_PARSE_MODE`
- **DEP-006**: Existing test framework (pytest) - For validation

**Breaking Changes:**

- **DEP-007**: Function signatures will change (adding formatter parameters) - may affect any external code calling these functions
- **DEP-008**: Removing `utils.py:send_telegram_message()` - need to verify nothing external uses it

## 5. Files

**Files to Modify:**

- **FILE-001**: `shared_code/telegram.py` - Major refactoring: add formatter abstraction, move formatting utilities, update sending functions
- **FILE-002**: `reports/current_report.py` - Remove nested functions, update imports, use new utilities
- **FILE-003**: `reports/daily_report.py` - Update telegram calls to use formatter abstraction, remove hardcoded parse_mode
- **FILE-004**: `reports/weekly_report.py` - Update telegram calls, remove hardcoded parse_mode
- **FILE-005**: `technical_analysis/reports/current_data_table.py` - Extract nested functions, use telegram utilities
- **FILE-006**: `infra/configuration.py` - Add `get_telegram_config()` helper
- **FILE-007**: `.env.example` - Add `TELEGRAM_PARSE_MODE` documentation
- **FILE-008**: `local.settings.json` - Add `TELEGRAM_PARSE_MODE` setting
- **FILE-009**: `README.md` - Document new configuration option

**Files to Delete/Remove Code From:**

- **FILE-010**: `utils.py` - Remove duplicate `send_telegram_message()` function (lines 23-33)

**New Files to Create:**

- **FILE-011**: `docs/TELEGRAM_FORMATTING.md` - Developer guide for telegram formatting
- **FILE-012**: `tests/test_telegram_formatters.py` - Tests for new formatter abstraction (optional, could add to existing test file)

## 6. Testing

**Unit Tests:**

- **TEST-001**: Test `HTMLFormatter` class - verify all format methods produce correct HTML tags
- **TEST-002**: Test `MarkdownV2Formatter` class - verify proper escaping of special characters
- **TEST-003**: Test `get_formatter()` factory - verify it returns correct formatter based on parse_mode
- **TEST-004**: Test `format_rsi_with_emoji()` - verify emoji selection based on thresholds
- **TEST-005**: Test `format_funding_rate_with_emoji()` - verify emoji selection
- **TEST-006**: Test `format_articles_for_telegram()` - verify article truncation and formatting
- **TEST-007**: Test `enhance_text_with_emojis()` - verify emoji insertion in headers
- **TEST-008**: Test `convert_ai_markdown_to_telegram_html()` - verify markdown conversion

**Integration Tests:**

- **TEST-009**: Test current report generation end-to-end with HTML format
- **TEST-010**: Test current report generation end-to-end with MarkdownV2 format
- **TEST-011**: Test daily report generation with both formats
- **TEST-012**: Test weekly report generation with both formats
- **TEST-013**: Test message splitting works correctly with both formats (messages > 4096 chars)

**Manual Testing:**

- **TEST-014**: Send test message to Telegram with HTML format, verify rendering
- **TEST-015**: Send test message to Telegram with MarkdownV2 format, verify rendering
- **TEST-016**: Toggle `TELEGRAM_PARSE_MODE` config and verify format switches correctly
- **TEST-017**: Verify emoji rendering in actual Telegram client
- **TEST-018**: Test very long messages (>4096 chars) split correctly in both formats

**Regression Tests:**

- **TEST-019**: Compare snapshot of current report output before/after refactor (should be identical when using same format)
- **TEST-020**: Verify all existing `tests/test_telegram_utils.py` tests still pass
- **TEST-021**: Run full test suite: `pytest tests/ -v --cov=shared_code.telegram`

## 7. Risks & Assumptions

**Risks:**

- **RISK-001**: Breaking production daily reports during refactoring
  - **Mitigation**: Implement phase-by-phase with comprehensive testing after each phase; keep backward compatibility during migration
  
- **RISK-002**: MarkdownV2 escaping edge cases may cause message send failures
  - **Mitigation**: Extensive testing with special characters; fallback logic in `try_send_report_with_html_or_markdown()`
  
- **RISK-003**: Message splitting logic may behave differently with MarkdownV2 vs HTML
  - **Mitigation**: Test long messages thoroughly; update `smart_split()` if needed to handle both formats
  
- **RISK-004**: Formatter abstraction may add complexity and performance overhead
  - **Mitigation**: Keep formatters lightweight; profile performance if issues arise
  
- **RISK-005**: Missing telegram sending locations (code we didn't find in analysis)
  - **Mitigation**: Use grep search to find ALL telegram imports and calls before starting

**Assumptions:**

- **ASSUMPTION-001**: HTML format is currently preferred (based on current code)
- **ASSUMPTION-002**: Users prefer emoji-enhanced messages (current implementation uses them)
- **ASSUMPTION-003**: 4096 character limit is sufficient after smart splitting
- **ASSUMPTION-004**: RSI thresholds (70/30) and funding rate thresholds (±0.01) are correct and won't change frequently
- **ASSUMPTION-005**: All reports will eventually use the same format (determined by global config)
- **ASSUMPTION-006**: Telegram API will continue to support both HTML and MarkdownV2 parse modes
- **ASSUMPTION-007**: No external code depends on internal telegram formatting functions

## 8. Related Specifications / Further Reading

**Internal Documentation:**
- Current `shared_code/telegram.py` implementation
- Existing `tests/test_telegram_utils.py` test cases
- Daily report generation flow in `reports/daily_report.py`

**External Resources:**
- [Telegram Bot API - Formatting Options](https://core.telegram.org/bots/api#formatting-options)
- [Telegram Bot API - MarkdownV2 Style](https://core.telegram.org/bots/api#markdownv2-style)
- [Telegram Bot API - HTML Style](https://core.telegram.org/bots/api#html-style)
- [Telegram Bot API - sendMessage](https://core.telegram.org/bots/api#sendmessage)
