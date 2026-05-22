# backend/tests/test_storage_service.py
"""
Tests: append_service.py, stream_service.py, and storage_service.py in V1.1

Covers:
  - append_chunk: creates entry on first append, appends on subsequent calls
  - append_chunk: updates bursts.updated_at (critical for continuity window)
  - get_app_state: returns nulls when no session exists
  - update_app_state: persists flareon and burst IDs
"""

import pytest
import sqlite3
import services.storage_service as storage_service
import services.flareon_service as flareon_service
import services.burst_service as burst_service
import services.append_service as append_service
import services.stream_service as stream_service


@pytest.fixture(autouse=True)
def inject_test_db(test_db: sqlite3.Connection, monkeypatch):
    monkeypatch.setattr("services.storage_service.get_db", lambda: test_db)
    monkeypatch.setattr("services.flareon_service.get_db", lambda: test_db)
    monkeypatch.setattr("services.burst_service.get_db", lambda: test_db)
    monkeypatch.setattr("services.append_service.get_db", lambda: test_db)
    monkeypatch.setattr("services.stream_service.get_db", lambda: test_db)


@pytest.mark.unit
def test_append_chunk_creates_burst_entry(test_db):
    flareon = flareon_service.create_flareon("Test")
    burst = burst_service.get_or_create_active_burst(flareon["id"])

    result = append_service.append_chunk(burst["id"], "Hello world")

    assert isinstance(result, int) and result == 0, (
        f"[append_service.append_chunk] First sequence number must be 0.\n"
        f"  Returned : {result}\n"
        f"  Expected : 0"
    )

    row = test_db.execute(
        "SELECT content_chunk FROM burst_entries WHERE burst_id = ?", (burst["id"],)
    ).fetchone()

    assert row is not None, (
        f"[append_service.append_chunk] No row found in burst_entries after append.\n"
        f"  burst_id : {burst['id']}"
    )
    assert row["content_chunk"] == "Hello world", (
        f"[append_service.append_chunk] Saved content chunk does not match input.\n"
        f"  Input    : 'Hello world'\n"
        f"  Saved    : '{row['content_chunk']}'"
    )


@pytest.mark.unit
def test_append_chunk_appends_to_entry_log(test_db):
    """Appending twice to the same burst creates two entries in sequence."""
    flareon = flareon_service.create_flareon("Update Test")
    burst = burst_service.get_or_create_active_burst(flareon["id"])

    seq1 = append_service.append_chunk(burst["id"], "Hello ")
    seq2 = append_service.append_chunk(burst["id"], "world!")

    assert seq1 == 0
    assert seq2 == 1

    rows = test_db.execute(
        "SELECT content_chunk, sequence_number FROM burst_entries WHERE burst_id = ? ORDER BY sequence_number ASC",
        (burst["id"],)
    ).fetchall()

    assert len(rows) == 2, (
        f"[append_service.append_chunk] Expected exactly 2 burst_entry rows after two appends.\n"
        f"  Found : {len(rows)} rows"
    )
    assert rows[0]["content_chunk"] == "Hello "
    assert rows[1]["content_chunk"] == "world!"

    reconstructed = stream_service.reconstruct_burst(burst["id"])
    assert reconstructed == "Hello world!"


@pytest.mark.unit
def test_append_chunk_updates_burst_updated_at(test_db):
    """Every append must refresh bursts.updated_at — this is what the continuity rule reads."""
    import time

    flareon = flareon_service.create_flareon("Timing")
    burst = burst_service.get_or_create_active_burst(flareon["id"])

    before = test_db.execute(
        "SELECT updated_at FROM bursts WHERE id = ?", (burst["id"],)
    ).fetchone()["updated_at"]

    time.sleep(1.1)  # Ensure timestamp changes
    append_service.append_chunk(burst["id"], "Updated content")

    after = test_db.execute(
        "SELECT updated_at FROM bursts WHERE id = ?", (burst["id"],)
    ).fetchone()["updated_at"]

    assert after != before, (
        f"[append_service.append_chunk] bursts.updated_at was NOT refreshed after append.\n"
        f"  Before save : {before}\n"
        f"  After save  : {after}"
    )


@pytest.mark.unit
def test_get_app_state_returns_nulls_on_fresh_db(test_db):
    state = storage_service.get_app_state()

    assert state["last_opened_flareon_id"] is None, (
        f"[storage_service.get_app_state] Fresh database should return null flareon_id.\n"
        f"  Returned : {state.get('last_opened_flareon_id')}\n"
        f"  Expected : None"
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
        f"  Retrieved: {state.get('last_opened_flareon_id')}"
    )
    assert state["last_opened_burst_id"] == burst["id"], (
        f"[storage_service.update_app_state] burst_id not persisted correctly.\n"
        f"  Stored   : {burst['id']}\n"
        f"  Retrieved: {state.get('last_opened_burst_id')}"
    )
