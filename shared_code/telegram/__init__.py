"""Telegram messaging package for CryptoMorningReports.

This package provides a unified interface for sending and formatting
Telegram messages with support for both HTML and MarkdownV2 parse modes.

Package Structure
-----------------
The package is organized into five specialized modules:

1. **constants.py** - Configuration constants and thresholds
   - Message/document size limits
   - RSI and funding rate thresholds
   - Emoji mappings and parse mode constants

2. **formatters.py** - Format abstraction layer
   - TelegramFormatter protocol for format-agnostic code
   - HTMLFormatter and MarkdownV2Formatter implementations
   - get_formatter() factory function

3. **text_processing.py** - Text conversion and sanitization
   - enforce_markdown_v2() for escaping special characters
   - sanitize_html() for cleaning HTML tags
   - smart_split() for message chunking

4. **formatting_utils.py** - Domain-specific formatting helpers
   - format_rsi_with_emoji() for RSI indicators
   - format_articles_for_telegram() for news articles
   - convert_ai_markdown_to_telegram_html() for AI output
   - Other utility formatters

5. **sending.py** - Telegram API communication
   - send_telegram_message() for text messages
   - send_telegram_document() for file uploads
   - try_send_report_with_html_or_markdown() with fallback

Public API
----------
All public functions and constants are re-exported from this __init__.py
for convenient importing:

    from shared_code.telegram import send_telegram_message, get_formatter

You can also import from submodules directly if preferred:

    from shared_code.telegram.sending import send_telegram_message
    from shared_code.telegram.formatters import HTMLFormatter

Constants:
    TELEGRAM_MAX_MESSAGE_LENGTH, TELEGRAM_MAX_DOCUMENT_SIZE
    ARTICLE_TITLE_MAX_LENGTH, ARTICLE_CONTENT_PREVIEW_LENGTH
    RSI_OVERBOUGHT, RSI_OVERSOLD, RSI_EMOJI_*
    FUNDING_RATE_HIGH, FUNDING_RATE_LOW
    DEFAULT_EMOJI_MAP, TELEGRAM_ALLOWED_HTML_TAGS
    MARKDOWN_V2_SPECIAL_CHARS
    PARSE_MODE_HTML, PARSE_MODE_MARKDOWN_V2, PARSE_MODE_NONE

Formatters:
    get_formatter(parse_mode: str) -> TelegramFormatter
    TelegramFormatter (Protocol)
    HTMLFormatter, MarkdownV2Formatter

Text Processing:
    enforce_markdown_v2(text: str) -> str
    sanitize_html(text: str) -> str
    smart_split(text: str, ...) -> list[str]

Formatting Utils:
    format_rsi_with_emoji(rsi: float, formatter: TelegramFormatter) -> str
    enhance_text_with_emojis(text: str, emoji_map: dict) -> str
    convert_ai_markdown_to_telegram_html(markdown: str) -> str
    format_articles_for_telegram(articles: list, ...) -> str
    format_price_with_currency(price: float, ...) -> str
    format_funding_rate_with_emoji(rate: float, ...) -> str

Sending:
    send_telegram_message(enabled: bool, token: str, chat_id: str,
                         message: str, ...) -> dict
    send_telegram_document(enabled: bool, token: str, chat_id: str,
                          file_path: str, ...) -> dict
    try_send_report_with_html_or_markdown(enabled: bool, token: str,
                                          chat_id: str, report: str) -> dict

Usage Example
-------------
    from shared_code.telegram import get_formatter, send_telegram_message

    # Get formatter based on preferred format
    formatter = get_formatter("HTML")

    # Build message using formatter
    message = formatter.format_bold("Important!") + " This is a message."

    # Send message to Telegram
    result = await send_telegram_message(
        enabled=True,
        token="your_bot_token",
        chat_id="your_chat_id",
        message=message,
        parse_mode="HTML"
    )

Version History
---------------
- 2.0.0: Package refactoring - split into specialized modules
- 1.x: Original monolithic telegram.py module
"""

# ============================================================================
# Public API Exports
# ============================================================================

# Constants
from .constants import (
    ARTICLE_CONTENT_PREVIEW_LENGTH,
    ARTICLE_TITLE_MAX_LENGTH,
    DEFAULT_EMOJI_MAP,
    FUNDING_RATE_HIGH,
    FUNDING_RATE_LOW,
    MARKDOWN_V2_SPECIAL_CHARS,
    PARSE_MODE_HTML,
    PARSE_MODE_MARKDOWN_V2,
    PARSE_MODE_NONE,
    RSI_EMOJI_NEUTRAL,
    RSI_EMOJI_OVERBOUGHT,
    RSI_EMOJI_OVERSOLD,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    TELEGRAM_ALLOWED_HTML_TAGS,
    TELEGRAM_MAX_DOCUMENT_SIZE,
    TELEGRAM_MAX_MESSAGE_LENGTH,
)

# Formatters
from .formatters import (
    HTMLFormatter,
    MarkdownV2Formatter,
    TelegramFormatter,
    get_formatter,
)

# Formatting Utils
from .formatting_utils import (
    convert_ai_markdown_to_telegram_html,
    enhance_text_with_emojis,
    format_articles_for_telegram,
    format_funding_rate_with_emoji,
    format_price_with_currency,
    format_rsi_with_emoji,
)

# Text Processing
from .text_processing import (
    enforce_markdown_v2,
    sanitize_html,
    smart_split,
)

# Sending
from .sending import (
    send_telegram_document,
    send_telegram_message,
    try_send_report_with_html_or_markdown,
)


# ============================================================================
# Package Metadata
# ============================================================================

__version__ = "2.0.0"  # Version 2.0 - Package refactoring
__all__ = [
    # Constants
    "ARTICLE_CONTENT_PREVIEW_LENGTH",
    "ARTICLE_TITLE_MAX_LENGTH",
    "DEFAULT_EMOJI_MAP",
    "FUNDING_RATE_HIGH",
    "FUNDING_RATE_LOW",
    "MARKDOWN_V2_SPECIAL_CHARS",
    "PARSE_MODE_HTML",
    "PARSE_MODE_MARKDOWN_V2",
    "PARSE_MODE_NONE",
    "RSI_EMOJI_NEUTRAL",
    "RSI_EMOJI_OVERBOUGHT",
    "RSI_EMOJI_OVERSOLD",
    "RSI_OVERBOUGHT",
    "RSI_OVERSOLD",
    "TELEGRAM_ALLOWED_HTML_TAGS",
    "TELEGRAM_MAX_DOCUMENT_SIZE",
    "TELEGRAM_MAX_MESSAGE_LENGTH",
    # Formatters
    "get_formatter",
    "HTMLFormatter",
    "MarkdownV2Formatter",
    "TelegramFormatter",
    # Formatting Utils
    "convert_ai_markdown_to_telegram_html",
    "enhance_text_with_emojis",
    "format_articles_for_telegram",
    "format_funding_rate_with_emoji",
    "format_price_with_currency",
    "format_rsi_with_emoji",
    # Sending
    "send_telegram_document",
    "send_telegram_message",
    "try_send_report_with_html_or_markdown",
    # Text Processing
    "enforce_markdown_v2",
    "sanitize_html",
    "smart_split",
]
