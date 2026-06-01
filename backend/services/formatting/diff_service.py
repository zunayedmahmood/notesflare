# services/formatting/diff_service.py

"""
Diff storage and action service for NotesFlare V1.2.

Stores formatting operations as diffs in burst_diffs.
Handles accept/reject and bulk actions.
Updates burst_lines.status on accept/reject.
Records line_history on every state change.
"""

import uuid
import json
from datetime import datetime, timezone
from database.db import get_db


def store_diffs(burst_id: int, line_records: list[dict], operations: list[dict]) -> list[dict]:
    """
    Given a list of line records and formatting operations, create diff rows.

    Clears any existing PENDING diffs for this burst before inserting new ones.
    Does NOT clear ACCEPTED or REJECTED diffs — those are permanent history.

    Returns the list of created diff dicts.
    """
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    # Delete pending diffs only (do not touch accepted/rejected)
    db.execute(
        "DELETE FROM burst_diffs WHERE burst_id = ? AND status = 'pending'",
        (burst_id,)
    )

    # Build a lookup from line_index → line_id
    index_to_line = {r["line_index"]: r for r in line_records}

    created = []
    for op in operations:
        line_idx = op["line_index"]
        if line_idx not in index_to_line:
            continue

        line_record = index_to_line[line_idx]
        diff_id = str(uuid.uuid4())

        db.execute(
            """
            INSERT INTO burst_diffs
                (diff_id, burst_id, line_id, operation, status,
                 raw_before, formatted_after, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?)
            """,
            (
                diff_id, burst_id, line_record["line_id"],
                op["operation"], op["raw_before"], op["formatted_after"],
                now, now,
            )
        )

        # Mark the line as pending
        db.execute(
            "UPDATE burst_lines SET status = 'pending', updated_at = ? WHERE line_id = ?",
            (now, line_record["line_id"])
        )

        created.append({
            "diff_id": diff_id,
            "burst_id": burst_id,
            "line_id": line_record["line_id"],
            "operation": op["operation"],
            "status": "pending",
            "raw_before": op["raw_before"],
            "formatted_after": op["formatted_after"],
        })

    db.commit()
    return created


def get_diffs_for_burst(burst_id: int) -> list[dict]:
    """Return all diffs for a burst ordered by creation time."""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM burst_diffs WHERE burst_id = ? ORDER BY created_at ASC",
        (burst_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def accept_diff(diff_id: str) -> dict:
    """Accept a single diff. Updates burst_lines.formatted_line and status."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    diff = db.execute(
        "SELECT * FROM burst_diffs WHERE diff_id = ?", (diff_id,)
    ).fetchone()
    if not diff:
        raise ValueError(f"Diff {diff_id} not found.")

    diff = dict(diff)

    db.execute(
        "UPDATE burst_diffs SET status = 'accepted', updated_at = ? WHERE diff_id = ?",
        (now, diff_id)
    )
    db.execute(
        """
        UPDATE burst_lines
        SET status = 'accepted', formatted_line = ?, updated_at = ?
        WHERE line_id = ?
        """,
        (diff["formatted_after"], now, diff["line_id"])
    )
    _record_history(db, diff["line_id"], "accept", {"diff_id": diff_id})
    db.commit()

    return {
        "diff_id": diff_id,
        "status": "accepted",
        "line_id": diff["line_id"],
        "updated_formatted_line": diff["formatted_after"],
    }


def reject_diff(diff_id: str) -> dict:
    """Reject a single diff. Restores formatted_line to raw_line."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    diff = db.execute(
        "SELECT * FROM burst_diffs WHERE diff_id = ?", (diff_id,)
    ).fetchone()
    if not diff:
        raise ValueError(f"Diff {diff_id} not found.")

    diff = dict(diff)

    db.execute(
        "UPDATE burst_diffs SET status = 'rejected', updated_at = ? WHERE diff_id = ?",
        (now, diff_id)
    )
    db.execute(
        """
        UPDATE burst_lines
        SET status = 'rejected', formatted_line = raw_line, updated_at = ?
        WHERE line_id = ?
        """,
        (now, diff["line_id"])
    )
    _record_history(db, diff["line_id"], "reject", {"diff_id": diff_id})
    db.commit()

    # Get updated raw_line for response
    line = db.execute(
        "SELECT raw_line FROM burst_lines WHERE line_id = ?", (diff["line_id"],)
    ).fetchone()

    return {
        "diff_id": diff_id,
        "status": "rejected",
        "line_id": diff["line_id"],
        "updated_formatted_line": dict(line)["raw_line"],
    }


def accept_all_pending(burst_id: int) -> list[dict]:
    """Accept all pending diffs for a burst."""
    db = get_db()
    pending = db.execute(
        "SELECT diff_id FROM burst_diffs WHERE burst_id = ? AND status = 'pending'",
        (burst_id,)
    ).fetchall()
    results = []
    for row in pending:
        results.append(accept_diff(row["diff_id"]))
    return results


def reject_all_pending(burst_id: int) -> list[dict]:
    """Reject all pending diffs for a burst."""
    db = get_db()
    pending = db.execute(
        "SELECT diff_id FROM burst_diffs WHERE burst_id = ? AND status = 'pending'",
        (burst_id,)
    ).fetchall()
    results = []
    for row in pending:
        results.append(reject_diff(row["diff_id"]))
    return results


def get_formatted_burst(burst_id: int, raw_text: str) -> dict:
    """
    Return the formatted text for a burst by applying all accepted diffs.
    Falls back to raw text if no accepted diffs exist.
    """
    db = get_db()
    lines_rows = db.execute(
        "SELECT * FROM burst_lines WHERE burst_id = ? ORDER BY line_index",
        (burst_id,)
    ).fetchall()

    if not lines_rows:
        return {
            "burst_id": burst_id,
            "has_formatting": False,
            "lines": [],
            "formatted_text": raw_text,
            "raw_text": raw_text,
        }

    lines = [dict(r) for r in lines_rows]
    has_accepted = any(l["status"] == "accepted" for l in lines)

    formatted_text = "\n".join(l["formatted_line"] for l in lines)

    return {
        "burst_id": burst_id,
        "has_formatting": has_accepted,
        "lines": lines,
        "formatted_text": formatted_text,
        "raw_text": raw_text,
    }


def _record_history(db, line_id: str, operation: str, detail: dict) -> None:
    import uuid as _uuid
    history_id = str(_uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "INSERT INTO line_history (history_id, line_id, operation, detail, created_at) VALUES (?, ?, ?, ?, ?)",
        (history_id, line_id, operation, json.dumps(detail), now),
    )
