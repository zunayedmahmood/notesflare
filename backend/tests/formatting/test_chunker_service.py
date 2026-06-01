# backend/tests/formatting/test_chunker_service.py

import pytest
from services.formatting.chunker_service import chunk_lines


class TestChunkLines:
    def test_empty_input_returns_empty(self):
        assert chunk_lines([]) == [], "chunker: empty input should return empty list"

    def test_single_chunk_for_short_content(self):
        lines = ["short line one", "short line two", "short line three"]
        chunks = chunk_lines(lines, chunk_size=1000)
        assert len(chunks) == 1, (
            f"chunker: short content should produce 1 chunk, got {len(chunks)}"
        )

    def test_multiple_chunks_for_long_content(self):
        # Create lines that exceed the chunk size
        long_lines = ["x" * 100 for _ in range(20)]
        chunks = chunk_lines(long_lines, chunk_size=500, overlap=50)
        assert len(chunks) > 1, (
            "chunker: long content should produce multiple chunks"
        )

    def test_overlap_present_in_consecutive_chunks(self):
        long_lines = [f"line content number {i} with padding chars here" for i in range(30)]
        chunks = chunk_lines(long_lines, chunk_size=200, overlap=50)
        if len(chunks) > 1:
            # Check that chunk 0 and chunk 1 share some line indices
            set_0 = set(chunks[0]["line_indices"])
            set_1 = set(chunks[1]["line_indices"])
            assert set_0 & set_1, (
                f"chunker: consecutive chunks should overlap. "
                f"Chunk 0 indices: {chunks[0]['line_indices']}, "
                f"Chunk 1 indices: {chunks[1]['line_indices']}"
            )

    def test_all_lines_covered(self):
        lines = [f"line {i}" for i in range(15)]
        chunks = chunk_lines(lines, chunk_size=100, overlap=20)
        covered = set()
        for c in chunks:
            covered.update(c["line_indices"])
        all_indices = set(range(len(lines)))
        assert covered == all_indices, (
            f"chunker: not all lines covered. Missing: {all_indices - covered}"
        )
