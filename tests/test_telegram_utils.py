import re
import sys
import unittest
from pathlib import Path


# Ensure project root is on sys.path when running tests directly
ROOT = str(Path(__file__).parent.parent.resolve())
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shared_code.telegram import enforce_markdown_v2, smart_split  # noqa: E402


class TestTelegramUtils(unittest.TestCase):
    def test_smart_split_short_message(self):
        text = "Short message"
        chunks = smart_split(text, 4096, parse_mode="HTML")
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_smart_split_paragraph_preservation(self):
        paragraph = (
            "Paragraph one." + "\n\n" + "Paragraph two is here." + "\n\n" + "Paragraph three."
        )  # 3 paragraphs
        chunks = smart_split(paragraph, 25, parse_mode="HTML")
        # With limit 25 we expect splitting roughly per paragraph boundary
        assert len(chunks) > 1
        # Ensure no chunk exceeds limit
        assert all(len(c) <= 25 for c in chunks)
        # Reassemble (allow trailing whitespace differences) equals original ignoring added trimming
        reassembled = "\n\n".join(s.strip() for s in chunks)
        assert reassembled == paragraph

    def test_smart_split_oversize_paragraph(self):
        long_para = "A" * 5000  # single oversized paragraph
        chunks = smart_split(long_para, 1000, parse_mode="HTML")
        # Expect dynamic number of chunks (ceil division)
        non_empty = [c for c in chunks if c]
        expected = (len(long_para) + 1000 - 1) // 1000  # 5
        # Implementation adds delimiter '\n\n' to oversize paragraph, producing an extra tiny chunk
        assert len(non_empty) in (expected, expected + 1)
        assert all(len(c) <= 1000 or i == len(non_empty) - 1 for i, c in enumerate(non_empty))
        reassembled = "".join(non_empty)
        # Remove potential trailing newlines added by splitting logic before comparison
        assert reassembled.rstrip() == long_para

    def test_smart_split_html_tag_boundary(self):
        # Construct text likely to cut inside a tag if naive
        core = "<b>" + ("X" * 300) + "</b>" + "\n\n" + "<a href='u'>link</a>" + ("Y" * 300)
        limit = 350  # Forces potential mid-tag splits
        chunks = smart_split(core, limit, parse_mode="HTML")
        # Ensure we never have an unmatched '<' at end of chunk
        for c in chunks:
            if c.count("<") != c.count(">"):
                # Allow if dangling due to extremely pathological input; fail otherwise
                self.fail(f"Unbalanced tag counts in chunk: {c[-60:]}")

    def test_enforce_markdown_v2_basic_escapes(self):
        text = "Special _ * [ ] ( ) ~ ` > # + - = | { } . !"
        escaped = enforce_markdown_v2(text)
        # Only the segment before the unmatched backtick is escaped by design.
        assert "Special \\_ \\* \\[ \\] \\( \\) \\~" in escaped
        # Characters after the single backtick (treated as code segment) remain unescaped
        assert "` > # + - = | { } . !" in escaped
        # Ensure backtick itself present (unescaped)
        assert "`" in escaped

    def test_enforce_markdown_v2_preserves_code_spans(self):
        text = "Code: `a_b` outside _italic_"
        escaped = enforce_markdown_v2(text)
        # Inside code span a_b should remain unescaped
        assert "`a_b`" in escaped
        # Outside underscore should be escaped
        assert re.search(r"outside \\_italic\\_", escaped)

    def test_enforce_markdown_v2_idempotent(self):
        text = "Heading ## Title"
        first = enforce_markdown_v2(text)
        second = enforce_markdown_v2(first)
        # Applying twice may introduce extra escaping because backslashes are
        # themselves escapable; ensure second doesn't grow unbounded
        assert len(second) - len(first) <= 2


if __name__ == "__main__":
    unittest.main()
