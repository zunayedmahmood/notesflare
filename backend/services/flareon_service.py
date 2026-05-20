# services/flareon_service.py

from database.db import get_db
from datetime import datetime, timezone


def create_flareon(name: str) -> dict:
    """
    Create a new Flareon with the given name.
    Returns the created Flareon as a dict.
    Raises ValueError if name already exists.
    """
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    try:
        cursor = db.execute(
            "INSERT INTO flareons (name, created_at, updated_at) VALUES (?, ?, ?)",
            (name.strip(), now, now)
        )
        db.commit()
        flareon_id = cursor.lastrowid
        return get_flareon_by_id(flareon_id)
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise ValueError(f"A Flareon named '{name}' already exists.")
        raise


def list_flareons() -> list[dict]:
    """Return all Flareons ordered by most recently opened, then by creation."""
    db = get_db()
    rows = db.execute(
        """
        SELECT id, name, created_at, last_opened_at
        FROM flareons
        ORDER BY
            CASE WHEN last_opened_at IS NULL THEN 1 ELSE 0 END,
            last_opened_at DESC,
            created_at ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def get_flareon_by_id(flareon_id: int) -> dict | None:
    """Return a single Flareon by ID, or None if not found."""
    db = get_db()
    row = db.execute(
        "SELECT id, name, created_at, last_opened_at FROM flareons WHERE id = ?",
        (flareon_id,)
    ).fetchone()
    return dict(row) if row else None


def touch_flareon(flareon_id: int) -> None:
    """
    Update last_opened_at to now.
    Call this every time a Flareon is opened.
    """
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "UPDATE flareons SET last_opened_at = ?, updated_at = ? WHERE id = ?",
        (now, now, flareon_id)
    )
    db.commit()
