# services/append_service.py

"""
Append service for NotesFlare V1.1.

Responsibility: write new content chunks to burst_entries and keep
bursts.updated_at current so the 30-minute continuity rule works correctly.

Every call to append_chunk:
1. Gets the next sequence_number for this burst
2. Inserts a new burst_entries row with the chunk
3. Updates bursts.updated_at so the continuity window resets

Why sequence_number is managed here and not by the DB default:
SQLite AUTOINCREMENT on id would work for global ordering but
sequence_number is per-burst. We query MAX(sequence_number) for the burst
and add 1. This is safe because the backend is single-threaded synchronous
(no concurrent writes to the same burst from the same process).
"""

from database.db import get_db
from datetime import datetime, timezone


def append_chunk(burst_id: int, text: str) -> int:
    """
    Append a text chunk to a burst's entry log.

    Args:
        burst_id: The burst to append to.
        text: The new text delta. Must be non-empty. The caller (route handler)
              is responsible for rejecting empty strings before calling here.

    Returns:
        The sequence_number assigned to this chunk.

    Side effect:
        Updates bursts.updated_at to now. This is critical — the continuity
        rule reads bursts.updated_at. If we don't update it on every append,
        the 30-minute window will not reset and a new burst will be created
        incorrectly after 30 minutes of inactivity even if the user resumed.
    """
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    # Get the next sequence number for this burst
    row = db.execute(
        "SELECT COALESCE(MAX(sequence_number), -1) as max_seq FROM burst_entries WHERE burst_id = ?",
        (burst_id,)
    ).fetchone()
    next_seq = row["max_seq"] + 1

    # Insert the chunk
    db.execute(
        """
        INSERT INTO burst_entries (burst_id, content_chunk, sequence_number, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (burst_id, text, next_seq, now)
    )

    # Update parent burst's updated_at — required for continuity rule
    db.execute(
        "UPDATE bursts SET updated_at = ? WHERE id = ?",
        (now, burst_id)
    )

    db.commit()
    return next_seq


def get_next_sequence_number(burst_id: int) -> int:
    """
    Preview what the next sequence number would be, without writing.
    Used by tests to verify ordering without side effects.
    """
    db = get_db()
    row = db.execute(
        "SELECT COALESCE(MAX(sequence_number), -1) as max_seq FROM burst_entries WHERE burst_id = ?",
        (burst_id,)
    ).fetchone()
    return row["max_seq"] + 1
