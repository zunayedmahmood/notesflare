# backend/tests/formatting/test_parser_service.py

import pytest
from services.formatting.parser_service import parse_lines


class TestParseLines:
    def test_returns_signal_per_line(self):
        lines = ["Hello world", "Another sentence here", ""]
        signals = parse_lines(lines)
        assert len(signals) == 3, (
            f"parser_service: expected 3 signals for 3 lines, got {len(signals)}"
        )

    def test_empty_line_has_zero_tokens(self):
        signals = parse_lines([""])
        assert signals[0]["token_count"] == 0, (
            f"parser_service: empty line should have 0 tokens, got {signals[0]['token_count']}"
        )

    def test_list_item_detection(self):
        lines = ["- first item", "* second item", "1. third item"]
        signals = parse_lines(lines)
        for i, sig in enumerate(signals):
            assert sig["is_list_item_candidate"], (
                f"parser_service: line {i} '{lines[i]}' should be detected as list item"
            )

    def test_conjunction_start_detection(self):
        signals = parse_lines(["And another thought"])
        assert signals[0]["has_conjunction_start"], (
            "parser_service: line starting with 'And' should have has_conjunction_start=True"
        )

    def test_protected_tokens_flagged(self):
        signals = parse_lines(["NotesFlare is the product"])
        assert signals[0]["contains_protected_token"], (
            "parser_service: 'NotesFlare' should be flagged as a protected token"
        )

    def test_non_protected_token_not_flagged(self):
        signals = parse_lines(["regular text about nothing special"])
        assert not signals[0]["contains_protected_token"], (
            "parser_service: normal text should not be flagged as protected"
        )
