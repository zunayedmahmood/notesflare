# NotesFlare V1.2 — Complete System Context

> **AI Context File: Master Reference for V1.2**
> Read this file to understand the complete state of NotesFlare as of V1.2.
> This file replaces the need to read `01_BRAND_AND_ARCHITECTURE.md`, `02_BACKEND.md`,
> `03_FRONTEND.md`, `V1_1_BACKEND.md`, `V1_1_FRONTEND.md`, `V1_2_BACKEND.md`,
> `V1_2_FRONTEND.md`, and `V1_2_BRIDGE_AND_TESTING.md` for orientation.
> It does NOT replace the implementation files for new changes — it is a context document, not a build guide.

---

## 1. PRODUCT IDENTITY

**Name:** NotesFlare
**Tagline:** *"Thought capture with near-zero cognitive friction."*
**What it is:** A persistent thought stream system. Not a notes app. Not a document editor.

### Core Concepts

| Term | Definition |
|---|---|
| **Flareon** | A thinking domain. A named space where a category of thought lives. Not a folder — a living thought stream. |
| **Burst** | A continuous writing session within a Flareon. Created automatically. Never named. |
| **Session Continuity** | If `current_time - last_burst_timestamp < 30 minutes`, the same Burst continues. Otherwise a new one begins automatically. |
| **Invisible Persistence** | Autosave fires 1 second after the user stops typing. The user never presses Save. |

### What Is Deliberately NOT in V1.2
Markdown rendering, AI/LLM integration, search, auth, cloud sync, WebSockets, rich text, plugins, tags, import/export, dark/light toggle, keyboard shortcut customization.

---

## 2. ARCHITECTURE OVERVIEW

```
Electron Shell (Desktop)
        │
        ▼
Next.js Frontend (React, TypeScript)   ──── HTTP localhost:8000 ────▶  Python Backend (FastAPI)
        │                                                                          │
        │                                                                          ▼
        │                                                                    SQLite Database
        └── Renders UI, manages local state, fires API calls ◀── JSON responses ──┘
```

### Runtime layers
- **Electron**: `electron/main.ts`, `electron/preload.ts`, `electron/window.ts`
- **Frontend**: Next.js, React 18, TypeScript, Tailwind (utility-only). Port 3000.
- **Backend**: FastAPI, uvicorn, SQLite via Python `sqlite3`. Port 8000.
- **Database**: SQLite at `storage/notesflare.db`

### Communication
All frontend↔backend communication is **local HTTP** on `localhost:8000/api/*`. No WebSockets. No Electron IPC to DB.

---

## 3. COMPLETE PROJECT FILE STRUCTURE (V1.2 STATE)

```
notesflare/
├── electron/
│   ├── main.ts
│   ├── preload.ts
│   └── window.ts
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                    # Stream page — main writing surface
│   │   └── flareon/
│   │       └── [id]/
│   │           └── page.tsx            # Archive page — burst history
│   │
│   ├── components/
│   │   ├── sidebar/
│   │   │   └── Sidebar.tsx
│   │   ├── stream/
│   │   │   ├── StreamInput.tsx         # The infinite stream textarea
│   │   │   ├── StreamShell.tsx         # Layout wrapper + FormatButton slot
│   │   │   ├── NavControls.tsx         # Archive navigation button
│   │   │   └── SessionIndicator.tsx    # Subtle burst start time indicator
│   │   ├── archive/
│   │   │   ├── BurstBlock.tsx          # (legacy — see FormattedPreview)
│   │   │   ├── BurstDivider.tsx        # Timestamp separator between bursts
│   │   │   └── BurstTimeline.tsx       # Archive page layout wrapper
│   │   ├── formatting/                 # NEW in V1.2
│   │   │   ├── FormatButton.tsx        # Trigger format from stream
│   │   │   ├── DiffReviewPanel.tsx     # Fixed-position right-side panel
│   │   │   ├── DiffLineItem.tsx        # Single diff with accept/reject
│   │   │   ├── FormattedPreview.tsx    # Archive burst with raw/formatted toggle
│   │   │   └── LineStatusBadge.tsx     # Visual status indicator
│   │   └── common/
│   │       ├── LoadingScreen.tsx
│   │       └── EmptyState.tsx
│   │
│   ├── hooks/
│   │   ├── useAutosave.ts              # Debounced append-only save
│   │   ├── useSession.ts               # Single-call session restore
│   │   ├── useStreamBuffer.ts          # Mutable ref buffer for stream input
│   │   ├── useFormatter.ts             # NEW in V1.2 — format lifecycle
│   │   └── useDiffReview.ts            # NEW in V1.2 — accept/reject actions
│   │
│   ├── lib/
│   │   └── api.ts                      # HTTP client — all backend calls
│   │
│   ├── types/
│   │   └── formatting.ts               # NEW in V1.2 — formatting TypeScript types
│   │
│   └── styles/
│       └── globals.css                 # CSS variables + base styles
│
├── backend/
│   ├── api/
│   │   ├── routes.py                   # All V1 + V1.1 routes
│   │   └── formatting_routes.py        # NEW in V1.2 — /api/format/* routes
│   │
│   ├── services/
│   │   ├── flareon_service.py
│   │   ├── burst_service.py
│   │   ├── storage_service.py
│   │   ├── append_service.py
│   │   ├── stream_service.py
│   │   ├── session_service.py
│   │   └── formatting/                 # NEW in V1.2
│   │       ├── __init__.py
│   │       ├── lexer_service.py
│   │       ├── parser_service.py
│   │       ├── chunker_service.py
│   │       ├── embedding_service.py
│   │       ├── formatter_service.py
│   │       ├── diff_service.py
│   │       └── lineage_service.py
│   │
│   ├── database/
│   │   ├── db.py                       # SQLite connection, init, migrations
│   │   └── schema.sql                  # All table definitions
│   │
│   ├── models/
│   │   ├── schemas.py                  # V1 + V1.1 Pydantic models
│   │   └── formatting_schemas.py       # NEW in V1.2 — formatting models
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── formatting/
│   │   │   ├── __init__.py
│   │   │   ├── test_lexer_service.py
│   │   │   ├── test_parser_service.py
│   │   │   ├── test_chunker_service.py
│   │   │   ├── test_embedding_service.py
│   │   │   ├── test_formatter_service.py
│   │   │   ├── test_diff_service.py
│   │   │   └── test_lineage_service.py
│   │   └── test_formatting_routes.py
│   │
│   └── main.py                         # FastAPI app entry point
│
├── e2e/
│   └── tests/
│       ├── 07_formatting_basic.spec.ts
│       └── 08_formatting_accept_reject.spec.ts
│
├── storage/
│   └── .gitkeep                        # notesflare.db lives here at runtime
│
├── scripts/
│   ├── start-dev.sh
│   └── start-dev.bat
│
├── package.json
├── requirements.txt
├── tsconfig.json
├── next.config.js
├── tailwind.config.js
├── .env.example
├── .gitignore
└── README.md
```

---

## 4. DATABASE SCHEMA (COMPLETE — V1.2 STATE)

### Table: `flareons`
```sql
CREATE TABLE IF NOT EXISTS flareons (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

### Table: `bursts`
```sql
CREATE TABLE IF NOT EXISTS bursts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flareon_id INTEGER NOT NULL REFERENCES flareons(id) ON DELETE CASCADE,
    started_at TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

### Table: `burst_entries` (V1.1 append-only schema)
```sql
CREATE TABLE IF NOT EXISTS burst_entries (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    burst_id         INTEGER NOT NULL REFERENCES bursts(id) ON DELETE CASCADE,
    content_chunk    TEXT    NOT NULL DEFAULT '',
    sequence_number  INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);
```
Content is reconstructed by ordering chunks by `sequence_number ASC` and concatenating. `burst_entries` is **immutable** — rows are never updated or deleted by the formatting pipeline.

### Table: `app_state`
```sql
CREATE TABLE IF NOT EXISTS app_state (
    id              INTEGER PRIMARY KEY,
    last_flareon_id INTEGER,
    last_burst_id   INTEGER,
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

### Table: `burst_lines` (NEW in V1.2)
```sql
CREATE TABLE IF NOT EXISTS burst_lines (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    line_id         TEXT    NOT NULL UNIQUE,
    burst_id        INTEGER NOT NULL REFERENCES bursts(id) ON DELETE CASCADE,
    line_index      INTEGER NOT NULL,
    raw_line        TEXT    NOT NULL DEFAULT '',
    formatted_line  TEXT    NOT NULL DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'untouched'
                    CHECK (status IN ('untouched', 'pending', 'accepted', 'rejected')),
    checksum        TEXT    NOT NULL DEFAULT '',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_burst_lines_burst_id ON burst_lines(burst_id, line_index);
```

### Table: `burst_diffs` (NEW in V1.2)
```sql
CREATE TABLE IF NOT EXISTS burst_diffs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    diff_id         TEXT    NOT NULL UNIQUE,
    burst_id        INTEGER NOT NULL REFERENCES bursts(id) ON DELETE CASCADE,
    line_id         TEXT    NOT NULL REFERENCES burst_lines(line_id) ON DELETE CASCADE,
    operation       TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'accepted', 'rejected')),
    raw_before      TEXT    NOT NULL DEFAULT '',
    formatted_after TEXT    NOT NULL DEFAULT '',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_burst_diffs_burst_id ON burst_diffs(burst_id, status);
```

### Table: `line_history` (NEW in V1.2)
```sql
CREATE TABLE IF NOT EXISTS line_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    history_id  TEXT    NOT NULL UNIQUE,
    line_id     TEXT    NOT NULL,
    operation   TEXT    NOT NULL,   -- 'create', 'split', 'accept', 'reject', 'reset'
    detail      TEXT,               -- JSON blob
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
```
`line_history` is insert-only. It is never updated or deleted. It is the permanent audit trail.

### Migration chain
1. `init_db()` runs `schema.sql` (creates all tables with `IF NOT EXISTS`)
2. `migrate_to_v1_1()` — detects V1 `burst_entries` schema (had `content` column) and migrates to append-only
3. `migrate_to_v1_2()` — guard-only; tables already created by `schema.sql`

---

## 5. COMPLETE API CONTRACT (ALL VERSIONS)

All endpoints are prefixed with `/api`. Backend runs on `localhost:8000`.

### V1 Endpoints (unchanged)
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Health check → `{"status": "ok"}` |
| GET | `/api/state` | App state (last flareon/burst IDs) |
| GET | `/api/flareons` | List all Flareons |
| POST | `/api/flareons` | Create Flareon → `{"name": "..."}` |
| GET | `/api/flareons/{id}` | Get Flareon + burst list |
| POST | `/api/save` | Legacy overwrite save (V1 only — not used in V1.1+) |
| POST | `/api/reset-test-db` | Test-mode DB reset (test only) |

### V1.1 Endpoints (unchanged)
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/session/resume` | Single-call session restore — returns flareon + burst + stream content |
| GET | `/api/session/switch/{flareon_id}` | Switch active Flareon, create/resume burst |
| POST | `/api/burst/append` | Append a text chunk → `{"burst_id": N, "text": "..."}` |

### V1.2 Formatting Endpoints (NEW)
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/format/burst` | Run full formatting pipeline → diffs |
| POST | `/api/format/diff/accept` | Accept one diff → `{"diff_id": "..."}` |
| POST | `/api/format/diff/reject` | Reject one diff → `{"diff_id": "..."}` |
| POST | `/api/format/diff/accept-all` | Accept all pending diffs → `{"burst_id": N}` |
| POST | `/api/format/diff/reject-all` | Reject all pending diffs → `{"burst_id": N}` |
| GET | `/api/format/burst/{id}` | Get formatted burst (raw + formatted text) |

### Key Response Shapes

**`GET /api/session/resume`**
```json
{
  "flareon": { "id": 1, "name": "My Flareon" },
  "burst_id": 3,
  "stream_content": "all appended chunks concatenated",
  "burst_started_at": "2024-01-01T10:00:00Z",
  "is_new_burst": false
}
```

**`POST /api/format/burst`**
```json
{
  "burst_id": 1,
  "lines": [
    { "line_id": "uuid", "line_index": 0, "raw_line": "text", "formatted_line": "text", "status": "pending", "checksum": "sha256" }
  ],
  "diffs": [
    { "diff_id": "uuid", "line_id": "uuid", "operation": "format_as_list_item", "status": "pending", "raw_before": "* item", "formatted_after": "- item" }
  ],
  "diff_count": 1,
  "processed_at": "2024-01-01T10:00:00Z"
}
```

---

## 6. PYTHON DEPENDENCIES (`requirements.txt`)

```
# V1 / V1.1 (unchanged)
fastapi==0.110.0
uvicorn==0.29.0
pydantic==2.6.4
pytest>=7.4.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
freezegun>=1.4.0
pytest-cov>=4.1.0

# V1.2 NLP (new)
spacy>=3.7.0
sentence-transformers>=2.7.0
onnxruntime>=1.18.0
numpy>=1.26.0
```

**Post-install required:**
```bash
python -m spacy download en_core_web_sm
```

**spaCy model used:** `en_core_web_sm`
**Embedding model used:** `sentence-transformers/all-MiniLM-L6-v2` (384-dim, CPU-optimized)

---

## 7. FRONTEND DEPENDENCIES

```json
{
  "dependencies": {
    "next": "14.x",
    "react": "18.x",
    "react-dom": "18.x"
  },
  "devDependencies": {
    "typescript": "5.x",
    "tailwindcss": "3.x",
    "@types/react": "18.x",
    "vitest": "1.x",
    "@testing-library/react": "14.x",
    "@testing-library/user-event": "14.x",
    "msw": "2.x",
    "@playwright/test": "1.x"
  }
}
```

---

## 8. CSS DESIGN TOKENS (COMPLETE)

All defined in `frontend/styles/globals.css` on `:root`:

### Color tokens (V1 — unchanged)
```css
--bg-base:            #0E0E10;   /* Main background */
--bg-surface:         #16161A;   /* Sidebar, panels */
--bg-elevated:        #1C1C22;   /* Cards, burst separators */
--border-subtle:      #2A2A35;   /* Dividers */
--text-primary:       #E8E8F0;   /* Writing area text */
--text-secondary:     #6B6B80;   /* Timestamps, labels */
--text-muted:         #3A3A50;   /* Placeholder text */
--accent-flare:       #7C6AF7;   /* Primary accent, cursor */
--accent-flare-dim:   #3D356B;   /* Hover states */
--accent-burst:       #4A9EFF;   /* Burst timestamp color */
--cursor:             #7C6AF7;   /* Blinking cursor */
```

### Typography tokens (V1 — unchanged)
```css
--font-writing:       'iA Writer Quattro', 'Courier Prime', monospace;
--font-ui:            'Inter', system-ui, sans-serif;
--text-size-writing:  18px;
--text-size-ui:       13px;
--line-height-writing: 1.8;
```

### Spacing tokens (V1 — unchanged)
```css
--sidebar-width:      220px;
--writing-max-width:  680px;
--writing-padding-x:  60px;
--writing-padding-y:  80px;
```

### V1.2 Formatting/Diff tokens (NEW)
```css
--diff-pending:       #4A9EFF;
--diff-pending-bg:    rgba(74, 158, 255, 0.06);
--diff-accepted:      #4ACA8A;
--diff-accepted-bg:   rgba(74, 202, 138, 0.06);
--diff-rejected:      #FF6B6B;
--diff-rejected-bg:   rgba(255, 107, 107, 0.06);
--panel-width:        360px;
--panel-bg:           #121216;
--panel-border:       #22222E;
--panel-header-height: 52px;
--format-btn-color:   #7C6AF7;
--format-btn-bg:      rgba(124, 106, 247, 0.08);
--format-btn-hover:   rgba(124, 106, 247, 0.15);
```

---

## 9. NLP PIPELINE ARCHITECTURE (V1.2)

The formatting pipeline runs **only on-demand** (user clicks "Format"). It never runs automatically.

### Pipeline Stages (in order)

```
POST /api/format/burst  →

  Stage 1: stream_service.reconstruct_burst(burst_id)
           → Concatenates all burst_entries chunks by sequence_number ASC
           → Raw text — this is sacred, never modified

  Stage 2: lexer_service.normalize_text(raw_text)
           → NFC unicode normalization
           → CRLF → LF
           → Strip trailing whitespace per line
           → Collapse 3+ blank lines to 2
           → NEVER changes words

  Stage 3: lineage_service.get_or_create_lines(burst_id, lines)
           → Assigns stable UUIDs to each line (SHA-256 checksum-based)
           → Reuses IDs if line content unchanged
           → New ID if content changed

  Stage 4: parser_service.parse_lines(lines)
           → spaCy en_core_web_sm
           → Per-line signals: is_list_item, is_heading, is_quote, etc.
           → Loaded once via @lru_cache

  Stage 5: chunker_service.chunk_lines(lines)
           → Overlapping sliding window (800 char chunks, 150 char overlap)
           → Output used for embedding coherence only

  Stage 6: embedding_service.embed_lines(lines) [optional — graceful fallback]
           → MiniLM all-MiniLM-L6-v2 via sentence-transformers
           → 384-dim float32 vectors per line
           → compute_similarity_sequence → cosine similarity between consecutive lines
           → Loaded once via @lru_cache

  Stage 7: formatter_service.generate_operations(signals, similarities)
           → Rule-driven, deterministic (no LLM)
           → Returns list of {line_index, operation, raw_before, formatted_after}
           → Operations: insert_paragraph_break, format_as_list_item, format_as_heading,
             format_as_quote, insert_line_break, normalize_spacing

  Stage 8: diff_service.store_diffs(burst_id, line_records, operations)
           → Clears PENDING diffs only (never touches ACCEPTED or REJECTED)
           → Inserts new pending diffs
           → Records in line_history (immutable audit)
```

### Immutability Guarantee
`burst_entries` rows are **NEVER modified** by the formatting pipeline. The raw text is reconstructed from these rows on every format call. Only `burst_lines`, `burst_diffs`, and `line_history` are written by the pipeline.

### Diff Status Flow
```
Line written → status: "untouched"
Format runs  → status: "pending"   (new diffs created)
User accepts → status: "accepted"  (formatted_line updated)
User rejects → status: "rejected"  (formatted_line = raw_line)
Re-format    → pending diffs cleared; accepted/rejected preserved
```

---

## 10. FRONTEND STATE MANAGEMENT (V1.2)

### Stream Page (`app/page.tsx`) — hook wiring

```
useSession         → session restore, flareon/burst state
useStreamBuffer    → mutable ref buffer for stream input text
useAutosave        → debounced append to backend (1s after typing stops)
useFormatter       → format request lifecycle, diff state
useDiffReview      → accept/reject actions with optimistic UI
```

### `useFormatter` state shape
```typescript
{
  burstId: number | null,
  isLoading: boolean,
  isOpen: boolean,           // Whether DiffReviewPanel is visible
  diffs: FormattingDiff[],
  lines: BurstLine[],
  error: string | null,
  processedAt: string | null,
}
```

### `useDiffReview` — optimistic pattern
All accept/reject calls update local state immediately, then fire the API call in the background. If the backend fails, the local state stays (eventual consistency on next reload).

### Critical behavior: Flareon switching
When the user switches Flareons, `formatter.resetFormatting()` must be called. The diff panel for Flareon A must not remain open when viewing Flareon B.

---

## 11. COMPONENT RESPONSIBILITY MAP

| Component | Location | Responsibility |
|---|---|---|
| `Sidebar` | `components/sidebar/` | Flareon list, create new Flareon |
| `StreamInput` | `components/stream/` | Infinite stream textarea, autosave trigger |
| `StreamShell` | `components/stream/` | Layout: stream + bottom controls + DiffReviewPanel slot |
| `NavControls` | `components/stream/` | Archive link, back button |
| `SessionIndicator` | `components/stream/` | Shows burst start time |
| `FormatButton` | `components/formatting/` | Triggers format, shows pending count |
| `DiffReviewPanel` | `components/formatting/` | Fixed right-side panel, list of diffs |
| `DiffLineItem` | `components/formatting/` | Single diff row with accept/reject |
| `LineStatusBadge` | `components/formatting/` | Color badge: pending/accepted/rejected |
| `FormattedPreview` | `components/formatting/` | Archive burst with raw/formatted toggle |
| `BurstTimeline` | `components/archive/` | Archive page layout |
| `BurstBlock` | `components/archive/` | Legacy burst display (superseded by FormattedPreview) |
| `BurstDivider` | `components/archive/` | Timestamp separator between bursts |
| `LoadingScreen` | `components/common/` | Session restore loading state |
| `EmptyState` | `components/common/` | No Flareon selected state |

---

## 12. TESTING INFRASTRUCTURE

### Backend tests
- Framework: `pytest`
- Test DB: In-memory SQLite (reset between tests via `conftest.py`)
- Location: `backend/tests/`
- Run all: `cd backend && pytest tests/ -v --cov=services`
- Run V1.2 only: `pytest tests/formatting/ tests/test_formatting_routes.py -v`

### Frontend tests
- Framework: `vitest` + `@testing-library/react`
- MSW (Mock Service Worker) for API mocking
- Location: `frontend/tests/`
- Run all: `cd frontend && npx vitest run`

### E2E tests
- Framework: Playwright
- Location: `e2e/tests/`
- Requires both backend + frontend running
- Run: `npx playwright test`

### Test file inventory (V1.2 additions)
```
backend/tests/formatting/
  test_lexer_service.py       — normalize_text, split_into_lines
  test_parser_service.py      — parse_lines signal correctness
  test_chunker_service.py     — chunk_lines shape and overlap
  test_embedding_service.py   — embed_lines shape, similarity range
  test_formatter_service.py   — generate_operations rule fidelity
  test_diff_service.py        — store/accept/reject/pending-clear
  test_lineage_service.py     — stable IDs, checksum

backend/tests/
  test_formatting_routes.py   — API route integration tests

frontend/tests/
  hooks/useFormatter.test.ts
  hooks/useDiffReview.test.ts
  components/FormatButton.test.tsx
  components/DiffReviewPanel.test.tsx

e2e/tests/
  07_formatting_basic.spec.ts
  08_formatting_accept_reject.spec.ts
```

---

## 13. KNOWN BUGS AND NOTES (V1.2)

### Typo in `useFormatter.ts`
There is a typo in the `useFormatter` hook: the close panel function is named `closePaenl` (misspelled). This must be matched exactly when calling it from `app/page.tsx`:
```typescript
// In app/page.tsx — use the typo as-is to match the hook's export
onDiffPanelClose={formatter.closePaenl}
```
If fixing the typo, update both the hook and all call sites.

### `BurstBlock` vs `FormattedPreview`
`BurstBlock` is the V1 component for rendering burst content. In V1.2, the archive page (`app/flareon/[id]/page.tsx`) replaces `<BurstBlock>` with `<FormattedPreview>`. `BurstBlock` remains in the codebase but is no longer used in the archive page directly.

### Embedding is optional
If `embedding_service` fails (model not downloaded, memory error), the pipeline continues with rule-only formatting. The `similarity_scores` parameter to `generate_operations` is `None`, and paragraph break detection falls back to the conjunction-based rule only. This is intentional — the pipeline should never hard-fail due to embedding issues.

### ONNX Runtime and GPU
`onnxruntime` is in `requirements.txt` and provides the backend accelerator. On CPU-only systems, it still works via `CPUExecutionProvider`. No GPU configuration is required.

---

## 14. HOW TO START THE APP (DEVELOPMENT)

### Start backend
```bash
cd backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python main.py
# Runs on http://localhost:8000
# Verify: curl http://localhost:8000/api/health → {"status":"ok"}
```

### Start frontend
```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

### Start Electron (optional, wraps the frontend)
```bash
npm run electron-dev
# (from project root, requires frontend + backend already running)
```

### Combined dev script
```bash
# Unix
./scripts/start-dev.sh

# Windows
scripts\start-dev.bat
```

---

## 15. VERSION HISTORY

| Version | Key Changes |
|---|---|
| **V1** | Electron shell + Next.js + FastAPI + SQLite. Single writing area. Flareons. Bursts. 30-min continuity. Overwrite save model. |
| **V1.1** | Append-only save model (`burst_entries` with `sequence_number`). Session resume (`/api/session/resume`). Stream page + Archive page split. `useStreamBuffer`. |
| **V1.2** | NLP formatting pipeline. spaCy + MiniLM. `burst_lines`, `burst_diffs`, `line_history` tables. `FormatButton`, `DiffReviewPanel`, `DiffLineItem`, `FormattedPreview`, `LineStatusBadge` components. `useFormatter`, `useDiffReview` hooks. 6 new `/api/format/*` endpoints. |

---

## 16. FUTURE VERSION NOTES (DO NOT IMPLEMENT IN V1.2)

These are planned for V2+ and must not be added to V1.2:

- Semantic search across Flareons (requires vector index)
- Auto-tagging and graph relationships between thoughts
- Local LLM integration (e.g., Ollama)
- Embeddings stored in DB for reuse across sessions (currently computed per-request)
- Flareon-level formatting preferences
- Export to Markdown/PDF
