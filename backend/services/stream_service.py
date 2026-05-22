# services/stream_service.py

"""
Stream service for NotesFlare V1.1.

Responsibility: read and reconstruct burst content from the append-only
burst_entries table. The full content of a burst is the concatenation of
all its content_chunk rows ordered by sequence_number ASC.

This service does NOT write. Writes go through append_service.
"""

from database.db import get_db


def reconstruct_burst(burst_id: int) -> str:
    """
    Reconstruct the full text content of a burst by concatenating all
    content_chunk rows in sequence_number order.

    Returns empty string if burst has no entries yet.
    This is the only correct way to read burst content in V1.1.
    """
    db = get_db()
    rows = db.execute(
        """
        SELECT content_chunk
        FROM burst_entries
        WHERE burst_id = ?
        ORDER BY sequence_number ASC
        """,
        (burst_id,)
    ).fetchall()

    return "".join(row["content_chunk"] for row in rows)


def get_all_bursts_with_content(flareon_id: int) -> list[dict]:
    """
    Return all bursts for a Flareon, each with fully reconstructed content.
    Used by the archive view endpoint.

    Returns list of dicts: {id, flareon_id, started_at, content}
    ordered oldest-first.
    """
    db = get_db()

    # Get all burst IDs for this Flareon
    burst_rows = db.execute(
        """
        SELECT id, flareon_id, started_at
        FROM bursts
        WHERE flareon_id = ?
        ORDER BY started_at ASC
        """,
        (flareon_id,)
    ).fetchall()

    result = []
    for burst in burst_rows:
        content = reconstruct_burst(burst["id"])
        result.append({
            "id": burst["id"],
            "flareon_id": burst["flareon_id"],
            "started_at": burst["started_at"],
            "content": content,
        })

    return result
