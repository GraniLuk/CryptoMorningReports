"""Text processing utilities for Telegram messages.

This module contains functions for processing and sanitizing text
for Telegram messages, including HTML sanitization, MarkdownV2 escaping,
and message splitting logic.
"""

import html
import re


def enforce_markdown_v2(text: str) -> str:
    """Escape characters required by Telegram MarkdownV2 while preserving existing.

    code spans. We do a lightweight parse: split by backticks and only escape in the
    non-code segments (even indices after split). This is not a full Markdown parser
    but sufficient for typical report content.
    """
    # Telegram MarkdownV2 special chars to escape:
    # _ * [ ] ( ) ~ ` > # + - = | { } . !
    special_pattern = re.compile(r"([_\*\[\]\(\)~`>#\+\-=\|{}\.\!])")
    parts = text.split("`")
    for i in range(0, len(parts), 2):  # only escape outside code spans
        parts[i] = special_pattern.sub(r"\\\1", parts[i])
    # Rejoin with unescaped backticks between parts
    return "`".join(parts)


def sanitize_html(message):
    """Escapes any HTML-like substrings that are not valid Telegram allowed tags.

    Allowed tags: b, i, u, s, code, pre, a (opening/closing, with optional attributes for <a>).
    """
    # List the allowed tag names. For the <a> tag, we allow attributes.
    allowed_tags = ["b", "i", "u", "s", "code", "pre", "a"]

    # Regex to match any HTML tag
    tag_regex = re.compile(r"</?([a-zA-Z]+)([^>]*)>")

    def replace_tag(match):
        tag_name = match.group(1).lower()
        full_tag = match.group(0)
        # Check if tag_name is one of the allowed tags.
        if tag_name in allowed_tags:
            # For safety, you can choose to do extra validation on attributes if needed.
            return full_tag
        # Escape the entire tag if not allowed.
        return html.escape(full_tag)

    # Replace any found HTML tag with our conditional replacement.
    return tag_regex.sub(replace_tag, message)


def smart_split(text: str, limit: int, parse_mode: str | None) -> list[str]:
    """Split the text into <=limit sized chunks, preferring to break on double newlines.

    (paragraphs). If a single paragraph exceeds the limit, fall back to hard slicing.
    For HTML parse_mode we also try not to cut inside an open tag (very naive: ensure
    open '<' without closing '>' inside the slice gets extended to the closing '>').
    """
    if len(text) <= limit:
        return [text]

    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = []
    current_len = 0
    for p in paragraphs:
        p_block = p + "\n\n"  # keep delimiter
        if len(p_block) > limit:
            # Flush current
            if current:
                chunks.append("".join(current).rstrip())
                current = []
                current_len = 0
            # Hard slice this oversize paragraph
            for i in range(0, len(p_block), limit):
                slice_ = p_block[i : i + limit]
                if parse_mode == "HTML":
                    slice_ = _extend_to_close_tag(p_block, i, slice_, limit)
                chunks.append(slice_)
            continue
        if current_len + len(p_block) <= limit:
            current.append(p_block)
            current_len += len(p_block)
        else:
            chunks.append("".join(current).rstrip())
            current = [p_block]
            current_len = len(p_block)

    if current:
        chunks.append("".join(current).rstrip())
    return chunks


def _extend_to_close_tag(_full_text: str, _start_index: int, slice_: str, _limit: int) -> str:
    """If the slice ends in the middle of an HTML tag (has unmatched '<'), extend until.

    the closing '>' if possible within a small lookahead window. This is a heuristic to
    reduce parse errors when using HTML parse_mode.
    """
    if slice_.count("<") == slice_.count(">"):
        return slice_
    # Look ahead up to 200 chars beyond limit (Telegram still enforces limit, so we must respect it)
    # If we can't fix within limit, return original slice.
    # Since we cannot exceed limit, we actually can only shrink, not extend. So instead we try to
    # trim back to last '>' to avoid dangling '<'.
    last_gt = slice_.rfind(">")
    last_lt = slice_.rfind("<")
    if last_lt > last_gt:
        # drop dangling part after last '<'
        return slice_[:last_lt]
    return slice_
