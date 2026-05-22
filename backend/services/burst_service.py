# services/burst_service.py

from database.db import get_db
from datetime import datetime, timezone, timedelta

CONTINUITY_WINDOW_MINUTES = 30


def get_or_create_active_burst(flareon_id: int) -> dict:
    """
    Core session logic. Implements the 30-minute continuity rule.
    Content is NOT returned here — use stream_service.reconstruct_burst separately.
    """
    db = get_db()

    latest_burst = db.execute(
        """
        SELECT id, flareon_id, started_at, updated_at
        FROM bursts
        WHERE flareon_id = ?
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (flareon_id,)
    ).fetchone()

    if latest_burst is not None:
        last_updated = _parse_iso(latest_burst["updated_at"])
        now = datetime.now(timezone.utc)
        elapsed = now - last_updated

        # Treat negative elapsed (system clock skew) as 0
        if elapsed.total_seconds() < 0:
            elapsed = timedelta(seconds=0)

        if elapsed < timedelta(minutes=CONTINUITY_WINDOW_MINUTES):
            return dict(latest_burst)

    return _create_burst(flareon_id)


def _create_burst(flareon_id: int) -> dict:
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    burst_cursor = db.execute(
        "INSERT INTO bursts (flareon_id, started_at, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (flareon_id, now, now, now)
    )
    burst_id = burst_cursor.lastrowid
    db.commit()

    # No burst_entry row is pre-created in V1.1.
    # The first append_chunk call will create the first entry.

    return {
        "id": burst_id,
        "flareon_id": flareon_id,
        "started_at": now,
        "updated_at": now,
    }


def get_all_bursts_for_flareon(flareon_id: int) -> list[dict]:
    """
    Return all bursts for a Flareon in chronological order (oldest first).
    Content is reconstructed from burst_entries chunks via stream_service.

    NOTE: This function now calls stream_service for each burst.
    For archive view with many bursts this is acceptable in V1.1.
    Future optimization: batch reconstruction query.
    """
    # Import here to avoid circular import (burst_service ↔ stream_service)
    from services import stream_service

    db = get_db()
    rows = db.execute(
        """
        SELECT id, flareon_id, started_at
        FROM bursts
        WHERE flareon_id = ?
        ORDER BY started_at ASC
        """,
        (flareon_id,)
    ).fetchall()

    result = []
    for row in rows:
        content = stream_service.reconstruct_burst(row["id"])
        result.append({
            "id": row["id"],
            "flareon_id": row["flareon_id"],
            "started_at": row["started_at"],
            "content": content,
        })
    return result


def _parse_iso(dt_string: str) -> datetime:
    """Parse ISO 8601 string from SQLite into an aware datetime."""
    dt = datetime.fromisoformat(dt_string)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
