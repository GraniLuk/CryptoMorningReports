# Phase 1: Preparation & Analysis - Documentation

**Date Created**: 2025-11-03  
**Status**: In Progress  
**Goal**: Audit existing telegram usage and establish baseline tests

---

## TASK-001: Document All Current Telegram Sending Locations ✅

### Primary Telegram Module
**File**: `shared_code/telegram.py`
- **Functions**:
  - `send_telegram_message()` - Main sending function using requests library
  - `send_telegram_document()` - Sends files/documents to Telegram
  - `try_send_report_with_html_or_markdown()` - Fallback logic for HTML → MarkdownV2
  - `smart_split()` - Splits messages > 4096 characters
  - `sanitize_html()` - Cleans HTML for Telegram
  - `enforce_markdown_v2()` - Escapes MarkdownV2 special characters

### Duplicate Implementation (TO BE REMOVED)
**File**: `utils.py` (lines 23-33)
- **Function**: `send_telegram_message(telegram_token, chat_id, message)`
- **Issue**: Uses different library (`telegram.Bot` instead of `requests`)
- **Status**: Must be removed in Phase 4

### Report Modules Using Telegram

#### 1. Daily Report
**File**: `reports/daily_report.py`
- **Imports**: `from shared_code.telegram import send_telegram_document, send_telegram_message`
- **Usage**: Multiple `send_telegram_message()` calls with `parse_mode="HTML"` (hardcoded)
- **Issues**: 
  - No format abstraction
  - Hardcoded HTML format throughout
  - Direct HTML string concatenation

#### 2. Weekly Report
**File**: `reports/weekly_report.py`
- **Imports**: `from shared_code.telegram import send_telegram_message`
- **Usage**: Single `send_telegram_message()` call at line 53 with `parse_mode="HTML"`
- **Issues**: Hardcoded HTML format

#### 3. Current Report
**File**: `reports/current_report.py`
- **Imports**: `from shared_code.telegram import try_send_report_with_html_or_markdown`
- **Usage**: Calls `try_send_report_with_html_or_markdown()` after generating report
- **Issues**: 
  - Contains nested formatting functions (see TASK-003)
  - Contains custom markdown → HTML converter
  - Hardcoded emoji mapping

#### 4. Send Current Report Script
**File**: `send_current_report.py`
- **Imports**: `from shared_code.telegram import send_telegram_message`
- **Usage**: Sends simple text message for testing/manual triggers
- **Issues**: None (simple usage)

#### 5. Function App (Azure Functions Entry Point)
**File**: `function_app.py`
- **Imports**: `from shared_code.telegram import send_telegram_message`
- **Usage**: Used for sending error notifications and status updates
- **Issues**: None (simple usage)

### Summary Table

| File | Function Used | Parse Mode | Format | Priority |
|------|--------------|------------|--------|----------|
| `shared_code/telegram.py` | Core implementation | Both HTML & MarkdownV2 | - | N/A |
| `utils.py` | `send_telegram_message()` | None (plain text) | Duplicate | **HIGH - DELETE** |
| `reports/daily_report.py` | `send_telegram_message()` | Hardcoded HTML | Multiple calls | **HIGH - REFACTOR** |
| `reports/weekly_report.py` | `send_telegram_message()` | Hardcoded HTML | Single call | **MEDIUM - REFACTOR** |
| `reports/current_report.py` | `try_send_report_with_html_or_markdown()` | Both (fallback) | Complex | **HIGH - REFACTOR** |
| `send_current_report.py` | `send_telegram_message()` | HTML | Simple | **LOW - UPDATE IMPORT** |
| `function_app.py` | `send_telegram_message()` | HTML | Simple | **LOW - UPDATE IMPORT** |
| `technical_analysis/reports/current_data_table.py` | None (formats for telegram) | HTML | Nested functions | **HIGH - EXTRACT** |

---

## TASK-003: Identify All Nested Formatting Functions ✅

### 1. `format_rsi_with_emoji()` - NESTED IN current_data_table.py

**Location**: `technical_analysis/reports/current_data_table.py` (line ~323, nested inside `format_current_data_for_telegram_html()`)

**Current Implementation**:
```python
def format_rsi_with_emoji(rsi_value):
    rsi_overbought_threshold = 70
    rsi_oversold_threshold = 30
    if rsi_value is None:
        return "N/A"
    rsi_str = f"{rsi_value:.2f}"
    if rsi_value >= rsi_overbought_threshold:
        return f"🔴 {rsi_str} (Overbought)"
    if rsi_value <= rsi_oversold_threshold:
        return f"🟢 {rsi_str} (Oversold)"
    return f"🟡 {rsi_str}"
```

**Issues**:
- Nested inside another function, not reusable
- Hardcoded thresholds (70/30)
- No type hints

**Extraction Plan**:
- Move to `shared_code/telegram/formatting_utils.py` as module-level function
- Extract thresholds to `constants.py` as `RSI_OVERBOUGHT = 70`, `RSI_OVERSOLD = 30`
- Add type hints: `format_rsi_with_emoji(rsi_value: float | None) -> str`

---

### 2. `enforce_emoji_usage()` - NESTED IN current_report.py

**Location**: `reports/current_report.py` (line ~629, nested inside `generate_crypto_situation_report()`)

**Current Implementation**:
```python
def enforce_emoji_usage(text):
    # Add emojis to section headers if missing
    emoji_map = {
        "Trend": "📈",
        "Price": "💰",
        "Target": "🎯",
        "Risk": "⚠️",
        "Support": "💰",
        "Resistance": "💰",
        "Trading": "💰",
        "Volatility": "⚠️",
        "Momentum": "📈",
        "Opportunity": "🎯",
    }

    def add_emoji(match):
        header = match.group(1)
        for key, emoji in emoji_map.items():
            if key.lower() in header.lower() and emoji not in header:
                return f"{emoji} {header}"
        return header

    # Add emojis to markdown headers
    return re.sub(
        r"^(##+)\s*(.+)$",
        lambda m: f"{m.group(1)} {add_emoji(m)}",
        text,
        flags=re.MULTILINE,
    )
```

**Issues**:
- Nested inside another function with nested inner function
- Hardcoded emoji map
- No type hints
- Not reusable across reports

**Extraction Plan**:
- Move to `shared_code/telegram/formatting_utils.py` as `enhance_text_with_emojis()`
- Make emoji_map a parameter with default value
- Extract default emoji map to `constants.py` as `DEFAULT_EMOJI_MAP`
- Add type hints: `enhance_text_with_emojis(text: str, emoji_map: dict[str, str] | None = None) -> str`

---

### 3. `convert_markdown_to_telegram_html()` - MODULE LEVEL IN current_report.py

**Location**: `reports/current_report.py` (line 334-391)

**Current Implementation**: Full markdown → HTML converter with support for headers, bold, italic, code, lists

**Issues**:
- Should be in telegram module, not in report module
- Only used by current_report.py currently but could be useful elsewhere
- Named generically but specifically designed for AI-generated markdown

**Extraction Plan**:
- Move to `shared_code/telegram/formatting_utils.py`
- Rename to `convert_ai_markdown_to_telegram_html()` for clarity
- Add comprehensive docstring
- Add type hints: `convert_ai_markdown_to_telegram_html(markdown_text: str) -> str`

---

### 4. `format_articles_for_html()` - MODULE LEVEL IN current_report.py

**Location**: `reports/current_report.py` (line 296-330)

**Current Implementation**: Formats cached news articles into HTML with truncation

**Issues**:
- Should be format-agnostic (support both HTML and MarkdownV2)
- Hardcoded HTML tags
- Hardcoded truncation lengths (ARTICLE_TITLE_MAX_LENGTH, ARTICLE_CONTENT_PREVIEW_LENGTH)

**Extraction Plan**:
- Move to `shared_code/telegram/formatting_utils.py`
- Rename to `format_articles_for_telegram()` and accept formatter parameter
- Make format-agnostic: `format_articles_for_telegram(articles: list[CachedArticle], formatter: TelegramFormatter) -> str`
- Use formatter methods for bold, italic, links instead of hardcoded HTML

---

## TASK-004: List All Magic Numbers and Thresholds to Extract ✅

### Constants Currently in Code

| Constant | Current Value | Location | Usage | Proposed Constant Name |
|----------|---------------|----------|-------|----------------------|
| Article title max length | 100 | `current_report.py` (line ~317) | Truncates article titles | `ARTICLE_TITLE_MAX_LENGTH` |
| Article content preview length | 500 | Not found in code snippet | Article preview | `ARTICLE_CONTENT_PREVIEW_LENGTH` |
| RSI overbought threshold | 70 | `current_data_table.py` (line ~324) | RSI indicator coloring | `RSI_OVERBOUGHT` |
| RSI oversold threshold | 30 | `current_data_table.py` (line ~325) | RSI indicator coloring | `RSI_OVERSOLD` |
| Funding rate high threshold | 0.01 | (assumed from context) | Derivatives formatting | `FUNDING_RATE_HIGH` |
| Funding rate low threshold | -0.01 | (assumed from context) | Derivatives formatting | `FUNDING_RATE_LOW` |
| Telegram message max length | 4096 | `telegram.py` (in smart_split) | Message splitting | `TELEGRAM_MAX_MESSAGE_LENGTH` |

### Constants File Structure

**File**: `shared_code/telegram/constants.py`

```python
"""Constants for Telegram messaging and formatting."""

# Message constraints
TELEGRAM_MAX_MESSAGE_LENGTH = 4096

# Article formatting
ARTICLE_TITLE_MAX_LENGTH = 100
ARTICLE_CONTENT_PREVIEW_LENGTH = 500

# Technical indicator thresholds
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

FUNDING_RATE_HIGH = 0.01
FUNDING_RATE_LOW = -0.01

# Emoji mappings
DEFAULT_EMOJI_MAP = {
    "Trend": "📈",
    "Price": "💰",
    "Target": "🎯",
    "Risk": "⚠️",
    "Support": "💰",
    "Resistance": "💰",
    "Trading": "💰",
    "Volatility": "⚠️",
    "Momentum": "📈",
    "Opportunity": "🎯",
}

# HTML tags allowed by Telegram
TELEGRAM_ALLOWED_HTML_TAGS = ["b", "i", "u", "s", "code", "pre", "a"]

# MarkdownV2 special characters that need escaping
MARKDOWN_V2_SPECIAL_CHARS = r"_*[]()~`>#+-=|{}.!"
```

---

## TASK-005: Review Existing Test Coverage ✅

### Current Test File: `tests/test_telegram_utils.py`

**Test Coverage Summary**:

| Function Tested | Test Cases | Coverage Status | Notes |
|----------------|------------|-----------------|-------|
| `smart_split()` | 4 tests | ✅ Good | Tests short messages, paragraph preservation, oversize paragraphs, HTML tag boundaries |
| `enforce_markdown_v2()` | 3 tests | ✅ Good | Tests basic escapes, code span preservation, idempotency |
| `send_telegram_message()` | 0 tests | ❌ Missing | No unit tests (requires mocking) |
| `send_telegram_document()` | 0 tests | ❌ Missing | No unit tests (requires mocking) |
| `try_send_report_with_html_or_markdown()` | 0 tests | ❌ Missing | No unit tests (requires mocking) |
| `sanitize_html()` | 0 tests | ❌ Missing | No unit tests |

**Existing Test Details**:

1. **`test_smart_split_short_message`**: Verifies short messages aren't split
2. **`test_smart_split_paragraph_preservation`**: Ensures paragraph boundaries respected
3. **`test_smart_split_oversize_paragraph`**: Tests splitting of large paragraphs
4. **`test_smart_split_html_tag_boundary`**: Ensures HTML tags aren't broken across chunks
5. **`test_enforce_markdown_v2_basic_escapes`**: Tests special character escaping
6. **`test_enforce_markdown_v2_preserves_code_spans`**: Ensures code blocks not escaped
7. **`test_enforce_markdown_v2_idempotent`**: Verifies repeated escaping doesn't break

**Gaps to Address in Testing**:
- No tests for sending functions (need mocking)
- No tests for HTML sanitization
- No tests for formatter abstraction (will be added in Phase 2)
- No tests for nested formatting functions (will be added when extracted)
- No integration tests for actual Telegram API calls

---

## Next Steps for Phase 1

### ✅ Completed Tasks:
- [x] TASK-001: Document all current telegram sending locations
- [x] TASK-003: Identify all nested formatting functions  
- [x] TASK-004: List all magic numbers and thresholds to be extracted
- [x] TASK-005: Review existing test coverage in tests/test_telegram_utils.py

### 🔄 Pending Tasks:
- [ ] TASK-002: Create snapshot tests for current telegram message outputs to verify no regressions
- [ ] TASK-006: Create baseline performance benchmarks for message formatting

### Action Items:
1. Create snapshot/baseline tests to capture current output formats
2. Run existing tests to ensure baseline: `pytest tests/test_telegram_utils.py -v`
3. Proceed to Phase 2: Package structure creation

---

## Risk Assessment

**Identified Risks**:
1. **RISK**: Multiple files depend on `shared_code/telegram.py` - changes could break imports
   - **Mitigation**: Use `__init__.py` for backward compatibility during migration
   
2. **RISK**: Daily report is in production - cannot afford regressions
   - **Mitigation**: Create snapshot tests before any changes
   
3. **RISK**: Nested functions have no unit tests currently
   - **Mitigation**: Write tests during extraction in Phase 3-4

**Dependencies Identified**:
- `requests` library (already present)
- `html` module (stdlib)
- `re` module (stdlib)
- Environment variables: `TELEGRAM_ENABLED`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`

---

## Conclusion

Phase 1 analysis complete. Key findings:
- **7 files** use telegram functionality
- **1 duplicate** implementation to remove (`utils.py`)
- **4 nested/misplaced** formatting functions to extract
- **7+ magic numbers** to extract as constants
- **Existing test coverage**: 50% (text processing good, sending functions untested)

Ready to proceed with Phase 2: Package structure creation.
