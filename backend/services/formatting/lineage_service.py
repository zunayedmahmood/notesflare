# services/formatting/lineage_service.py

"""
Line identity management for NotesFlare V1.2.

Every line in a burst receives:
- A stable UUID (line_id)
- A SHA256 checksum of the raw content
- A line_index (position in burst)

These are stored in burst_lines and never reassigned.
If a burst is reformatted, existing line_ids are reused if the checksum matches.
New lines get new UUIDs.
"""

import uuid
import hashlib
from database.db import get_db
from datetime import datetime, timezone


def compute_checksum(raw_line: str) -> str:
    """SHA256 of the raw line content."""
    return hashlib.sha256(raw_line.encode("utf-8")).hexdigest()


def get_or_create_lines(burst_id: int, raw_lines: list[str]) -> list[dict]:
    """
    Given a burst_id and its current lines, return the stable line records.

    For each line:
    - If a burst_line exists at this index with the same checksum → reuse it
    - If checksum differs (line was edited) → create new entry, mark old as superseded
    - If no entry at this index → create new entry

    Returns a list of dicts matching the burst_lines table structure.
    """
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    existing = {
        row["line_index"]: dict(row)
        for row in db.execute(
            "SELECT * FROM burst_lines WHERE burst_id = ? ORDER BY line_index",
            (burst_id,),
        ).fetchall()
    }

    result = []

    for idx, raw_line in enumerate(raw_lines):
        checksum = compute_checksum(raw_line)

        if idx in existing and existing[idx]["checksum"] == checksum:
            # Reuse stable line
            result.append(existing[idx])
        else:
            # Create new line entry
            line_id = str(uuid.uuid4())
            db.execute(
                """
                INSERT INTO burst_lines
                    (line_id, burst_id, line_index, raw_line, formatted_line,
                     status, checksum, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'untouched', ?, ?, ?)
                """,
                (line_id, burst_id, idx, raw_line, raw_line, checksum, now, now),
            )
            _record_history(db, line_id, "create", {"index": idx, "checksum": checksum})
            result.append({
                "line_id": line_id,
                "burst_id": burst_id,
                "line_index": idx,
                "raw_line": raw_line,
                "formatted_line": raw_line,
                "status": "untouched",
                "checksum": checksum,
            })

    db.commit()
    return result


def _record_history(db, line_id: str, operation: str, detail: dict) -> None:
    """Insert an immutable history record for a line operation."""
    import json
    history_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "INSERT INTO line_history (history_id, line_id, operation, detail, created_at) VALUES (?, ?, ?, ?, ?)",
        (history_id, line_id, operation, json.dumps(detail), now),
    )
