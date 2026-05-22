# NotesFlare — Frontend ↔ Backend Integration & Data Flow

> **AI Instruction File 05 of 08**
> This file documents how the frontend and backend communicate: the full data flow for every user action, error handling strategy, request/response contracts, timing requirements, and the rules governing when each layer is responsible for what. Read all previous instruction files before this one.

---

## 1. COMMUNICATION PROTOCOL

The frontend and backend communicate exclusively via **HTTP on localhost:8000**.

All requests go through `frontend/lib/api.ts`. No component or hook may call `fetch()` directly. All backend calls are centralized in `api.ts`.

The backend always responds with JSON. The frontend parses JSON and updates React state. There is no WebSocket, no polling loop, no real-time channel. Every data update is request-driven.

---

## 2. THE FIVE USER ACTIONS AND THEIR DATA FLOWS

### Action 1: App Startup (Session Restore)

**Trigger:** App launches. `useSession` hook runs in `page.tsx`.

**Flow:**
```
useSession.initSession()
  │
  ├─→ GET /api/flareons
  │     Response: { flareons: [...] }
  │     Effect: Populate sidebar with Flareon list
  │
  ├─→ GET /api/state
  │     Response: { last_opened_flareon_id: N, last_opened_burst_id: M }
  │     Effect: Know which Flareon was last open
  │
  └─→ GET /api/flareons/{last_opened_flareon_id}   (only if ID is not null)
        Response: { flareon: {...}, bursts: [...], active_burst_id: M }
        Effect: Set activeFlareon in state → WritingArea renders
```

**Timing requirement:** The full sequence must complete in under 1 second under normal conditions (local SQLite, no network). If the backend hasn't started yet, `useSession` will fail. The Electron shell ensures the backend is running before the window opens (see `04_ELECTRON_SHELL.md`).

**Error handling:** If any call fails during startup, log to console and render the app in an empty state. Do NOT show an error screen. The user can still create a new Flareon.

---

### Action 2: User Opens a Flareon

**Trigger:** User clicks a Flareon in the sidebar.

**Flow:**
```
Sidebar: onSelectFlareon(id)
  │
  └─→ useSession.openFlareon(id)
        │
        ├─→ GET /api/flareons/{id}
        │     Backend logic (invisible to frontend):
        │       - touch_flareon(id)
        │       - get_or_create_active_burst(id)  ← 30-min continuity rule
        │       - update_app_state(id, active_burst_id)
        │     Response: { flareon, bursts, active_burst_id }
        │
        └─→ GET /api/flareons   (refresh list for updated last_opened_at ordering)
              Response: { flareons: [...] }
              Effect: Sidebar reorders Flareons
```

**State update after this action:**
- `activeFlareon` is set to the full FlareonDetail
- `content` is set to the active burst's current content
- `WritingArea` remounts (via `key` change) and auto-focuses the textarea
- Cursor is placed at the end of the content

**What the frontend does NOT do:**
- It does NOT decide whether to create a new burst
- It does NOT check the 30-minute window
- It simply accepts `active_burst_id` from the backend and uses it

---

### Action 3: User Types (Autosave)

**Trigger:** Every keystroke in the `textarea` inside `WritingArea`.

**Flow:**
```
WritingArea: onChange → onContentChange(newContent)
  │
  └─→ page.tsx: setContent(newContent)
        │
        └─→ useAutosave(activeBurstId, content) runs via useEffect
              │
              ├─ Clears previous debounce timer
              └─ Sets new timer for 1000ms
                    │
                    (1 second of no typing)
                    │
                    └─→ POST /api/save
                          Body: { burst_id: N, content: "..." }
                          Response: { success: true, burst_entry_id: M }
                          Effect: Nothing visible — save is silent
```

**Timing requirement:** The save must fire at most 1 second after the user stops typing. This is enforced by `SAVE_DELAY_MS = 1000` in `useAutosave.ts`.

**Silent saves:** The user NEVER sees a "Saving..." indicator, a checkmark, or any save confirmation. Autosave is invisible. This is a core product principle.

**On save failure:** Log the error to console. Do not show the user. The next keystroke will reset the timer and attempt another save. Content is preserved in React state even if the save fails.

---

### Action 4: User Creates a Flareon

**Trigger:** User types a name in the sidebar's create input and presses Enter.

**Flow:**
```
Sidebar: handleCreate()
  │
  └─→ useSession.createFlareon(name)
        │
        ├─→ POST /api/flareons
        │     Body: { name: "New Flareon Name" }
        │     Response: { id: N, name: "...", created_at: "..." }
        │
        └─→ openFlareon(newFlareon.id)   (immediately open the new Flareon)
              │
              └─→ (same flow as Action 2)
```

**After creation:**
- The new Flareon appears at the top of the sidebar (it was just opened)
- The writing area is empty (first burst has no content yet)
- The textarea is focused and ready to type

**Error handling:** If the backend returns 400 (name already exists), show the error message below the input field. This is the only error that should be surfaced to the user in the sidebar.

---

### Action 5: App Quit (Implicit Save)

**Trigger:** User closes the window.

**Flow:**
```
User closes window
  │
  ├─→ Electron: app "quit" event fires
  │     Kills Python backend process
  │
  └─→ Frontend: Nothing special
        (Last autosave fired ≤1 second ago if user was typing)
```

**There is no explicit "quit save" call.** The debounced autosave ensures content is saved within 1 second of the last keystroke. If the user quits in the middle of typing, up to 1 second of content may be lost. This is acceptable for V1. It is explicitly documented behavior, not a bug.

---

## 3. REQUEST/RESPONSE CONTRACT (FULL SPECIFICATION)

### GET /api/health

**Request:** No parameters.

**Response:**
```json
{ "status": "ok" }
```

**Caller:** Electron main process during startup polling.

---

### GET /api/state

**Request:** No parameters.

**Response:**
```json
{
  "last_opened_flareon_id": 3,
  "last_opened_burst_id": 17
}
```

Or when no session exists:
```json
{
  "last_opened_flareon_id": null,
  "last_opened_burst_id": null
}
```

**Caller:** `useSession` on startup.

---

### GET /api/flareons

**Request:** No parameters.

**Response:**
```json
{
  "flareons": [
    {
      "id": 1,
      "name": "Thermodynamics",
      "created_at": "2025-01-10T08:00:00",
      "last_opened_at": "2025-01-15T14:30:00"
    },
    {
      "id": 2,
      "name": "Cooking Notes",
      "created_at": "2025-01-08T10:00:00",
      "last_opened_at": "2025-01-12T19:00:00"
    }
  ]
}
```

Ordered by: most recently opened first, then creation date ascending.

**Caller:** `useSession` on startup and after any Flareon open or create.

---

### POST /api/flareons

**Request body:**
```json
{ "name": "Islamic Research" }
```

**Success response (201):**
```json
{
  "id": 3,
  "name": "Islamic Research",
  "created_at": "2025-01-15T10:00:00",
  "last_opened_at": null
}
```

**Error response (400):**
```json
{ "detail": "A Flareon named 'Islamic Research' already exists." }
```

**Caller:** `useSession.createFlareon`.

---

### GET /api/flareons/{id}

**Request:** Path parameter `id` (integer).

**Success response (200):**
```json
{
  "flareon": {
    "id": 1,
    "name": "Thermodynamics",
    "created_at": "2025-01-10T08:00:00",
    "last_opened_at": "2025-01-15T14:32:00"
  },
  "bursts": [
    {
      "id": 5,
      "flareon_id": 1,
      "started_at": "2025-01-10T08:00:00",
      "content": "Today I was thinking about entropy..."
    },
    {
      "id": 12,
      "flareon_id": 1,
      "started_at": "2025-01-12T20:00:00",
      "content": "Revisiting the Carnot cycle..."
    },
    {
      "id": 17,
      "flareon_id": 1,
      "started_at": "2025-01-15T14:30:00",
      "content": ""
    }
  ],
  "active_burst_id": 17
}
```

`bursts` is always ordered chronologically (oldest first). The active burst (identified by `active_burst_id`) is always the last item in the array. Past bursts are all items except the last.

**Error response (404):**
```json
{ "detail": "Flareon not found." }
```

**Caller:** `useSession` on startup (for last-opened Flareon) and on every Flareon click.

---

### POST /api/save

**Request body:**
```json
{
  "burst_id": 17,
  "content": "Today I was thinking about the Boltzmann constant and how..."
}
```

**Success response (200):**
```json
{
  "success": true,
  "burst_entry_id": 42
}
```

**No error cases in V1.** If the burst_id doesn't exist, log the error server-side and return a 500 — but do not design UI to handle this case. It should never happen in normal usage.

**Caller:** `useAutosave` hook, 1 second after last keystroke.

---

## 4. STATE MANAGEMENT RULES

### Where State Lives

| State | Location | Why |
|---|---|---|
| Flareon list | `useSession` hook | Session-level; needs to persist across Flareon switches |
| Active Flareon detail | `useSession` hook | Session-level; shared between sidebar and writing area |
| Current typing content | `page.tsx` useState | Needs to be accessible by both WritingArea and useAutosave |
| Last saved content | `useAutosave` ref | Internal to the hook; not exposed to UI |

### What React State Is NOT Used For

- Deciding what burst to write into (backend decides)
- Tracking whether content is saved (invisible; never shown)
- Storing historical burst content (read from backend on Flareon open)

---

## 5. ERROR HANDLING PHILOSOPHY

The app has two classes of errors:

### Class A: User-Visible Errors
These are rare, directly caused by user input, and must be surfaced.

| Error | Where Shown | Example |
|---|---|---|
| Duplicate Flareon name | Below the create input in sidebar | "A Flareon named X already exists." |

**That's it.** Only one user-visible error type in V1.

### Class B: Background Errors
These are network failures, server errors, or timeouts during autosave or non-critical loads. They are:
- Logged to `console.error`
- Silently ignored by the UI
- Never surfaced to the user

**Rationale:** Interrupting a user's thought to tell them a save failed is worse than the failed save itself. The user was writing — that is the only thing that matters. Interruption is the enemy.

---

## 6. TIMING REQUIREMENTS SUMMARY

| Action | Requirement |
|---|---|
| Backend health check (startup) | < 10 seconds total, polled every 200ms |
| Session restore (startup) | 3 API calls, must complete in < 1 second |
| Flareon open | 2 API calls, should feel < 200ms |
| Autosave trigger delay | Exactly 1000ms after last keystroke |
| Autosave HTTP call | Should complete in < 100ms on localhost |
| Window visible after launch | < 2 seconds from OS launch |

---

## 7. INTEGRATION TESTING SCRIPT

Run these manual tests in order after bringing up both the backend and frontend:

```
TEST 1: Fresh start
  - Start backend
  - Open app
  - Verify: sidebar is empty, writing area shows "Select a Flareon to begin."

TEST 2: Create a Flareon
  - Click "+ New Flareon"
  - Type "Test Flareon" → press Enter
  - Verify: Flareon appears in sidebar (highlighted), writing area shows "Test Flareon" label

TEST 3: Write and autosave
  - Type "Hello world" in the writing area
  - Wait 2 seconds
  - Check backend DB: burst_entries table should have "Hello world" as content
  - Verify: No save indicator ever appeared in the UI

TEST 4: Session restore
  - Quit the app
  - Reopen the app
  - Verify: "Test Flareon" is active, "Hello world" is pre-filled in the textarea

TEST 5: 30-minute continuity (simulate)
  - With Test Flareon open, manually UPDATE bursts SET updated_at = datetime('now', '-31 minutes') in SQLite
  - Click another Flareon, then click Test Flareon again
  - Verify: A new burst section appears below the "Hello world" burst
  - Verify: The new burst has today's timestamp

TEST 6: Multiple Flareons
  - Create "Science" and "Cooking" Flareons
  - Write in each
  - Verify: Switching between them shows correct content for each

TEST 7: Duplicate name error
  - Try to create a Flareon named "Test Flareon" again
  - Verify: Error message appears, no crash, input remains active

TEST 8: Long content
  - Type 500+ words in a Flareon
  - Verify: Textarea grows to fit content (no scrollbar visible inside textarea)
  - Verify: Page scroll works correctly
```

---

## 8. DEBUGGING TIPS

### Backend not responding
```bash
curl http://127.0.0.1:8000/api/health
# Should return: {"status":"ok"}
```

### Check what's in the database
```bash
sqlite3 storage/notesflare.db
.tables
SELECT * FROM flareons;
SELECT * FROM bursts;
SELECT * FROM burst_entries;
SELECT * FROM app_state;
.quit
```

### Verify autosave is firing
Add a temporary `console.log` in `storage_service.py`'s `save_content` function:
```python
print(f"[Save] burst_id={burst_id}, len={len(content)}")
```

Remove the log after verifying.

### Check the 30-minute logic manually
```bash
sqlite3 storage/notesflare.db "UPDATE bursts SET updated_at = datetime('now', '-31 minutes') WHERE id = 1;"
```
Then open the Flareon — a new burst should be created.
