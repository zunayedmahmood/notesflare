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

from database.db import init_db, get_db
from main import app


@pytest.fixture
def test_db() -> sqlite3.Connection:
    """
    Returns a fresh in-memory SQLite database with the full NotesFlare schema applied.
    Isolation: each test function gets a brand-new database. No state leaks between tests.
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
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
