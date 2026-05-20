# NotesFlare

> Thought capture with near-zero cognitive friction.

NotesFlare is a local-first desktop app for persistent thought streaming.
Your thinking lives in **Flareons** (thinking domains), organized into
**Bursts** (continuous writing sessions). The app saves automatically.
You never manage files.

---

## Prerequisites

- **Node.js** 20+ — https://nodejs.org
- **Python** 3.11+ — https://python.org

---

## Setup

```bash
git clone https://github.com/yourname/notesflare.git
cd notesflare
bash scripts/install.sh
```

On Windows:
```batch
git clone https://github.com/yourname/notesflare.git
cd notesflare
scripts\install.bat
```

---

## Run

```bash
bash scripts/start-dev.sh
```

On Windows:
```batch
scripts\start-dev.bat
```

---

## Architecture

| Layer | Technology |
|---|---|
| Desktop shell | Electron 30 |
| Frontend | Next.js 14 + React 18 |
| Backend | Python + FastAPI |
| Database | SQLite (local, embedded) |

See the `docs/` folder for full architecture and instruction files.

---

## Data Storage

Your thoughts are stored locally in:
- **macOS**: `storage/notesflare.db` (relative to the project directory)
- **Windows**: `storage\notesflare.db`

This file is never uploaded anywhere. It is yours.

---

## Development

The backend API runs at `http://localhost:8000`.
Interactive API docs: `http://localhost:8000/docs` (while backend is running).
