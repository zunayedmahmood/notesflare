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


def init_db() -> None:
    """Run schema.sql to initialize all tables. Safe to call multiple times."""
    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text()
    db = get_db()
    db.executescript(schema_sql)
    db.commit()
