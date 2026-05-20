# backend/tests/test_storage_service.py
"""
Tests: storage_service.py

Covers:
  - save_content: creates entry on first save, updates on subsequent saves
  - save_content: updates bursts.updated_at (critical for continuity window)
  - get_app_state: returns nulls when no session exists
  - update_app_state: persists flareon and burst IDs
"""

import pytest
import sqlite3
import services.storage_service as storage_service
import services.flareon_service as flareon_service
import services.burst_service as burst_service


@pytest.fixture(autouse=True)
def inject_test_db(test_db: sqlite3.Connection, monkeypatch):
    monkeypatch.setattr("services.storage_service.get_db", lambda: test_db)
    monkeypatch.setattr("services.flareon_service.get_db", lambda: test_db)
    monkeypatch.setattr("services.burst_service.get_db", lambda: test_db)


@pytest.mark.unit
def test_save_content_creates_burst_entry(test_db):
    flareon = flareon_service.create_flareon("Test")
    burst = burst_service.get_or_create_active_burst(flareon["id"])

    result = storage_service.save_content(burst["id"], "Hello world")

    assert isinstance(result, int) and result > 0, (
        f"[storage_service.save_content] Return value must be a positive integer burst_entry_id.\n"
        f"  Returned : {result}\n"
        f"  Expected : positive integer\n"
        f"  Fix      : After INSERT or UPDATE, return the burst_entry row id."
    )

    row = test_db.execute(
        "SELECT content FROM burst_entries WHERE burst_id = ?", (burst["id"],)
    ).fetchone()

    assert row is not None, (
        f"[storage_service.save_content] No row found in burst_entries after save.\n"
        f"  burst_id : {burst['id']}\n"
        f"  Fix      : Ensure INSERT INTO burst_entries commits successfully."
    )
    assert row["content"] == "Hello world", (
        f"[storage_service.save_content] Saved content does not match input.\n"
        f"  Input    : 'Hello world'\n"
        f"  Saved    : '{row['content']}'\n"
        f"  Fix      : Verify the content parameter is correctly bound in the SQL query."
    )


@pytest.mark.unit
def test_save_content_updates_existing_entry(test_db):
    """Saving twice to the same burst updates, not duplicates, the burst_entry."""
    flareon = flareon_service.create_flareon("Update Test")
    burst = burst_service.get_or_create_active_burst(flareon["id"])

    storage_service.save_content(burst["id"], "Draft one")
    storage_service.save_content(burst["id"], "Draft two — updated")

    rows = test_db.execute(
        "SELECT content FROM burst_entries WHERE burst_id = ?", (burst["id"],)
    ).fetchall()

    assert len(rows) == 1, (
        f"[storage_service.save_content] Expected exactly 1 burst_entry row after two saves.\n"
        f"  Found : {len(rows)} rows\n"
        f"  Each burst has at most one burst_entry in V1 (UNIQUE constraint on burst_id).\n"
        f"  Fix   : Use INSERT OR REPLACE, or check-then-update logic. "
        f"Do not INSERT a new row on every save call."
    )
    assert rows[0]["content"] == "Draft two — updated", (
        f"[storage_service.save_content] Content was not updated after second save.\n"
        f"  Expected : 'Draft two — updated'\n"
        f"  Found    : '{rows[0]['content']}'\n"
        f"  Fix      : The UPDATE branch of the upsert logic must replace the content."
    )


@pytest.mark.unit
def test_save_content_updates_burst_updated_at(test_db):
    """Every save must refresh bursts.updated_at — this is what the continuity rule reads."""
    import time

    flareon = flareon_service.create_flareon("Timing")
    burst = burst_service.get_or_create_active_burst(flareon["id"])

    before = test_db.execute(
        "SELECT updated_at FROM bursts WHERE id = ?", (burst["id"],)
    ).fetchone()["updated_at"]

    time.sleep(1.1)  # Ensure timestamp changes
    storage_service.save_content(burst["id"], "Updated content")

    after = test_db.execute(
        "SELECT updated_at FROM bursts WHERE id = ?", (burst["id"],)
    ).fetchone()["updated_at"]

    assert after != before, (
        f"[storage_service.save_content] bursts.updated_at was NOT refreshed after save.\n"
        f"  Before save : {before}\n"
        f"  After save  : {after}\n"
        f"  This is the most dangerous bug in NotesFlare: if updated_at doesn't refresh,\n"
        f"  the 30-minute continuity window calculates from burst creation time, not last\n"
        f"  user activity. Every session longer than 30 min will spuriously create new bursts.\n"
        f"  Fix: In storage_service.save_content, after the burst_entries upsert, run:\n"
        f"       UPDATE bursts SET updated_at = ? WHERE id = ?"
    )


@pytest.mark.unit
def test_get_app_state_returns_nulls_on_fresh_db(test_db):
    state = storage_service.get_app_state()

    assert state["last_opened_flareon_id"] is None, (
        f"[storage_service.get_app_state] Fresh database should return null flareon_id.\n"
        f"  Returned : {state.get('last_opened_flareon_id')}\n"
        f"  Expected : None\n"
        f"  Fix      : app_state row is initialized with NULLs; ensure SELECT reads them as None."
    )


@pytest.mark.unit
def test_update_and_retrieve_app_state(test_db):
    flareon = flareon_service.create_flareon("Philosophy")
    burst = burst_service.get_or_create_active_burst(flareon["id"])

    storage_service.update_app_state(flareon["id"], burst["id"])
    state = storage_service.get_app_state()

    assert state["last_opened_flareon_id"] == flareon["id"], (
        f"[storage_service.update_app_state] flareon_id not persisted correctly.\n"
        f"  Stored   : {flareon['id']}\n"
        f"  Retrieved: {state.get('last_opened_flareon_id')}\n"
        f"  Fix      : UPDATE app_state SET last_opened_flareon_id = ? WHERE id = 1"
    )
    assert state["last_opened_burst_id"] == burst["id"], (
        f"[storage_service.update_app_state] burst_id not persisted correctly.\n"
        f"  Stored   : {burst['id']}\n"
        f"  Retrieved: {state.get('last_opened_burst_id')}\n"
        f"  Fix      : UPDATE app_state SET last_opened_burst_id = ? WHERE id = 1"
    )
