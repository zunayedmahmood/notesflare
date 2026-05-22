# NotesFlare — Testing Guide: Setup, Strategy & Diagnostic Error Output

> **AI Instruction File 09 of 08 (Addendum)**
> This file covers the complete testing strategy for NotesFlare V1: what to test, how to set it up, how to run it, and — most critically — how errors must be formatted so any failure gives you an immediately actionable diagnosis. Read all previous instruction files before this one. This file assumes a working implementation exists and is now being verified.

---

## 1. PHILOSOPHY OF TESTING FOR NOTESFLARE

### What Testing Means Here

NotesFlare has one core promise: **thought capture with near-zero friction**. That means the most dangerous bugs are not crashes — they are silent failures. A save that doesn't persist. A burst that continues when it shouldn't. A session that restores to the wrong Flareon. These bugs don't throw exceptions. They corrupt the user's thinking space quietly.

Testing strategy reflects this:

- **Backend unit tests** verify data correctness and the 30-minute continuity rule
- **API integration tests** verify the full HTTP contract between layers
- **Frontend hook tests** verify autosave timing and session restore logic
- **End-to-end tests** verify the full user flows across all three layers
- **Database integrity tests** verify persistent state after restarts

### The Error Output Principle

Every test failure must answer three questions immediately, without the developer opening any code:

1. **What exact input triggered the failure?**
2. **What did the system actually return?**
3. **What was expected, and where in the codebase is the relevant logic?**

Vague error messages like `AssertionError` or `Expected true to be false` are not acceptable. Every assertion in this codebase must carry a message that names the component, the condition, and the exact values.

---

## 2. TEST STACK

### Backend (Python)

| Tool | Version | Role |
|---|---|---|
| `pytest` | 7.x+ | Test runner |
| `pytest-asyncio` | 0.23+ | Async test support (for FastAPI) |
| `httpx` | 0.27+ | Async HTTP client for API tests |
| `freezegun` | 1.4+ | Freeze/manipulate datetime in burst continuity tests |
| `pytest-cov` | 4.x+ | Coverage reporting |

### Frontend (TypeScript/React)

| Tool | Version | Role |
|---|---|---|
| `vitest` | 1.x+ | Fast test runner (Vite-native, replaces Jest for Next.js) |
| `@testing-library/react` | 14.x+ | Component and hook testing |
| `@testing-library/user-event` | 14.x+ | Realistic user interaction simulation |
| `msw` | 2.x+ | Mock Service Worker — intercepts HTTP calls in tests |
| `@vitest/coverage-v8` | 1.x+ | Coverage |

### End-to-End

| Tool | Version | Role |
|---|---|---|
| `playwright` | 1.44+ | Full browser automation against running app |

---

## 3. DIRECTORY STRUCTURE FOR TESTS

Add these directories to the existing project structure. Do not modify existing directories.

```
notesflare/
│
├── backend/
│   └── tests/
│       ├── conftest.py               # Shared fixtures: test DB, test client
│       ├── test_db_init.py           # Database schema and initialization
│       ├── test_flareon_service.py   # flareon_service unit tests
│       ├── test_burst_service.py     # burst_service unit tests (incl. 30-min rule)
│       ├── test_storage_service.py   # storage_service unit tests
│       ├── test_routes.py            # Full API route integration tests
│       └── test_app_state.py         # App state read/write tests
│
├── frontend/
│   └── tests/
│       ├── setup.ts                  # Global test setup (MSW server start)
│       ├── mocks/
│       │   └── handlers.ts           # MSW request handlers (mock backend)
│       ├── hooks/
│       │   ├── useAutosave.test.ts   # Autosave debounce + save call tests
│       │   └── useSession.test.ts    # Session init + Flareon open/create tests
│       ├── components/
│       │   ├── Sidebar.test.tsx      # Sidebar render + interaction tests
│       │   ├── WritingArea.test.tsx  # Writing area render + typing tests
│       │   └── BurstBlock.test.tsx   # Burst display + timestamp format tests
│       └── lib/
│           └── api.test.ts           # API client error handling tests
│
├── e2e/
│   ├── playwright.config.ts          # Playwright configuration
│   ├── fixtures/
│   │   └── app.fixture.ts            # App launch + teardown fixture
│   └── tests/
│       ├── 01_startup.spec.ts        # Cold start + empty state
│       ├── 02_flareon_create.spec.ts # Flareon creation flow
│       ├── 03_autosave.spec.ts       # Typing + persistence verification
│       ├── 04_session_restore.spec.ts# Quit + reopen continuity
│       ├── 05_burst_continuity.spec.ts # 30-minute rule
│       └── 06_error_states.spec.ts   # Duplicate name, long content
│
└── scripts/
    ├── test-backend.sh               # Run all backend tests with coverage
    ├── test-frontend.sh              # Run all frontend tests with coverage
    └── test-e2e.sh                   # Launch app + run e2e suite
```

---

## 4. INSTALLATION: TEST DEPENDENCIES

### 4.1 Backend Test Dependencies

Add to `requirements.txt`:

```
# --- existing dependencies ---
fastapi>=0.110.0
uvicorn>=0.29.0
pydantic>=2.0.0

# --- test dependencies ---
pytest>=7.4.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
freezegun>=1.4.0
pytest-cov>=4.1.0
```

Install:

```bash
pip install -r requirements.txt --break-system-packages
# or inside venv:
pip install -r requirements.txt
```

### 4.2 Frontend Test Dependencies

Add to `package.json` under `devDependencies`:

```json
{
  "devDependencies": {
    "vitest": "^1.6.0",
    "@vitest/coverage-v8": "^1.6.0",
    "@testing-library/react": "^14.3.0",
    "@testing-library/user-event": "^14.5.0",
    "@testing-library/jest-dom": "^6.4.0",
    "msw": "^2.3.0",
    "jsdom": "^24.1.0",
    "happy-dom": "^14.12.0"
  }
}
```

Install:

```bash
npm install
```

### 4.3 E2E Test Dependencies

```bash
npm install --save-dev @playwright/test
npx playwright install chromium
```

---

## 5. CONFIGURATION FILES

### 5.1 pytest.ini (place in project root)

```ini
[pytest]
testpaths = backend/tests
asyncio_mode = auto
addopts =
    --tb=short
    --strict-markers
    -v
    --cov=backend
    --cov-report=term-missing
    --cov-report=html:coverage/backend

markers =
    unit: Unit tests for a single function or service
    integration: Tests that span multiple modules or hit the database
    api: Tests that go through the HTTP layer
    slow: Tests that manipulate time or run multiple scenarios
```

### 5.2 vitest.config.ts (place in project root or frontend/)

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./frontend/tests/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      reportsDirectory: './coverage/frontend',
      include: ['frontend/**/*.{ts,tsx}'],
      exclude: ['frontend/tests/**', 'frontend/app/layout.tsx'],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './frontend'),
    },
  },
});
```

### 5.3 playwright.config.ts

```typescript
// e2e/playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e/tests',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: false,         // NotesFlare tests are stateful — run serially
  retries: 0,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'coverage/e2e', open: 'never' }],
  ],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // Electron-specific: override to point at Electron app when running locally
  // For CI: use Next.js dev server directly
  webServer: {
    command: 'npm run dev:frontend',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
    timeout: 15_000,
  },
});
```

---

## 6. BACKEND TESTS — FULL SPECIFICATION

### 6.1 conftest.py

This is the foundation. Every backend test uses fixtures from here.

```python
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
    yield conn
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
```

---

### 6.2 test_db_init.py

```python
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
```

---

### 6.3 test_flareon_service.py

```python
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
```

---

### 6.4 test_burst_service.py

This is the most critical test file. The 30-minute continuity rule is the heart of the product.

```python
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
    After a save, bursts.updated_at is refreshed. This means typing extends
    the 30-minute window — the burst won't expire as long as the user is active.
    """
    flareon = flareon_service.create_flareon("Writing")
    initial_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    with freeze_time(initial_time):
        burst = burst_service.get_or_create_active_burst(flareon["id"])
        storage_service.save_content(burst["id"], "First thought.")

    # 25 minutes later, save again (user was actively typing)
    mid_time = initial_time + timedelta(minutes=25)
    with freeze_time(mid_time):
        storage_service.save_content(burst["id"], "First thought. Second thought.")

    # Now 20 minutes after the LAST save (25 + 20 = 45 min from start, but only 20 from last save)
    late_time = mid_time + timedelta(minutes=20)
    with freeze_time(late_time):
        burst_again = burst_service.get_or_create_active_burst(flareon["id"])

    assert burst["id"] == burst_again["id"], (
        f"[burst_service + storage_service] Saving content must refresh the continuity window.\n"
        f"  Timeline:\n"
        f"    t=0min   : First open + first save\n"
        f"    t=25min  : Second save (user actively typing)\n"
        f"    t=45min  : Third open (20 min after last save — should continue)\n"
        f"  Expected : Same burst id {burst['id']} returned at t=45min\n"
        f"  Got      : New burst created — updated_at was not refreshed on save.\n"
        f"  Fix      : storage_service.save_content must UPDATE bursts SET updated_at = ? "
        f"after every save. Without this, the continuity window calculates from the burst's "
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
```

---

### 6.5 test_storage_service.py

```python
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

    assert "burst_entry_id" in result, (
        f"[storage_service.save_content] Return value must contain 'burst_entry_id'.\n"
        f"  Returned : {result}\n"
        f"  Expected : dict with 'burst_entry_id' key\n"
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
```

---

### 6.6 test_routes.py

```python
# backend/tests/test_routes.py
"""
Tests: API route integration (api/routes.py)

These tests go through the full HTTP stack: request → route → service → DB → response.
Every endpoint is tested for:
  - Correct status codes
  - Correct response shape
  - Correct error responses
"""

import pytest
from httpx import AsyncClient


@pytest.mark.api
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/health")

    assert response.status_code == 200, (
        f"[GET /api/health] Expected 200 OK.\n"
        f"  Status   : {response.status_code}\n"
        f"  Body     : {response.text}\n"
        f"  Fix      : Ensure @router.get('/health') is registered and FastAPI app starts."
    )
    assert response.json() == {"status": "ok"}, (
        f"[GET /api/health] Unexpected response body.\n"
        f"  Expected : {{\"status\": \"ok\"}}\n"
        f"  Got      : {response.json()}"
    )


@pytest.mark.api
async def test_get_state_fresh(client: AsyncClient):
    response = await client.get("/api/state")
    data = response.json()

    assert response.status_code == 200, (
        f"[GET /api/state] Expected 200 on fresh DB.\n"
        f"  Status : {response.status_code}\n"
        f"  Body   : {response.text}"
    )
    assert data["last_opened_flareon_id"] is None, (
        f"[GET /api/state] Expected null flareon_id on fresh start.\n"
        f"  Got : {data}"
    )


@pytest.mark.api
async def test_create_flareon_success(client: AsyncClient):
    response = await client.post("/api/flareons", json={"name": "Physics"})

    assert response.status_code == 201, (
        f"[POST /api/flareons] Expected 201 Created.\n"
        f"  Status : {response.status_code}\n"
        f"  Body   : {response.text}\n"
        f"  Fix    : Route must return JSONResponse with status_code=201, not 200."
    )
    data = response.json()
    assert data["name"] == "Physics", (
        f"[POST /api/flareons] Name mismatch in response.\n"
        f"  Sent   : 'Physics'\n"
        f"  Got    : {data}"
    )
    assert isinstance(data["id"], int) and data["id"] > 0, (
        f"[POST /api/flareons] Response must include a positive integer 'id'.\n"
        f"  Got id : {data.get('id')}"
    )


@pytest.mark.api
async def test_create_flareon_duplicate_returns_400(client: AsyncClient):
    await client.post("/api/flareons", json={"name": "Cooking"})
    response = await client.post("/api/flareons", json={"name": "Cooking"})

    assert response.status_code == 400, (
        f"[POST /api/flareons] Duplicate name must return 400.\n"
        f"  Status : {response.status_code}\n"
        f"  Body   : {response.text}\n"
        f"  Fix    : Route must catch ValueError from flareon_service and return "
        f"HTTPException(status_code=400, detail=str(e))."
    )
    assert "Cooking" in response.json().get("detail", ""), (
        f"[POST /api/flareons] 400 error detail must include the duplicate name.\n"
        f"  Got : {response.json()}"
    )


@pytest.mark.api
async def test_get_flareon_returns_bursts_array(client: AsyncClient):
    create_resp = await client.post("/api/flareons", json={"name": "Biology"})
    fid = create_resp.json()["id"]

    response = await client.get(f"/api/flareons/{fid}")
    data = response.json()

    assert response.status_code == 200, (
        f"[GET /api/flareons/{{id}}] Expected 200.\n"
        f"  Status : {response.status_code}\n"
        f"  Body   : {response.text}"
    )
    assert "bursts" in data, (
        f"[GET /api/flareons/{{id}}] Response must include 'bursts' array.\n"
        f"  Keys found : {list(data.keys())}"
    )
    assert "active_burst_id" in data, (
        f"[GET /api/flareons/{{id}}] Response must include 'active_burst_id'.\n"
        f"  This field tells the frontend which burst to write into.\n"
        f"  Keys found : {list(data.keys())}"
    )
    assert isinstance(data["bursts"], list), (
        f"[GET /api/flareons/{{id}}] 'bursts' must be a list.\n"
        f"  Type found : {type(data['bursts'])}"
    )


@pytest.mark.api
async def test_get_flareon_not_found_returns_404(client: AsyncClient):
    response = await client.get("/api/flareons/99999")

    assert response.status_code == 404, (
        f"[GET /api/flareons/{{id}}] Non-existent Flareon must return 404.\n"
        f"  Status : {response.status_code}\n"
        f"  Body   : {response.text}\n"
        f"  Fix    : Route must check if flareon_service.get_flareon_by_id returns None "
        f"and raise HTTPException(status_code=404)."
    )


@pytest.mark.api
async def test_save_endpoint_persists_content(client: AsyncClient):
    create_resp = await client.post("/api/flareons", json={"name": "Mechanics"})
    fid = create_resp.json()["id"]
    open_resp = await client.get(f"/api/flareons/{fid}")
    burst_id = open_resp.json()["active_burst_id"]

    save_resp = await client.post("/api/save", json={
        "burst_id": burst_id,
        "content": "Force equals mass times acceleration."
    })

    assert save_resp.status_code == 200, (
        f"[POST /api/save] Expected 200.\n"
        f"  Status : {save_resp.status_code}\n"
        f"  Body   : {save_resp.text}"
    )
    assert save_resp.json().get("success") is True, (
        f"[POST /api/save] Response must include {{\"success\": true}}.\n"
        f"  Got : {save_resp.json()}"
    )

    # Re-open to verify content was persisted
    verify_resp = await client.get(f"/api/flareons/{fid}")
    active_burst = next(
        (b for b in verify_resp.json()["bursts"]
         if b["id"] == burst_id), None
    )

    assert active_burst is not None, (
        f"[POST /api/save → GET /api/flareons/{{id}}] Burst not found in re-fetch.\n"
        f"  burst_id : {burst_id}\n"
        f"  Bursts in response : {[b['id'] for b in verify_resp.json()['bursts']]}"
    )
    assert active_burst["content"] == "Force equals mass times acceleration.", (
        f"[POST /api/save] Content not persisted after save.\n"
        f"  Saved    : 'Force equals mass times acceleration.'\n"
        f"  Retrieved: '{active_burst['content']}'\n"
        f"  Fix      : Verify storage_service.save_content is correctly updating "
        f"the burst_entries row and that the GET endpoint reads the content back via JOIN."
    )


@pytest.mark.api
async def test_list_flareons_returns_ordered_list(client: AsyncClient):
    await client.post("/api/flareons", json={"name": "Alpha"})
    await client.post("/api/flareons", json={"name": "Beta"})

    response = await client.get("/api/flareons")
    data = response.json()

    assert "flareons" in data, (
        f"[GET /api/flareons] Response must have 'flareons' key.\n"
        f"  Got : {list(data.keys())}"
    )
    assert isinstance(data["flareons"], list), (
        f"[GET /api/flareons] 'flareons' must be a list.\n"
        f"  Type : {type(data['flareons'])}"
    )
    assert len(data["flareons"]) >= 2, (
        f"[GET /api/flareons] Expected at least 2 Flareons after creating two.\n"
        f"  Found : {len(data['flareons'])}"
    )
```

---

## 7. FRONTEND TESTS — FULL SPECIFICATION

### 7.1 frontend/tests/setup.ts

```typescript
// frontend/tests/setup.ts
import '@testing-library/jest-dom';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { server } from './mocks/handlers';

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### 7.2 frontend/tests/mocks/handlers.ts

```typescript
// frontend/tests/mocks/handlers.ts
/**
 * MSW mock handlers that simulate the Python backend.
 * Tests import and override these handlers to simulate different backend states.
 */

import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

const BASE = 'http://localhost:8000';

export const defaultHandlers = [
  http.get(`${BASE}/api/health`, () =>
    HttpResponse.json({ status: 'ok' })
  ),

  http.get(`${BASE}/api/state`, () =>
    HttpResponse.json({
      last_opened_flareon_id: null,
      last_opened_burst_id: null,
    })
  ),

  http.get(`${BASE}/api/flareons`, () =>
    HttpResponse.json({ flareons: [] })
  ),

  http.post(`${BASE}/api/flareons`, async ({ request }) => {
    const body = await request.json() as { name: string };
    return HttpResponse.json(
      { id: 1, name: body.name, created_at: '2025-01-15T10:00:00', last_opened_at: null },
      { status: 201 }
    );
  }),

  http.get(`${BASE}/api/flareons/:id`, ({ params }) => {
    const id = Number(params.id);
    return HttpResponse.json({
      flareon: { id, name: 'Test Flareon', created_at: '2025-01-15T10:00:00', last_opened_at: null },
      bursts: [
        { id: 1, flareon_id: id, started_at: '2025-01-15T10:00:00', content: '' }
      ],
      active_burst_id: 1,
    });
  }),

  http.post(`${BASE}/api/save`, () =>
    HttpResponse.json({ success: true, burst_entry_id: 1 })
  ),
];

export const server = setupServer(...defaultHandlers);
```

### 7.3 hooks/useAutosave.test.ts

```typescript
// frontend/tests/hooks/useAutosave.test.ts
/**
 * Tests: useAutosave hook
 *
 * Critical behaviors:
 * - Save must fire AFTER 1000ms of inactivity (not before)
 * - Rapid typing resets the timer (debounce)
 * - No save fires when burstId is null
 * - Save is silent — no state change visible to caller
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAutosave } from '@/hooks/useAutosave';
import * as api from '@/lib/api';

vi.mock('@/lib/api');

const mockSave = vi.spyOn(api, 'saveContent').mockResolvedValue({ success: true, burst_entry_id: 1 });

describe('useAutosave', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockSave.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('does not save if burstId is null', async () => {
    renderHook(() => useAutosave(null, 'some content'));
    await act(async () => { vi.advanceTimersByTime(2000); });

    expect(mockSave).not.toHaveBeenCalled();
  }, {
    onFail: () => `[useAutosave] Save was called with null burstId.
  Expected : api.saveContent NOT called
  Got      : api.saveContent called ${mockSave.mock.calls.length} time(s)
  Fix      : useAutosave must guard: if (!burstId) return; before setting the timer.
  Consequence: POST /api/save would fire with burst_id: null, causing a 500 from the backend.`
  });

  it('does not save immediately on mount', async () => {
    renderHook(() => useAutosave(1, 'initial content'));
    // Do NOT advance timers

    expect(mockSave).not.toHaveBeenCalled();
  });

  it('saves after 1000ms of no content change', async () => {
    renderHook(() => useAutosave(1, 'Hello world'));
    await act(async () => { vi.advanceTimersByTime(1000); });

    expect(mockSave).toHaveBeenCalledTimes(1);
    expect(mockSave).toHaveBeenCalledWith(1, 'Hello world');
  });

  it('does NOT save before 1000ms', async () => {
    renderHook(() => useAutosave(1, 'Typing...'));
    await act(async () => { vi.advanceTimersByTime(999); });

    expect(mockSave).not.toHaveBeenCalled();
  }, {
    onFail: () => `[useAutosave] Save fired before the 1000ms debounce delay.
  Elapsed  : 999ms
  Expected : 0 save calls
  Got      : ${mockSave.mock.calls.length} save call(s)
  Fix      : SAVE_DELAY_MS must be 1000. Check the setTimeout value in useAutosave.ts.`
  });

  it('resets timer when content changes rapidly', async () => {
    const { rerender } = renderHook(
      ({ content }) => useAutosave(1, content),
      { initialProps: { content: 'A' } }
    );

    await act(async () => { vi.advanceTimersByTime(500); });
    rerender({ content: 'AB' });
    await act(async () => { vi.advanceTimersByTime(500); });
    rerender({ content: 'ABC' });
    await act(async () => { vi.advanceTimersByTime(500); });

    // Only 500ms since last change — should not have fired yet
    expect(mockSave).not.toHaveBeenCalled();

    // Now let the full 1000ms pass after last change
    await act(async () => { vi.advanceTimersByTime(500); });

    expect(mockSave).toHaveBeenCalledTimes(1);
    expect(mockSave).toHaveBeenCalledWith(1, 'ABC');
  }, {
    onFail: () => `[useAutosave] Debounce is not resetting on content change.
  Scenario : content changed at t=0, t=500, t=1000 (500ms intervals)
  Expected : Exactly 1 save call, at t=2000ms (1000ms after last change)
  Got      : ${mockSave.mock.calls.length} save call(s)
  Fix      : useEffect must clearTimeout(timer) before setting a new one.
             Pattern: const timer = setTimeout(...); return () => clearTimeout(timer);`
  });
});
```

### 7.4 components/BurstBlock.test.tsx

```typescript
// frontend/tests/components/BurstBlock.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import BurstBlock from '@/components/BurstBlock';

describe('BurstBlock', () => {
  it('renders the burst content', () => {
    render(<BurstBlock startedAt="2025-01-15T14:30:00" content="Entropy always increases." />);
    expect(screen.getByText('Entropy always increases.')).toBeInTheDocument();
  });

  it('renders a human-readable timestamp, not raw ISO string', () => {
    render(<BurstBlock startedAt="2025-01-15T14:30:00" content="Some thought." />);
    const raw = screen.queryByText('2025-01-15T14:30:00');

    expect(raw).toBeNull();
  }, {
    onFail: () => `[BurstBlock] Raw ISO timestamp found in rendered output.
  Input     : startedAt="2025-01-15T14:30:00"
  Expected  : A formatted string like "Jan 15, 2:30 PM" (not ISO)
  Found     : Raw ISO string rendered to DOM
  Fix       : BurstBlock must call formatTimestamp(startedAt) and render the result.
              formatTimestamp should use Intl.DateTimeFormat or a similar formatter.`
  });

  it('renders empty content without crashing', () => {
    render(<BurstBlock startedAt="2025-01-15T14:30:00" content="" />);
    // Should not throw
  });
});
```

---

## 8. END-TO-END TESTS — FULL SPECIFICATION

### 8.1 e2e/fixtures/app.fixture.ts

```typescript
// e2e/fixtures/app.fixture.ts
/**
 * Shared fixture for all E2E tests.
 * Provides a fresh test database before each test by calling a reset endpoint
 * (available only in test mode) and ensures the backend is running.
 */

import { test as base, expect } from '@playwright/test';

export const test = base.extend({
  page: async ({ page }, use) => {
    // Wipe the test database before each E2E test
    await page.request.post('http://localhost:8000/api/test/reset', {
      failOnStatusCode: true,
    }).catch(() => {
      throw new Error(
        '[E2E Fixture] Could not reset test database.\n' +
        '  POST http://localhost:8000/api/test/reset returned non-200.\n' +
        '  This endpoint must exist in the backend when NOTESFLARE_ENV=test.\n' +
        '  Fix: Add a /api/test/reset route in routes.py that drops and re-creates\n' +
        '  all tables. Guard it: if os.getenv("NOTESFLARE_ENV") != "test": raise 403.'
      );
    });

    await use(page);
  },
});

export { expect };
```

### 8.2 e2e/tests/01_startup.spec.ts

```typescript
// e2e/tests/01_startup.spec.ts
import { test, expect } from '../fixtures/app.fixture';

test.describe('App Startup', () => {
  test('fresh start shows empty sidebar and placeholder writing area', async ({ page }) => {
    await page.goto('/');

    const sidebar = page.locator('[data-testid="sidebar"]');
    await expect(sidebar).toBeVisible({
      timeout: 2000,
    });

    const flareonItems = page.locator('[data-testid="flareon-item"]');
    await expect(flareonItems).toHaveCount(0, {
      timeout: 2000,
    });

    const placeholder = page.locator('[data-testid="writing-area-placeholder"]');
    await expect(placeholder).toBeVisible();
    await expect(placeholder).toContainText('Select a Flareon');
  });

  test('writing area is not visible without a selected Flareon', async ({ page }) => {
    await page.goto('/');

    const textarea = page.locator('[data-testid="writing-textarea"]');
    await expect(textarea).not.toBeVisible();
  });

  test('app loads within 2 seconds', async ({ page }) => {
    const start = Date.now();
    await page.goto('/');
    await page.locator('[data-testid="sidebar"]').waitFor({ state: 'visible' });
    const elapsed = Date.now() - start;

    expect(elapsed).toBeLessThan(2000);
  }, {
    annotation: {
      type: 'performance',
      description: `[E2E Startup] App did not render within 2 seconds.
  This violates the core product performance requirement.
  Check: Is the backend responding? Is the Next.js build optimized?
  Run: curl http://localhost:8000/api/health to verify backend is up.`
    }
  });
});
```

### 8.3 e2e/tests/03_autosave.spec.ts

```typescript
// e2e/tests/03_autosave.spec.ts
import { test, expect } from '../fixtures/app.fixture';

test.describe('Autosave', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.locator('[data-testid="new-flareon-input"]').fill('Autosave Test');
    await page.keyboard.press('Enter');
    await page.locator('[data-testid="writing-textarea"]').waitFor({ state: 'visible' });
  });

  test('content is persisted 1 second after typing stops', async ({ page, request }) => {
    const textarea = page.locator('[data-testid="writing-textarea"]');
    await textarea.click();
    await textarea.type('Test content for autosave');

    // Wait 1.5 seconds for debounce + HTTP save to complete
    await page.waitForTimeout(1500);

    // Query the backend directly to verify DB write
    const response = await request.get('http://localhost:8000/api/flareons');
    const data = await response.json();
    const flareon = data.flareons.find((f: { name: string }) => f.name === 'Autosave Test');

    expect(flareon).toBeDefined();

    const detail = await request.get(`http://localhost:8000/api/flareons/${flareon.id}`);
    const detailData = await detail.json();
    const activeBurst = detailData.bursts.find(
      (b: { id: number }) => b.id === detailData.active_burst_id
    );

    expect(activeBurst?.content).toBe('Test content for autosave');
  }, {
    annotation: {
      description: `[E2E Autosave] Content not found in database after typing + 1.5s wait.
  Possible causes:
  1. useAutosave debounce timer is not 1000ms
  2. POST /api/save is failing silently (check Network tab in browser devtools)
  3. storage_service.save_content is not committing (missing db.commit())
  4. The burst_id passed to /api/save is null (Flareon not properly opened)
  Debug: Open browser devtools Network tab and look for POST /api/save requests.`
    }
  });

  test('no save indicator appears in the UI during typing', async ({ page }) => {
    const textarea = page.locator('[data-testid="writing-textarea"]');
    await textarea.type('Silent typing');

    // Check for any save-related text in the entire DOM
    const saveText = page.locator('text=/saving|saved|sync/i');
    await expect(saveText).toHaveCount(0);
  });
});
```

### 8.4 e2e/tests/04_session_restore.spec.ts

```typescript
// e2e/tests/04_session_restore.spec.ts
import { test, expect } from '../fixtures/app.fixture';

test.describe('Session Restore', () => {
  test('reopening app restores last Flareon and content', async ({ page }) => {
    await page.goto('/');

    // Create flareon and write content
    await page.locator('[data-testid="new-flareon-input"]').fill('Restore Me');
    await page.keyboard.press('Enter');
    const textarea = page.locator('[data-testid="writing-textarea"]');
    await textarea.waitFor({ state: 'visible' });
    await textarea.type('This should survive a reload');
    await page.waitForTimeout(1500); // let autosave fire

    // Simulate app restart by navigating away and back
    await page.goto('about:blank');
    await page.goto('/');

    // Verify session restored
    const restoredFlareon = page.locator('[data-testid="flareon-item"].active');
    await expect(restoredFlareon).toContainText('Restore Me');

    const restoredTextarea = page.locator('[data-testid="writing-textarea"]');
    await expect(restoredTextarea).toHaveValue('This should survive a reload');
  }, {
    annotation: {
      description: `[E2E Session Restore] Content or active Flareon not restored on reload.
  Check:
  1. GET /api/state returns the correct last_opened_flareon_id after typing
  2. useSession.initSession() correctly calls GET /api/state then GET /api/flareons/{id}
  3. The textarea value is set from the active burst's content on Flareon open
  4. storage_service.update_app_state is called inside the GET /api/flareons/{id} route handler`
    }
  });
});
```

---

## 9. TEST RUNNER SCRIPTS

### 9.1 scripts/test-backend.sh

```bash
#!/bin/bash
# scripts/test-backend.sh
# Run all backend tests with coverage report.
# Usage: ./scripts/test-backend.sh
# Usage (specific file): ./scripts/test-backend.sh backend/tests/test_burst_service.py
# Usage (specific marker): ./scripts/test-backend.sh -m "unit"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     NotesFlare — Backend Test Suite          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Activate virtual environment if present
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
    echo "✓ Virtual environment activated"
else
    echo "⚠ No .venv found — using system Python"
fi

# Verify pytest is installed
if ! python -m pytest --version > /dev/null 2>&1; then
    echo ""
    echo "✗ ERROR: pytest not found."
    echo "  Run: pip install -r requirements.txt"
    echo "  Or:  pip install pytest pytest-asyncio httpx freezegun pytest-cov"
    exit 1
fi

echo "✓ pytest found: $(python -m pytest --version 2>&1 | head -1)"
echo ""

cd "$PROJECT_ROOT"

# Run pytest with extra verbosity for error diagnosis
python -m pytest "$@" \
    --tb=long \
    --showlocals \
    -v \
    --cov=backend \
    --cov-report=term-missing \
    --cov-report=html:coverage/backend \
    2>&1

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ All backend tests passed."
    echo "  Coverage report: coverage/backend/index.html"
else
    echo "✗ Backend tests FAILED (exit code: $EXIT_CODE)"
    echo ""
    echo "  Diagnostic guide:"
    echo "  ─────────────────────────────────────────────"
    echo "  ImportError on service modules  → Check sys.path in conftest.py"
    echo "  sqlite3 OperationalError        → schema.sql has a syntax error"
    echo "  freezegun has no effect         → datetime.now() not imported correctly"
    echo "  httpx transport error           → FastAPI app failed to start in test mode"
    echo "  AssertionError with no message  → Test was written without a message arg"
    echo ""
    echo "  Full output above. Start with the FIRST failure — later failures are often cascades."
fi

exit $EXIT_CODE
```

### 9.2 scripts/test-frontend.sh

```bash
#!/bin/bash
# scripts/test-frontend.sh
# Run all frontend tests with coverage.
# Usage: ./scripts/test-frontend.sh
# Usage (watch mode): ./scripts/test-frontend.sh --watch
# Usage (single file): ./scripts/test-frontend.sh frontend/tests/hooks/useAutosave.test.ts

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     NotesFlare — Frontend Test Suite         ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

cd "$PROJECT_ROOT"

if [ ! -d "node_modules" ]; then
    echo "✗ ERROR: node_modules not found."
    echo "  Run: npm install"
    exit 1
fi

if ! npx vitest --version > /dev/null 2>&1; then
    echo "✗ ERROR: vitest not found in node_modules."
    echo "  Run: npm install --save-dev vitest"
    exit 1
fi

echo "✓ vitest found: $(npx vitest --version 2>&1 | head -1)"
echo ""

npx vitest run "$@" \
    --reporter=verbose \
    --coverage \
    2>&1

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ All frontend tests passed."
    echo "  Coverage report: coverage/frontend/index.html"
else
    echo "✗ Frontend tests FAILED (exit code: $EXIT_CODE)"
    echo ""
    echo "  Diagnostic guide:"
    echo "  ─────────────────────────────────────────────"
    echo "  Cannot find module '@/...'  → Check vitest.config.ts alias for '@'"
    echo "  fetch is not defined        → Add global fetch polyfill in setup.ts"
    echo "  MSW handler not matched     → Check BASE URL in handlers.ts matches api.ts"
    echo "  act() warning               → Wrap state updates in act() in test"
    echo "  Timer not advancing         → Must call vi.useFakeTimers() in beforeEach"
fi

exit $EXIT_CODE
```

### 9.3 scripts/test-e2e.sh

```bash
#!/bin/bash
# scripts/test-e2e.sh
# Start the app stack (backend + frontend) then run Playwright E2E tests.
# Requires: backend running, frontend built or dev server running.
# Usage: ./scripts/test-e2e.sh
# Usage (headed, for debug): ./scripts/test-e2e.sh --headed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     NotesFlare — E2E Test Suite              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

cd "$PROJECT_ROOT"

# Start Python backend in test mode
echo "→ Starting backend in test mode..."
NOTESFLARE_ENV=test python backend/main.py &
BACKEND_PID=$!

# Wait for backend health
echo "→ Waiting for backend to be ready..."
for i in $(seq 1 20); do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "✓ Backend ready (took ${i} attempts)"
        break
    fi
    if [ $i -eq 20 ]; then
        echo "✗ ERROR: Backend did not start within 20 attempts."
        echo "  Check: python backend/main.py starts without errors"
        echo "  Check: Port 8000 is not occupied by another process"
        echo "  Run: lsof -i :8000"
        kill $BACKEND_PID 2>/dev/null
        exit 1
    fi
    sleep 0.5
done

# Run E2E tests
echo "→ Running Playwright tests..."
npx playwright test "$@" 2>&1
E2E_EXIT=$?

# Cleanup
echo "→ Stopping backend (PID: $BACKEND_PID)"
kill $BACKEND_PID 2>/dev/null

echo ""
if [ $E2E_EXIT -eq 0 ]; then
    echo "✓ All E2E tests passed."
    echo "  HTML report: coverage/e2e/index.html"
else
    echo "✗ E2E tests FAILED (exit code: $E2E_EXIT)"
    echo ""
    echo "  Diagnostic guide:"
    echo "  ─────────────────────────────────────────────"
    echo "  Timeout waiting for element  → Add data-testid attributes to all components"
    echo "  Cannot reset test DB         → Ensure /api/test/reset exists in backend"
    echo "  App loads but sidebar empty  → GET /api/flareons returning error or empty"
    echo "  Autosave test fails          → Check browser network tab in --headed mode"
    echo ""
    echo "  Re-run with screenshots: ./scripts/test-e2e.sh --headed"
    echo "  View last failure screenshots: ls coverage/e2e/test-results/"
fi

exit $E2E_EXIT
```

Make all scripts executable:

```bash
chmod +x scripts/test-backend.sh scripts/test-frontend.sh scripts/test-e2e.sh
```

---

## 10. ADD TO package.json SCRIPTS

```json
{
  "scripts": {
    "test": "npm run test:backend && npm run test:frontend",
    "test:backend": "./scripts/test-backend.sh",
    "test:frontend": "./scripts/test-frontend.sh",
    "test:e2e": "./scripts/test-e2e.sh",
    "test:backend:watch": "cd backend && pytest-watch",
    "test:frontend:watch": "npx vitest --watch",
    "test:coverage": "npm run test:backend && npm run test:frontend && echo 'Coverage in coverage/'"
  }
}
```

---

## 11. DATA-TESTID ATTRIBUTE REQUIREMENTS

All components must have `data-testid` attributes for E2E test selectors. This is a hard requirement — E2E tests depend on these selectors. Never use CSS classes or text content as primary E2E selectors.

| Component | Element | Required data-testid |
|---|---|---|
| `Sidebar.tsx` | Root container | `sidebar` |
| `Sidebar.tsx` | Each Flareon list item | `flareon-item` |
| `Sidebar.tsx` | Currently active item | `flareon-item` + class `active` |
| `Sidebar.tsx` | New Flareon input | `new-flareon-input` |
| `Sidebar.tsx` | New Flareon button | `new-flareon-button` |
| `Sidebar.tsx` | Duplicate name error | `flareon-name-error` |
| `WritingArea.tsx` | Root container | `writing-area` |
| `WritingArea.tsx` | The textarea | `writing-textarea` |
| `WritingArea.tsx` | Empty placeholder | `writing-area-placeholder` |
| `WritingArea.tsx` | Flareon name label | `flareon-label` |
| `BurstBlock.tsx` | Root container | `burst-block` |
| `BurstBlock.tsx` | Timestamp label | `burst-timestamp` |

Example implementation in `Sidebar.tsx`:

```tsx
<aside data-testid="sidebar">
  {flareons.map(f => (
    <div
      key={f.id}
      data-testid="flareon-item"
      className={activeFlareon?.id === f.id ? 'active' : ''}
    >
      {f.name}
    </div>
  ))}
  <input data-testid="new-flareon-input" ... />
</aside>
```

---

## 12. BACKEND TEST ENVIRONMENT SETUP

The backend needs a `/api/test/reset` endpoint that is only active in test mode. Add this to `backend/api/routes.py`:

```python
import os

@router.post("/test/reset", include_in_schema=False)
def reset_test_database():
    """
    Wipe and re-initialize the database. Only available in NOTESFLARE_ENV=test.
    Used by E2E tests to guarantee a clean state before each test run.
    """
    if os.getenv("NOTESFLARE_ENV") != "test":
        raise HTTPException(
            status_code=403,
            detail=(
                "[/api/test/reset] This endpoint is only available in test mode. "
                "Set NOTESFLARE_ENV=test to enable it. "
                "Never call this endpoint in production or development."
            )
        )

    db = get_db()
    schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
    db.executescript("DROP TABLE IF EXISTS burst_entries; DROP TABLE IF EXISTS bursts; "
                     "DROP TABLE IF EXISTS flareons; DROP TABLE IF EXISTS app_state;")
    db.executescript(schema_path.read_text())
    db.commit()

    return {"reset": True}
```

---

## 13. QUICK-REFERENCE COMMAND TABLE

| Command | What it runs | When to use |
|---|---|---|
| `./scripts/test-backend.sh` | All Python tests + coverage | After any backend change |
| `./scripts/test-backend.sh -m unit` | Unit tests only (fast) | During development |
| `./scripts/test-backend.sh -m slow` | Time-manipulation tests | Before committing burst logic changes |
| `./scripts/test-backend.sh backend/tests/test_burst_service.py` | One file | Debugging continuity rule |
| `./scripts/test-backend.sh -k "30_min"` | Tests matching name pattern | Targeting specific behavior |
| `./scripts/test-frontend.sh` | All vitest tests + coverage | After any frontend change |
| `./scripts/test-frontend.sh --watch` | Vitest watch mode | During hook development |
| `./scripts/test-e2e.sh` | Full E2E suite headless | Before a release |
| `./scripts/test-e2e.sh --headed` | E2E with browser visible | Debugging a flaky test |
| `npm test` | Backend + frontend (no E2E) | Pre-commit check |

---

## 14. READING A FAILING TEST OUTPUT

Every test failure in this codebase follows the same structure. Here is how to read it:

```
FAILED backend/tests/test_burst_service.py::test_within_30_minutes_returns_same_burst

AssertionError: [burst_service — 30-minute rule] Same burst must be returned when gap < 30 min.
  First open  : 2025-01-15T14:00:00+00:00 → burst id 1
  Second open : 2025-01-15T14:20:00+00:00 (20 min later) → burst id 2    ← PROBLEM
  Gap         : 20 minutes (under the 30-minute threshold)
  Expected    : Both calls return burst id 1
  Got         : Two different burst ids — a new burst was created incorrectly.
  Fix         : In burst_service.get_or_create_active_burst, the continuity check
                must compare datetime.utcnow() against bursts.updated_at. Ensure the
                comparison uses the correct field (updated_at, NOT started_at).
```

Reading guide:

1. **File + test name** (`test_burst_service.py::test_within_30_minutes_returns_same_burst`) — tells you exactly what behavior broke and which service owns it
2. **First line of message** (`[burst_service — 30-minute rule]`) — names the component and rule being tested
3. **Actual values** (burst id 1 vs burst id 2) — the raw data to compare against the DB
4. **Fix line** — tells you exactly which function to look at and what to change

If you see `AssertionError` with no message text (just `assert x == y`), that test was written incorrectly — add a message argument to the `assert` statement as shown throughout this file.

---

## 15. COVERAGE TARGETS

These are minimum acceptable coverage levels before V1 is considered complete.

| Layer | Target | Critical Paths |
|---|---|---|
| `burst_service.py` | 95% | `get_or_create_active_burst` must be 100% |
| `storage_service.py` | 90% | `save_content`, `update_app_state` must be 100% |
| `flareon_service.py` | 85% | `create_flareon` duplicate check must be 100% |
| `api/routes.py` | 80% | All error response branches covered |
| `hooks/useAutosave.ts` | 90% | Debounce + null guard must be 100% |
| `hooks/useSession.ts` | 75% | `initSession` and `openFlareon` covered |

View coverage report after running tests:

```bash
# Backend
open coverage/backend/index.html

# Frontend
open coverage/frontend/index.html
```