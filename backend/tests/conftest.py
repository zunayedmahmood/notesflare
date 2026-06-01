# backend/tests/conftest.py
"""
Shared test fixtures for NotesFlare backend tests.

Every test that touches the database uses a fresh, isolated SQLite database
in memory. No test ever reads or writes to the real `storage/notesflare.db`.

Fixtures:
  - test_db:     A fresh in-memory SQLite connection with schema applied.
  - client:      An httpx AsyncClient pointed at the FastAPI app, patched
                 to use `test_db` instead of the real database connection.
"""

import sqlite3
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from pathlib import Path

# Adjust import path based on how pytest discovers the backend
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import freezegun
freezegun.configure(extend_ignore_list=[
    'transformers', 'torch', 'spacy', 'sentence_transformers',
    'PIL', 'huggingface_hub', 'numpy', 'onnxruntime'
])

from database.db import init_db, get_db
from main import app


@pytest.fixture
def test_db() -> sqlite3.Connection:
    """
    Returns a fresh in-memory SQLite database with the full NotesFlare schema applied.
    Isolation: each test function gets a brand-new database. No state leaks between tests.
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row

    schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
    assert schema_path.exists(), (
        f"[conftest] schema.sql not found at expected path: {schema_path}\n"
        f"  This means either the file was never created or the project structure "
        f"does not match 01_BRAND_AND_ARCHITECTURE.md spec.\n"
        f"  Expected location: backend/database/schema.sql"
    )

    schema_sql = schema_path.read_text()
    conn.executescript(schema_sql)
    conn.commit()
    
    # Overwrite the global connection in db.py for the duration of the test
    # so services calling get_db() will use this in-memory test database.
    import database.db
    old_connection = database.db._connection
    database.db._connection = conn
    
    yield conn
    
    database.db._connection = old_connection
    conn.close()


@pytest_asyncio.fixture
async def client(test_db: sqlite3.Connection) -> AsyncClient:
    """
    Returns an httpx AsyncClient that calls the FastAPI app directly (no real HTTP).
    The app's `get_db` dependency is overridden to use the isolated test_db.
    """
    def override_get_db():
        return test_db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver"
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def create_burst(test_db):
    """Factory fixture to create a burst for a given flareon_id."""
    from services.burst_service import _create_burst

    def _factory(flareon_id: int) -> dict:
        return _create_burst(flareon_id)

    return _factory


@pytest.fixture
def create_flareon(test_db):
    """Factory fixture to create a flareon."""
    from services.flareon_service import create_flareon as _create_flareon
    return _create_flareon


@pytest.fixture
def test_client(test_db):
    """Synchronous test client for route testing."""
    from fastapi.testclient import TestClient
    from main import app
    from database.db import get_db
    
    def override_get_db():
        return test_db
        
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def burst_with_content(test_db):
    """
    Creates a Flareon + Burst and appends multi-line content.
    Returns dict with flareon_id, burst_id, raw_text.
    """
    from services.flareon_service import create_flareon as _create_flareon
    from services.burst_service import get_or_create_active_burst
    from services.append_service import append_chunk

    flareon = _create_flareon("Formatting Test Flareon")
    burst = get_or_create_active_burst(flareon["id"])
    burst_id = burst["id"]

    text_chunks = [
        "this is the first thought in the burst\n",
        "and this is a continuation of thinking\n",
        "need: embeddings\n",
        "need: chunking\n",
        "need: vector cache\n",
        "some final reflection here",
    ]
    for chunk in text_chunks:
        append_chunk(burst_id, chunk)

    return {
        "flareon_id": flareon["id"],
        "burst_id": burst_id,
        "raw_text": "".join(text_chunks),
    }


