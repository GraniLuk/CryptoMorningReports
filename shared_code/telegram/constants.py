"""Constants for Telegram messaging and formatting.

This module contains all constants used across the telegram package,
including message constraints, formatting thresholds, and emoji mappings.
"""

# ============================================================================
# Message Constraints
# ============================================================================

# Maximum message length allowed by Telegram API
TELEGRAM_MAX_MESSAGE_LENGTH = 4096

# Maximum document size for Telegram Bot API (50MB for standard bots)
TELEGRAM_MAX_DOCUMENT_SIZE = 50 * 1024 * 1024


# ============================================================================
# Article Formatting
# ============================================================================

# Maximum length for article titles before truncation
ARTICLE_TITLE_MAX_LENGTH = 100

# Maximum length for article content preview
ARTICLE_CONTENT_PREVIEW_LENGTH = 500


# ============================================================================
# Technical Indicator Thresholds
# ============================================================================

# RSI overbought threshold (values >= this are considered overbought)
RSI_OVERBOUGHT = 70

# RSI oversold threshold (values <= this are considered oversold)
RSI_OVERSOLD = 30

# Funding rate high threshold (positive extreme)
FUNDING_RATE_HIGH = 0.01

# Funding rate low threshold (negative extreme)
FUNDING_RATE_LOW = -0.01


# ============================================================================
# Emoji Mappings
# ============================================================================

# Default emoji mappings for section headers
# Used by enhance_text_with_emojis() to add context-appropriate emojis
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

# RSI indicator emojis
RSI_EMOJI_OVERBOUGHT = "🔴"  # Red circle for overbought conditions
RSI_EMOJI_OVERSOLD = "🟢"  # Green circle for oversold conditions
RSI_EMOJI_NEUTRAL = "🟡"  # Yellow circle for neutral conditions


# ============================================================================
# Telegram HTML/Markdown Formatting
# ============================================================================

# HTML tags allowed by Telegram Bot API
# Reference: https://core.telegram.org/bots/api#html-style
TELEGRAM_ALLOWED_HTML_TAGS = ["b", "i", "u", "s", "code", "pre", "a"]

# MarkdownV2 special characters that need escaping
# Reference: https://core.telegram.org/bots/api#markdownv2-style
MARKDOWN_V2_SPECIAL_CHARS = r"_*[]()~`>#+-=|{}.!"


# ============================================================================
# Parse Modes
# ============================================================================

# Available parse modes for Telegram messages
PARSE_MODE_HTML = "HTML"
PARSE_MODE_MARKDOWN_V2 = "MarkdownV2"
PARSE_MODE_NONE = None
