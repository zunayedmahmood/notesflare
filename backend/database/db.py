# database/db.py

import sqlite3
import os
from pathlib import Path

# DB is stored in the /storage directory at project root
_DB_PATH = Path(__file__).resolve().parents[2] / "storage" / "notesflare.db"
_connection: sqlite3.Connection | None = None


def get_db() -> sqlite3.Connection:
    """Return the singleton SQLite connection. Creates it on first call."""
    global _connection
    if _connection is None:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _connection.row_factory = sqlite3.Row  # Rows accessible as dicts
        _connection.execute("PRAGMA journal_mode=WAL")   # Better concurrency
        _connection.execute("PRAGMA foreign_keys=ON")    # Enforce FK constraints
    return _connection


def migrate_to_v1_1(db: sqlite3.Connection) -> None:
    """
    One-time migration: drop the V1 burst_entries table and recreate it
    with the V1.1 append-only schema.

    This loses all existing burst content. Acceptable for V1→V1.1 transition
    because: (a) V1 is pre-release, (b) the schema is incompatible.

    Guard: only runs if the old column name 'content' exists on burst_entries.
    """
    # Inspect existing columns
    rows = db.execute("PRAGMA table_info(burst_entries)").fetchall()
    col_names = [row["name"] for row in rows]

    if "content" in col_names and "content_chunk" not in col_names:
        print("[migrate] Detected V1 burst_entries schema. Migrating to V1.1...")
        db.execute("DROP TABLE IF EXISTS burst_entries")
        db.executescript("""
            CREATE TABLE burst_entries (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                burst_id         INTEGER NOT NULL REFERENCES bursts(id) ON DELETE CASCADE,
                content_chunk    TEXT    NOT NULL DEFAULT '',
                sequence_number  INTEGER NOT NULL DEFAULT 0,
                created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
            );
        """)
        db.commit()
        print("[migrate] Migration complete. Previous burst content cleared.")


def init_db() -> None:
    """Run schema.sql to initialize all tables. Safe to call multiple times."""
    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text()
    db = get_db()
    db.executescript(schema_sql)
    migrate_to_v1_1(db)   # ← add this line
    db.commit()
