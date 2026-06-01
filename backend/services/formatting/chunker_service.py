# services/formatting/chunker_service.py

"""
Chunking engine for NotesFlare V1.2.

Chunks exist ONLY inside bursts — never crossing burst boundaries.
Uses overlapping sliding windows to preserve semantic continuity.
"""

from typing import List


DEFAULT_CHUNK_SIZE = 800       # chars per chunk
DEFAULT_OVERLAP    = 150       # overlap between consecutive chunks


def chunk_lines(lines: list[str], chunk_size: int = DEFAULT_CHUNK_SIZE,
                overlap: int = DEFAULT_OVERLAP) -> list[dict]:
    """
    Split a list of lines into overlapping chunks.

    Returns a list of chunk dicts:
    {
        "chunk_index": int,
        "lines": list[str],
        "line_indices": list[int],   # Original line indices in burst
        "char_start": int,
        "char_end": int,
    }
    """
    if not lines:
        return []

    chunks = []
    current_chunk_lines = []
    current_chunk_indices = []
    current_chars = 0
    chunk_index = 0

    for line_idx, line in enumerate(lines):
        line_chars = len(line) + 1  # +1 for newline

        if current_chars + line_chars > chunk_size and current_chunk_lines:
            # Emit current chunk
            chunks.append(_make_chunk(chunk_index, current_chunk_lines, current_chunk_indices))
            chunk_index += 1

            # Start new chunk with overlap: keep last N chars worth of lines
            overlap_lines, overlap_indices = _trim_to_overlap(
                current_chunk_lines, current_chunk_indices, overlap
            )
            current_chunk_lines = overlap_lines + [line]
            current_chunk_indices = overlap_indices + [line_idx]
            current_chars = sum(len(l) + 1 for l in current_chunk_lines)
        else:
            current_chunk_lines.append(line)
            current_chunk_indices.append(line_idx)
            current_chars += line_chars

    if current_chunk_lines:
        chunks.append(_make_chunk(chunk_index, current_chunk_lines, current_chunk_indices))

    return chunks


def _make_chunk(index: int, lines: list[str], indices: list[int]) -> dict:
    text = "\n".join(lines)
    return {
        "chunk_index": index,
        "lines": lines,
        "line_indices": indices,
        "char_start": 0,   # Relative within chunk
        "char_end": len(text),
    }


def _trim_to_overlap(lines: list[str], indices: list[int], overlap: int) -> tuple:
    """Return the trailing portion of lines that fits within `overlap` chars."""
    kept_lines = []
    kept_indices = []
    total = 0
    for line, idx in zip(reversed(lines), reversed(indices)):
        total += len(line) + 1
        if total > overlap:
            break
        kept_lines.insert(0, line)
        kept_indices.insert(0, idx)
    return kept_lines, kept_indices
