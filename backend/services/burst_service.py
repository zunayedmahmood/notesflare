# services/burst_service.py

from database.db import get_db
from datetime import datetime, timezone, timedelta

CONTINUITY_WINDOW_MINUTES = 30


def get_or_create_active_burst(flareon_id: int) -> dict:
    """
    Core session logic. Implements the 30-minute continuity rule:
    - If the latest burst for this Flareon was updated within 30 minutes: return it
    - Otherwise: create a new burst and return it

    Returns a dict with keys: id, flareon_id, started_at, content
    """
    db = get_db()

    # Find the most recently updated burst for this Flareon
    latest_burst = db.execute(
        """
        SELECT b.id, b.flareon_id, b.started_at, b.updated_at,
               COALESCE(be.content, '') as content
        FROM bursts b
        LEFT JOIN burst_entries be ON be.burst_id = b.id
        WHERE b.flareon_id = ?
        ORDER BY b.updated_at DESC
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
            # Continue existing burst
            return dict(latest_burst)

    # Create new burst
    return _create_burst(flareon_id)


def _create_burst(flareon_id: int) -> dict:
    """
    Insert a new burst row and a corresponding empty burst_entry row.
    Returns the new burst as a dict.
    """
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    burst_cursor = db.execute(
        "INSERT INTO bursts (flareon_id, started_at, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (flareon_id, now, now, now)
    )
    burst_id = burst_cursor.lastrowid

    db.execute(
        "INSERT INTO burst_entries (burst_id, content, created_at, updated_at) VALUES (?, '', ?, ?)",
        (burst_id, now, now)
    )
    db.commit()

    return {
        "id": burst_id,
        "flareon_id": flareon_id,
        "started_at": now,
        "updated_at": now,
        "content": ""
    }


def get_all_bursts_for_flareon(flareon_id: int) -> list[dict]:
    """
    Return all bursts for a Flareon in chronological order (oldest first).
    Each burst includes its content from burst_entries.
    """
    db = get_db()
    rows = db.execute(
        """
        SELECT b.id, b.flareon_id, b.started_at,
               COALESCE(be.content, '') as content
        FROM bursts b
        LEFT JOIN burst_entries be ON be.burst_id = b.id
        WHERE b.flareon_id = ?
        ORDER BY b.started_at ASC
        """,
        (flareon_id,)
    ).fetchall()
    return [dict(row) for row in rows]


def _parse_iso(dt_string: str) -> datetime:
    """Parse ISO 8601 string from SQLite into an aware datetime."""
    dt = datetime.fromisoformat(dt_string)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
