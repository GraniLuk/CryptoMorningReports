"""Tests for telegram formatting utilities.

This module tests the high-level formatting functions in the telegram package,
including RSI formatting, article formatting, price formatting, and markdown conversion.
"""

from shared_code.telegram import (
    convert_ai_markdown_to_telegram_html,
    enhance_text_with_emojis,
    format_articles_for_telegram,
    format_funding_rate_with_emoji,
    format_price_with_currency,
    format_rsi_with_emoji,
)
from shared_code.telegram.formatters import HTMLFormatter, MarkdownV2Formatter


# ============================================================================
# format_rsi_with_emoji() Tests
# ============================================================================


class TestFormatRsiWithEmoji:
    """Test RSI value formatting with emoji indicators."""

    def test_overbought_default_threshold(self):
        """Test that RSI >= 70 shows overbought emoji and label."""
        result = format_rsi_with_emoji(75.5)
        assert result == "🔴 75.50 (Overbought)"

    def test_overbought_at_threshold(self):
        """Test that RSI = 70 exactly shows overbought."""
        result = format_rsi_with_emoji(70.0)
        assert result == "🔴 70.00 (Overbought)"

    def test_oversold_default_threshold(self):
        """Test that RSI <= 30 shows oversold emoji and label."""
        result = format_rsi_with_emoji(25.3)
        assert result == "🟢 25.30 (Oversold)"

    def test_oversold_at_threshold(self):
        """Test that RSI = 30 exactly shows oversold."""
        result = format_rsi_with_emoji(30.0)
        assert result == "🟢 30.00 (Oversold)"

    def test_neutral_range(self):
        """Test that RSI in neutral range (30-70) shows neutral emoji."""
        result = format_rsi_with_emoji(50.0)
        assert result == "🟡 50.00"

        result = format_rsi_with_emoji(31.0)
        assert result == "🟡 31.00"

        result = format_rsi_with_emoji(69.9)
        assert result == "🟡 69.90"

    def test_none_value(self):
        """Test that None returns 'N/A'."""
        result = format_rsi_with_emoji(None)
        assert result == "N/A"

    def test_custom_thresholds(self):
        """Test using custom overbought/oversold thresholds."""
        # More aggressive thresholds
        result = format_rsi_with_emoji(65.0, overbought_threshold=65, oversold_threshold=35)
        assert result == "🔴 65.00 (Overbought)"

        result = format_rsi_with_emoji(35.0, overbought_threshold=65, oversold_threshold=35)
        assert result == "🟢 35.00 (Oversold)"

        result = format_rsi_with_emoji(50.0, overbought_threshold=65, oversold_threshold=35)
        assert result == "🟡 50.00"

    def test_decimal_precision(self):
        """Test that values are formatted to 2 decimal places."""
        result = format_rsi_with_emoji(45.123456)
        assert result == "🟡 45.12"

        result = format_rsi_with_emoji(75.999)
        assert result == "🔴 76.00 (Overbought)"


# ============================================================================
# enhance_text_with_emojis() Tests
# ============================================================================


class TestEnhanceTextWithEmojis:
    """Test emoji enhancement for markdown headers."""

    def test_single_header_with_matching_keyword(self):
        """Test that matching keyword gets emoji prepended."""
        text = "## Trend Analysis"
        result = enhance_text_with_emojis(text)
        assert "📈" in result
        assert "## 📈 Trend Analysis" in result

    def test_multiple_headers(self):
        """Test multiple headers with different keywords."""
        text = """## Trend Analysis
Some content here.
### Price Movement
More content.
### Risk Assessment"""
        result = enhance_text_with_emojis(text)
        assert "📈 Trend Analysis" in result
        assert "💰 Price Movement" in result
        assert "⚠️ Risk Assessment" in result

    def test_header_already_has_emoji(self):
        """Test that emoji is not duplicated if already present."""
        text = "## 📈 Trend Analysis"
        result = enhance_text_with_emojis(text)
        # Should not duplicate the emoji
        assert result.count("📈") == 1

    def test_custom_emoji_map(self):
        """Test using a custom emoji mapping."""
        text = "## Custom Section\n### Another Section"
        custom_map = {
            "Custom": "🎨",
            "Another": "🔧",
        }
        result = enhance_text_with_emojis(text, emoji_map=custom_map)
        assert "🎨 Custom Section" in result
        assert "🔧 Another Section" in result

    def test_case_insensitive_matching(self):
        """Test that keyword matching is case-insensitive."""
        text = "## TREND analysis"
        result = enhance_text_with_emojis(text)
        assert "📈" in result

    def test_no_matching_keywords(self):
        """Test that headers without matching keywords remain unchanged."""
        text = "## Unknown Topic"
        result = enhance_text_with_emojis(text)
        assert result == "## Unknown Topic"

    def test_different_header_levels(self):
        """Test that emojis work for all header levels (#, ##, ###, etc)."""
        text = """# Trend
## Trend
### Trend
#### Trend"""
        result = enhance_text_with_emojis(text)
        # All should get emojis
        assert result.count("📈") == 4

    def test_empty_text(self):
        """Test that empty text is handled correctly."""
        result = enhance_text_with_emojis("")
        assert result == ""


# ============================================================================
# convert_ai_markdown_to_telegram_html() Tests
# ============================================================================


class TestConvertAiMarkdownToTelegramHtml:
    """Test markdown to HTML conversion for AI-generated text."""

    def test_headers_level_1(self):
        """Test level 1 header conversion."""
        result = convert_ai_markdown_to_telegram_html("# Main Header")
        assert "<b>▓▓▓ Main Header ▓▓▓</b>" in result

    def test_headers_level_2(self):
        """Test level 2 header conversion."""
        result = convert_ai_markdown_to_telegram_html("## Section Header")
        assert "<b>═══ Section Header ═══</b>" in result

    def test_headers_level_3(self):
        """Test level 3 header conversion."""
        result = convert_ai_markdown_to_telegram_html("### Subsection")
        assert "<b><u>Subsection</u></b>" in result

    def test_bold_text(self):
        """Test bold text conversion."""
        result = convert_ai_markdown_to_telegram_html("This is **bold** text")
        assert "<b>bold</b>" in result

    def test_italic_text_asterisk(self):
        """Test italic text with asterisks."""
        result = convert_ai_markdown_to_telegram_html("This is *italic* text")
        assert "<i>italic</i>" in result

    def test_italic_text_underscore(self):
        """Test italic text with underscores."""
        result = convert_ai_markdown_to_telegram_html("This is _italic_ text")
        assert "<i>italic</i>" in result

    def test_inline_code(self):
        """Test inline code conversion."""
        result = convert_ai_markdown_to_telegram_html("Use `code` here")
        assert "<code>code</code>" in result

    def test_code_block(self):
        """Test code block conversion."""
        markdown = """```python
def hello():
    print("world")
```"""
        result = convert_ai_markdown_to_telegram_html(markdown)
        assert "<pre>" in result
        assert "</pre>" in result

    def test_bullet_points(self):
        """Test bullet point conversion."""
        markdown = """- First item
- Second item
* Third item"""
        result = convert_ai_markdown_to_telegram_html(markdown)
        assert "  • First item" in result
        assert "  • Second item" in result
        assert "  • Third item" in result

    def test_numbered_list(self):
        """Test numbered list conversion."""
        markdown = """1. First
2. Second
3. Third"""
        result = convert_ai_markdown_to_telegram_html(markdown)
        assert "  1. First" in result
        assert "  2. Second" in result
        assert "  3. Third" in result

    def test_html_escaping(self):
        """Test that HTML special characters are escaped."""
        result = convert_ai_markdown_to_telegram_html("Test <script> & 'quotes'")
        # Should escape HTML special characters
        assert "&lt;script&gt;" in result
        assert "&amp;" in result
        # Quotes might be escaped too
        assert "&#x27;" in result or "'" in result

    def test_section_spacing(self):
        """Test that section headers get spacing."""
        markdown = "## Section One\n## Section Two"
        result = convert_ai_markdown_to_telegram_html(markdown)
        # Should have newlines around section headers
        assert "\n<b>═══ Section One ═══</b>\n" in result

    def test_complex_markdown(self):
        """Test complex markdown with multiple features."""
        markdown = """# Main Title

## Analysis

This is **bold** and this is *italic*.

### Key Points

- Point **one**
- Point `two`

```
code block
```"""
        result = convert_ai_markdown_to_telegram_html(markdown)
        assert "<b>▓▓▓ Main Title ▓▓▓</b>" in result
        assert "<b>═══ Analysis ═══</b>" in result
        assert "<b>bold</b>" in result
        assert "<i>italic</i>" in result
        assert "<b><u>Key Points</u></b>" in result
        assert "  • Point" in result
        assert "<pre>" in result


# ============================================================================
# format_articles_for_telegram() Tests
# ============================================================================


class MockArticle:
    """Mock CachedArticle for testing."""

    def __init__(self, title, published, source, link):
        """Initialize mock article with test data."""
        self.title = title
        self.published = published
        self.source = source
        self.link = link


class TestFormatArticlesForTelegram:
    """Test article formatting for Telegram."""

    def test_empty_articles_list(self):
        """Test that empty list returns empty string."""
        result = format_articles_for_telegram([])
        assert result == ""

    def test_single_article_html(self):
        """Test formatting a single article with HTML formatter."""
        articles = [
            MockArticle(
                title="Bitcoin Surges",
                published="2024-01-15T10:30:00",
                source="CoinDesk",
                link="https://example.com/article",
            ),
        ]
        result = format_articles_for_telegram(articles, HTMLFormatter())
        assert "<b>📰 Recent News Articles</b>" in result
        assert "<b>1. Bitcoin Surges</b>" in result
        assert "<i>🕒 2024-01-15 10:30 UTC | 📡 CoinDesk</i>" in result
        assert '<a href="https://example.com/article">Read more</a>' in result

    def test_single_article_markdownv2(self):
        """Test formatting a single article with MarkdownV2 formatter."""
        articles = [
            MockArticle(
                title="Bitcoin Surges",
                published="2024-01-15T10:30:00",
                source="CoinDesk",
                link="https://example.com/article",
            ),
        ]
        result = format_articles_for_telegram(articles, MarkdownV2Formatter())
        # MarkdownV2 uses single * for bold, not **
        assert "*📰 Recent News Articles*" in result
        assert "*1. Bitcoin Surges*" in result
        assert "[Read more](https://example.com/article)" in result

    def test_multiple_articles(self):
        """Test formatting multiple articles."""
        articles = [
            MockArticle("Article 1", "2024-01-15T10:00:00", "Source1", "http://1.com"),
            MockArticle("Article 2", "2024-01-15T11:00:00", "Source2", "http://2.com"),
            MockArticle("Article 3", "2024-01-15T12:00:00", "Source3", "http://3.com"),
        ]
        result = format_articles_for_telegram(articles, HTMLFormatter())
        assert "<b>1. Article 1</b>" in result
        assert "<b>2. Article 2</b>" in result
        assert "<b>3. Article 3</b>" in result

    def test_title_truncation_default(self):
        """Test that long titles are truncated at default length."""
        long_title = "A" * 150  # Longer than default ARTICLE_TITLE_MAX_LENGTH (100)
        articles = [MockArticle(long_title, "2024-01-15T10:00:00", "Source", "http://test.com")]
        result = format_articles_for_telegram(articles)
        # Should be truncated to 100 chars + "..."
        assert "A" * 100 + "..." in result
        assert "A" * 150 not in result

    def test_title_truncation_custom(self):
        """Test title truncation with custom max length."""
        long_title = "B" * 100
        articles = [MockArticle(long_title, "2024-01-15T10:00:00", "Source", "http://test.com")]
        result = format_articles_for_telegram(articles, max_title_length=50)
        assert "B" * 50 + "..." in result

    def test_default_formatter_is_html(self):
        """Test that HTML formatter is used by default."""
        articles = [MockArticle("Test", "2024-01-15T10:00:00", "Source", "http://test.com")]
        result = format_articles_for_telegram(articles)
        # HTML tags should be present
        assert "<b>" in result
        assert "<i>" in result
        assert "<a href=" in result

    def test_invalid_date_format(self):
        """Test handling of invalid date formats."""
        articles = [MockArticle("Test", "invalid-date", "Source", "http://test.com")]
        result = format_articles_for_telegram(articles)
        # Should fallback to the raw string
        assert "invalid-date" in result


# ============================================================================
# format_price_with_currency() Tests
# ============================================================================


class TestFormatPriceWithCurrency:
    """Test price formatting with currency symbols."""

    def test_default_currency_symbol(self):
        """Test formatting with default $ symbol."""
        result = format_price_with_currency(1234.5678)
        assert result == "$1,234.5678"

    def test_custom_currency_symbol(self):
        """Test formatting with custom currency symbol."""
        result = format_price_with_currency(1000.0, currency_symbol="€")
        assert result == "€1,000.0000"

    def test_custom_decimal_places(self):
        """Test formatting with custom decimal places."""
        result = format_price_with_currency(1234.5678, decimal_places=2)
        assert result == "$1,234.57"

        result = format_price_with_currency(1234.5678, decimal_places=8)
        assert result == "$1,234.56780000"

    def test_none_value(self):
        """Test that None returns 'N/A'."""
        result = format_price_with_currency(None)
        assert result == "N/A"

    def test_small_values(self):
        """Test formatting very small cryptocurrency prices."""
        result = format_price_with_currency(0.00012345, decimal_places=8)
        assert result == "$0.00012345"

    def test_large_values(self):
        """Test formatting large values with thousand separators."""
        result = format_price_with_currency(1234567.89, decimal_places=2)
        assert result == "$1,234,567.89"

    def test_zero_value(self):
        """Test formatting zero value."""
        result = format_price_with_currency(0.0, decimal_places=2)
        assert result == "$0.00"


# ============================================================================
# format_funding_rate_with_emoji() Tests
# ============================================================================


class TestFormatFundingRateWithEmoji:
    """Test funding rate formatting with emoji indicators."""

    def test_high_positive_rate(self):
        """Test high positive funding rate (expensive to long)."""
        result = format_funding_rate_with_emoji(0.015)
        assert result == "🔴 1.50%"

    def test_high_negative_rate(self):
        """Test high negative funding rate (expensive to short)."""
        result = format_funding_rate_with_emoji(-0.012)
        assert result == "🟢 -1.20%"

    def test_neutral_rate(self):
        """Test neutral funding rate."""
        result = format_funding_rate_with_emoji(0.0005)
        assert result == "🟡 0.05%"

    def test_at_high_threshold(self):
        """Test funding rate exactly at high threshold."""
        result = format_funding_rate_with_emoji(0.01)  # Default high threshold
        assert result == "🔴 1.00%"

    def test_at_low_threshold(self):
        """Test funding rate exactly at low threshold."""
        result = format_funding_rate_with_emoji(-0.01)  # Default low threshold
        assert result == "🟢 -1.00%"

    def test_custom_thresholds(self):
        """Test with custom high/low thresholds."""
        result = format_funding_rate_with_emoji(0.005, high_threshold=0.005, low_threshold=-0.005)
        assert result == "🔴 0.50%"

        result = format_funding_rate_with_emoji(-0.005, high_threshold=0.005, low_threshold=-0.005)
        assert result == "🟢 -0.50%"

    def test_without_percentage(self):
        """Test formatting without percentage conversion."""
        result = format_funding_rate_with_emoji(0.015, as_percentage=False)
        assert result == "🔴 0.0150"

        result = format_funding_rate_with_emoji(-0.012, as_percentage=False)
        assert result == "🟢 -0.0120"

    def test_none_value(self):
        """Test that None returns 'N/A'."""
        result = format_funding_rate_with_emoji(None)
        assert result == "N/A"

    def test_zero_funding_rate(self):
        """Test zero funding rate (neutral)."""
        result = format_funding_rate_with_emoji(0.0)
        assert result == "🟡 0.00%"


# ============================================================================
# Integration Tests
# ============================================================================


class TestFormattingUtilsIntegration:
    """Integration tests combining multiple formatting utilities."""

    def test_rsi_and_price_together(self):
        """Test formatting RSI and price in a report context."""
        rsi = format_rsi_with_emoji(75.5)
        price = format_price_with_currency(12345.67, decimal_places=2)

        assert rsi == "🔴 75.50 (Overbought)"
        assert price == "$12,345.67"

        # Could be used in a report like:
        report = f"Price: {price}\nRSI: {rsi}"
        assert "Price: $12,345.67" in report
        assert "RSI: 🔴 75.50 (Overbought)" in report

    def test_markdown_with_emojis_pipeline(self):
        """Test the full pipeline: enhance emojis -> convert to HTML."""
        markdown = """## Trend Analysis
Current market shows **bullish** momentum.

### Risk Assessment
Proceed with *caution*."""

        # First enhance with emojis
        enhanced = enhance_text_with_emojis(markdown)
        assert "📈" in enhanced
        assert "⚠️" in enhanced

        # Then convert to HTML
        html = convert_ai_markdown_to_telegram_html(enhanced)
        assert "<b>═══ 📈 Trend Analysis ═══</b>" in html
        assert "<b><u>⚠️ Risk Assessment</u></b>" in html
        assert "<b>bullish</b>" in html
        assert "<i>caution</i>" in html
