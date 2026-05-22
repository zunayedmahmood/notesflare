# backend/tests/test_burst_service.py
"""
Tests: burst_service.py

The most critical service in NotesFlare. These tests verify:
  - Burst is created on first Flareon open
  - Same burst is returned if within 30-minute window
  - New burst is created if outside 30-minute window
  - get_all_bursts_for_flareon returns chronological order
  - Burst updated_at is refreshed on save (so continuity window extends)
"""

import pytest
import sqlite3
from datetime import datetime, timedelta, timezone
from freezegun import freeze_time

import services.burst_service as burst_service
import services.flareon_service as flareon_service
import services.storage_service as storage_service

THIRTY_MIN_BOUNDARY = 30  # minutes


@pytest.fixture(autouse=True)
def inject_test_db(test_db: sqlite3.Connection, monkeypatch):
    monkeypatch.setattr("services.burst_service.get_db", lambda: test_db)
    monkeypatch.setattr("services.flareon_service.get_db", lambda: test_db)
    monkeypatch.setattr("services.storage_service.get_db", lambda: test_db)
    monkeypatch.setattr("services.append_service.get_db", lambda: test_db)


@pytest.mark.unit
def test_first_open_creates_burst(test_db):
    """Opening a Flareon for the first time must create exactly one burst."""
    flareon = flareon_service.create_flareon("Physics")

    burst = burst_service.get_or_create_active_burst(flareon["id"])

    assert burst is not None, (
        f"[burst_service.get_or_create_active_burst] No burst returned on first open.\n"
        f"  Flareon id : {flareon['id']}\n"
        f"  Returned   : None\n"
        f"  Expected   : A newly created burst dict with at minimum 'id' and 'flareon_id'\n"
        f"  Fix        : When no bursts exist for this flareon_id, create one via "
        f"_create_burst(flareon_id)."
    )
    assert burst["flareon_id"] == flareon["id"], (
        f"[burst_service.get_or_create_active_burst] Burst belongs to wrong Flareon.\n"
        f"  Burst flareon_id : {burst.get('flareon_id')}\n"
        f"  Expected         : {flareon['id']}\n"
        f"  Fix              : INSERT INTO bursts must use the correct flareon_id parameter."
    )

    # Verify exactly one burst exists
    count = test_db.execute(
        "SELECT COUNT(*) as cnt FROM bursts WHERE flareon_id = ?", (flareon["id"],)
    ).fetchone()["cnt"]

    assert count == 1, (
        f"[burst_service.get_or_create_active_burst] Expected exactly 1 burst after first open.\n"
        f"  Found : {count} burst(s)\n"
        f"  Fix   : Ensure _create_burst inserts exactly once and is not called multiple times."
    )


@pytest.mark.unit
@pytest.mark.slow
def test_within_30_minutes_returns_same_burst(test_db):
    """
    If the user opens a Flareon twice within 30 minutes, both calls must
    return the same burst ID. No new burst should be created.
    """
    flareon = flareon_service.create_flareon("Startup Ideas")

    initial_time = datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc)

    with freeze_time(initial_time):
        burst_first = burst_service.get_or_create_active_burst(flareon["id"])

    # 20 minutes later — within the 30-minute window
    second_open_time = initial_time + timedelta(minutes=20)

    with freeze_time(second_open_time):
        burst_second = burst_service.get_or_create_active_burst(flareon["id"])

    assert burst_first["id"] == burst_second["id"], (
        f"[burst_service — 30-minute rule] Same burst must be returned when gap < 30 min.\n"
        f"  First open  : {initial_time.isoformat()} → burst id {burst_first['id']}\n"
        f"  Second open : {second_open_time.isoformat()} (20 min later) → burst id {burst_second['id']}\n"
        f"  Gap         : 20 minutes (under the {THIRTY_MIN_BOUNDARY}-minute threshold)\n"
        f"  Expected    : Both calls return burst id {burst_first['id']}\n"
        f"  Got         : Two different burst ids — a new burst was created incorrectly.\n"
        f"  Fix         : In burst_service.get_or_create_active_burst, the continuity check "
        f"must compare datetime.utcnow() against bursts.updated_at. Ensure the comparison "
        f"uses the correct field (updated_at, NOT started_at) and that datetime parsing "
        f"handles the ISO 8601 string format stored in SQLite."
    )


@pytest.mark.unit
@pytest.mark.slow
def test_after_30_minutes_creates_new_burst(test_db):
    """
    If the user opens a Flareon more than 30 minutes after the last burst,
    a new burst must be created. The old burst must not be modified.
    """
    flareon = flareon_service.create_flareon("Deep Work")

    initial_time = datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc)

    with freeze_time(initial_time):
        burst_first = burst_service.get_or_create_active_burst(flareon["id"])

    # 31 minutes later — outside the window
    second_open_time = initial_time + timedelta(minutes=31)

    with freeze_time(second_open_time):
        burst_second = burst_service.get_or_create_active_burst(flareon["id"])

    assert burst_first["id"] != burst_second["id"], (
        f"[burst_service — 30-minute rule] New burst must be created when gap > 30 min.\n"
        f"  First open  : {initial_time.isoformat()} → burst id {burst_first['id']}\n"
        f"  Second open : {second_open_time.isoformat()} (31 min later) → burst id {burst_second['id']}\n"
        f"  Gap         : 31 minutes (exceeds the {THIRTY_MIN_BOUNDARY}-minute threshold)\n"
        f"  Expected    : burst_second has a DIFFERENT id than burst_first\n"
        f"  Got         : Both are burst id {burst_first['id']} — continuity window not enforced.\n"
        f"  Fix         : The condition should be: "
        f"(now - updated_at).total_seconds() > {THIRTY_MIN_BOUNDARY * 60}. "
        f"Check that you're comparing total_seconds(), not minutes directly."
    )

    # Verify total burst count is now 2
    count = test_db.execute(
        "SELECT COUNT(*) as cnt FROM bursts WHERE flareon_id = ?", (flareon["id"],)
    ).fetchone()["cnt"]

    assert count == 2, (
        f"[burst_service — 30-minute rule] Expected exactly 2 bursts after second open at 31 min.\n"
        f"  Found : {count} burst(s) for flareon_id={flareon['id']}\n"
        f"  Fix   : _create_burst should insert a new row; check that it commits and "
        f"that get_or_create_active_burst calls it exactly once when threshold is exceeded."
    )


@pytest.mark.unit
@pytest.mark.slow
def test_exactly_at_30_minute_boundary_creates_new_burst(test_db):
    """
    At exactly 30 minutes (not under, not over), a new burst is created.
    The rule is: gap < 30 minutes → continue. Gap >= 30 minutes → new burst.
    """
    flareon = flareon_service.create_flareon("Boundary Test")
    initial_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    with freeze_time(initial_time):
        burst_first = burst_service.get_or_create_active_burst(flareon["id"])

    exact_boundary = initial_time + timedelta(minutes=30)

    with freeze_time(exact_boundary):
        burst_second = burst_service.get_or_create_active_burst(flareon["id"])

    assert burst_first["id"] != burst_second["id"], (
        f"[burst_service — boundary] At exactly 30 minutes, a new burst must be created.\n"
        f"  Gap      : exactly 30 minutes\n"
        f"  Rule     : gap < 30 min → continue; gap >= 30 min → new burst\n"
        f"  Expected : New burst (different id)\n"
        f"  Got      : Same burst id {burst_first['id']} — boundary condition is wrong.\n"
        f"  Fix      : Use strict less-than: `if gap_seconds < 1800` (not <=)."
    )


@pytest.mark.unit
def test_save_extends_continuity_window(test_db):
    """
    After an append, bursts.updated_at is refreshed. This means typing extends
    the 30-minute window — the burst won't expire as long as the user is active.
    """
    import services.append_service as append_service
    flareon = flareon_service.create_flareon("Writing")
    initial_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    with freeze_time(initial_time):
        burst = burst_service.get_or_create_active_burst(flareon["id"])
        append_service.append_chunk(burst["id"], "First thought.")

    # 25 minutes later, save again (user was actively typing)
    mid_time = initial_time + timedelta(minutes=25)
    with freeze_time(mid_time):
        append_service.append_chunk(burst["id"], "First thought. Second thought.")

    # Now 20 minutes after the LAST save (25 + 20 = 45 min from start, but only 20 from last save)
    late_time = mid_time + timedelta(minutes=20)
    with freeze_time(late_time):
        burst_again = burst_service.get_or_create_active_burst(flareon["id"])

    assert burst["id"] == burst_again["id"], (
        f"[burst_service + append_service] Appending chunk must refresh the continuity window.\n"
        f"  Timeline:\n"
        f"    t=0min   : First open + first save\n"
        f"    t=25min  : Second save (user actively typing)\n"
        f"    t=45min  : Third open (20 min after last save — should continue)\n"
        f"  Expected : Same burst id {burst['id']} returned at t=45min\n"
        f"  Got      : New burst created — updated_at was not refreshed on append.\n"
        f"  Fix      : append_service.append_chunk must UPDATE bursts SET updated_at = ? "
        f"after every append. Without this, the continuity window calculates from the burst's "
        f"creation time, not from the last user activity."
    )


@pytest.mark.unit
def test_get_all_bursts_chronological_order(test_db):
    """Bursts for a Flareon must be returned oldest-first."""
    flareon = flareon_service.create_flareon("Chronology Test")

    t1 = datetime(2025, 1, 10, 8, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2025, 1, 12, 14, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2025, 1, 15, 20, 0, 0, tzinfo=timezone.utc)

    with freeze_time(t1):
        burst_service.get_or_create_active_burst(flareon["id"])
    with freeze_time(t2):
        burst_service.get_or_create_active_burst(flareon["id"])
    with freeze_time(t3):
        burst_service.get_or_create_active_burst(flareon["id"])

    bursts = burst_service.get_all_bursts_for_flareon(flareon["id"])

    assert len(bursts) == 3, (
        f"[burst_service.get_all_bursts_for_flareon] Expected 3 bursts.\n"
        f"  Found : {len(bursts)}\n"
        f"  Fix   : Verify INSERT is committing and SELECT returns all rows for flareon_id."
    )

    started_ats = [b["started_at"] for b in bursts]
    assert started_ats == sorted(started_ats), (
        f"[burst_service.get_all_bursts_for_flareon] Bursts must be ordered oldest-first.\n"
        f"  Returned order : {started_ats}\n"
        f"  Expected order : {sorted(started_ats)}\n"
        f"  Fix            : Add ORDER BY started_at ASC to the SELECT query."
    )
