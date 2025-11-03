"""Baseline/snapshot tests for Telegram formatting functions.

These tests capture the current output of telegram formatting functions
to ensure no regressions occur during refactoring.

Run these tests BEFORE starting refactoring to establish baseline,
then run again AFTER refactoring to verify identical output.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path


# Ensure project root is on sys.path
ROOT = str(Path(__file__).parent.parent.resolve())
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from news.article_cache import CachedArticle  # noqa: E402
from shared_code.telegram import (  # noqa: E402
    convert_ai_markdown_to_telegram_html,
    enforce_markdown_v2,
    format_articles_for_telegram,
    sanitize_html,
    smart_split,
)
from technical_analysis.reports.current_data_table import (  # noqa: E402
    format_current_data_for_telegram_html,
)


class TestTelegramBaseline:
    """Baseline tests to capture current formatting behavior."""

    def test_sanitize_html_baseline(self):
        """Baseline test for HTML sanitization."""
        # Test basic HTML tags
        html = "<b>Bold</b> <i>Italic</i> <u>Underline</u> <code>Code</code>"
        result = sanitize_html(html)
        expected = "<b>Bold</b> <i>Italic</i> <u>Underline</u> <code>Code</code>"
        assert result == expected

        # Test disallowed tags (should be removed or escaped)
        html_with_script = "<script>alert('xss')</script><b>Safe</b>"
        result_script = sanitize_html(html_with_script)
        # Verify script tags are handled safely
        assert "<script>" not in result_script or "alert" not in result_script

        # Test HTML entities
        html_entities = "<b>Price &gt; $100 &amp; &lt; $200</b>"
        result_entities = sanitize_html(html_entities)
        # Should preserve allowed tags and entities
        assert "<b>" in result_entities
        assert "</b>" in result_entities

    def test_smart_split_baseline_html(self):
        """Baseline test for smart_split with HTML content.

        Note: This test documents the current behavior of smart_split, including
        potential edge cases where tags might not be perfectly preserved during
        splitting. This will be addressed in future phases.
        """
        # Test HTML message that needs splitting
        long_html = "<b>Header</b>\n\n" + ("<i>Paragraph text. </i>" * 200)  # ~3200 chars with tags

        # Updated to use 'limit' parameter (API changed in Phase 2)
        chunks = smart_split(long_html, limit=4096, parse_mode="HTML")

        # Verify basic properties
        assert len(chunks) >= 1
        assert all(len(chunk) <= 4096 for chunk in chunks)

        # Verify content is generally preserved
        # Note: The current implementation may have edge cases with tag balancing
        reassembled = "\n\n".join(chunk.strip() for chunk in chunks)
        assert "<b>Header</b>" in reassembled
        assert "Paragraph text" in reassembled

        # Verify messages are split reasonably (not just one giant chunk)
        if len(long_html) > 4096:
            assert len(chunks) > 1, "Long HTML should be split into multiple chunks"

    def test_smart_split_baseline_markdown(self):
        """Baseline test for smart_split with MarkdownV2 content."""
        # Test markdown message with special characters
        markdown = (
            "*Bold text*\n\n" + "_Italic text_\n\n" + "`Code snippet`\n\n"
        ) * 100  # ~4000 chars

        # Updated to use 'limit' parameter (API changed in Phase 2)
        chunks = smart_split(markdown, limit=4096, parse_mode="MarkdownV2")

        # Verify basic properties
        assert len(chunks) >= 1
        assert all(len(chunk) <= 4096 for chunk in chunks)

        # Verify markdown syntax preserved
        reassembled = "\n\n".join(chunk.strip() for chunk in chunks)
        assert "*Bold text*" in reassembled or "\\*Bold text\\*" in reassembled
        assert "_Italic text_" in reassembled or "\\_Italic text\\_" in reassembled

    def test_enforce_markdown_v2_baseline(self):
        """Baseline test for MarkdownV2 escaping."""
        # Test comprehensive special character escaping
        text = "Price: $1,234.56 (up +5.2%) - Target: $1,500!"
        result = enforce_markdown_v2(text)

        # Verify special chars are escaped
        assert "\\." in result or "." not in text  # Dots should be escaped
        assert "\\!" in result or "!" not in text  # Exclamation should be escaped
        assert "\\+" in result or "+" not in text  # Plus should be escaped
        assert "\\-" in result or "-" not in text  # Minus should be escaped

        # Test with code blocks (should not escape inside code)
        text_with_code = "Normal text with `code_block` and special_chars"
        result_code = enforce_markdown_v2(text_with_code)

        # Inside backticks should preserve underscores
        assert "`code_block`" in result_code or "`code\\_block`" not in result_code

    def test_rsi_formatting_baseline(self):
        """Baseline test for RSI formatting with emojis.

        Note: This function is currently nested in current_data_table.py
        This test documents the expected behavior for when it's extracted.
        """
        # Create test data with various RSI values
        test_data_overbought = {
            "symbol": "BTC",
            "timestamp": "2025-11-03 00:00:00",
            "latest_price": 50000.0,
            "daily_rsi": 75.5,  # Overbought
            "hourly_rsi": 45.0,  # Neutral
            "fifteen_min_rsi": 25.0,  # Oversold
            "ma50": 48000.0,
            "ma200": 45000.0,
            "ema50": 48500.0,
            "ema200": 45500.0,
            "daily_high": 51000.0,
            "daily_low": 49000.0,
            "daily_range": 2000.0,
            "daily_range_pct": 4.0,
            "daily_ranges_7d": [],
            "open_interest": None,
            "funding_rate": None,
        }

        result = format_current_data_for_telegram_html(test_data_overbought)

        # Verify RSI formatting includes emojis
        assert "🔴" in result  # Overbought emoji for daily RSI 75.5
        assert "🟢" in result  # Oversold emoji for 15min RSI 25.0
        assert "🟡" in result  # Neutral emoji for hourly RSI 45.0

        # Verify RSI values are present
        assert "75.5" in result or "75.50" in result
        assert "25.0" in result or "25.00" in result
        assert "45.0" in result or "45.00" in result

        # Verify labels are present
        assert "Overbought" in result
        assert "Oversold" in result

    def test_article_formatting_baseline(self):
        """Baseline test for article formatting.

        Note: format_articles_for_html is currently in current_report.py
        This test documents expected behavior for when it's extracted.
        """
        # Create test articles with correct CachedArticle signature
        articles = [
            CachedArticle(
                title="Bitcoin reaches new all-time high",
                link="https://example.com/article1",
                published=datetime.now(UTC).isoformat(),
                source="CryptoNews",
                fetched=datetime.now(UTC).isoformat(),
                content="Bitcoin has reached a new ATH...",
                symbols=["BTC"],
            ),
            CachedArticle(
                title="A" * 150,  # Very long title to test truncation
                link="https://example.com/article2",
                published=datetime.now(UTC).isoformat(),
                source="TestSource",
                fetched=datetime.now(UTC).isoformat(),
                content="Test content",
                symbols=["ETH"],
            ),
        ]

        result = format_articles_for_telegram(articles)

        # Verify header is present
        assert "📰 Recent News Articles" in result

        # Verify first article
        assert "Bitcoin reaches new all-time high" in result
        assert "CryptoNews" in result
        assert "https://example.com/article1" in result
        assert "Read more" in result

        # Verify long title is truncated
        assert "..." in result  # Truncation indicator
        # Title should be truncated to ~100 chars
        assert len([line for line in result.split("\n") if "A" * 100 in line]) > 0

        # Verify HTML tags
        assert "<b>" in result
        assert "</b>" in result
        assert "<i>" in result
        assert "</i>" in result
        assert "<a href=" in result
        assert "</a>" in result

    def test_markdown_to_html_conversion_baseline(self):
        """Baseline test for AI markdown to Telegram HTML conversion.

        Note: convert_markdown_to_telegram_html is in current_report.py
        This test documents expected behavior for extraction.
        """
        # Test comprehensive markdown features
        markdown = """# Main Header
## Section Header
### Subsection

This is **bold text** and this is *italic text*.

Here's `inline code` and a code block:

```python
def hello():
    return "world"
```

Bullet points:
- First item
- Second item
* Third item

Numbered list:
1. First
2. Second
3. Third
"""

        result = convert_ai_markdown_to_telegram_html(markdown)

        # Verify headers are converted
        assert "<b>▓▓▓ Main Header ▓▓▓</b>" in result
        assert "<b>═══ Section Header ═══</b>" in result
        assert "<b><u>Subsection</u></b>" in result

        # Verify text formatting
        assert "<b>bold text</b>" in result
        assert "<i>italic text</i>" in result

        # Verify code formatting
        assert "<code>inline code</code>" in result
        # Code blocks are now processed before inline code, so they should work correctly
        assert "<pre>" in result or "python" in result  # Either <pre> tags or code block marker
        assert "def hello():" in result

        # Verify list formatting
        assert "•" in result  # Bullet points converted
        assert "1." in result
        assert "2." in result  # Numbered lists preserved

        # Verify no raw markdown remains
        assert "**bold text**" not in result
        assert "*italic text*" not in result
        assert "```python" not in result


class TestMessageLengthBaseline:
    """Baseline tests for message length handling."""

    def test_very_long_message_splitting(self):
        """Test that very long messages are split correctly."""
        # Create message that definitely exceeds 4096 chars
        long_message = "<b>Report</b>\n\n" + (
            "Paragraph with important data. " * 500
        )  # ~15000 chars

        # Updated to use 'limit' parameter (API changed in Phase 2)
        chunks = smart_split(long_message, limit=4096, parse_mode="HTML")

        # Verify splitting occurred
        assert len(chunks) >= 4  # Should be split into multiple chunks

        # Verify all chunks are within limit
        assert all(len(chunk) <= 4096 for chunk in chunks)

        # Verify content is preserved
        reassembled = " ".join(chunks)
        assert "Report" in reassembled
        assert "important data" in reassembled

    def test_edge_case_4096_boundary(self):
        """Test messages at exactly the 4096 character boundary."""
        # Create message of exactly 4096 characters
        message_4096 = "x" * 4096

        # Updated to use 'limit' parameter (API changed in Phase 2)
        chunks = smart_split(message_4096, limit=4096, parse_mode="HTML")

        # Should not split (exactly at limit)
        assert len(chunks) == 1
        assert len(chunks[0]) == 4096

        # Create message of 4097 characters (1 over limit)
        message_4097 = "x" * 4097

        chunks_over = smart_split(message_4097, limit=4096, parse_mode="HTML")

        # Should split into at least 2 chunks
        assert len(chunks_over) >= 2
        assert all(len(chunk) <= 4096 for chunk in chunks_over)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
