# NotesFlare — Brand Identity, Philosophy & Full System Architecture

> **AI Instruction File 01 of 08**
> This file defines the product identity, brand emotion, target audience, visual language, and the complete technical architecture that every subsequent instruction file builds upon. Read this file first. Every decision made in other files must be consistent with this one.

---

## 1. PRODUCT IDENTITY

### Name
**NotesFlare**

### Tagline
> *"Thought capture with near-zero cognitive friction."*

### What It Is
NotesFlare is a **persistent thought stream system** — not a notes app, not a document editor, not a markdown tool.

It is the place where a person's thinking *lives*. The user opens it and their thoughts are already there, already waiting, already in context. The app never asks them to start fresh. The app never asks them to name a file, create a folder, or choose where to save. The system handles all of that invisibly.

### What It Is NOT
- It is NOT a note-taking app (no note management, no tagging, no search in V1)
- It is NOT a document editor (no formatting toolbar, no rich text, no markdown rendering)
- It is NOT a productivity suite (no tasks, no calendars, no dashboards)
- It is NOT a knowledge base (no linking, no wiki, no backlinks in V1)

### The Core Metric
```
Time between thought and writing.
```
This is the only metric that matters in V1. Every engineering and design decision must reduce this number.

---

## 2. BRAND EMOTION

The emotional experience of NotesFlare must feel like:

| Feeling | Description |
|---|---|
| **Instant** | The app is ready before the user is ready |
| **Invisible** | Technology disappears; only thinking remains |
| **Calm** | No alerts, no badges, no noise |
| **Persistent** | Thoughts accumulate; nothing is ever lost |
| **Trusted** | The user never worries about saving |
| **Private** | Local-first, offline-first, always on-device |

The app should feel like a **trusted companion for the thinking mind** — like a physical notebook that remembers everything, never runs out of pages, and is always open to the right page.

---

## 3. TARGET AUDIENCE

### Primary User
- Knowledge workers, researchers, writers, students
- People who think in bursts: shower thoughts, late-night ideas, research spirals
- People who feel friction with existing apps (Notion is too heavy, Apple Notes feels disposable, Obsidian feels like work)

### Secondary User
- Builders, developers, founders who need a thinking space separate from their project tools
- Academics doing long-form thinking across multiple domains (e.g., physics, Islamic studies, cooking)

### User Psychology
The target user:
- Has many **thinking domains** (subjects they think deeply about)
- Thinks in **sessions**: short bursts of focused thought
- Hates losing context when they reopen an app
- Hates being asked "what do you want to call this?"
- Values **continuity** above all else

---

## 4. COLOR PALETTE

### Design Philosophy
The color system must reinforce calm, focus, and darkness. The default (and only V1) theme is **dark**.

### Palette Definition

| Token | Hex | Usage |
|---|---|---|
| `--bg-base` | `#0E0E10` | Main app background |
| `--bg-surface` | `#16161A` | Sidebar, panels |
| `--bg-elevated` | `#1C1C22` | Cards, burst separators |
| `--border-subtle` | `#2A2A35` | Dividers, outlines |
| `--text-primary` | `#E8E8F0` | Main writing area text |
| `--text-secondary` | `#6B6B80` | Timestamps, labels, sidebar text |
| `--text-muted` | `#3A3A50` | Placeholder text |
| `--accent-flare` | `#7C6AF7` | Primary accent (Flareon selection, focus ring) |
| `--accent-flare-dim` | `#3D356B` | Hover states, subtle highlights |
| `--accent-burst` | `#4A9EFF` | Burst timestamp label color |
| `--cursor` | `#7C6AF7` | Blinking cursor in writing area |

### Typography

| Token | Value | Usage |
|---|---|---|
| `--font-writing` | `'iA Writer Quattro', 'Courier Prime', monospace` | Writing area |
| `--font-ui` | `'Inter', system-ui, sans-serif` | All UI elements |
| `--text-size-writing` | `18px` | Writing area font size |
| `--text-size-ui` | `13px` | Sidebar, labels |
| `--line-height-writing` | `1.8` | Generous line height for readability |

### Spacing

| Token | Value |
|---|---|
| `--sidebar-width` | `220px` |
| `--writing-max-width` | `680px` |
| `--writing-padding-x` | `60px` |
| `--writing-padding-y` | `80px` |

---

## 5. CORE CONCEPTS (VOCABULARY)

All code, documentation, and UI copy must use these exact terms. Do not substitute synonyms.

### Flareon
A **thinking domain**. A named space where a category of thought lives.

Examples:
- `Thermodynamics`
- `Startup Ideas`
- `Islamic Research`
- `Cooking Notes`
- `PhD Research`

A Flareon is not a folder. It is not a project. It is a **living stream** of thought in one domain.

### Burst
A **continuous writing session** within a Flareon.

A Burst is created automatically — never manually. When a user opens a Flareon, the system checks the last Burst's timestamp. If the gap is less than 30 minutes, the same Burst continues. If it has been more than 30 minutes, a new Burst begins automatically.

Bursts are **displayed sequentially** in the writing area, separated by a subtle timestamp divider. Together they form the full thought history of a Flareon.

### Session Continuity
The rule: `current_time - last_burst_timestamp < 30 minutes → same burst`.

This is the heart of the product. It makes NotesFlare feel alive.

### Invisible Persistence
The user never presses Save. The system saves automatically, 1 second after the user stops typing (debounced autosave).

---

## 6. FULL SYSTEM ARCHITECTURE

### Layer Overview

```
┌─────────────────────────────────────────┐
│          Electron Shell (Desktop)        │
│  - Window lifecycle                      │
│  - IPC bridge                            │
│  - Native OS integration                 │
│  - Startup orchestration                 │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│         Next.js Frontend (React)         │
│  - UI rendering                          │
│  - Writing interface                     │
│  - Flareon navigation                    │
│  - Local editor state                    │
│  - Session restoration                   │
└────────────────────┬────────────────────┘
                     │ HTTP (localhost:8000)
┌────────────────────▼────────────────────┐
│         Python Backend (FastAPI)         │
│  - Session logic                         │
│  - Burst management                      │
│  - Autosave pipeline                     │
│  - Database operations                   │
│  - App state management                  │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│         SQLite Database                  │
│  - flareons                              │
│  - bursts                                │
│  - burst_entries                         │
│  - app_state                             │
└─────────────────────────────────────────┘
```

### Why This Architecture

**Separation of runtimes:**
- The JS ecosystem (Electron + Next.js) handles everything visual and interactive
- The Python ecosystem handles everything about data, persistence, and future intelligence

This is intentionally future-proof. In V2+, Python will handle:
- Embeddings and vector indexing
- Semantic search across Flareons
- NLP and auto-tagging
- Graph relationships between thoughts
- Local LLM integration

The V1 architecture is identical to the V2+ architecture in structure — only the Python modules change.

### Communication Model

In V1, the frontend communicates with the backend via **local HTTP** on `localhost:8000`.

Why not WebSockets? — Not needed in V1. HTTP is simpler, more debuggable, and sufficient for the save + load use cases.

Why not Electron IPC directly to SQLite? — Python backend is a strategic investment. The cost is one extra HTTP hop. The benefit is a clean separation of data logic from rendering logic, and a future-ready Python data layer.

---

## 7. FULL PROJECT DIRECTORY STRUCTURE

The AI building this project must create exactly this directory structure. Do not add directories that are not listed here. Do not remove directories that are listed here.

```
notesflare/
│
├── electron/
│   ├── main.ts              # Electron entry point, window creation, IPC
│   ├── preload.ts           # Electron preload — exposes safe IPC to renderer
│   └── window.ts            # Window configuration constants
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx       # Root layout
│   │   └── page.tsx         # Main app page
│   ├── components/
│   │   ├── Sidebar.tsx      # Flareon list sidebar
│   │   ├── WritingArea.tsx  # Main writing canvas
│   │   ├── BurstBlock.tsx   # Individual burst display
│   │   └── FlareLabel.tsx   # Flareon name header
│   ├── hooks/
│   │   ├── useAutosave.ts   # Debounced save hook
│   │   └── useSession.ts    # Session restore hook
│   ├── lib/
│   │   └── api.ts           # HTTP client to Python backend
│   └── styles/
│       └── globals.css      # CSS variables, base styles
│
├── backend/
│   ├── api/
│   │   └── routes.py        # FastAPI route definitions
│   ├── services/
│   │   ├── flareon_service.py   # Flareon CRUD logic
│   │   ├── burst_service.py     # Burst logic + continuity check
│   │   └── storage_service.py   # Save/load content
│   ├── database/
│   │   ├── db.py            # SQLite connection + initialization
│   │   └── schema.sql       # Table definitions
│   ├── models/
│   │   └── schemas.py       # Pydantic request/response models
│   └── main.py              # FastAPI app entry point
│
├── storage/
│   └── .gitkeep             # SQLite DB lives here at runtime
│
├── scripts/
│   ├── start-dev.sh         # Unix startup script
│   └── start-dev.bat        # Windows startup script
│
├── package.json             # Electron + frontend dependencies
├── requirements.txt         # Python dependencies
├── tsconfig.json            # TypeScript config
├── next.config.js           # Next.js config
├── tailwind.config.js       # Tailwind config
├── .env.example             # Environment variable template
├── .gitignore               # Git ignore rules
└── README.md                # Setup and run instructions
```

---

## 8. DATABASE SCHEMA (OVERVIEW)

Full schema details are in `06_DATABASE_AND_PERSISTENCE.md`. Summary here for orientation:

| Table | Purpose |
|---|---|
| `flareons` | Named thinking domains |
| `bursts` | Continuous writing sessions within a Flareon |
| `burst_entries` | The actual text content of each burst |
| `app_state` | Stores last-opened Flareon + Burst for instant resume |

---

## 9. DEVELOPMENT PHASES

The AI must implement in this order. Do not skip phases. Do not implement phase N+1 before phase N is working.

| Phase | What Gets Built | Success Criteria |
|---|---|---|
| 1 | Project scaffolding: Electron shell + Next.js + Python FastAPI boot | All three processes launch without errors |
| 2 | Database + persistence layer | SQLite initializes; data reads/writes succeed |
| 3 | Flareon system | Create, list, and open Flareons |
| 4 | Burst automation | 30-minute continuity logic works correctly |
| 5 | Autosave + writing flow | Typing saves within 1 second of stopping |
| 6 | Session restore | App reopens to exact last position |
| 7 | UI polish | Calm, minimal, instant-feeling interface |

---

## 10. WHAT MUST NOT BE BUILT IN V1

This is a hard constraint. Do not implement any of the following, regardless of how natural it might seem to add:

- Markdown rendering or parsing
- AI or LLM integration of any kind
- Semantic or full-text search
- Authentication or accounts
- Cloud sync or remote storage
- WebSocket-based real-time sync
- Collaborative editing
- Rich text formatting (bold, italic, headings)
- Plugin system
- Tags, labels, or categories
- Import/export functionality
- Keyboard shortcut customization
- Dark/light theme toggle (dark only in V1)

If any of the above appears to be implied by a user request, implement only what is explicitly described in these instruction files.

---

## 11. ENGINEERING PRINCIPLES (ALL FILES MUST FOLLOW)

These principles apply to every file in every instruction set:

### Think Before Coding
- State assumptions explicitly before implementing
- If multiple interpretations exist, list them and pick the most aligned with the philosophy
- If something is simpler, prefer it

### Simplicity First
- Minimum code that solves the problem
- No abstractions for single-use code
- No speculative features
- If it could be 50 lines, don't write 200

### Surgical Changes
- When editing existing code: change only what is necessary
- Match existing style even if you'd do it differently
- Remove only dead code that YOUR changes created

### Goal-Driven Execution
- Transform every task into a verifiable goal
- For multi-step tasks, state a plan with verification checkpoints
- Loop until verified, not until done
