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
    - enforce_markdown_v2() - (TODO: Phase 6)
    - sanitize_html() - (TODO: Phase 6)
    - smart_split() - (TODO: Phase 6)

Formatting Utils:
    - format_rsi_with_emoji() - Format RSI values with emoji indicators
    - enhance_text_with_emojis() - Add emojis to markdown headers
    - convert_ai_markdown_to_telegram_html() - Convert AI markdown to HTML
    - format_articles_for_telegram() - Format news articles for Telegram
    - format_price_with_currency() - Format price with currency symbol
    - format_funding_rate_with_emoji() - Format funding rate with emoji

Sending:
    - send_telegram_message() - (TODO: Phase 4)
    - send_telegram_document() - (TODO: Phase 4)
    - try_send_report_with_html_or_markdown() - (TODO: Phase 4)

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

# Text Processing (TODO: Phase 6 - These are temporarily imported from old telegram.py)
# Import from parent module (old telegram.py) for backward compatibility
# Temporarily import from old telegram.py file (in shared_code directory)
# These will be moved to text_processing.py in Phase 6
try:
    # Import from parent shared_code.telegram module (the old .py file, not this package)
    import importlib.util
    import sys
    from pathlib import Path

    _old_telegram_path = Path(__file__).parent.parent / "telegram.py"
    spec = importlib.util.spec_from_file_location("old_telegram", _old_telegram_path)
    if spec and spec.loader:
        old_telegram = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(old_telegram)

        enforce_markdown_v2 = old_telegram.enforce_markdown_v2
        sanitize_html = old_telegram.sanitize_html
        smart_split = old_telegram.smart_split
        send_telegram_message = old_telegram.send_telegram_message
        send_telegram_document = old_telegram.send_telegram_document
        try_send_report_with_html_or_markdown = old_telegram.try_send_report_with_html_or_markdown
    else:
        raise ImportError("Could not load old telegram module")
except (ImportError, AttributeError) as e:
    # If import fails, define stub functions
    import sys

    print(f"Warning: Could not import from old telegram.py: {e}", file=sys.stderr)

    def enforce_markdown_v2(text: str) -> str:
        """Temporary stub - will be implemented in Phase 6."""
        msg = "This function will be moved in Phase 6"
        raise NotImplementedError(msg)

    def sanitize_html(message: str) -> str:
        """Temporary stub - will be implemented in Phase 6."""
        msg = "This function will be moved in Phase 6"
        raise NotImplementedError(msg)

    def smart_split(text: str, limit: int, parse_mode: str | None) -> list[str]:
        """Temporary stub - will be implemented in Phase 6."""
        msg = "This function will be moved in Phase 6"
        raise NotImplementedError(msg)

    async def send_telegram_message(**kwargs):
        """Temporary stub - will be implemented in Phase 4."""
        msg = "This function will be moved in Phase 4"
        raise NotImplementedError(msg)

    async def send_telegram_document(**kwargs):
        """Temporary stub - will be implemented in Phase 4."""
        msg = "This function will be moved in Phase 4"
        raise NotImplementedError(msg)

    async def try_send_report_with_html_or_markdown(**kwargs):
        """Temporary stub - will be implemented in Phase 4."""
        msg = "This function will be moved in Phase 4"
        raise NotImplementedError(msg)


# from .text_processing import (
#     enforce_markdown_v2,
#     sanitize_html,
#     smart_split,
# )

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
