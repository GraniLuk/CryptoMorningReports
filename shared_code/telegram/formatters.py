"""Telegram message formatters for HTML and MarkdownV2.

This module provides a formatter abstraction layer that allows easy switching
between HTML and MarkdownV2 parse modes for Telegram messages.

The TelegramFormatter protocol defines the interface for all formatters,
and the get_formatter() factory function creates the appropriate formatter
based on the requested parse mode.
"""

from typing import Protocol

from .constants import PARSE_MODE_HTML, PARSE_MODE_MARKDOWN_V2


class TelegramFormatter(Protocol):
    """Protocol defining the interface for Telegram message formatters.

    All formatters must implement these methods to provide consistent
    formatting across different parse modes (HTML, MarkdownV2).
    """

    def format_bold(self, text: str) -> str:
        """Format text as bold.

        Args:
            text: Text to format

        Returns:
            Formatted text with bold styling
        """
        ...

    def format_italic(self, text: str) -> str:
        """Format text as italic.

        Args:
            text: Text to format

        Returns:
            Formatted text with italic styling
        """
        ...

    def format_underline(self, text: str) -> str:
        """Format text as underlined.

        Args:
            text: Text to format

        Returns:
            Formatted text with underline styling
        """
        ...

    def format_strikethrough(self, text: str) -> str:
        """Format text as strikethrough.

        Args:
            text: Text to format

        Returns:
            Formatted text with strikethrough styling
        """
        ...

    def format_code(self, text: str) -> str:
        """Format text as inline code.

        Args:
            text: Text to format

        Returns:
            Formatted text as inline code
        """
        ...

    def format_code_block(self, text: str, language: str = "") -> str:
        """Format text as code block.

        Args:
            text: Code text to format
            language: Programming language for syntax highlighting (optional)

        Returns:
            Formatted text as code block
        """
        ...

    def format_link(self, text: str, url: str) -> str:
        """Format text as hyperlink.

        Args:
            text: Link text to display
            url: URL to link to

        Returns:
            Formatted hyperlink
        """
        ...

    def format_header(self, text: str, level: int = 1) -> str:
        """Format text as header.

        Args:
            text: Header text
            level: Header level (1-3)

        Returns:
            Formatted header text
        """
        ...


class HTMLFormatter:
    """Formatter for Telegram HTML parse mode.

    Implements the TelegramFormatter protocol to output HTML tags
    compatible with Telegram's HTML parser.

    Reference: https://core.telegram.org/bots/api#html-style
    """

    def format_bold(self, text: str) -> str:
        """Format text as bold using HTML."""
        return f"<b>{text}</b>"

    def format_italic(self, text: str) -> str:
        """Format text as italic using HTML."""
        return f"<i>{text}</i>"

    def format_underline(self, text: str) -> str:
        """Format text as underlined using HTML."""
        return f"<u>{text}</u>"

    def format_strikethrough(self, text: str) -> str:
        """Format text as strikethrough using HTML."""
        return f"<s>{text}</s>"

    def format_code(self, text: str) -> str:
        """Format text as inline code using HTML."""
        return f"<code>{text}</code>"

    def format_code_block(self, text: str, language: str = "") -> str:
        """Format text as code block using HTML.

        Note: Telegram HTML doesn't support language-specific syntax highlighting.
        """
        return f"<pre>{text}</pre>"

    def format_link(self, text: str, url: str) -> str:
        """Format text as hyperlink using HTML."""
        return f'<a href="{url}">{text}</a>'

    def format_header(self, text: str, level: int = 1) -> str:
        """Format text as header using HTML bold and decorative characters.

        Args:
            text: Header text
            level: 1 = top level (▓▓▓), 2 = section (═══), 3 = subsection (underline)
        """
        if level == 1:
            return f"<b>▓▓▓ {text} ▓▓▓</b>"
        elif level == 2:
            return f"<b>═══ {text} ═══</b>"
        else:  # level 3 or higher
            return f"<b><u>{text}</u></b>"


class MarkdownV2Formatter:
    """Formatter for Telegram MarkdownV2 parse mode.

    Implements the TelegramFormatter protocol to output MarkdownV2 syntax
    compatible with Telegram's MarkdownV2 parser.

    Note: Special characters must be escaped. This is handled by the
    enforce_markdown_v2() function in text_processing module.

    Reference: https://core.telegram.org/bots/api#markdownv2-style
    """

    def format_bold(self, text: str) -> str:
        """Format text as bold using MarkdownV2."""
        return f"*{text}*"

    def format_italic(self, text: str) -> str:
        """Format text as italic using MarkdownV2."""
        return f"_{text}_"

    def format_underline(self, text: str) -> str:
        """Format text as underlined using MarkdownV2."""
        return f"__{text}__"

    def format_strikethrough(self, text: str) -> str:
        """Format text as strikethrough using MarkdownV2."""
        return f"~{text}~"

    def format_code(self, text: str) -> str:
        """Format text as inline code using MarkdownV2."""
        return f"`{text}`"

    def format_code_block(self, text: str, language: str = "") -> str:
        """Format text as code block using MarkdownV2.

        Args:
            text: Code text
            language: Programming language (e.g., 'python', 'javascript')
        """
        if language:
            return f"```{language}\n{text}\n```"
        return f"```\n{text}\n```"

    def format_link(self, text: str, url: str) -> str:
        """Format text as hyperlink using MarkdownV2."""
        return f"[{text}]({url})"

    def format_header(self, text: str, level: int = 1) -> str:
        """Format text as header using MarkdownV2 bold and decorative characters.

        Args:
            text: Header text
            level: 1 = top level (▓▓▓), 2 = section (═══), 3 = subsection (underline)
        """
        if level == 1:
            return f"*▓▓▓ {text} ▓▓▓*"
        elif level == 2:
            return f"*═══ {text} ═══*"
        else:  # level 3 or higher
            return f"__{text}__"


def get_formatter(parse_mode: str | None) -> TelegramFormatter:
    """Factory function to get the appropriate formatter for a parse mode.

    Args:
        parse_mode: Telegram parse mode ("HTML", "MarkdownV2", or None)

    Returns:
        Formatter instance implementing TelegramFormatter protocol

    Raises:
        ValueError: If parse_mode is not supported

    Examples:
        >>> formatter = get_formatter("HTML")
        >>> formatter.format_bold("Hello")
        '<b>Hello</b>'

        >>> formatter = get_formatter("MarkdownV2")
        >>> formatter.format_bold("Hello")
        '*Hello*'
    """
    if parse_mode == PARSE_MODE_HTML:
        return HTMLFormatter()
    elif parse_mode == PARSE_MODE_MARKDOWN_V2:
        return MarkdownV2Formatter()
    elif parse_mode is None or parse_mode == "":
        # Default to HTML for backward compatibility
        return HTMLFormatter()
    else:
        raise ValueError(
            f"Unsupported parse_mode: {parse_mode}. "
            f"Supported modes: '{PARSE_MODE_HTML}', '{PARSE_MODE_MARKDOWN_V2}', None"
        )
