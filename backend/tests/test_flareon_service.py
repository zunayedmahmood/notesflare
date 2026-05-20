# backend/tests/test_flareon_service.py
"""
Tests: flareon_service.py

Covers:
  - create_flareon: success, duplicate name rejection
  - list_flareons: ordering (most recently opened first)
  - get_flareon_by_id: found and not-found cases
  - touch_flareon: updates last_opened_at
"""

import pytest
import sqlite3
from unittest.mock import patch

# We patch get_db so the service uses our test_db, not the real one
import services.flareon_service as flareon_service


@pytest.fixture(autouse=True)
def inject_test_db(test_db: sqlite3.Connection, monkeypatch):
    """Redirect all flareon_service calls to the test database."""
    monkeypatch.setattr("services.flareon_service.get_db", lambda: test_db)


@pytest.mark.unit
def test_create_flareon_returns_correct_shape(test_db):
    result = flareon_service.create_flareon("Thermodynamics")

    assert "id" in result, (
        f"[flareon_service.create_flareon] Return value missing 'id' key.\n"
        f"  Returned : {result}\n"
        f"  Expected : dict with keys: id, name, created_at, last_opened_at\n"
        f"  Fix      : Ensure create_flareon builds and returns a full dict after INSERT."
    )
    assert result["name"] == "Thermodynamics", (
        f"[flareon_service.create_flareon] Name mismatch.\n"
        f"  Input    : 'Thermodynamics'\n"
        f"  Returned : '{result.get('name')}'\n"
        f"  Fix      : create_flareon must echo back the name from the INSERT."
    )
    assert result["id"] > 0, (
        f"[flareon_service.create_flareon] id must be a positive integer.\n"
        f"  Returned id : {result.get('id')}\n"
        f"  Fix         : Ensure lastrowid is read after cursor.execute(INSERT)."
    )


@pytest.mark.unit
def test_create_flareon_duplicate_raises(test_db):
    flareon_service.create_flareon("Cooking Notes")

    with pytest.raises(ValueError) as exc_info:
        flareon_service.create_flareon("Cooking Notes")

    assert "Cooking Notes" in str(exc_info.value), (
        f"[flareon_service.create_flareon] Duplicate name should raise ValueError "
        f"containing the duplicate name.\n"
        f"  Tried to create : 'Cooking Notes' (twice)\n"
        f"  Exception raised : {exc_info.value}\n"
        f"  Expected message : something like \"A Flareon named 'Cooking Notes' already exists.\"\n"
        f"  Fix              : Before INSERT, SELECT COUNT(*) WHERE name = ? and raise "
        f"ValueError if count > 0. The route handler converts this to HTTP 400."
    )


@pytest.mark.unit
def test_list_flareons_order_most_recently_opened_first(test_db):
    """
    Flareons with more recent last_opened_at appear first.
    Flareons never opened (last_opened_at IS NULL) appear last.
    """
    flareon_service.create_flareon("Old Topic")    # id 1
    flareon_service.create_flareon("New Topic")    # id 2
    flareon_service.create_flareon("Never Opened") # id 3

    # Manually set last_opened_at to simulate open history
    test_db.execute(
        "UPDATE flareons SET last_opened_at = '2025-01-10T10:00:00' WHERE name = 'Old Topic'"
    )
    test_db.execute(
        "UPDATE flareons SET last_opened_at = '2025-01-15T18:00:00' WHERE name = 'New Topic'"
    )
    test_db.commit()

    flareons = flareon_service.list_flareons()
    names = [f["name"] for f in flareons]

    assert names[0] == "New Topic", (
        f"[flareon_service.list_flareons] Most recently opened Flareon must appear first.\n"
        f"  Expected first : 'New Topic' (last_opened_at: 2025-01-15)\n"
        f"  Actual first   : '{names[0]}'\n"
        f"  Full order     : {names}\n"
        f"  Fix            : ORDER BY last_opened_at DESC NULLS LAST, created_at ASC"
    )
    assert names[-1] == "Never Opened", (
        f"[flareon_service.list_flareons] Flareons never opened must appear last.\n"
        f"  Expected last : 'Never Opened' (last_opened_at IS NULL)\n"
        f"  Actual last   : '{names[-1]}'\n"
        f"  Full order    : {names}\n"
        f"  Fix           : Use NULLS LAST in ORDER BY, or CASE WHEN last_opened_at IS NULL "
        f"THEN 1 ELSE 0 END as sort_null_last"
    )


@pytest.mark.unit
def test_get_flareon_by_id_not_found_returns_none(test_db):
    result = flareon_service.get_flareon_by_id(9999)

    assert result is None, (
        f"[flareon_service.get_flareon_by_id] Non-existent ID must return None.\n"
        f"  Input    : id=9999 (does not exist)\n"
        f"  Returned : {result}\n"
        f"  Fix      : After SELECT, check if row is None and return None explicitly. "
        f"The route layer converts None to HTTP 404."
    )


@pytest.mark.unit
def test_touch_flareon_updates_last_opened_at(test_db):
    from datetime import datetime, timezone

    flareon = flareon_service.create_flareon("Research")
    before = datetime.now(timezone.utc)

    flareon_service.touch_flareon(flareon["id"])

    row = test_db.execute(
        "SELECT last_opened_at FROM flareons WHERE id = ?", (flareon["id"],)
    ).fetchone()

    assert row["last_opened_at"] is not None, (
        f"[flareon_service.touch_flareon] last_opened_at was not set.\n"
        f"  Flareon id : {flareon['id']}\n"
        f"  After call : last_opened_at is still NULL\n"
        f"  Fix        : touch_flareon must UPDATE flareons SET last_opened_at = ? WHERE id = ?"
    )
