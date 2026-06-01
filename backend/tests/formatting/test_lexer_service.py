# backend/tests/formatting/test_lexer_service.py

import pytest
from services.formatting.lexer_service import normalize_text, split_into_lines


class TestNormalizeText:
    def test_unicode_nfc_normalization(self):
        # Decomposed 'é' (e + combining accent) → composed 'é'
        decomposed = "caf\u0065\u0301"
        result = normalize_text(decomposed)
        assert result == "caf\u00e9", (
            f"NFC normalization failed: expected 'café', got '{result}'"
        )

    def test_trailing_whitespace_stripped_per_line(self):
        text = "hello   \nworld   \n"
        result = normalize_text(text)
        lines = result.split("\n")
        assert not lines[0].endswith(" "), (
            f"lexer_service: trailing whitespace not stripped from line 0: '{lines[0]}'"
        )

    def test_multiple_blank_lines_collapsed(self):
        text = "line one\n\n\n\n\nline two"
        result = normalize_text(text)
        assert "\n\n\n" not in result, (
            f"lexer_service: 3+ consecutive blank lines not collapsed. Got:\n{repr(result)}"
        )

    def test_windows_line_endings_normalized(self):
        text = "line one\r\nline two\r\n"
        result = normalize_text(text)
        assert "\r" not in result, (
            f"lexer_service: Windows line endings not removed. Got: {repr(result)}"
        )

    def test_words_unchanged(self):
        original = "rn NotesFlare graphification MiniLM"
        result = normalize_text(original)
        assert result == original, (
            f"lexer_service: Words must not change. "
            f"Input: '{original}' → Output: '{result}'"
        )

    def test_empty_string_returns_empty(self):
        assert normalize_text("") == "", "lexer_service: empty string should return empty string"


class TestSplitIntoLines:
    def test_basic_split(self):
        lines = split_into_lines("hello\nworld")
        assert lines == ["hello", "world"], f"Expected ['hello', 'world'], got {lines}"

    def test_blank_lines_preserved(self):
        lines = split_into_lines("hello\n\nworld")
        assert len(lines) == 3, (
            f"split_into_lines: blank line should be preserved. Got {lines}"
        )
        assert lines[1] == "", f"Middle element should be empty string, got '{lines[1]}'"
