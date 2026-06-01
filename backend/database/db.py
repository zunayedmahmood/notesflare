import sqlite3
import os
import threading
from pathlib import Path

# DB is stored in the /storage directory at project root
_DB_PATH = Path(__file__).resolve().parents[2] / "storage" / "notesflare.db"
_connection: sqlite3.Connection | None = None

_local = threading.local()
_all_connections = []
_all_connections_lock = threading.Lock()


def get_db() -> sqlite3.Connection:
    """Return the thread-local SQLite connection, or the E2E override connection if set."""
    global _connection
    if _connection is not None:
        return _connection

    if not hasattr(_local, "connection") or _local.connection is None:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row  # Rows accessible as dicts
        conn.execute("PRAGMA journal_mode=WAL")   # Better concurrency
        conn.execute("PRAGMA foreign_keys=ON")    # Enforce FK constraints
        _local.connection = conn
        with _all_connections_lock:
            _all_connections.append(conn)
    return _local.connection


def close_all_connections() -> None:
    """Close all thread-local connections and the global connection override."""
    global _connection, _all_connections
    with _all_connections_lock:
        for conn in _all_connections:
            try:
                conn.close()
            except Exception:
                pass
        _all_connections.clear()
    if hasattr(_local, "connection"):
        _local.connection = None
    if _connection is not None:
        try:
            _connection.close()
        except Exception:
            pass
        _connection = None



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


def migrate_to_v1_2(db: sqlite3.Connection) -> None:
    """
    V1.2 migration: add burst_lines, burst_diffs, line_history tables.
    Guard: only runs if burst_lines does not already exist.
    Safe to run on a fresh database (schema.sql already creates them).
    """
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='burst_lines'"
    ).fetchall()

    if not rows:
        print("[migrate] V1.2: Creating formatting tables (burst_lines, burst_diffs, line_history)...")
        # Tables are created by schema.sql on next executescript call.
        # This guard just prevents double-logging.
        print("[migrate] V1.2: Complete.")


def init_db() -> None:
    """Run schema.sql to initialize all tables. Safe to call multiple times."""
    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text()
    db = get_db()
    db.executescript(schema_sql)
    migrate_to_v1_1(db)    # Existing V1.1 migration
    migrate_to_v1_2(db)    # New V1.2 migration
    db.commit()
