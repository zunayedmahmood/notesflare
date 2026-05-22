# backend/tests/test_schema_migration.py

"""
Tests that the V1→V1.1 schema migration runs correctly.
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path


@pytest.mark.unit
def test_migration_detects_v1_schema():
    """
    migrate_to_v1_1 must detect the V1 schema (has 'content' column)
    and replace it with the V1.1 schema (has 'content_chunk').
    """
    # Create a temporary in-memory DB with V1 schema
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    # V1 burst_entries schema
    conn.executescript("""
        CREATE TABLE flareons (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT);
        CREATE TABLE bursts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flareon_id INTEGER REFERENCES flareons(id),
            started_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE burst_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            burst_id INTEGER REFERENCES bursts(id),
            content TEXT DEFAULT '',
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE app_state (id INTEGER PRIMARY KEY CHECK (id = 1));
        INSERT OR IGNORE INTO app_state (id) VALUES (1);
    """)
    conn.commit()

    # Run migration directly
    from database.db import migrate_to_v1_1
    migrate_to_v1_1(conn)

    # Verify schema changed
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(burst_entries)").fetchall()}

    assert "content_chunk" in cols, (
        f"[migration] After migration, burst_entries must have 'content_chunk' column. "
        f"Found columns: {cols}"
    )
    assert "content" not in cols, (
        f"[migration] After migration, burst_entries must NOT have 'content' column. "
        f"Found columns: {cols}"
    )
    assert "sequence_number" in cols, (
        f"[migration] After migration, burst_entries must have 'sequence_number' column. "
        f"Found columns: {cols}"
    )
    conn.close()


@pytest.mark.unit
def test_migration_is_idempotent_on_v1_1_schema():
    """
    Running migrate_to_v1_1 on a DB that already has V1.1 schema must be a no-op.
    No error, no data loss.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    # V1.1 burst_entries schema
    conn.executescript("""
        CREATE TABLE flareons (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT);
        CREATE TABLE bursts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flareon_id INTEGER REFERENCES flareons(id),
            started_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE burst_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            burst_id INTEGER REFERENCES bursts(id),
            content_chunk TEXT DEFAULT '',
            sequence_number INTEGER DEFAULT 0,
            created_at TEXT
        );
        CREATE TABLE app_state (id INTEGER PRIMARY KEY CHECK (id = 1));
        INSERT OR IGNORE INTO app_state (id) VALUES (1);
    """)
    conn.commit()

    # Should not raise
    from database.db import migrate_to_v1_1

    try:
        migrate_to_v1_1(conn)
    except Exception as e:
        pytest.fail(
            f"[migration] migrate_to_v1_1 must be a no-op on V1.1 schema. "
            f"Raised: {e}"
        )

    # Schema must still be correct
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(burst_entries)").fetchall()}
    assert "content_chunk" in cols
    conn.close()
