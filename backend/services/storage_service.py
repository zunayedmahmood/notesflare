# services/storage_service.py

from database.db import get_db
from datetime import datetime, timezone


# save_content() was removed in V1.1.
# Content persistence is now handled by append_service.append_chunk().
# The /api/save endpoint is superseded by /api/burst/append.


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
