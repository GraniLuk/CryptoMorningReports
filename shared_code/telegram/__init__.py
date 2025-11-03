"""Telegram messaging package for CryptoMorningReports.

This package provides a unified interface for sending and formatting
Telegram messages with support for both HTML and MarkdownV2 parse modes.

Public API:
-----------

Constants:
    - TELEGRAM_MAX_MESSAGE_LENGTH
    - ARTICLE_TITLE_MAX_LENGTH
    - RSI_OVERBOUGHT, RSI_OVERSOLD
    - All other constants from constants module

Formatters:
    - get_formatter() - Factory function for format selection
    - HTMLFormatter, MarkdownV2Formatter - Formatter implementations

Text Processing:
    - enforce_markdown_v2() - Escape MarkdownV2 special characters
    - sanitize_html() - Sanitize HTML to Telegram-allowed tags
    - smart_split() - Split text into chunks respecting limits

Formatting Utils:
    - format_rsi_with_emoji() - Format RSI values with emoji indicators
    - enhance_text_with_emojis() - Add emojis to markdown headers
    - convert_ai_markdown_to_telegram_html() - Convert AI markdown to HTML
    - format_articles_for_telegram() - Format news articles for Telegram
    - format_price_with_currency() - Format price with currency symbol
    - format_funding_rate_with_emoji() - Format funding rate with emoji

Sending:
    - send_telegram_message() - Send text message to Telegram
    - send_telegram_document() - Send document to Telegram
    - try_send_report_with_html_or_markdown() - Send with fallback

Usage:
------
    from shared_code.telegram import get_formatter, send_telegram_message

    # Get HTML formatter
    formatter = get_formatter("HTML")
    message = formatter.format_bold("Important!") + " This is a message."

    # Send message
    await send_telegram_message(
        enabled=True,
        token="...",
        chat_id="...",
        message=message,
        parse_mode="HTML"
    )
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

# Text Processing - Now imported from text_processing module
from .text_processing import (
    enforce_markdown_v2,
    sanitize_html,
    smart_split,
)

# Sending - Now imported from sending module
from .sending import (
    send_telegram_document,
    send_telegram_message,
    try_send_report_with_html_or_markdown,
)


# Commented out old Phase 6 TODOs - all modules now imported above

# Formatting Utils (TODO: Phase 3-5)
# from .formatting_utils import (
#     convert_ai_markdown_to_telegram_html,
#     enhance_text_with_emojis,
#     format_articles_for_telegram,
#     format_funding_rate_with_emoji,
#     format_price_with_currency,
#     format_rsi_with_emoji,
# )

# Sending (TODO: Phase 4 - These are temporarily imported from old telegram.py above)
# from .sending import (
#     send_telegram_document,
#     send_telegram_message,
#     try_send_report_with_html_or_markdown,
# )


# ============================================================================
# Package Metadata
# ============================================================================

__version__ = "2.0.0"  # Version 2.0 - Package refactoring
__all__ = [
    # Constants
    "TELEGRAM_MAX_MESSAGE_LENGTH",
    "TELEGRAM_MAX_DOCUMENT_SIZE",
    "ARTICLE_TITLE_MAX_LENGTH",
    "ARTICLE_CONTENT_PREVIEW_LENGTH",
    "RSI_OVERBOUGHT",
    "RSI_OVERSOLD",
    "RSI_EMOJI_OVERBOUGHT",
    "RSI_EMOJI_OVERSOLD",
    "RSI_EMOJI_NEUTRAL",
    "FUNDING_RATE_HIGH",
    "FUNDING_RATE_LOW",
    "DEFAULT_EMOJI_MAP",
    "TELEGRAM_ALLOWED_HTML_TAGS",
    "MARKDOWN_V2_SPECIAL_CHARS",
    "PARSE_MODE_HTML",
    "PARSE_MODE_MARKDOWN_V2",
    "PARSE_MODE_NONE",
    # Formatters
    "TelegramFormatter",
    "HTMLFormatter",
    "MarkdownV2Formatter",
    "get_formatter",
    # Text Processing (TODO: Phase 6)
    "enforce_markdown_v2",
    "sanitize_html",
    "smart_split",
    # Formatting Utils
    "convert_ai_markdown_to_telegram_html",
    "enhance_text_with_emojis",
    "format_articles_for_telegram",
    "format_funding_rate_with_emoji",
    "format_price_with_currency",
    "format_rsi_with_emoji",
    # Sending (TODO: Phase 4)
    "send_telegram_message",
    "send_telegram_document",
    "try_send_report_with_html_or_markdown",
]
