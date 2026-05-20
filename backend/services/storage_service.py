# services/storage_service.py

from database.db import get_db
from datetime import datetime, timezone


def save_content(burst_id: int, content: str) -> int:
    """
    Save or update content for a burst.
    - If a burst_entry exists for this burst_id: UPDATE it
    - If not: INSERT a new one

    Returns the burst_entry id.
    This is called by the debounced autosave from the frontend.
    """
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    existing = db.execute(
        "SELECT id FROM burst_entries WHERE burst_id = ?",
        (burst_id,)
    ).fetchone()

    if existing:
        db.execute(
            "UPDATE burst_entries SET content = ?, updated_at = ? WHERE burst_id = ?",
            (content, now, burst_id)
        )
        # Also update the parent burst's updated_at — this is what the continuity
        # check reads. If we don't update bursts.updated_at, the 30-min window
        # won't reset on save.
        db.execute(
            "UPDATE bursts SET updated_at = ? WHERE id = ?",
            (now, burst_id)
        )
        db.commit()
        return existing["id"]
    else:
        cursor = db.execute(
            "INSERT INTO burst_entries (burst_id, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (burst_id, content, now, now)
        )
        db.execute(
            "UPDATE bursts SET updated_at = ? WHERE id = ?",
            (now, burst_id)
        )
        db.commit()
        return cursor.lastrowid


def get_app_state() -> dict:
    """Return the singleton app_state row."""
    db = get_db()
    row = db.execute(
        "SELECT last_opened_flareon_id, last_opened_burst_id FROM app_state WHERE id = 1"
    ).fetchone()
    return dict(row) if row else {}


def update_app_state(flareon_id: int, burst_id: int) -> None:
    """
    Update the app_state singleton row.
    Call this every time the user opens a Flareon (after burst resolution).
    """
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        """
        UPDATE app_state
        SET last_opened_flareon_id = ?,
            last_opened_burst_id = ?,
            last_active_at = ?
        WHERE id = 1
        """,
        (flareon_id, burst_id, now)
    )
    db.commit()
