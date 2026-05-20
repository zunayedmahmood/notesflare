# NotesFlare — Database Design & Persistence Layer

> **AI Instruction File 08 of 08**
> This file is the complete reference for NotesFlare's data layer: the full schema with reasoning for every decision, query patterns, the autosave pipeline, the session continuity algorithm, migration strategy, and data integrity rules. Read `02_BACKEND.md` alongside this file — the service files implement the patterns described here.

---

## 1. DATABASE PHILOSOPHY

The database must be:

| Property | Meaning |
|---|---|
| **Local-first** | Data lives on the user's device. No network required, ever. |
| **Embedded** | No server process. SQLite is a library, not a service. |
| **Durable** | Every keystroke (after 1 second) is persisted. No data loss on crash. |
| **Fast** | Writes must complete in < 10ms. Reads in < 50ms. |
| **Inspectable** | Any developer can open the DB with `sqlite3` and read it. |
| **Schema-simple** | 4 tables. No joins beyond 2 levels. |

SQLite satisfies all of these. It is the correct choice for a local-first desktop app.

---

## 2. FULL SCHEMA

### Table: flareons

The top-level entity. Represents a named thinking domain.

```sql
CREATE TABLE IF NOT EXISTS flareons (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    last_opened_at  TEXT    -- NULL until first opened
);
```

**Column explanations:**

| Column | Type | Why |
|---|---|---|
| `id` | INTEGER PK | Stable identifier referenced by bursts |
| `name` | TEXT UNIQUE | User-visible domain name. Unique because duplicates would confuse. |
| `created_at` | TEXT | ISO 8601. Immutable after creation. |
| `updated_at` | TEXT | Updated on any change (currently only name changes — not planned for V1) |
| `last_opened_at` | TEXT | NULL on creation. Set when user opens this Flareon. Used for sidebar ordering. |

**Why UNIQUE on name?** Flareons are identified in the UI by name. Two Flareons with the same name would be indistinguishable. The constraint enforces uniqueness at the database level, not just in application code.

**Why TEXT for dates?** SQLite has no native DATETIME type. TEXT in ISO 8601 format (`2025-01-15T14:30:00`) is conventional and has a useful property: ISO 8601 strings sort correctly as text. `ORDER BY created_at` works correctly without any conversion.

---

### Table: bursts

A continuous writing session within a Flareon.

```sql
CREATE TABLE IF NOT EXISTS bursts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    flareon_id  INTEGER NOT NULL REFERENCES flareons(id) ON DELETE CASCADE,
    started_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    ended_at    TEXT,   -- NULL while active; reserved for future use
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

**Column explanations:**

| Column | Type | Why |
|---|---|---|
| `flareon_id` | INTEGER FK | Which Flareon this burst belongs to |
| `started_at` | TEXT | Displayed as the timestamp label in the UI |
| `ended_at` | TEXT NULL | Reserved for V2. In V1, always NULL. A burst is "active" if it's the latest. |
| `updated_at` | TEXT | **Critical.** This is what the 30-minute continuity check reads. Updated on every save. |

**Why is `updated_at` critical?**

The 30-minute continuity rule is: `now - burst.updated_at < 30 minutes → continue this burst`.

When the user saves content, the backend must update `bursts.updated_at` in addition to `burst_entries.updated_at`. If only `burst_entries` is updated, the continuity check will not see the recent activity and may create a new burst prematurely.

This is a common bug to introduce accidentally. The rule is:
```
Every save MUST update both burst_entries.updated_at AND bursts.updated_at.
```

**ON DELETE CASCADE:** If a Flareon is deleted (not in V1 UI, but possible via direct DB manipulation), all its bursts are automatically deleted too.

---

### Table: burst_entries

The actual text content typed by the user.

```sql
CREATE TABLE IF NOT EXISTS burst_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    burst_id    INTEGER NOT NULL UNIQUE REFERENCES bursts(id) ON DELETE CASCADE,
    content     TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

**Column explanations:**

| Column | Type | Why |
|---|---|---|
| `burst_id` | INTEGER FK UNIQUE | One-to-one relationship with bursts (in V1) |
| `content` | TEXT | The full text the user has typed |
| `updated_at` | TEXT | When content was last saved |

**Why separate from bursts?**

In V1, it is a strict one-to-one relationship: one burst has exactly one entry. This seems like it could just be a column on `bursts`. However, the separation is intentional:

1. **Future: multiple entries per burst.** In V2, a burst might have individual timestamped "flashes" of thought within it — each keystroke session could be a separate entry. Keeping entries separate makes this possible without schema migration.
2. **Separation of concerns.** `bursts` describes *when* writing happened. `burst_entries` describes *what* was written. These are conceptually different.
3. **Large content isolation.** TEXT columns with large values can cause SQLite to store them in overflow pages. Keeping large content in its own table means the `bursts` table stays compact for fast time-based queries.

**UNIQUE on burst_id:** Enforces the V1 one-to-one relationship at the database level. The save logic in `storage_service.py` uses `INSERT OR REPLACE` semantics (check + upsert) rather than relying on SQLite's ON CONFLICT.

---

### Table: app_state

A singleton table that tracks the user's last position.

```sql
CREATE TABLE IF NOT EXISTS app_state (
    id                      INTEGER PRIMARY KEY CHECK (id = 1),
    last_opened_flareon_id  INTEGER REFERENCES flareons(id),
    last_opened_burst_id    INTEGER REFERENCES bursts(id),
    last_active_at          TEXT
);

-- Seed the singleton row on DB initialization
INSERT OR IGNORE INTO app_state (id) VALUES (1);
```

**Why `CHECK (id = 1)`?**

This enforces a singleton pattern at the database level. There can only ever be one row in `app_state`. Attempts to insert a second row fail immediately. This prevents bugs where multiple rows accumulate and the `SELECT` returns ambiguous results.

The singleton is always updated with:
```sql
UPDATE app_state SET ... WHERE id = 1;
```

And always read with:
```sql
SELECT * FROM app_state WHERE id = 1;
```

**What this enables:**

On every app launch, the startup sequence calls `GET /api/state`. The backend reads `app_state` and returns `last_opened_flareon_id`. The frontend uses this to call `GET /api/flareons/{id}` and restore the last session — no search, no guessing, direct lookup.

---

## 3. QUERY PATTERNS

### Pattern 1: List Flareons (sidebar order)

```sql
SELECT id, name, created_at, last_opened_at
FROM flareons
ORDER BY
    CASE WHEN last_opened_at IS NULL THEN 1 ELSE 0 END,  -- Never-opened last
    last_opened_at DESC,                                   -- Most recent first
    created_at ASC                                         -- Tie-break: oldest first
```

**Why this ordering?** The sidebar shows the most recently used Flareons at the top. Newly created but never-opened Flareons go to the bottom. This mirrors how people use notebooks — most active domains surface to the top naturally.

---

### Pattern 2: Get Active Burst (30-minute continuity check)

```sql
SELECT b.id, b.flareon_id, b.started_at, b.updated_at,
       COALESCE(be.content, '') as content
FROM bursts b
LEFT JOIN burst_entries be ON be.burst_id = b.id
WHERE b.flareon_id = ?
ORDER BY b.updated_at DESC
LIMIT 1
```

This returns the most recently updated burst for the Flareon, along with its content.

The Python service then checks:
```python
elapsed = datetime.now(UTC) - parse_iso(row["updated_at"])
if elapsed < timedelta(minutes=30):
    return existing_burst  # Continue
else:
    return create_new_burst()  # New session
```

**Why `LEFT JOIN` instead of `INNER JOIN`?** A burst may have been created but the `burst_entries` row may not yet have been committed (race condition during first creation). `LEFT JOIN` + `COALESCE(be.content, '')` handles this gracefully.

---

### Pattern 3: Get All Bursts for Flareon (render writing area)

```sql
SELECT b.id, b.flareon_id, b.started_at,
       COALESCE(be.content, '') as content
FROM bursts b
LEFT JOIN burst_entries be ON be.burst_id = b.id
WHERE b.flareon_id = ?
ORDER BY b.started_at ASC
```

Returns all bursts oldest-first. The frontend renders them in order: past bursts (dimmed, read-only), then the active burst (textarea).

---

### Pattern 4: Save Content (autosave)

```sql
-- Check if entry exists
SELECT id FROM burst_entries WHERE burst_id = ?

-- If exists:
UPDATE burst_entries SET content = ?, updated_at = ? WHERE burst_id = ?
UPDATE bursts SET updated_at = ? WHERE id = ?

-- If not exists:
INSERT INTO burst_entries (burst_id, content, created_at, updated_at) VALUES (?, ?, ?, ?)
UPDATE bursts SET updated_at = ? WHERE id = ?
```

Both branches update `bursts.updated_at`. This is the invariant that must never be violated.

---

### Pattern 5: Update App State (on every Flareon open)

```sql
UPDATE app_state
SET last_opened_flareon_id = ?,
    last_opened_burst_id = ?,
    last_active_at = ?
WHERE id = 1
```

Called immediately after burst resolution, before returning the response to the frontend. This ensures that if the app crashes before the user does anything, the next launch still opens the correct Flareon and the correct burst.

---

## 4. DATABASE INITIALIZATION

The `init_db()` function runs on every backend startup. It is idempotent — safe to call any number of times because all table definitions use `CREATE TABLE IF NOT EXISTS`.

```python
def init_db() -> None:
    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text()
    db = get_db()
    db.executescript(schema_sql)
    db.commit()
```

**Order matters in `schema.sql`:** Tables must be created in dependency order:
1. `flareons` (no dependencies)
2. `bursts` (depends on `flareons`)
3. `burst_entries` (depends on `bursts`)
4. `app_state` (no dependencies; singleton seed also here)

---

## 5. AUTOSAVE PIPELINE (COMPLETE)

This is the most important data flow in the application. Every character the user types must be durably persisted.

### Timeline

```
T+0.000s   User types a character
           └── React state updates immediately (no save yet)

T+0.001s   useAutosave detects content changed
           └── Clears previous debounce timer
           └── Sets new 1000ms timer

T+0.500s   User types another character
           └── Clears timer, sets new 1000ms timer

T+1.500s   User pauses
           └── 1000ms timer fires

T+1.500s   POST /api/save fires
           └── { burst_id: N, content: "full content" }

T+1.501s   Backend receives request
           └── storage_service.save_content(burst_id, content)
           └── UPDATE burst_entries SET content = ?
           └── UPDATE bursts SET updated_at = ?
           └── db.commit()

T+1.505s   Response: { success: true, burst_entry_id: M }
           └── useAutosave updates lastSavedRef
           └── No UI change
```

**Total latency from typing stop to durability: ~5ms** (SQLite write on SSD).

### What "full content" means

The frontend sends the **complete current content** of the active burst on every save — not a diff, not appended text. This is simpler and safer:

- No need to reconstruct state from incremental patches
- If a save is missed (network blip), the next save catches up
- SQLite handles large TEXT writes efficiently

For V1 content sizes (a few thousand words per burst), this is entirely appropriate.

### Durability guarantee

SQLite's default journal mode (`DELETE`) wraps each write in a transaction. With `WAL` mode (set in `db.py`), writes are even faster because they don't block reads. After `db.commit()` returns, the data is durably written to the WAL file. A system crash after commit does not lose the data.

---

## 6. THE 30-MINUTE CONTINUITY ALGORITHM

This is the core intelligence of NotesFlare. The algorithm must be implemented exactly as specified.

### Specification

```
FUNCTION get_or_create_active_burst(flareon_id):

  1. Query the latest burst for flareon_id, ordered by updated_at DESC

  2. IF no burst exists:
       → CREATE new burst
       → CREATE corresponding empty burst_entry
       → RETURN new burst

  3. IF latest burst updated_at is within 30 minutes of now:
       → RETURN existing burst  (continue the session)

  4. IF latest burst updated_at is more than 30 minutes ago:
       → CREATE new burst
       → CREATE corresponding empty burst_entry
       → RETURN new burst
```

### Edge Cases

**Edge case 1: Burst exists but burst_entry is missing**
The LEFT JOIN + COALESCE handles this. The burst is returned with empty content. This can happen if the first burst_entry INSERT failed in a previous run.

**Edge case 2: Two Flareon opens within 30 minutes**
The first open may create a new burst (if > 30 minutes from the previous burst). The second open, within 30 minutes of the first, returns the same burst. The key is that `updated_at` is read at the moment of the check — so any save within 30 minutes extends the continuity window.

**Edge case 3: System clock skew**
If the system clock jumps backward (e.g., NTP correction), `now - updated_at` may be negative. In Python:
```python
elapsed = now - last_updated
if elapsed.total_seconds() < 0:
    elapsed = timedelta(seconds=0)  # Treat negative elapsed as 0 (continue burst)
```

**Edge case 4: First ever open of a Flareon**
No burst exists. Query returns no rows. `if latest_burst is not None:` is False. New burst is created.

**Edge case 5: Flareon with only empty bursts**
If the user opens a Flareon and immediately switches away without typing, the burst has no content. On the next open (within 30 minutes), the same empty burst is returned — no double-empty-burst accumulation.

---

## 7. DATA INTEGRITY RULES

These rules must be enforced by the application. SQLite constraints enforce what they can; the rest is application responsibility.

| Rule | Enforcer |
|---|---|
| Every burst must have exactly one burst_entry | Application (create entry immediately after burst) |
| `bursts.updated_at` must be updated on every content save | Application (storage_service.py) |
| `app_state` has exactly one row | SQLite `CHECK (id = 1)` |
| Flareon names are unique | SQLite `UNIQUE` on `flareons.name` |
| Foreign keys are enforced | `PRAGMA foreign_keys = ON` on every connection |
| All timestamps are UTC ISO 8601 | Application (use `datetime.now(timezone.utc).isoformat()`) |

---

## 8. SQLITE PRAGMAS

Set these on every new connection (in `db.py`):

```python
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA foreign_keys=ON")
```

| Pragma | Value | Effect |
|---|---|---|
| `journal_mode` | `WAL` | Write-Ahead Logging — faster writes, concurrent reads |
| `foreign_keys` | `ON` | Enforce FK constraints (OFF by default in SQLite) |

Do not set `PRAGMA synchronous = OFF`. The default (`NORMAL` in WAL mode) provides adequate durability. Turning it off risks data loss on system crash.

---

## 9. DATABASE FILE LOCATION

The SQLite database lives at:
```
{project_root}/storage/notesflare.db
```

This path is constructed in `db.py` using:
```python
_DB_PATH = Path(__file__).resolve().parents[2] / "storage" / "notesflare.db"
```

`__file__` is `backend/database/db.py`. `.parents[2]` resolves to the project root.

**Why not `AppData` or a system path?**

In V1, the database lives next to the source code. This makes it:
- Trivially inspectable during development
- Easy to back up (copy the `storage/` directory)
- Easy to wipe and restart (delete `storage/notesflare.db`)

In a production build (future V2), the path would use Electron's `app.getPath('userData')` to store data in the OS-appropriate location. For V1 development, the local path is correct.

---

## 10. BACKUP AND RECOVERY (V1 GUIDANCE)

NotesFlare V1 has no backup system. This is intentional — backup is a V2+ feature. However, the following guidance should be in the README:

**Manual backup:**
```bash
cp storage/notesflare.db storage/notesflare.backup.db
```

**Recovery from backup:**
```bash
cp storage/notesflare.backup.db storage/notesflare.db
```

**Inspect the database directly:**
```bash
sqlite3 storage/notesflare.db
.tables
SELECT name, last_opened_at FROM flareons;
SELECT COUNT(*) FROM burst_entries;
.quit
```

---

## 11. SCHEMA MIGRATION STRATEGY (V1→V2)

NotesFlare V1 does not have a migration system. This is acceptable because:
- V1 is a prototype
- The schema is simple
- User data volume is small (text only)

When V2 introduces schema changes, the recommended approach is:

1. Add a `schema_version` table (single row, integer version number)
2. On startup, check the version
3. If version < current, run migration SQL files in sequence
4. Migration SQL is in `backend/database/migrations/001_add_tags.sql`, etc.

Do NOT implement this in V1. Mention it in code comments as `# TODO V2: migrations` where relevant.

---

## 12. VERIFICATION QUERIES

Use these SQL queries to verify correct behavior during development:

```sql
-- Verify schema exists
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;
-- Expected: app_state, burst_entries, bursts, flareons

-- Verify app_state singleton
SELECT COUNT(*) FROM app_state;
-- Expected: 1

-- Verify burst-to-entry relationship (should be 1:1)
SELECT b.id, COUNT(be.id) as entry_count
FROM bursts b
LEFT JOIN burst_entries be ON be.burst_id = b.id
GROUP BY b.id
HAVING entry_count != 1;
-- Expected: 0 rows (all bursts have exactly 1 entry)

-- Check 30-minute window logic manually
SELECT
  b.id,
  b.flareon_id,
  b.updated_at,
  ROUND((julianday('now') - julianday(b.updated_at)) * 24 * 60, 1) as minutes_ago
FROM bursts b
ORDER BY b.updated_at DESC
LIMIT 5;
-- Use this to understand which bursts are within/outside the 30-minute window

-- Full content dump for a Flareon (verify writes)
SELECT b.started_at, be.content, be.updated_at
FROM bursts b
JOIN burst_entries be ON be.burst_id = b.id
WHERE b.flareon_id = 1
ORDER BY b.started_at ASC;
```
