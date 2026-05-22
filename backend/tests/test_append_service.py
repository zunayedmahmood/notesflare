# backend/tests/test_append_service.py

"""
Unit tests for append_service.py.

Critical paths:
- append_chunk assigns sequence numbers correctly
- append_chunk updates bursts.updated_at
- Empty-text guard (tested at the route level, not here)
- sequence_number is per-burst, not global
"""

import pytest
from freezegun import freeze_time
from datetime import datetime, timezone

# conftest.py provides: test_db, test_client, create_flareon, create_burst
# (same fixtures used in existing test files)


@pytest.mark.unit
def test_first_chunk_gets_sequence_zero(test_db, create_flareon, create_burst):
    """
    The first chunk appended to a burst must have sequence_number 0.

    Why: reconstruction reads ORDER BY sequence_number ASC.
    If the first chunk gets a non-zero sequence, it may be ordered
    after later chunks and content will be corrupted.
    """
    from services.append_service import append_chunk

    flareon = create_flareon("Test Flareon")
    burst = create_burst(flareon["id"])

    seq = append_chunk(burst["id"], "Hello ")

    assert seq == 0, (
        f"[append_service] First chunk must have sequence_number 0. "
        f"Got: {seq}. "
        f"Fix: ensure COALESCE(MAX(sequence_number), -1) + 1 starts at 0 "
        f"when no entries exist for a burst."
    )


@pytest.mark.unit
def test_sequence_numbers_increment_monotonically(test_db, create_flareon, create_burst):
    """
    Multiple appends to the same burst must produce 0, 1, 2, ...

    Why: reconstruction depends on strict monotonic ordering.
    """
    from services.append_service import append_chunk

    flareon = create_flareon("Sequence Test")
    burst = create_burst(flareon["id"])

    seq0 = append_chunk(burst["id"], "chunk A")
    seq1 = append_chunk(burst["id"], " chunk B")
    seq2 = append_chunk(burst["id"], " chunk C")

    assert seq0 == 0 and seq1 == 1 and seq2 == 2, (
        f"[append_service] Sequence numbers must be 0, 1, 2. "
        f"Got: {seq0}, {seq1}, {seq2}. "
        f"Fix: ensure each call reads MAX(sequence_number) fresh from DB."
    )


@pytest.mark.unit
def test_sequence_numbers_are_per_burst(test_db, create_flareon, create_burst):
    """
    Sequence numbers restart at 0 for each burst.
    Burst A's seq=0,1,2 does not affect Burst B starting at seq=0.

    Why: sequence_number is a per-burst counter, not a global counter.
    """
    from services.append_service import append_chunk

    flareon = create_flareon("Per-Burst Test")
    burst_a = create_burst(flareon["id"])
    burst_b = create_burst(flareon["id"])

    append_chunk(burst_a["id"], "A0")
    append_chunk(burst_a["id"], "A1")
    seq_b0 = append_chunk(burst_b["id"], "B0")

    assert seq_b0 == 0, (
        f"[append_service] sequence_number must restart at 0 for each burst. "
        f"Got seq_b0={seq_b0} (expected 0). "
        f"Fix: filter by burst_id in MAX(sequence_number) query."
    )


@pytest.mark.unit
@freeze_time("2025-01-15 14:00:00", tz_offset=0)
def test_append_updates_burst_updated_at(test_db, create_flareon, create_burst):
    """
    append_chunk must update bursts.updated_at to now.

    Why: the 30-minute continuity check reads bursts.updated_at.
    If we don't update it on append, the window will not reset and
    a new burst will be created incorrectly.
    """
    from services.append_service import append_chunk
    from database.db import get_db

    flareon = create_flareon("Timestamp Test")
    burst = create_burst(flareon["id"])

    original_updated_at = burst.get("updated_at", "")

    with freeze_time("2025-01-15 14:15:00"):
        append_chunk(burst["id"], "some text")

    db = get_db()
    row = db.execute(
        "SELECT updated_at FROM bursts WHERE id = ?", (burst["id"],)
    ).fetchone()
    updated = row["updated_at"]

    assert "14:15" in updated, (
        f"[append_service] bursts.updated_at must update to 14:15:00 after append. "
        f"Got: {updated}. "
        f"Original: {original_updated_at}. "
        f"Fix: ensure append_chunk executes "
        f"UPDATE bursts SET updated_at = now WHERE id = burst_id."
    )


@pytest.mark.unit
def test_append_to_nonexistent_burst_fails_gracefully(test_db):
    """
    Appending to a burst ID that doesn't exist must fail — not silently succeed.

    Why: if this silently succeeds, an orphaned burst_entry is created
    with no parent, which corrupts the DB.

    The expected behavior: SQLite foreign key constraint violation.
    """
    from services.append_service import append_chunk
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        append_chunk(99999, "orphaned chunk")

    assert "FOREIGN KEY" in str(exc_info.value).upper() or "CONSTRAINT" in str(
        exc_info.value
    ).upper(), (
        f"[append_service] Appending to non-existent burst must raise FK error. "
        f"Got: {exc_info.value}. "
        f"Fix: ensure PRAGMA foreign_keys=ON is set in db.py."
    )
