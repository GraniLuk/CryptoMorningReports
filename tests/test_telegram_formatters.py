"""Tests for telegram package formatters.

These tests verify the formatter abstraction layer and ensure
both HTML and MarkdownV2 formatters work correctly.
"""

import sys
from pathlib import Path

import pytest


# Ensure project root is on sys.path
ROOT = str(Path(__file__).parent.parent.resolve())
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shared_code.telegram import (  # noqa: E402
    HTMLFormatter,
    MarkdownV2Formatter,
    get_formatter,
)


class TestGetFormatter:
    """Tests for the get_formatter factory function."""

    def test_get_formatter_html(self):
        """Test getting HTML formatter."""
        formatter = get_formatter("HTML")
        assert isinstance(formatter, HTMLFormatter)

    def test_get_formatter_markdown_v2(self):
        """Test getting MarkdownV2 formatter."""
        formatter = get_formatter("MarkdownV2")
        assert isinstance(formatter, MarkdownV2Formatter)

    def test_get_formatter_none_defaults_to_html(self):
        """Test that None defaults to HTML formatter."""
        formatter = get_formatter(None)
        assert isinstance(formatter, HTMLFormatter)

    def test_get_formatter_empty_string_defaults_to_html(self):
        """Test that empty string defaults to HTML formatter."""
        formatter = get_formatter("")
        assert isinstance(formatter, HTMLFormatter)

    def test_get_formatter_invalid_raises_error(self):
        """Test that invalid parse mode raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported parse_mode"):
            get_formatter("INVALID")


class TestHTMLFormatter:
    """Tests for HTMLFormatter."""

    def test_format_bold(self):
        """Test HTML bold formatting."""
        formatter = HTMLFormatter()
        assert formatter.format_bold("Test") == "<b>Test</b>"

    def test_format_italic(self):
        """Test HTML italic formatting."""
        formatter = HTMLFormatter()
        assert formatter.format_italic("Test") == "<i>Test</i>"

    def test_format_underline(self):
        """Test HTML underline formatting."""
        formatter = HTMLFormatter()
        assert formatter.format_underline("Test") == "<u>Test</u>"

    def test_format_strikethrough(self):
        """Test HTML strikethrough formatting."""
        formatter = HTMLFormatter()
        assert formatter.format_strikethrough("Test") == "<s>Test</s>"

    def test_format_code(self):
        """Test HTML inline code formatting."""
        formatter = HTMLFormatter()
        assert formatter.format_code("code") == "<code>code</code>"

    def test_format_code_block(self):
        """Test HTML code block formatting."""
        formatter = HTMLFormatter()
        result = formatter.format_code_block("def hello():\n    pass")
        assert result == "<pre>def hello():\n    pass</pre>"

    def test_format_link(self):
        """Test HTML link formatting."""
        formatter = HTMLFormatter()
        result = formatter.format_link("Click here", "https://example.com")
        assert result == '<a href="https://example.com">Click here</a>'

    def test_format_header_level_1(self):
        """Test HTML header level 1."""
        formatter = HTMLFormatter()
        result = formatter.format_header("Title", level=1)
        assert result == "<b>▓▓▓ Title ▓▓▓</b>"

    def test_format_header_level_2(self):
        """Test HTML header level 2."""
        formatter = HTMLFormatter()
        result = formatter.format_header("Section", level=2)
        assert result == "<b>═══ Section ═══</b>"

    def test_format_header_level_3(self):
        """Test HTML header level 3."""
        formatter = HTMLFormatter()
        result = formatter.format_header("Subsection", level=3)
        assert result == "<b><u>Subsection</u></b>"


class TestMarkdownV2Formatter:
    """Tests for MarkdownV2Formatter."""

    def test_format_bold(self):
        """Test MarkdownV2 bold formatting."""
        formatter = MarkdownV2Formatter()
        assert formatter.format_bold("Test") == "*Test*"

    def test_format_italic(self):
        """Test MarkdownV2 italic formatting."""
        formatter = MarkdownV2Formatter()
        assert formatter.format_italic("Test") == "_Test_"

    def test_format_underline(self):
        """Test MarkdownV2 underline formatting."""
        formatter = MarkdownV2Formatter()
        assert formatter.format_underline("Test") == "__Test__"

    def test_format_strikethrough(self):
        """Test MarkdownV2 strikethrough formatting."""
        formatter = MarkdownV2Formatter()
        assert formatter.format_strikethrough("Test") == "~Test~"

    def test_format_code(self):
        """Test MarkdownV2 inline code formatting."""
        formatter = MarkdownV2Formatter()
        assert formatter.format_code("code") == "`code`"

    def test_format_code_block_without_language(self):
        """Test MarkdownV2 code block without language."""
        formatter = MarkdownV2Formatter()
        result = formatter.format_code_block("def hello():\n    pass")
        assert result == "```\ndef hello():\n    pass\n```"

    def test_format_code_block_with_language(self):
        """Test MarkdownV2 code block formatting."""
        formatter = MarkdownV2Formatter()
        result = formatter.format_code_block("def hello():\n    pass")
        assert result == "```\ndef hello():\n    pass\n```"

    def test_format_link(self):
        """Test MarkdownV2 link formatting."""
        formatter = MarkdownV2Formatter()
        result = formatter.format_link("Click here", "https://example.com")
        assert result == "[Click here](https://example.com)"

    def test_format_header_level_1(self):
        """Test MarkdownV2 header level 1."""
        formatter = MarkdownV2Formatter()
        result = formatter.format_header("Title", level=1)
        assert result == "*▓▓▓ Title ▓▓▓*"

    def test_format_header_level_2(self):
        """Test MarkdownV2 header level 2."""
        formatter = MarkdownV2Formatter()
        result = formatter.format_header("Section", level=2)
        assert result == "*═══ Section ═══*"

    def test_format_header_level_3(self):
        """Test MarkdownV2 header level 3."""
        formatter = MarkdownV2Formatter()
        result = formatter.format_header("Subsection", level=3)
        assert result == "__Subsection__"


class TestFormatterIntegration:
    """Integration tests for formatter usage patterns."""

    def test_building_complex_html_message(self):
        """Test building a complex message with HTML formatter."""
        formatter = get_formatter("HTML")

        message = (
            formatter.format_header("Market Report", level=1)
            + "\n\n"
            + formatter.format_bold("BTC Price:")
            + " $50,000\n"
            + formatter.format_italic("Change:")
            + " +5%\n\n"
            + formatter.format_link("Read more", "https://example.com")
        )

        assert "<b>▓▓▓ Market Report ▓▓▓</b>" in message
        assert "<b>BTC Price:</b>" in message
        assert "<i>Change:</i>" in message
        assert '<a href="https://example.com">Read more</a>' in message

    def test_building_complex_markdown_message(self):
        """Test building a complex message with MarkdownV2 formatter."""
        formatter = get_formatter("MarkdownV2")

        message = (
            formatter.format_header("Market Report", level=1)
            + "\n\n"
            + formatter.format_bold("BTC Price:")
            + " $50,000\n"
            + formatter.format_italic("Change:")
            + " +5%\n\n"
            + formatter.format_link("Read more", "https://example.com")
        )

        assert "*▓▓▓ Market Report ▓▓▓*" in message
        assert "*BTC Price:*" in message
        assert "_Change:_" in message
        assert "[Read more](https://example.com)" in message


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
