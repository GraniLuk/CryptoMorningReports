# Telegram Formatting Package Guide

This guide explains the `shared_code.telegram` package structure, how to use formatters, and how to switch between HTML and MarkdownV2 formats.

## Table of Contents

- [Overview](#overview)
- [Package Structure](#package-structure)
- [Quick Start](#quick-start)
- [Format Switching](#format-switching)
- [Using Formatters](#using-formatters)
- [Common Patterns](#common-patterns)
- [Migration Guide](#migration-guide)

## Overview

The `shared_code.telegram` package provides a unified interface for sending and formatting Telegram messages with support for both HTML and MarkdownV2 parse modes.

**Key Features:**
- ✅ Format abstraction (HTML and MarkdownV2)
- ✅ Message splitting for long content
- ✅ Document uploads with size validation
- ✅ Automatic fallback between formats
- ✅ Domain-specific formatters (RSI, articles, prices)
- ✅ Environment-based configuration

## Package Structure

```
shared_code/telegram/
├── __init__.py                # Public API exports
├── constants.py               # Configuration constants
├── formatters.py              # Format abstraction layer
├── formatting_utils.py        # Domain-specific helpers
├── sending.py                 # Telegram API communication
└── text_processing.py         # Text sanitization & splitting
```

### Module Responsibilities

#### 1. `constants.py`
Central location for all package constants:
- Message/document size limits
- RSI and funding rate thresholds
- Emoji mappings
- Parse mode constants

```python
from shared_code.telegram import (
    TELEGRAM_MAX_MESSAGE_LENGTH,  # 4096
    PARSE_MODE_HTML,              # "HTML"
    PARSE_MODE_MARKDOWN_V2,       # "MarkdownV2"
    RSI_OVERBOUGHT,               # 70
)
```

#### 2. `formatters.py`
Format abstraction with Protocol interface:
- `TelegramFormatter` protocol
- `HTMLFormatter` implementation
- `MarkdownV2Formatter` implementation
- `get_formatter()` factory function

```python
from shared_code.telegram import get_formatter, HTMLFormatter

# Get formatter by parse mode
formatter = get_formatter("HTML")

# Or create directly
html_formatter = HTMLFormatter()

# Use formatter methods
text = formatter.format_bold("Important!")
```

#### 3. `text_processing.py`
Text conversion and sanitization:
- `enforce_markdown_v2()` - Escape MarkdownV2 special characters
- `sanitize_html()` - Clean HTML tags
- `smart_split()` - Split long messages intelligently

```python
from shared_code.telegram import smart_split, enforce_markdown_v2

# Split long message
chunks = smart_split(long_message, max_length=4096, parse_mode="HTML")

# Escape MarkdownV2
safe_text = enforce_markdown_v2("Special chars: _*[]()~`>#+-=|{}.!")
```

#### 4. `formatting_utils.py`
Domain-specific formatting helpers:
- `format_rsi_with_emoji()` - RSI indicators with emojis
- `format_articles_for_telegram()` - News articles formatting
- `format_price_with_currency()` - Price display
- `convert_ai_markdown_to_telegram_html()` - AI output conversion

```python
from shared_code.telegram import format_rsi_with_emoji

# Format RSI value
rsi_display = format_rsi_with_emoji(75.5)
# Returns: "75.50 🔴" (red circle for overbought)
```

#### 5. `sending.py`
Telegram API communication:
- `send_telegram_message()` - Send text messages
- `send_telegram_document()` - Upload documents
- `try_send_report_with_html_or_markdown()` - Auto fallback

```python
from shared_code.telegram import send_telegram_message

await send_telegram_message(
    enabled=True,
    token=telegram_token,
    chat_id=chat_id,
    message="<b>Hello!</b>",
    parse_mode="HTML",
)
```

## Quick Start

### Basic Message Sending

```python
from shared_code.telegram import send_telegram_message

# HTML format (default)
await send_telegram_message(
    enabled=True,
    token=os.getenv("TELEGRAM_TOKEN"),
    chat_id=os.getenv("TELEGRAM_CHAT_ID"),
    message="<b>Bold text</b> and <i>italic</i>",
    parse_mode="HTML",
)

# MarkdownV2 format
await send_telegram_message(
    enabled=True,
    token=os.getenv("TELEGRAM_TOKEN"),
    chat_id=os.getenv("TELEGRAM_CHAT_ID"),
    message="*Bold text* and _italic_",
    parse_mode="MarkdownV2",
)
```

### Using Formatters

```python
from shared_code.telegram import get_formatter

# Get formatter based on config
formatter = get_formatter("HTML")

# Build message using formatter methods
message = formatter.format_bold("Price Alert") + "\n"
message += formatter.format_italic("BTC reached $50,000") + "\n"
message += formatter.format_code("Price: $50,123.45")

# Send message
await send_telegram_message(
    enabled=True,
    token=telegram_token,
    chat_id=chat_id,
    message=message,
    parse_mode="HTML",
)
```

## Format Switching

### Environment Configuration

Set the `TELEGRAM_PARSE_MODE` environment variable to switch between formats globally:

```bash
# .env file
TELEGRAM_PARSE_MODE=HTML        # Default
# or
TELEGRAM_PARSE_MODE=MarkdownV2
```

### Using get_telegram_parse_mode()

```python
from infra.configuration import get_telegram_parse_mode

# Get configured parse mode
parse_mode = get_telegram_parse_mode()  # Returns "HTML" or "MarkdownV2"

# Use in reports
telegram_parse_mode = get_telegram_parse_mode()
logger.info("Using Telegram parse mode: %s", telegram_parse_mode)

await send_telegram_message(
    enabled=True,
    token=telegram_token,
    chat_id=chat_id,
    message=formatted_message,
    parse_mode=telegram_parse_mode,  # Uses configured mode
)
```

### Format-Agnostic Code

Write code that works with any format using the formatter abstraction:

```python
from shared_code.telegram import get_formatter

def format_report(data, parse_mode="HTML"):
    """Generate report that works with both formats."""
    formatter = get_formatter(parse_mode)
    
    report = formatter.format_header("Market Report", level=1) + "\n\n"
    report += formatter.format_bold("Current Price: ") + f"${data['price']}\n"
    report += formatter.format_italic("24h Change: ") + f"{data['change']}%\n"
    
    return report

# Use with HTML
html_report = format_report(data, "HTML")

# Use with MarkdownV2
md_report = format_report(data, "MarkdownV2")
```

## Using Formatters

### Formatter Methods

All formatters implement the `TelegramFormatter` protocol:

```python
class TelegramFormatter(Protocol):
    """Protocol defining formatter interface."""
    
    def format_bold(self, text: str) -> str: ...
    def format_italic(self, text: str) -> str: ...
    def format_underline(self, text: str) -> str: ...
    def format_strikethrough(self, text: str) -> str: ...
    def format_code(self, text: str) -> str: ...
    def format_code_block(self, text: str, language: str = "") -> str: ...
    def format_link(self, text: str, url: str) -> str: ...
    def format_header(self, text: str, level: int = 1) -> str: ...
```

### HTML Formatter Example

```python
from shared_code.telegram import HTMLFormatter

formatter = HTMLFormatter()

# Basic formatting
bold = formatter.format_bold("Important!")       # <b>Important!</b>
italic = formatter.format_italic("Note:")        # <i>Note:</i>
code = formatter.format_code("print('hello')")   # <code>print('hello')</code>

# Headers
h1 = formatter.format_header("Title", level=1)   # <b>▓▓▓ Title ▓▓▓</b>
h2 = formatter.format_header("Section", level=2) # <b>═══ Section ═══</b>

# Links
link = formatter.format_link("Click here", "https://example.com")
# <a href="https://example.com">Click here</a>

# Code blocks
code_block = formatter.format_code_block("def hello():\n    print('Hi')", "python")
# <pre>def hello():\n    print('Hi')</pre>
```

### MarkdownV2 Formatter Example

```python
from shared_code.telegram import MarkdownV2Formatter

formatter = MarkdownV2Formatter()

# Basic formatting
bold = formatter.format_bold("Important!")       # *Important!*
italic = formatter.format_italic("Note:")        # _Note:_
code = formatter.format_code("print('hello')")   # `print('hello')`

# Headers
h1 = formatter.format_header("Title", level=1)   # *▓▓▓ Title ▓▓▓*
h2 = formatter.format_header("Section", level=2) # *═══ Section ═══*

# Links
link = formatter.format_link("Click here", "https://example.com")
# [Click here](https://example.com)

# Code blocks (auto-escapes special chars)
code_block = formatter.format_code_block("def hello():\n    print('Hi')", "python")
# ```python\ndef hello():\n    print('Hi')\n```
```

## Common Patterns

### Pattern 1: Format RSI Indicators

```python
from shared_code.telegram import format_rsi_with_emoji

# Format RSI with automatic emoji
rsi_display = format_rsi_with_emoji(
    rsi_value=75.5,
    overbought_threshold=70,
    oversold_threshold=30,
)
# Returns: "75.50 🔴" (red for overbought)

rsi_display = format_rsi_with_emoji(25.3)
# Returns: "25.30 🟢" (green for oversold)

rsi_display = format_rsi_with_emoji(50.0)
# Returns: "50.00 🟡" (yellow for neutral)
```

### Pattern 2: Format News Articles

```python
from shared_code.telegram import format_articles_for_telegram, HTMLFormatter

articles = [
    CachedArticle(
        title="Bitcoin Breaks $50K",
        source="CoinDesk",
        published="2025-11-03T10:00:00",
        link="https://example.com/article1",
    ),
]

# Format with HTML
html_formatter = HTMLFormatter()
formatted = format_articles_for_telegram(articles, html_formatter)

# Format with MarkdownV2
from shared_code.telegram import MarkdownV2Formatter
md_formatter = MarkdownV2Formatter()
formatted = format_articles_for_telegram(articles, md_formatter)
```

### Pattern 3: Auto-Fallback Sending

```python
from shared_code.telegram import try_send_report_with_html_or_markdown

# Tries HTML first, falls back to MarkdownV2 if HTML fails
success = await try_send_report_with_html_or_markdown(
    telegram_enabled=True,
    telegram_token=telegram_token,
    telegram_chat_id=chat_id,
    message=formatted_report,
)

if success:
    logger.info("Report sent successfully")
else:
    logger.warning("Failed to send report")
```

### Pattern 4: Split Long Messages

```python
from shared_code.telegram import smart_split, send_telegram_message

# Split long message into chunks
chunks = smart_split(
    long_message,
    max_length=4096,
    parse_mode="HTML",
)

# Send each chunk
for chunk in chunks:
    await send_telegram_message(
        enabled=True,
        token=telegram_token,
        chat_id=chat_id,
        message=chunk,
        parse_mode="HTML",
    )
```

### Pattern 5: Format Prices

```python
from shared_code.telegram import format_price_with_currency

# Format price with default symbol
price_str = format_price_with_currency(50123.456789)
# Returns: "$50,123.46"

# Custom currency and decimals
price_str = format_price_with_currency(
    price=1234.5678,
    currency_symbol="€",
    decimal_places=4,
)
# Returns: "€1,234.5678"
```

## Migration Guide

### For New Code

When writing new code that sends Telegram messages:

1. **Import from the package:**
   ```python
   from shared_code.telegram import send_telegram_message, get_formatter
   ```

2. **Use environment configuration:**
   ```python
   from infra.configuration import get_telegram_parse_mode
   
   parse_mode = get_telegram_parse_mode()
   ```

3. **Write format-agnostic code:**
   ```python
   def create_report(data, parse_mode="HTML"):
       formatter = get_formatter(parse_mode)
       # Use formatter methods instead of hardcoded tags
       return formatter.format_bold("Title") + "\n" + data
   ```

### For Existing Code

If you have old code using direct Telegram API calls:

**Before:**
```python
message = f"<b>Price:</b> ${price}"
requests.post(
    f"https://api.telegram.org/bot{token}/sendMessage",
    json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
)
```

**After:**
```python
from shared_code.telegram import send_telegram_message, get_formatter
from infra.configuration import get_telegram_parse_mode

parse_mode = get_telegram_parse_mode()
formatter = get_formatter(parse_mode)

message = formatter.format_bold("Price:") + f" ${price}"
await send_telegram_message(
    enabled=True,
    token=token,
    chat_id=chat_id,
    message=message,
    parse_mode=parse_mode,
)
```

### Best Practices

1. ✅ **Use formatters** instead of hardcoding HTML/Markdown tags
2. ✅ **Use `get_telegram_parse_mode()`** to respect environment configuration
3. ✅ **Import from package root** (`shared_code.telegram`) not submodules
4. ✅ **Use `smart_split()`** for long messages to prevent truncation
5. ✅ **Use domain helpers** (`format_rsi_with_emoji`, `format_articles_for_telegram`)
6. ✅ **Add logging** to show which parse mode is being used

## Testing

### Unit Testing Formatters

```python
from shared_code.telegram import HTMLFormatter, MarkdownV2Formatter

def test_html_formatter():
    formatter = HTMLFormatter()
    assert formatter.format_bold("Test") == "<b>Test</b>"
    assert formatter.format_italic("Test") == "<i>Test</i>"

def test_markdown_formatter():
    formatter = MarkdownV2Formatter()
    # Note: MarkdownV2 escapes special characters
    assert formatter.format_bold("Test") == "*Test*"
    assert formatter.format_italic("Test") == "_Test_"
```

### Integration Testing

```python
from shared_code.telegram import get_formatter

def test_format_switching():
    # Test HTML
    html_formatter = get_formatter("HTML")
    html_output = html_formatter.format_bold("Price: $100")
    assert "<b>" in html_output
    
    # Test MarkdownV2
    md_formatter = get_formatter("MarkdownV2")
    md_output = md_formatter.format_bold("Price: $100")
    assert "*" in md_output
```

## Troubleshooting

### Issue: Message sends as plain text
**Solution:** Check that `parse_mode` is set correctly and matches the formatting used.

### Issue: Special characters cause errors
**Solution:** Use `enforce_markdown_v2()` for MarkdownV2 or `sanitize_html()` for HTML.

### Issue: Message exceeds 4096 characters
**Solution:** Use `smart_split()` to chunk the message before sending.

### Issue: Format not switching with environment variable
**Solution:** Check that `TELEGRAM_PARSE_MODE` is set in your `.env` file and the value is exactly `HTML` or `MarkdownV2` (case-sensitive).

## Reference

### Supported HTML Tags (HTML Mode)
- `<b>bold</b>` - Bold text
- `<i>italic</i>` - Italic text
- `<u>underline</u>` - Underlined text
- `<s>strike</s>` - Strikethrough text
- `<code>code</code>` - Inline code
- `<pre>code block</pre>` - Code block
- `<a href="url">link</a>` - Hyperlink

### MarkdownV2 Special Characters
These characters must be escaped with `\` in MarkdownV2 mode:
```
_ * [ ] ( ) ~ ` > # + - = | { } . !
```

Use `enforce_markdown_v2()` to handle escaping automatically.

### Environment Variables

```bash
# Required
TELEGRAM_ENABLED=true
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Optional (defaults to HTML)
TELEGRAM_PARSE_MODE=HTML        # or MarkdownV2
```

## Additional Resources

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [HTML Style Guide](https://core.telegram.org/bots/api#html-style)
- [MarkdownV2 Style Guide](https://core.telegram.org/bots/api#markdownv2-style)
- [Package Tests](../tests/test_telegram_formatters.py)
