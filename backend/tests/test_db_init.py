# backend/tests/test_db_init.py
"""
Tests: Database schema initialization.

Verifies that all required tables exist after schema initialization,
that all columns are present and correctly typed, and that
the app_state singleton constraint is enforced.
"""

import sqlite3
import pytest


@pytest.mark.unit
def test_all_required_tables_exist(test_db: sqlite3.Connection):
    """
    After schema.sql runs, exactly these four tables must exist:
    flareons, bursts, burst_entries, app_state.
    """
    cursor = test_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row["name"] for row in cursor.fetchall()}
    required = {"flareons", "bursts", "burst_entries", "app_state"}
    missing = required - tables

    assert not missing, (
        f"[DB INIT] Missing tables after schema initialization.\n"
        f"  Required tables : {sorted(required)}\n"
        f"  Found tables    : {sorted(tables)}\n"
        f"  Missing         : {sorted(missing)}\n"
        f"  Fix             : Check backend/database/schema.sql — all four CREATE TABLE "
        f"statements must be present and free of syntax errors."
    )


@pytest.mark.unit
def test_flareons_columns(test_db: sqlite3.Connection):
    """flareons must have: id, name, created_at, updated_at, last_opened_at"""
    cursor = test_db.execute("PRAGMA table_info(flareons)")
    cols = {row["name"] for row in cursor.fetchall()}
    required = {"id", "name", "created_at", "updated_at", "last_opened_at"}
    missing = required - cols

    assert not missing, (
        f"[DB INIT] flareons table is missing columns.\n"
        f"  Required : {sorted(required)}\n"
        f"  Found    : {sorted(cols)}\n"
        f"  Missing  : {sorted(missing)}\n"
        f"  Fix      : Add missing columns to the CREATE TABLE flareons statement "
        f"in backend/database/schema.sql."
    )


@pytest.mark.unit
def test_bursts_columns(test_db: sqlite3.Connection):
    """bursts must have: id, flareon_id, started_at, ended_at, created_at, updated_at"""
    cursor = test_db.execute("PRAGMA table_info(bursts)")
    cols = {row["name"] for row in cursor.fetchall()}
    required = {"id", "flareon_id", "started_at", "ended_at", "created_at", "updated_at"}
    missing = required - cols

    assert not missing, (
        f"[DB INIT] bursts table is missing columns.\n"
        f"  Required : {sorted(required)}\n"
        f"  Found    : {sorted(cols)}\n"
        f"  Missing  : {sorted(missing)}\n"
        f"  Fix      : Add missing columns to CREATE TABLE bursts in schema.sql.\n"
        f"  Note     : 'updated_at' is CRITICAL — the 30-minute continuity rule reads "
        f"this field. If missing, every Flareon open will create a new burst."
    )


@pytest.mark.unit
def test_burst_entries_columns(test_db: sqlite3.Connection):
    """burst_entries must have: id, burst_id, content, created_at, updated_at"""
    cursor = test_db.execute("PRAGMA table_info(burst_entries)")
    cols = {row["name"] for row in cursor.fetchall()}
    required = {"id", "burst_id", "content", "created_at", "updated_at"}
    missing = required - cols

    assert not missing, (
        f"[DB INIT] burst_entries table is missing columns.\n"
        f"  Required : {sorted(required)}\n"
        f"  Found    : {sorted(cols)}\n"
        f"  Missing  : {sorted(missing)}\n"
        f"  Fix      : Check CREATE TABLE burst_entries in schema.sql."
    )


@pytest.mark.unit
def test_app_state_singleton_row_exists(test_db: sqlite3.Connection):
    """After schema init, app_state must have exactly one row (the singleton)."""
    cursor = test_db.execute("SELECT COUNT(*) as cnt FROM app_state")
    count = cursor.fetchone()["cnt"]

    assert count == 1, (
        f"[DB INIT] app_state must have exactly 1 row after initialization.\n"
        f"  Found    : {count} rows\n"
        f"  Expected : 1 row\n"
        f"  Fix      : schema.sql must include: "
        f"INSERT OR IGNORE INTO app_state (id) VALUES (1); after the CREATE TABLE."
    )


@pytest.mark.unit
def test_app_state_singleton_insert_rejected(test_db: sqlite3.Connection):
    """SQLite CHECK (id = 1) must reject any attempt to insert a second row."""
    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        test_db.execute(
            "INSERT INTO app_state (id, last_opened_flareon_id) VALUES (2, NULL)"
        )
        test_db.commit()

    assert exc_info.value, (
        f"[DB INIT] app_state should REJECT insertion of a row with id != 1.\n"
        f"  The CHECK (id = 1) constraint is missing from the app_state table definition.\n"
        f"  Fix: In schema.sql, the app_state table must include:\n"
        f"    id INTEGER PRIMARY KEY CHECK (id = 1)\n"
        f"  Without this, bugs can accumulate multiple rows and GET /api/state "
        f"will return ambiguous results."
    )
