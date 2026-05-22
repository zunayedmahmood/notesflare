# backend/tests/test_stream_service.py

"""
Unit tests for stream_service.py — content reconstruction.
"""

import pytest


@pytest.mark.unit
def test_reconstruct_empty_burst(test_db, create_flareon, create_burst):
    """
    A burst with no entries must return empty string, not None or error.
    """
    from services.stream_service import reconstruct_burst

    flareon = create_flareon("Empty Burst Test")
    burst = create_burst(flareon["id"])

    content = reconstruct_burst(burst["id"])

    assert content == "", (
        f"[stream_service] reconstruct_burst on empty burst must return ''. "
        f"Got: {repr(content)}. "
        f"Fix: ensure the JOIN or SELECT returns '' via COALESCE or empty join."
    )


@pytest.mark.unit
def test_reconstruct_single_chunk(test_db, create_flareon, create_burst):
    """
    A burst with one chunk returns that chunk as-is.
    """
    from services.stream_service import reconstruct_burst
    from services.append_service import append_chunk

    flareon = create_flareon("Single Chunk Test")
    burst = create_burst(flareon["id"])

    append_chunk(burst["id"], "Hello world")
    content = reconstruct_burst(burst["id"])

    assert content == "Hello world", (
        f"[stream_service] Single chunk reconstruction failed. "
        f"Expected: 'Hello world'. Got: {repr(content)}."
    )


@pytest.mark.unit
def test_reconstruct_multiple_chunks_in_order(test_db, create_flareon, create_burst):
    """
    Multiple chunks must concatenate in sequence_number order.
    This is the core invariant of the append model.
    """
    from services.stream_service import reconstruct_burst
    from services.append_service import append_chunk

    flareon = create_flareon("Multi Chunk Test")
    burst = create_burst(flareon["id"])

    append_chunk(burst["id"], "The quick ")
    append_chunk(burst["id"], "brown fox ")
    append_chunk(burst["id"], "jumps over")

    content = reconstruct_burst(burst["id"])

    assert content == "The quick brown fox jumps over", (
        f"[stream_service] Multi-chunk reconstruction produced wrong content. "
        f"Expected: 'The quick brown fox jumps over'. "
        f"Got: {repr(content)}. "
        f"Fix: ensure ORDER BY sequence_number ASC in the SELECT query."
    )


@pytest.mark.unit
def test_reconstruct_does_not_cross_burst_boundary(test_db, create_flareon, create_burst):
    """
    reconstruct_burst(burst_A_id) must only return burst A's chunks,
    not chunks from burst B of the same Flareon.
    """
    from services.stream_service import reconstruct_burst
    from services.append_service import append_chunk

    flareon = create_flareon("Boundary Test")
    burst_a = create_burst(flareon["id"])
    burst_b = create_burst(flareon["id"])

    append_chunk(burst_a["id"], "Burst A content")
    append_chunk(burst_b["id"], "Burst B content")

    content_a = reconstruct_burst(burst_a["id"])
    content_b = reconstruct_burst(burst_b["id"])

    assert content_a == "Burst A content", (
        f"[stream_service] reconstruct_burst(A) must not include B's chunks. "
        f"Got: {repr(content_a)}"
    )
    assert content_b == "Burst B content", (
        f"[stream_service] reconstruct_burst(B) must not include A's chunks. "
        f"Got: {repr(content_b)}"
    )
