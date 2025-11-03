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

- **Unify** all Telegram sending and formatting logic in `shared_code/telegram/` package
- **Abstract** format selection (HTML vs MarkdownV2) with easy switching via configuration
- **Eliminate** code duplication across daily, weekly, and current reports
- **Refactor** nested formatting functions to reusable module-level utilities
- **Standardize** message formatting with consistent emoji usage, article formatting, and indicator displays
- **Organize** code into a well-structured package with clear separation of concerns

The end result will be a clean, maintainable telegram package with:
- `constants.py` - All configuration constants
- `formatters.py` - Formatter classes and factory
- `sending.py` - Message/document sending functions
- `formatting_utils.py` - Formatting utilities for indicators and articles
- `text_processing.py` - Text processing and conversion utilities
- `__init__.py` - Public API exports

Reports can import from `shared_code.telegram` as before, with a simple configuration flag to switch between HTML and MarkdownV2 formats.

## 1. Requirements & Constraints

**Requirements:**

- **REQ-001**: All reports (daily, weekly, current) must use the same telegram sending functions
- **REQ-002**: Support both HTML and MarkdownV2 parse modes with easy configuration switching
- **REQ-003**: Format selection must be controlled by a single configuration variable (e.g., `TELEGRAM_PARSE_MODE` env var)
- **REQ-004**: All telegram utilities must be organized in `shared_code/telegram/` package
- **REQ-005**: Public API must be accessible via `shared_code.telegram` imports (backward compatible)
- **REQ-006**: Article formatting must be consistent across all reports that use news articles
- **REQ-007**: Technical indicator formatting (RSI, price, funding rate) must use consistent emojis and thresholds
- **REQ-008**: All existing tests must pass after refactoring
- **REQ-009**: Backward compatibility: existing reports should continue to work during migration
- **REQ-010**: Each module file should have a single, clear responsibility (constants, formatters, sending, etc.)

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
- **GUD-006**: Each module file should be < 300 lines when possible
- **GUD-007**: Use `__init__.py` to define public API, keep internal helpers private

**Patterns to Follow:**

- **PAT-001**: Strategy Pattern - Format selection via configuration
- **PAT-002**: Factory Pattern - Create formatters based on parse_mode
- **PAT-003**: Single Responsibility - Each formatter does one thing well
- **PAT-004**: Separation of Concerns - Formatting logic separate from report generation

## 2. Implementation Steps

### Phase 1: Preparation & Analysis ✅ COMPLETED

**GOAL-001**: Audit existing telegram usage and establish baseline tests

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Document all current telegram sending locations (daily_report.py, weekly_report.py, current_report.py, utils.py, send_current_report.py) | ✅ | 2025-11-03 |
| TASK-002 | Create snapshot tests for current telegram message outputs to verify no regressions | ✅ | 2025-11-03 |
| TASK-003 | Identify all nested formatting functions in current_report.py and current_data_table.py | ✅ | 2025-11-03 |
| TASK-004 | List all magic numbers and thresholds (RSI 70/30, article lengths 100/500) to be extracted | ✅ | 2025-11-03 |
| TASK-005 | Review existing test coverage in ``tests/test_telegram_utils.py`` | ✅ | 2025-11-03 |

**Phase 1 Deliverables**:
- ✅ `plan/telegram-phase1-analysis.md` - Detailed analysis document
- ✅ `plan/telegram-phase1-summary.md` - Phase completion summary
- ✅ `tests/test_telegram_baseline.py` - Baseline test reference
- ✅ All existing tests passing (7/7)

**Status**: READY FOR PHASE 2
| TASK-006 | Design package structure: determine what goes in each module file (constants, formatters, sending, formatting_utils, text_processing) | | |

### Phase 2: Create Package Structure & Constants

**GOAL-002**: Set up the `shared_code/telegram/` package structure with constants

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-007 | Create `shared_code/telegram/` directory | | |
| TASK-008 | Create `shared_code/telegram/__init__.py` with initial imports (empty, will populate later) | | |
| TASK-009 | Create `shared_code/telegram/constants.py` with all constants: `MAX_TELEGRAM_LENGTH`, `MAX_DOCUMENT_SIZE`, `ARTICLE_TITLE_MAX_LENGTH`, `ARTICLE_CONTENT_PREVIEW_LENGTH`, `RSI_OVERBOUGHT`, `RSI_OVERSOLD`, `FUNDING_RATE_HIGH`, `FUNDING_RATE_LOW`, `EMOJI_MAP` | | |
| TASK-010 | Update current `shared_code/telegram.py` to import constants from new package (temporary bridge for compatibility) | | |
| TASK-011 | Write unit tests for constants module (verify values are correct) | | |

### Phase 3: Create Formatter Abstraction Layer

**GOAL-003**: Build formatters module with format-agnostic interface

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-012 | Create `shared_code/telegram/formatters.py` file | | |
| TASK-013 | Define `TelegramFormatter` Protocol with methods: `format_header()`, `format_bold()`, `format_italic()`, `format_code()`, `format_code_block()`, `format_link()`, `format_underline()` | | |
| TASK-014 | Implement `HTMLFormatter` class with all format methods outputting Telegram-compatible HTML | | |
| TASK-015 | Implement `MarkdownV2Formatter` class with all format methods outputting properly escaped MarkdownV2 | | |
| TASK-016 | Create `get_formatter(parse_mode: str) -> TelegramFormatter` factory function | | |
| TASK-017 | Add `TELEGRAM_PARSE_MODE` environment variable support in `infra/configuration.py` (default: "HTML") | | |
| TASK-018 | Write comprehensive unit tests for both formatter implementations | | |

### Phase 4: Create Text Processing Module

**GOAL-004**: Move text processing utilities to dedicated module

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-019 | Create `shared_code/telegram/text_processing.py` file | | |
| TASK-020 | Move `enforce_markdown_v2()` from current `telegram.py` to `text_processing.py` | | |
| TASK-021 | Move `sanitize_html()` from current `telegram.py` to `text_processing.py` | | |
| TASK-022 | Move `smart_split()` and `_extend_to_close_tag()` from current `telegram.py` to `text_processing.py` | | |
| TASK-023 | Move `convert_markdown_to_telegram_html()` from `current_report.py` to `text_processing.py` (rename to `convert_ai_markdown_to_telegram_html()`) | | |
| TASK-024 | Update imports in text_processing.py to use `constants` module | | |
| TASK-025 | Write unit tests for all text processing functions | | |

### Phase 5: Create Formatting Utilities Module

**GOAL-005**: Extract and consolidate formatting utilities

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-026 | Create `shared_code/telegram/formatting_utils.py` file | | |
| TASK-027 | Extract `enforce_emoji_usage()` from `current_report.py` nested function to `formatting_utils.py` as `enhance_text_with_emojis(text: str, emoji_map: dict \| None = None) -> str` | | |
| TASK-028 | Move `format_articles_for_html()` from `current_report.py` to `formatting_utils.py` as `format_articles_for_telegram(articles, formatter)` | | |
| TASK-029 | Extract `format_rsi_with_emoji()` from `current_data_table.py` to `formatting_utils.py` as module-level function | | |
| TASK-030 | Create `format_price_with_currency(price: float \| None, decimals: int = 4, prefix: str = "$") -> str` utility | | |
| TASK-031 | Create `format_funding_rate_with_emoji(rate: float \| None) -> str` utility | | |
| TASK-032 | Update all formatting utils to import from `constants` module | | |
| TASK-033 | Write comprehensive unit tests for all formatting utilities | | |

### Phase 6: Create Sending Module

**GOAL-006**: Move sending functions to dedicated module

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-034 | Create `shared_code/telegram/sending.py` file | | |
| TASK-035 | Move `send_telegram_message()` and helper functions from current `telegram.py` to `sending.py` | | |
| TASK-036 | Move `send_telegram_document()` and helper functions from current `telegram.py` to `sending.py` | | |
| TASK-037 | Move `try_send_report_with_html_or_markdown()` from current `telegram.py` to `sending.py` | | |
| TASK-038 | Update `send_telegram_message()` to optionally use formatter abstraction internally | | |
| TASK-039 | Update `try_send_report_with_html_or_markdown()` to respect `TELEGRAM_PARSE_MODE` config | | |
| TASK-040 | Add optional `parse_mode_override` parameter to sending functions for testing flexibility | | |
| TASK-041 | Update imports in sending.py to use other package modules (constants, text_processing, formatters) | | |
| TASK-042 | Write unit tests for sending module (mock requests) | | |

### Phase 7: Update Package Public API

**GOAL-007**: Define clean public API in `__init__.py`

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-043 | Update `shared_code/telegram/__init__.py` to import and re-export all public functions from submodules | | |
| TASK-044 | Define `__all__` list with all public API symbols | | |
| TASK-045 | Add module-level docstring explaining package organization | | |
| TASK-046 | Verify backward compatibility: imports like `from shared_code.telegram import send_telegram_message` still work | | |
| TASK-047 | Delete old `shared_code/telegram.py` file after verifying all functionality is migrated | | |

### Phase 8: Remove Duplicates & Clean Up Source Files

**GOAL-008**: Remove duplicate code and update existing files

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-048 | Delete duplicate `send_telegram_message()` from `utils.py` (lines 23-33) | | |
| TASK-049 | Remove `convert_markdown_to_telegram_html()` from `current_report.py` | | |
| TASK-050 | Remove `format_articles_for_html()` from `current_report.py` | | |
| TASK-051 | Remove `enforce_emoji_usage()` nested function from `current_report.py` | | |
| TASK-052 | Remove `format_rsi_with_emoji()` nested function from `current_data_table.py` | | |
| TASK-053 | Update imports in `current_report.py` to use new telegram package | | |
| TASK-054 | Update imports in `current_data_table.py` to use new telegram package | | |

### Phase 9: Refactor Current Report

**GOAL-009**: Update `current_report.py` to use telegram package

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-055 | Update imports in `current_report.py` to use telegram package functions | | |
| TASK-056 | Update AI-generated markdown conversion to use new text processing utilities | | |
| TASK-057 | Update article formatting to use new formatting utilities | | |
| TASK-058 | Test current report generation with refactored code | | |

### Phase 10: Refactor Technical Analysis Reports

**GOAL-010**: Update `current_data_table.py` to use telegram package

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-059 | Update imports in `current_data_table.py` to use telegram package | | |
| TASK-060 | Refactor `format_current_data_for_telegram_html()` to accept formatter parameter and be format-agnostic | | |
| TASK-061 | Rename to `format_current_data_for_telegram(symbol_data, formatter)` for clarity | | |
| TASK-062 | Test current data table formatting with both HTML and MarkdownV2 | | |

### Phase 11: Refactor Daily & Weekly Reports

**GOAL-011**: Update daily and weekly reports to use telegram package with format switching

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-063 | Review current HTML formatting in daily report sections | | |
| TASK-064 | Update all `send_telegram_message()` calls in daily_report.py to use telegram package | | |
| TASK-065 | Replace hardcoded `parse_mode="HTML"` with `TELEGRAM_PARSE_MODE` config in daily_report.py | | |
| TASK-066 | Update weekly_report.py to use telegram package | | |
| TASK-067 | Replace hardcoded `parse_mode="HTML"` with `TELEGRAM_PARSE_MODE` config in weekly_report.py | | |
| TASK-068 | Test that both reports work with HTML and MarkdownV2 formats | | |

### Phase 12: Configuration & Format Switching

**GOAL-012**: Implement easy format switching via configuration

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-069 | Add `TELEGRAM_PARSE_MODE` to `.env.example` with documentation | | |
| TASK-070 | Add `TELEGRAM_PARSE_MODE` to `local.settings.json` template | | |
| TASK-071 | Create helper function `get_telegram_config()` in `infra/configuration.py` that returns formatter, parse_mode, etc. | | |
| TASK-072 | Update all reports to call `get_telegram_config()` instead of hardcoding format | | |
| TASK-073 | Add logging to show which format is being used on startup | | |

### Phase 13: Testing & Validation

**GOAL-013**: Comprehensive testing to ensure no regressions and both formats work

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-074 | Update existing tests in `tests/test_telegram_utils.py` to work with new package structure | | |
| TASK-075 | Add integration tests for formatter abstraction layer | | |
| TASK-076 | Test current report with `TELEGRAM_PARSE_MODE=HTML` | | |
| TASK-077 | Test current report with `TELEGRAM_PARSE_MODE=MarkdownV2` | | |
| TASK-078 | Test daily report with both formats | | |
| TASK-079 | Test weekly report with both formats | | |
| TASK-080 | Verify message splitting still works correctly with both formats | | |
| TASK-081 | Test edge cases: very long messages, special characters, emojis | | |
| TASK-082 | Validate that all reports send successfully to actual Telegram (staging environment) | | |
| TASK-083 | Run full test suite: `pytest tests/ -v --cov=shared_code.telegram` | | |

### Phase 14: Documentation & Cleanup

**GOAL-014**: Document new architecture and clean up obsolete code

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-084 | Update each module file's docstring with clear explanation of its purpose | | |
| TASK-085 | Add inline documentation for `TelegramFormatter` protocol/class | | |
| TASK-086 | Create `docs/TELEGRAM_FORMATTING.md` guide explaining package structure, format switching, and formatter usage | | |
| TASK-087 | Update README.md with new `TELEGRAM_PARSE_MODE` configuration option | | |
| TASK-088 | Remove any leftover commented-out code from refactoring | | |
| TASK-089 | Run linters (ruff) and fix any new issues | | |
| TASK-090 | Run type checker (pyright) and fix any type issues | | |
| TASK-091 | Create migration guide for any future telegram code additions | | |

## 3. Alternatives

**Alternative Approaches Considered:**

- **ALT-001**: Keep everything in a single `telegram.py` file
  - **Rejected**: Would create 600-800+ line file; violates Single Responsibility Principle; hard to navigate and maintain; difficult to test individual components
  
- **ALT-002**: Keep HTML and MarkdownV2 in separate modules (`telegram_html.py`, `telegram_markdown.py`)
  - **Rejected**: Would duplicate sending logic; harder to switch between formats; more files to maintain
  
- **ALT-003**: Use string template approach (Jinja2) for formatting
  - **Rejected**: Overkill for simple formatting; adds dependency; harder to test individual formatters
  
- **ALT-004**: Keep nested formatting functions as-is and just unify sending
  - **Rejected**: Doesn't solve code duplication; nested functions aren't reusable across reports
  
- **ALT-005**: Use markdown library (like `python-markdown`) for conversion
  - **Rejected**: Telegram markdown is non-standard; would still need custom converter; adds dependency
  
- **ALT-006**: Keep format hardcoded per report (some always HTML, some always Markdown)
  - **Rejected**: Doesn't allow easy A/B testing of formats; inconsistent user experience

- **ALT-007**: Create even more granular modules (e.g., separate files for each formatter class)
  - **Rejected**: Over-engineering; 5-6 module files is optimal balance; more files add navigation overhead without significant benefit

## 4. Dependencies

**Internal Dependencies:**

- **DEP-001**: `infra/configuration.py` - Need to add `get_telegram_config()` helper
- **DEP-002**: `infra/telegram_logging_handler.py` - May need logging updates for format selection
- **DEP-003**: All report modules depend on `shared_code/telegram/` package refactor
- **DEP-004**: Package internal dependencies: `formatters.py` imports `constants.py`, `sending.py` imports `constants.py` and `text_processing.py`, etc.

**External Dependencies:**

- **DEP-005**: `requests` library - Already used for Telegram API calls
- **DEP-006**: Environment variable system (.env, local.settings.json) - For `TELEGRAM_PARSE_MODE`
- **DEP-007**: Existing test framework (pytest) - For validation
- **DEP-008**: Python 3.10+ for Protocol support (already required)

**Breaking Changes:**

- **DEP-009**: Import paths change from `shared_code.telegram` to `shared_code.telegram.*` for internal imports (but public API via `__init__.py` remains backward compatible)
- **DEP-010**: Function signatures will change (adding formatter parameters) - may affect any external code calling these functions
- **DEP-011**: Removing `utils.py:send_telegram_message()` - need to verify nothing external uses it
- **DEP-012**: Old `shared_code/telegram.py` file will be deleted and replaced with package directory

## 5. Files

**Files to Modify:**

- **FILE-001**: `infra/configuration.py` - Add `get_telegram_config()` helper
- **FILE-002**: `.env.example` - Add `TELEGRAM_PARSE_MODE` documentation
- **FILE-003**: `local.settings.json` - Add `TELEGRAM_PARSE_MODE` setting
- **FILE-004**: `README.md` - Document new configuration option
- **FILE-005**: `reports/current_report.py` - Remove nested functions, update imports
- **FILE-006**: `reports/daily_report.py` - Update telegram calls, remove hardcoded parse_mode
- **FILE-007**: `reports/weekly_report.py` - Update telegram calls, remove hardcoded parse_mode
- **FILE-008**: `technical_analysis/reports/current_data_table.py` - Extract nested functions, use telegram package
- **FILE-009**: `tests/test_telegram_utils.py` - Update tests for new package structure

**Files to Delete:**

- **FILE-010**: `shared_code/telegram.py` - Will be replaced by `shared_code/telegram/` package
- **FILE-011**: `utils.py` - Remove duplicate `send_telegram_message()` function (lines 23-33) or delete entire file if nothing else remains

**New Files to Create (Package Structure):**

- **FILE-012**: `shared_code/telegram/__init__.py` - Package initialization and public API exports
- **FILE-013**: `shared_code/telegram/constants.py` - All constants (RSI thresholds, article lengths, emoji map, etc.)
- **FILE-014**: `shared_code/telegram/formatters.py` - TelegramFormatter protocol, HTMLFormatter, MarkdownV2Formatter, get_formatter()
- **FILE-015**: `shared_code/telegram/sending.py` - send_telegram_message(), send_telegram_document(), try_send_report_with_html_or_markdown()
- **FILE-016**: `shared_code/telegram/formatting_utils.py` - format_rsi_with_emoji(), format_articles_for_telegram(), enhance_text_with_emojis(), etc.
- **FILE-017**: `shared_code/telegram/text_processing.py` - convert_ai_markdown_to_telegram_html(), sanitize_html(), enforce_markdown_v2(), smart_split()

**New Documentation Files:**

- **FILE-018**: `docs/TELEGRAM_FORMATTING.md` - Developer guide for telegram package usage
- **FILE-019**: `docs/TELEGRAM_MIGRATION.md` - Migration guide from old structure to new package (optional)

## 6. Testing

**Unit Tests:**

- **TEST-001**: Test `constants.py` - verify all constants have expected values
- **TEST-002**: Test `HTMLFormatter` class - verify all format methods produce correct HTML tags
- **TEST-003**: Test `MarkdownV2Formatter` class - verify proper escaping of special characters
- **TEST-004**: Test `get_formatter()` factory - verify it returns correct formatter based on parse_mode
- **TEST-005**: Test `format_rsi_with_emoji()` - verify emoji selection based on thresholds
- **TEST-006**: Test `format_funding_rate_with_emoji()` - verify emoji selection
- **TEST-007**: Test `format_price_with_currency()` - verify price formatting with different decimals
- **TEST-008**: Test `format_articles_for_telegram()` - verify article truncation and formatting
- **TEST-009**: Test `enhance_text_with_emojis()` - verify emoji insertion in headers
- **TEST-010**: Test `convert_ai_markdown_to_telegram_html()` - verify markdown conversion
- **TEST-011**: Test `sanitize_html()` - verify HTML sanitization
- **TEST-012**: Test `enforce_markdown_v2()` - verify MarkdownV2 escaping
- **TEST-013**: Test `smart_split()` - verify message splitting logic
- **TEST-014**: Test package imports - verify `from shared_code.telegram import X` works for all public functions

**Integration Tests:**

- **TEST-015**: Test current report generation end-to-end with HTML format
- **TEST-016**: Test current report generation end-to-end with MarkdownV2 format
- **TEST-017**: Test daily report generation with both formats
- **TEST-018**: Test weekly report generation with both formats
- **TEST-019**: Test message splitting works correctly with both formats (messages > 4096 chars)
- **TEST-020**: Test cross-module dependencies (formatters using constants, sending using text_processing, etc.)

**Manual Testing:**

- **TEST-021**: Send test message to Telegram with HTML format, verify rendering
- **TEST-022**: Send test message to Telegram with MarkdownV2 format, verify rendering
- **TEST-023**: Toggle `TELEGRAM_PARSE_MODE` config and verify format switches correctly
- **TEST-024**: Verify emoji rendering in actual Telegram client
- **TEST-025**: Test very long messages (>4096 chars) split correctly in both formats
- **TEST-026**: Import functions from package in Python REPL to verify public API works

**Regression Tests:**

- **TEST-027**: Compare snapshot of current report output before/after refactor (should be identical when using same format)
- **TEST-028**: Verify all existing `tests/test_telegram_utils.py` tests still pass after migration
- **TEST-029**: Run full test suite: `pytest tests/ -v --cov=shared_code.telegram`
- **TEST-030**: Verify no broken imports across entire codebase: `python -m compileall .`

## 7. Risks & Assumptions

**Risks:**

- **RISK-001**: Breaking production daily reports during refactoring
  - **Mitigation**: Implement phase-by-phase with comprehensive testing after each phase; keep backward compatibility during migration
  
- **RISK-002**: MarkdownV2 escaping edge cases may cause message send failures
  - **Mitigation**: Extensive testing with special characters; fallback logic in `try_send_report_with_html_or_markdown()`
  
- **RISK-003**: Message splitting logic may behave differently with MarkdownV2 vs HTML
  - **Mitigation**: Test long messages thoroughly; update `smart_split()` if needed to handle both formats
  
- **RISK-004**: Formatter abstraction may add complexity and performance overhead
  - **Mitigation**: Keep formatters lightweight; profile performance if issues arise; formatters are simple string operations with minimal overhead
  
- **RISK-005**: Missing telegram sending locations (code we didn't find in analysis)
  - **Mitigation**: Use grep search to find ALL telegram imports and calls before starting

- **RISK-006**: Package structure might confuse developers unfamiliar with Python packages
  - **Mitigation**: Clear documentation in `docs/TELEGRAM_FORMATTING.md`; well-defined public API in `__init__.py`; migration guide

- **RISK-007**: Circular import issues between package modules
  - **Mitigation**: Careful dependency design (constants → formatters/text_processing → formatting_utils → sending); avoid cross-imports

**Assumptions:**

- **ASSUMPTION-001**: HTML format is currently preferred (based on current code)
- **ASSUMPTION-002**: Users prefer emoji-enhanced messages (current implementation uses them)
- **ASSUMPTION-003**: 4096 character limit is sufficient after smart splitting
- **ASSUMPTION-004**: RSI thresholds (70/30) and funding rate thresholds (±0.01) are correct and won't change frequently
- **ASSUMPTION-005**: All reports will eventually use the same format (determined by global config)
- **ASSUMPTION-006**: Telegram API will continue to support both HTML and MarkdownV2 parse modes
- **ASSUMPTION-007**: No external code depends on internal telegram formatting functions
- **ASSUMPTION-008**: Python package structure with 5-6 module files is manageable and won't over-complicate the codebase
- **ASSUMPTION-009**: Developers are familiar with Python package imports and `__init__.py` re-exports
- **ASSUMPTION-010**: Module files won't grow beyond 300 lines each, maintaining readability

## 8. Related Specifications / Further Reading

**Internal Documentation:**
- New `shared_code/telegram/` package structure
- Each module file's docstring (constants.py, formatters.py, sending.py, formatting_utils.py, text_processing.py)
- Existing `tests/test_telegram_utils.py` test cases
- Daily report generation flow in `reports/daily_report.py`

**Package Structure Reference:**
```
shared_code/telegram/
├── __init__.py              # Public API exports
├── constants.py             # Configuration constants
├── formatters.py            # Formatter classes (HTML, MarkdownV2)
├── sending.py               # Message/document sending
├── formatting_utils.py      # Indicator & article formatting
└── text_processing.py       # Text conversion & sanitization
```

**External Resources:**
- [Telegram Bot API - Formatting Options](https://core.telegram.org/bots/api#formatting-options)
- [Telegram Bot API - MarkdownV2 Style](https://core.telegram.org/bots/api#markdownv2-style)
- [Telegram Bot API - HTML Style](https://core.telegram.org/bots/api#html-style)
- [Telegram Bot API - sendMessage](https://core.telegram.org/bots/api#sendmessage)
- [Python Packages Documentation](https://docs.python.org/3/tutorial/modules.html#packages)
