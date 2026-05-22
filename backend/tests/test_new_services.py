# backend/tests/test_new_services.py
"""
Tests for helper/uncovered methods in append_service and stream_service.
"""

import pytest
import sqlite3
from datetime import datetime, timezone
import services.flareon_service as flareon_service
import services.burst_service as burst_service
import services.append_service as append_service
import services.stream_service as stream_service


@pytest.fixture(autouse=True)
def inject_test_db(test_db: sqlite3.Connection, monkeypatch):
    monkeypatch.setattr("services.flareon_service.get_db", lambda: test_db)
    monkeypatch.setattr("services.burst_service.get_db", lambda: test_db)
    monkeypatch.setattr("services.append_service.get_db", lambda: test_db)
    monkeypatch.setattr("services.stream_service.get_db", lambda: test_db)


@pytest.mark.unit
def test_get_next_sequence_number(test_db):
    flareon = flareon_service.create_flareon("Next Seq Test")
    burst = burst_service.get_or_create_active_burst(flareon["id"])

    # Fresh burst next sequence number should be 0
    assert append_service.get_next_sequence_number(burst["id"]) == 0

    # Append first chunk
    append_service.append_chunk(burst["id"], "A")
    assert append_service.get_next_sequence_number(burst["id"]) == 1

    # Append second chunk
    append_service.append_chunk(burst["id"], "B")
    assert append_service.get_next_sequence_number(burst["id"]) == 2


@pytest.mark.unit
def test_get_all_bursts_with_content(test_db):
    flareon = flareon_service.create_flareon("All Bursts Content Test")
    
    # Create two bursts manually at different times
    b1 = burst_service.get_or_create_active_burst(flareon["id"])
    append_service.append_chunk(b1["id"], "Chunk from first burst.")

    # We manually create a second burst (forcing it by calling _create_burst)
    b2 = burst_service._create_burst(flareon["id"])
    append_service.append_chunk(b2["id"], "Chunk from second burst.")

    bursts = stream_service.get_all_bursts_with_content(flareon["id"])

    assert len(bursts) == 2
    assert bursts[0]["id"] == b1["id"]
    assert bursts[0]["content"] == "Chunk from first burst."
    assert bursts[1]["id"] == b2["id"]
    assert bursts[1]["content"] == "Chunk from second burst."
