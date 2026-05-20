# NotesFlare — Backend Build Instructions (Python + FastAPI + SQLite)

> **AI Instruction File 02 of 08**
> This file covers the complete Python backend: project setup, FastAPI configuration, all service modules, database initialization, and every API endpoint. Read `01_BRAND_AND_ARCHITECTURE.md` before this file. The backend is the intelligence layer of NotesFlare — it owns all data, all session logic, and all persistence decisions.

---

## 1. ROLE OF THE BACKEND

The Python backend is NOT a simple CRUD server. It owns **session intelligence**:

- It decides whether a new Burst should be created or an existing one continued
- It manages the `app_state` table to enable instant resume
- It handles all database reads and writes
- It is the single source of truth for all Flareon and Burst data

The frontend is a rendering layer. The frontend never touches the database directly. All data flows through this backend.

---

## 2. TECHNOLOGY STACK

| Technology | Version | Reason |
|---|---|---|
| Python | 3.11+ | Modern async support, type hints |
| FastAPI | 0.110+ | Lightweight, async, auto-docs, future AI-ready |
| SQLite | Built-in | Zero-setup, local-first, embedded |
| Pydantic | 2.x | Request/response validation (FastAPI dependency) |
| Uvicorn | Latest | ASGI server for FastAPI |

**No ORM.** Use raw SQL with Python's built-in `sqlite3` module. ORMs add unnecessary abstraction for this scale and make future schema inspection harder.

---

## 3. DIRECTORY STRUCTURE (BACKEND ONLY)

```
backend/
├── api/
│   └── routes.py            # All FastAPI route handlers
├── services/
│   ├── flareon_service.py   # Flareon create/list/open operations
│   ├── burst_service.py     # Burst creation + 30-min continuity logic
│   └── storage_service.py   # Content save and retrieval
├── database/
│   ├── db.py                # Connection management + initialization
│   └── schema.sql           # SQL table definitions
├── models/
│   └── schemas.py           # Pydantic models for request/response
└── main.py                  # FastAPI app setup, middleware, startup
```

---

## 4. DATABASE LAYER

### 4.1 schema.sql

This file defines ALL tables. It must be idempotent — safe to run multiple times using `CREATE TABLE IF NOT EXISTS`.

```sql
-- schema.sql

CREATE TABLE IF NOT EXISTS flareons (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    last_opened_at TEXT
);

CREATE TABLE IF NOT EXISTS bursts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    flareon_id  INTEGER NOT NULL REFERENCES flareons(id) ON DELETE CASCADE,
    started_at  TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at    TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS burst_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    burst_id    INTEGER NOT NULL REFERENCES bursts(id) ON DELETE CASCADE,
    content     TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS app_state (
    id                      INTEGER PRIMARY KEY CHECK (id = 1),
    last_opened_flareon_id  INTEGER REFERENCES flareons(id),
    last_opened_burst_id    INTEGER REFERENCES bursts(id),
    last_active_at          TEXT
);

-- Seed one app_state row that always exists
INSERT OR IGNORE INTO app_state (id) VALUES (1);
```

**Why `app_state` has `CHECK (id = 1)`:** This enforces a singleton row. There is only ever one row in `app_state`. Updates use `UPDATE app_state SET ... WHERE id = 1`. This prevents bugs from accidental multiple rows.

**Why dates are TEXT:** SQLite has no native datetime type. Storing ISO 8601 strings (`2025-01-15T14:30:00`) is the conventional approach. Use `datetime('now')` for insertion defaults. Compare with standard string comparison — ISO 8601 strings sort correctly lexicographically.

### 4.2 db.py

The database module manages a single connection per process. It initializes the schema on startup and provides a helper to get a connection.

```python
# database/db.py

import sqlite3
import os
from pathlib import Path

# DB is stored in the /storage directory at project root
_DB_PATH = Path(__file__).resolve().parents[2] / "storage" / "notesflare.db"
_connection: sqlite3.Connection | None = None


def get_db() -> sqlite3.Connection:
    """Return the singleton SQLite connection. Creates it on first call."""
    global _connection
    if _connection is None:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _connection.row_factory = sqlite3.Row  # Rows accessible as dicts
        _connection.execute("PRAGMA journal_mode=WAL")   # Better concurrency
        _connection.execute("PRAGMA foreign_keys=ON")    # Enforce FK constraints
    return _connection


def init_db() -> None:
    """Run schema.sql to initialize all tables. Safe to call multiple times."""
    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text()
    db = get_db()
    db.executescript(schema_sql)
    db.commit()
```

**Important implementation notes:**
- `check_same_thread=False` is necessary because FastAPI runs handlers in threads; SQLite default rejects cross-thread access
- `row_factory = sqlite3.Row` makes query results accessible as `row["column_name"]` instead of positional `row[0]`
- `PRAGMA journal_mode=WAL` enables Write-Ahead Logging — better for concurrent reads during writes
- `PRAGMA foreign_keys=ON` must be set per-connection in SQLite; it is off by default

---

## 5. PYDANTIC MODELS

### models/schemas.py

Define all request and response shapes here. The API routes use these directly.

```python
# models/schemas.py

from pydantic import BaseModel
from typing import Optional


# --- Flareon Models ---

class FlareonCreate(BaseModel):
    name: str

class FlareonResponse(BaseModel):
    id: int
    name: str
    created_at: str
    last_opened_at: Optional[str] = None

class FlareonListResponse(BaseModel):
    flareons: list[FlareonResponse]


# --- Burst Models ---

class BurstResponse(BaseModel):
    id: int
    flareon_id: int
    started_at: str
    content: str  # Aggregated content from burst_entries

class FlareonDetailResponse(BaseModel):
    flareon: FlareonResponse
    bursts: list[BurstResponse]
    active_burst_id: int  # The burst the user should be typing into


# --- Save Models ---

class SaveContentRequest(BaseModel):
    burst_id: int
    content: str

class SaveContentResponse(BaseModel):
    success: bool
    burst_entry_id: int


# --- App State Models ---

class AppStateResponse(BaseModel):
    last_opened_flareon_id: Optional[int] = None
    last_opened_burst_id: Optional[int] = None

class AppStateUpdate(BaseModel):
    flareon_id: int
    burst_id: int
```

---

## 6. SERVICE LAYER

### 6.1 flareon_service.py

Handles all Flareon operations. No business logic about bursts here — that belongs in `burst_service.py`.

```python
# services/flareon_service.py

from database.db import get_db
from datetime import datetime, timezone


def create_flareon(name: str) -> dict:
    """
    Create a new Flareon with the given name.
    Returns the created Flareon as a dict.
    Raises ValueError if name already exists.
    """
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO flareons (name) VALUES (?)",
            (name.strip(),)
        )
        db.commit()
        flareon_id = cursor.lastrowid
        return get_flareon_by_id(flareon_id)
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise ValueError(f"A Flareon named '{name}' already exists.")
        raise


def list_flareons() -> list[dict]:
    """Return all Flareons ordered by most recently opened, then by creation."""
    db = get_db()
    rows = db.execute(
        """
        SELECT id, name, created_at, last_opened_at
        FROM flareons
        ORDER BY
            CASE WHEN last_opened_at IS NULL THEN 1 ELSE 0 END,
            last_opened_at DESC,
            created_at ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def get_flareon_by_id(flareon_id: int) -> dict | None:
    """Return a single Flareon by ID, or None if not found."""
    db = get_db()
    row = db.execute(
        "SELECT id, name, created_at, last_opened_at FROM flareons WHERE id = ?",
        (flareon_id,)
    ).fetchone()
    return dict(row) if row else None


def touch_flareon(flareon_id: int) -> None:
    """
    Update last_opened_at to now.
    Call this every time a Flareon is opened.
    """
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "UPDATE flareons SET last_opened_at = ?, updated_at = ? WHERE id = ?",
        (now, now, flareon_id)
    )
    db.commit()
```

### 6.2 burst_service.py

This is the most important service. It implements the **30-minute continuity rule** — the heart of the product.

```python
# services/burst_service.py

from database.db import get_db
from datetime import datetime, timezone, timedelta

CONTINUITY_WINDOW_MINUTES = 30


def get_or_create_active_burst(flareon_id: int) -> dict:
    """
    Core session logic. Implements the 30-minute continuity rule:
    - If the latest burst for this Flareon was updated within 30 minutes: return it
    - Otherwise: create a new burst and return it

    Returns a dict with keys: id, flareon_id, started_at, content
    """
    db = get_db()

    # Find the most recently updated burst for this Flareon
    latest_burst = db.execute(
        """
        SELECT b.id, b.flareon_id, b.started_at, b.updated_at,
               COALESCE(be.content, '') as content
        FROM bursts b
        LEFT JOIN burst_entries be ON be.burst_id = b.id
        WHERE b.flareon_id = ?
        ORDER BY b.updated_at DESC
        LIMIT 1
        """,
        (flareon_id,)
    ).fetchone()

    if latest_burst is not None:
        last_updated = _parse_iso(latest_burst["updated_at"])
        now = datetime.now(timezone.utc)
        elapsed = now - last_updated

        if elapsed < timedelta(minutes=CONTINUITY_WINDOW_MINUTES):
            # Continue existing burst
            return dict(latest_burst)

    # Create new burst
    return _create_burst(flareon_id)


def _create_burst(flareon_id: int) -> dict:
    """
    Insert a new burst row and a corresponding empty burst_entry row.
    Returns the new burst as a dict.
    """
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    burst_cursor = db.execute(
        "INSERT INTO bursts (flareon_id, started_at) VALUES (?, ?)",
        (flareon_id, now)
    )
    burst_id = burst_cursor.lastrowid

    db.execute(
        "INSERT INTO burst_entries (burst_id, content) VALUES (?, '')",
        (burst_id,)
    )
    db.commit()

    return {
        "id": burst_id,
        "flareon_id": flareon_id,
        "started_at": now,
        "updated_at": now,
        "content": ""
    }


def get_all_bursts_for_flareon(flareon_id: int) -> list[dict]:
    """
    Return all bursts for a Flareon in chronological order (oldest first).
    Each burst includes its content from burst_entries.
    """
    db = get_db()
    rows = db.execute(
        """
        SELECT b.id, b.flareon_id, b.started_at,
               COALESCE(be.content, '') as content
        FROM bursts b
        LEFT JOIN burst_entries be ON be.burst_id = b.id
        WHERE b.flareon_id = ?
        ORDER BY b.started_at ASC
        """,
        (flareon_id,)
    ).fetchall()
    return [dict(row) for row in rows]


def _parse_iso(dt_string: str) -> datetime:
    """Parse ISO 8601 string from SQLite into an aware datetime."""
    dt = datetime.fromisoformat(dt_string)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
```

**Critical implementation notes for `get_or_create_active_burst`:**
- Always check `latest_burst` against the real current time — never hardcode or mock the time
- The `CONTINUITY_WINDOW_MINUTES = 30` constant must be at the top so it is easily configurable without searching the file
- The LEFT JOIN on `burst_entries` handles the case where a burst has no entry yet (returns empty string via COALESCE)
- Return the full burst dict including content so the frontend can immediately render it without a second request

### 6.3 storage_service.py

Handles saving typed content to `burst_entries`. This is the autosave target.

```python
# services/storage_service.py

from database.db import get_db
from datetime import datetime, timezone


def save_content(burst_id: int, content: str) -> int:
    """
    Save or update content for a burst.
    - If a burst_entry exists for this burst_id: UPDATE it
    - If not: INSERT a new one

    Returns the burst_entry id.
    This is called by the debounced autosave from the frontend.
    """
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    existing = db.execute(
        "SELECT id FROM burst_entries WHERE burst_id = ?",
        (burst_id,)
    ).fetchone()

    if existing:
        db.execute(
            "UPDATE burst_entries SET content = ?, updated_at = ? WHERE burst_id = ?",
            (content, now, burst_id)
        )
        # Also update the parent burst's updated_at — this is what the continuity
        # check reads. If we don't update bursts.updated_at, the 30-min window
        # won't reset on save.
        db.execute(
            "UPDATE bursts SET updated_at = ? WHERE id = ?",
            (now, burst_id)
        )
        db.commit()
        return existing["id"]
    else:
        cursor = db.execute(
            "INSERT INTO burst_entries (burst_id, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (burst_id, content, now, now)
        )
        db.execute(
            "UPDATE bursts SET updated_at = ? WHERE id = ?",
            (now, burst_id)
        )
        db.commit()
        return cursor.lastrowid


def get_app_state() -> dict:
    """Return the singleton app_state row."""
    db = get_db()
    row = db.execute(
        "SELECT last_opened_flareon_id, last_opened_burst_id FROM app_state WHERE id = 1"
    ).fetchone()
    return dict(row) if row else {}


def update_app_state(flareon_id: int, burst_id: int) -> None:
    """
    Update the app_state singleton row.
    Call this every time the user opens a Flareon (after burst resolution).
    """
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        """
        UPDATE app_state
        SET last_opened_flareon_id = ?,
            last_opened_burst_id = ?,
            last_active_at = ?
        WHERE id = 1
        """,
        (flareon_id, burst_id, now)
    )
    db.commit()
```

---

## 7. API ROUTES

### api/routes.py

All endpoints are defined here. Keep route handlers thin — they validate input, call a service, and return the response. No business logic in routes.

```python
# api/routes.py

from fastapi import APIRouter, HTTPException
from models.schemas import (
    FlareonCreate, FlareonListResponse, FlareonDetailResponse,
    FlareonResponse, BurstResponse,
    SaveContentRequest, SaveContentResponse,
    AppStateResponse, AppStateUpdate,
)
from services import flareon_service, burst_service, storage_service

router = APIRouter()


# ─── Health ──────────────────────────────────────────────────────────────────

@router.get("/health")
def health_check():
    """Simple liveness check. Frontend polls this on startup."""
    return {"status": "ok"}


# ─── App State ────────────────────────────────────────────────────────────────

@router.get("/state", response_model=AppStateResponse)
def get_app_state():
    """
    Return the last-opened Flareon and Burst IDs.
    Frontend calls this on startup to know where to resume.
    Returns null IDs if the user has never opened a Flareon.
    """
    state = storage_service.get_app_state()
    return AppStateResponse(
        last_opened_flareon_id=state.get("last_opened_flareon_id"),
        last_opened_burst_id=state.get("last_opened_burst_id"),
    )


# ─── Flareons ─────────────────────────────────────────────────────────────────

@router.get("/flareons", response_model=FlareonListResponse)
def list_flareons():
    """Return all Flareons, ordered by most recently opened."""
    flareons = flareon_service.list_flareons()
    return FlareonListResponse(
        flareons=[FlareonResponse(**f) for f in flareons]
    )


@router.post("/flareons", response_model=FlareonResponse, status_code=201)
def create_flareon(body: FlareonCreate):
    """
    Create a new Flareon.
    Returns 400 if a Flareon with the same name already exists.
    """
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Flareon name cannot be empty.")
    try:
        flareon = flareon_service.create_flareon(body.name)
        return FlareonResponse(**flareon)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/flareons/{flareon_id}", response_model=FlareonDetailResponse)
def open_flareon(flareon_id: int):
    """
    Open a Flareon. This is the main data-loading endpoint.

    On call:
    1. Verifies the Flareon exists
    2. Touches last_opened_at
    3. Resolves active burst (30-min continuity rule)
    4. Updates app_state
    5. Returns all bursts + active burst ID

    The frontend renders all bursts and focuses the active one.
    """
    flareon = flareon_service.get_flareon_by_id(flareon_id)
    if not flareon:
        raise HTTPException(status_code=404, detail="Flareon not found.")

    flareon_service.touch_flareon(flareon_id)

    active_burst = burst_service.get_or_create_active_burst(flareon_id)
    all_bursts = burst_service.get_all_bursts_for_flareon(flareon_id)

    storage_service.update_app_state(flareon_id, active_burst["id"])

    return FlareonDetailResponse(
        flareon=FlareonResponse(**flareon),
        bursts=[BurstResponse(**b) for b in all_bursts],
        active_burst_id=active_burst["id"],
    )


# ─── Content Save ─────────────────────────────────────────────────────────────

@router.post("/save", response_model=SaveContentResponse)
def save_content(body: SaveContentRequest):
    """
    Save content for a burst. Called by the frontend's debounced autosave.
    This endpoint must be fast — it is called every time the user pauses typing.
    """
    entry_id = storage_service.save_content(body.burst_id, body.content)
    return SaveContentResponse(success=True, burst_entry_id=entry_id)
```

---

## 8. MAIN APPLICATION ENTRY POINT

### main.py

```python
# main.py

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.db import init_db
from api.routes import router


app = FastAPI(
    title="NotesFlare Backend",
    description="Persistent thought stream API",
    version="1.0.0",
    docs_url="/docs",   # Available at http://localhost:8000/docs during dev
)

# Allow all origins in V1 — frontend runs on localhost with Electron
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    """Initialize the database on server start."""
    init_db()
    print("NotesFlare backend started. Database initialized.")


app.include_router(router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,       # Set True during active development only
        log_level="warning",
    )
```

---

## 9. REQUIREMENTS.TXT

```
fastapi==0.110.0
uvicorn==0.29.0
pydantic==2.6.4
```

No other dependencies. Do not add anything that is not needed for V1.

---

## 10. API CONTRACT SUMMARY

This is the full API surface. The frontend must only call these endpoints. No endpoint may be added in V1 without a corresponding update to this instruction file.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness check |
| GET | `/api/state` | Get last-opened Flareon + Burst for resume |
| GET | `/api/flareons` | List all Flareons |
| POST | `/api/flareons` | Create a new Flareon |
| GET | `/api/flareons/{id}` | Open a Flareon (resolves burst, returns all data) |
| POST | `/api/save` | Autosave content for a burst |

---

## 11. VERIFICATION CHECKLIST

Before moving to the frontend, verify each item:

- [ ] `python main.py` starts without errors
- [ ] `GET /api/health` returns `{"status": "ok"}`
- [ ] `POST /api/flareons` with `{"name": "Test"}` creates a Flareon
- [ ] `GET /api/flareons` returns the created Flareon
- [ ] `GET /api/flareons/1` returns the Flareon with an auto-created Burst
- [ ] Calling `GET /api/flareons/1` within 30 minutes returns the SAME burst ID
- [ ] Calling `GET /api/flareons/1` after manually editing the DB to set `updated_at` > 30 minutes ago creates a NEW burst
- [ ] `POST /api/save` with valid burst_id updates the content
- [ ] `GET /api/state` returns the last-opened Flareon and Burst IDs after opening a Flareon
- [ ] `notesflare.db` is created in the `/storage` directory

---

## 12. COMMON MISTAKES TO AVOID

**Do not:**
- Use an ORM (SQLAlchemy, Tortoise, etc.) — raw sqlite3 only
- Use async database calls — sqlite3 is synchronous; keep it that way
- Store content directly on the `bursts` table — content lives in `burst_entries`
- Forget to update `bursts.updated_at` when saving content — the continuity check reads this field
- Return different date formats from different endpoints — always ISO 8601 strings
- Expose the database file path in any API response

**Do:**
- Keep all business logic in service files, not route handlers
- Use `db.commit()` after every write operation
- Handle `ValueError` from services and convert to HTTP 400 in routes
- Log startup confirmation so the Electron main process can detect backend readiness
