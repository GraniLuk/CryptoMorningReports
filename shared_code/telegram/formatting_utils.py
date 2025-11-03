"""Formatting utilities for Telegram messages.

This module contains high-level formatting functions for common patterns
like RSI indicators, articles, price displays, and markdown conversion.
"""

import html as html_module
import re
from datetime import datetime

from .constants import (
    ARTICLE_TITLE_MAX_LENGTH,
    DEFAULT_EMOJI_MAP,
    FUNDING_RATE_HIGH,
    FUNDING_RATE_LOW,
    RSI_EMOJI_NEUTRAL,
    RSI_EMOJI_OVERBOUGHT,
    RSI_EMOJI_OVERSOLD,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
)
from .formatters import TelegramFormatter, get_formatter


try:
    from news.article_cache import CachedArticle
except ImportError:
    # Fallback for when news module is not available
    CachedArticle = None  # type: ignore


def format_rsi_with_emoji(
    rsi_value: float | None,
    overbought_threshold: float = RSI_OVERBOUGHT,
    oversold_threshold: float = RSI_OVERSOLD,
) -> str:
    """Format RSI value with appropriate emoji and label.

    Args:
        rsi_value: RSI value to format (0-100 scale), or None
        overbought_threshold: Threshold above which RSI is considered overbought (default: 70)
        oversold_threshold: Threshold below which RSI is considered oversold (default: 30)

    Returns:
        Formatted string with emoji and optional label:
        - "N/A" if rsi_value is None
        - "🔴 XX.XX (Overbought)" if >= overbought_threshold
        - "🟢 XX.XX (Oversold)" if <= oversold_threshold
        - "🟡 XX.XX" otherwise

    Examples:
        >>> format_rsi_with_emoji(75.5)
        '🔴 75.50 (Overbought)'
        >>> format_rsi_with_emoji(25.3)
        '🟢 25.30 (Oversold)'
        >>> format_rsi_with_emoji(50.0)
        '🟡 50.00'
        >>> format_rsi_with_emoji(None)
        'N/A'
    """
    if rsi_value is None:
        return "N/A"

    rsi_str = f"{rsi_value:.2f}"

    if rsi_value >= overbought_threshold:
        return f"{RSI_EMOJI_OVERBOUGHT} {rsi_str} (Overbought)"
    if rsi_value <= oversold_threshold:
        return f"{RSI_EMOJI_OVERSOLD} {rsi_str} (Oversold)"
    return f"{RSI_EMOJI_NEUTRAL} {rsi_str}"


def enhance_text_with_emojis(
    text: str,
    emoji_map: dict[str, str] | None = None,
) -> str:
    """Add emojis to markdown section headers based on keyword matching.

    Scans markdown headers (lines starting with #) and prepends emojis
    if the header contains certain keywords and doesn't already have the emoji.

    Args:
        text: Markdown text with headers to enhance
        emoji_map: Dictionary mapping keywords to emojis. If None, uses DEFAULT_EMOJI_MAP.
            Example: {"Trend": "📈", "Price": "💰", "Risk": "⚠️"}

    Returns:
        Text with emojis added to matching headers

    Examples:
        >>> text = "## Trend Analysis\\nBullish trend detected"
        >>> enhance_text_with_emojis(text)
        '## 📈 Trend Analysis\\nBullish trend detected'

        >>> text = "### Risk Assessment"
        >>> enhance_text_with_emojis(text, {"Risk": "⚠️"})
        '### ⚠️ Risk Assessment'
    """
    if emoji_map is None:
        emoji_map = DEFAULT_EMOJI_MAP

    def add_emoji(match):
        """Add emoji to header text if keyword matches."""
        header_text = match.group(2)
        for keyword, emoji in emoji_map.items():
            if keyword.lower() in header_text.lower() and emoji not in header_text:
                return f"{emoji} {header_text}"
        return header_text

    # Match markdown headers and apply emoji addition
    # Pattern matches: # header or ## header (with optional space)
    def replace_header(match):
        """Replace header with emoji-enhanced version."""
        hashes = match.group(1)
        header_text = match.group(2)
        enhanced_header = add_emoji(match)
        # Only add space if header_text doesn't start with emoji
        if enhanced_header and enhanced_header != header_text:
            return f"{hashes} {enhanced_header}"
        return f"{hashes} {header_text}"

    return re.sub(
        r"^(#+)\s*(.+)$",
        replace_header,
        text,
        flags=re.MULTILINE,
    )


def convert_ai_markdown_to_telegram_html(markdown_text: str) -> str:
    """Convert AI-generated markdown text to Telegram-compatible HTML.

    Designed specifically for AI-generated analysis text. Converts common
    markdown patterns to HTML tags supported by Telegram's parse_mode='HTML'.

    Supported Markdown Features:
        - Headers: #, ##, ### converted to styled <b> and <u> HTML tags
        - Bold: **text** converted to <b>text</b>
        - Italic: *text* and _text_ converted to <i>text</i>
        - Inline code: `text` converted to <code>text</code>
        - Code blocks: ```text``` converted to <pre>text</pre>
        - Bullet points: - and * converted to •
        - Numbered lists: 1. 2. etc. preserved with indentation

    Limitations:
        - Nested markdown (e.g., bold inside italic) may not be fully supported
        - Complex tables, links, images not converted
        - HTML escaping is minimal; ensure input is from trusted AI source

    Args:
        markdown_text: Markdown formatted text from AI analysis

    Returns:
        HTML formatted text compatible with Telegram's HTML parse mode

    Examples:
        >>> convert_ai_markdown_to_telegram_html("## Analysis\\n**Bold** text")
        '<b>═══ Analysis ═══</b>\\n<b>Bold</b> text'
    """
    # First escape HTML special characters to prevent Telegram parsing errors
    html_text = html_module.escape(markdown_text)

    # Convert code blocks FIRST (before inline code)
    html_text = re.sub(r"```[\w]*\n(.*?)\n```", r"<pre>\1</pre>", html_text, flags=re.DOTALL)

    # Convert headers with decorative characters
    html_text = re.sub(r"^### (.+)$", r"<b><u>\1</u></b>", html_text, flags=re.MULTILINE)
    html_text = re.sub(r"^## (.+)$", r"<b>═══ \1 ═══</b>", html_text, flags=re.MULTILINE)
    html_text = re.sub(r"^# (.+)$", r"<b>▓▓▓ \1 ▓▓▓</b>", html_text, flags=re.MULTILINE)

    # Convert bold text
    html_text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html_text)

    # Convert italic text
    html_text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", html_text)
    html_text = re.sub(r"_(.+?)_", r"<i>\1</i>", html_text)

    # Convert inline code (after code blocks)
    html_text = re.sub(r"`(.+?)`", r"<code>\1</code>", html_text)

    # Convert bullet points with • for better visibility
    html_text = re.sub(r"^\s*[-*]\s+(.+)$", r"  • \1", html_text, flags=re.MULTILINE)

    # Convert numbered lists
    html_text = re.sub(r"^\s*(\d+)\.\s+(.+)$", r"  \1. \2", html_text, flags=re.MULTILINE)

    # Add spacing around section headers
    return re.sub(r"(<b>═══.*?═══</b>)", r"\n\1\n", html_text)


def format_articles_for_telegram(
    articles: list,
    formatter: TelegramFormatter | None = None,
    max_title_length: int = ARTICLE_TITLE_MAX_LENGTH,
) -> str:
    """Format cached news articles for Telegram using specified formatter.

    Args:
        articles: List of CachedArticle instances with title, published, source, link
        formatter: TelegramFormatter instance (HTML or MarkdownV2). If None, uses HTML.
        max_title_length: Maximum length for article titles before truncation

    Returns:
        Formatted string with article information ready for Telegram

    Examples:
        >>> from shared_code.telegram import HTMLFormatter
        >>> articles = [CachedArticle(title="Bitcoin News", ...)]
        >>> format_articles_for_telegram(articles, HTMLFormatter())
        '<b>📰 Recent News Articles</b>\\n\\n<b>1. Bitcoin News</b>\\n...'
    """
    if not articles:
        return ""

    if formatter is None:
        formatter = get_formatter("HTML")

    # Format header
    result = formatter.format_bold("📰 Recent News Articles") + "\n\n"

    for i, article in enumerate(articles, 1):
        # Parse published date to make it more readable
        try:
            published_dt = datetime.fromisoformat(article.published)
            time_str = published_dt.strftime("%Y-%m-%d %H:%M UTC")
        except (ValueError, AttributeError):
            time_str = article.published

        # Truncate title if too long
        title = article.title
        if len(title) > max_title_length:
            title = title[:max_title_length] + "..."

        # Format article entry
        result += formatter.format_bold(f"{i}. {title}") + "\n"
        result += formatter.format_italic(f"🕒 {time_str} | 📡 {article.source}") + "\n"
        result += formatter.format_link("Read more", article.link) + "\n\n"

    return result


def format_price_with_currency(
    price: float | None,
    currency_symbol: str = "$",
    decimal_places: int = 4,
) -> str:
    """Format a price value with currency symbol and thousand separators.

    Args:
        price: Price value to format, or None
        currency_symbol: Currency symbol to prepend (default: "$")
        decimal_places: Number of decimal places to display (default: 4)

    Returns:
        Formatted price string with currency symbol and separators,
        or "N/A" if price is None

    Examples:
        >>> format_price_with_currency(1234.5678)
        '$1,234.5678'
        >>> format_price_with_currency(0.0001234, decimal_places=8)
        '$0.00012340'
        >>> format_price_with_currency(None)
        'N/A'
        >>> format_price_with_currency(1000, currency_symbol="€", decimal_places=2)
        '€1,000.00'
    """
    if price is None:
        return "N/A"

    return f"{currency_symbol}{price:,.{decimal_places}f}"


def format_funding_rate_with_emoji(
    funding_rate: float | None,
    high_threshold: float = FUNDING_RATE_HIGH,
    low_threshold: float = FUNDING_RATE_LOW,
    as_percentage: bool = True,
) -> str:
    """Format funding rate with emoji based on threshold.

    Args:
        funding_rate: Funding rate value (typically -0.01 to 0.01), or None
        high_threshold: Threshold above which rate is considered high (default: 0.01)
        low_threshold: Threshold below which rate is considered low (default: -0.01)
        as_percentage: If True, multiply by 100 and add % sign (default: True)

    Returns:
        Formatted string with emoji:
        - "N/A" if funding_rate is None
        - "🔴 X.XX%" if >= high_threshold (expensive to long)
        - "🟢 X.XX%" if <= low_threshold (expensive to short)
        - "🟡 X.XX%" otherwise (neutral)

    Examples:
        >>> format_funding_rate_with_emoji(0.015)
        '🔴 1.50%'
        >>> format_funding_rate_with_emoji(-0.012)
        '🟢 -1.20%'
        >>> format_funding_rate_with_emoji(0.0005)
        '🟡 0.05%'
        >>> format_funding_rate_with_emoji(0.0005, as_percentage=False)
        '🟡 0.0005'
        >>> format_funding_rate_with_emoji(None)
        'N/A'
    """
    if funding_rate is None:
        return "N/A"

    # Format the value
    if as_percentage:
        value_str = f"{funding_rate * 100:.2f}%"
    else:
        value_str = f"{funding_rate:.4f}"

    # Select emoji based on threshold
    if funding_rate >= high_threshold:
        emoji = "🔴"  # High positive funding rate
    elif funding_rate <= low_threshold:
        emoji = "🟢"  # High negative funding rate
    else:
        emoji = "🟡"  # Neutral funding rate

    return f"{emoji} {value_str}"
