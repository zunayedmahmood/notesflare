# backend/tests/test_formatting_pipeline.py

import pytest
import sqlite3
from services.formatting import (
    lexer_service, parser_service, chunker_service,
    embedding_service, formatter_service, diff_service, lineage_service
)
from services import flareon_service, burst_service, append_service, stream_service


@pytest.mark.unit
def test_lexer_normalize_text():
    raw = "Hello\r\nworld  \n\n\n\nHow is NotesFlare?   "
    normalized = lexer_service.normalize_text(raw)
    assert normalized == "Hello\nworld\n\nHow is NotesFlare?"
    
    lines = lexer_service.split_into_lines(normalized)
    assert lines == ["Hello", "world", "", "How is NotesFlare?"]


@pytest.mark.unit
def test_parser_signals():
    # Heading candidate (short, no verb, no punctuation)
    # List candidate (starts with dash or dot)
    # Quote candidate (starts with quotes)
    lines = [
        "Introduction to NotesFlare",
        "  - This is a list item",
        "\"This is a quote.\"",
        "The quick brown fox jumps over the lazy dog.",
        "And we are done."
    ]
    signals = parser_service.parse_lines(lines)
    
    assert len(signals) == 5
    # Check Introduction to NotesFlare is heading candidate
    assert signals[0]["is_heading_candidate"] is True
    # Check contains protected token NotesFlare
    assert signals[0]["contains_protected_token"] is True
    
    # Check list item candidate
    assert signals[1]["is_list_item_candidate"] is True
    
    # Check quote candidate
    assert signals[2]["is_quote_candidate"] is True
    
    # Check conjunction start
    assert signals[4]["has_conjunction_start"] is True


@pytest.mark.unit
def test_chunker_logic():
    lines = ["a" * 100, "b" * 100, "c" * 100]
    chunks = chunker_service.chunk_lines(lines, chunk_size=150, overlap=50)
    # Chunk size is 150, so each single line plus newline fits, but not two together (202 chars).
    assert len(chunks) == 3
    assert chunks[0]["line_indices"] == [0]
    assert chunks[1]["line_indices"] == [1]


@pytest.mark.unit
def test_formatter_operations():
    signals = [
        {
            "line_index": 0,
            "text": "getting started",
            "is_sentence_start": True,
            "is_sentence_end": True,
            "is_list_item_candidate": False,
            "is_heading_candidate": True,
            "is_quote_candidate": False,
            "has_conjunction_start": False,
            "token_count": 2,
            "contains_protected_token": False,
        },
        {
            "line_index": 1,
            "text": "* step one",
            "is_sentence_start": True,
            "is_sentence_end": True,
            "is_list_item_candidate": True,
            "is_heading_candidate": False,
            "is_quote_candidate": False,
            "has_conjunction_start": False,
            "token_count": 3,
            "contains_protected_token": False,
        }
    ]
    ops = formatter_service.generate_operations(signals)
    assert len(ops) == 2
    assert ops[0]["operation"] == "format_as_heading"
    assert ops[0]["formatted_after"] == "Getting Started"
    assert ops[1]["operation"] == "format_as_list_item"
    assert ops[1]["formatted_after"] == "- step one"


@pytest.mark.unit
def test_stable_lineage_and_diffs(test_db):
    flareon = flareon_service.create_flareon("Lineage Test")
    burst = burst_service.get_or_create_active_burst(flareon["id"])
    
    raw_lines = ["getting started", "* step one"]
    # Stage 3: Stable line IDs
    line_records = lineage_service.get_or_create_lines(burst["id"], raw_lines)
    assert len(line_records) == 2
    assert line_records[0]["line_index"] == 0
    assert line_records[0]["status"] == "untouched"
    
    # Store diffs
    ops = [
        {
            "line_index": 0,
            "operation": "format_as_heading",
            "raw_before": "getting started",
            "formatted_after": "Getting Started",
        }
    ]
    diffs = diff_service.store_diffs(burst["id"], line_records, ops)
    assert len(diffs) == 1
    assert diffs[0]["operation"] == "format_as_heading"
    assert diffs[0]["status"] == "pending"
    
    # Accept diff
    accept_res = diff_service.accept_diff(diffs[0]["diff_id"])
    assert accept_res["status"] == "accepted"
    
    # Verify line status changed
    lines_dict = diff_service.get_formatted_burst(burst["id"], "getting started\n* step one")
    assert lines_dict["lines"][0]["status"] == "accepted"
    assert lines_dict["lines"][0]["formatted_line"] == "Getting Started"
    assert lines_dict["formatted_text"] == "Getting Started\n* step one"

@pytest.mark.unit
def test_formatter_splits_unpunctuated_semantic_clause():
    raw = (
        "semantic chunking should happen after stabilization because structure itself "
        "carries meaning embeddings become more coherent afterwards"
    )
    signals = parser_service.parse_lines([raw])
    ops = formatter_service.generate_operations(signals)
    assert len(ops) == 1
    assert ops[0]["operation"] == "insert_line_break"
    assert ops[0]["formatted_after"] == (
        "semantic chunking should happen after stabilization because structure itself "
        "carries meaning\n\nembeddings become more coherent afterwards"
    )


@pytest.mark.unit
def test_formatter_splits_raw_option_marker():
    raw = "need vector db maybe sqlite first then benchmark"
    signals = parser_service.parse_lines([raw])
    ops = formatter_service.generate_operations(signals)
    assert len(ops) == 1
    assert ops[0]["operation"] == "insert_line_break"
    assert ops[0]["formatted_after"] == "need vector db\n\nmaybe sqlite first then benchmark"


@pytest.mark.unit
def test_formatter_splits_another_point_marker():
    raw = "paper discusses retrieval another point is chunking quality"
    signals = parser_service.parse_lines([raw])
    ops = formatter_service.generate_operations(signals)
    assert len(ops) == 1
    assert ops[0]["operation"] == "insert_line_break"
    assert ops[0]["formatted_after"] == "paper discusses retrieval\n\nanother point is chunking quality"


@pytest.mark.unit
def test_formatter_splits_long_sentence_dump():
    raw = (
        "This file defines the product identity, brand emotion, target audience, visual language, "
        "and the complete technical architecture that every subsequent instruction file builds upon. "
        "Read this file first. Every decision made in other files must be consistent with this one. "
        "It is the place where a person's thinking *lives*. The user opens it and their thoughts are "
        "already there, already waiting, already in context. The app never asks them to start fresh."
    )
    signals = parser_service.parse_lines([raw])
    ops = formatter_service.generate_operations(signals)
    assert len(ops) == 1
    assert ops[0]["operation"] == "insert_line_break"
    assert "\n" in ops[0]["formatted_after"]
    assert "The app never asks them to start fresh." in ops[0]["formatted_after"]
