# NotesFlare — Setup, Dev Environment & Startup Scripts

> **AI Instruction File 07 of 08**
> This file covers everything needed to get NotesFlare running from a fresh clone: prerequisites, installation, one-command startup, environment configuration, and the cross-platform startup scripts. Read `01_BRAND_AND_ARCHITECTURE.md` before this file. This file produces a working development environment that any developer (or AI agent) can reproduce exactly.

---

## 1. SETUP PHILOSOPHY

NotesFlare's setup must satisfy a single requirement:

```
One clone → one command → running app.
```

A developer who has just cloned the repository should be able to run a single script and have the app running. No manual steps. No "also make sure you install X." No environment-specific workarounds documented as footnotes.

The setup is split into two concerns:
1. **Prerequisites** — what must exist on the machine before setup (documented here, cannot be automated)
2. **Installation** — what can be automated (automated by a single script)

---

## 2. PREREQUISITES (CANNOT BE AUTOMATED)

These must be installed by the developer before running any setup scripts. The README must list these clearly.

| Prerequisite | Minimum Version | Check Command |
|---|---|---|
| Node.js | 20.0.0 | `node --version` |
| Python | 3.11.0 | `python3 --version` |
| npm | 9.0.0 (comes with Node) | `npm --version` |
| pip | 23.0 (comes with Python) | `pip3 --version` |
| Git | Any recent version | `git --version` |

**No other system dependencies.** SQLite is built into Python's standard library. Electron bundles its own Chromium. There is no external database server, no Redis, no Docker required.

---

## 3. ENVIRONMENT VARIABLES

Create `.env.example` at project root. Developers copy this to `.env`.

```bash
# .env.example
# Copy this file to .env and fill in values as needed.
# For V1, no values are required — defaults work for local development.

# Backend port (default: 8000)
# Only change if port 8000 is occupied on your machine.
NOTESFLARE_PORT=8000

# Python path override (optional)
# Set this if 'python3' is not in your PATH or you use a venv.
# Example: PYTHON_PATH=/Users/you/.venv/bin/python
PYTHON_PATH=
```

In V1, no `.env` values are required. The defaults are correct for all standard installations.

---

## 4. PYTHON VIRTUAL ENVIRONMENT (RECOMMENDED)

While not mandatory, all scripts should check for and use a virtual environment if one exists.

### Creating a venv (developer does this once)
```bash
cd notesflare
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Detecting venv in scripts
Scripts must check for `.venv` before falling back to system Python:

```bash
# Shell script venv detection
if [ -d ".venv" ]; then
  PYTHON=".venv/bin/python"
else
  PYTHON=$(which python3 || which python)
fi
```

```batch
:: Batch script venv detection
IF EXIST ".venv\Scripts\python.exe" (
  SET PYTHON=.venv\Scripts\python.exe
) ELSE (
  SET PYTHON=python
)
```

---

## 5. INSTALLATION SCRIPT

Create `scripts/install.sh` (and `scripts/install.bat` for Windows). This script:
1. Installs npm dependencies
2. Installs Python dependencies (into venv if available)
3. Creates the `storage/` directory

### scripts/install.sh

```bash
#!/usr/bin/env bash
set -e

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  NotesFlare — Installation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Navigate to project root (script may be called from anywhere)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# ─── Node dependencies ───────────────────────────────────────────────────────
echo "→ Installing Node.js dependencies..."
npm install
echo "✓ Node.js dependencies installed."
echo ""

# ─── Python dependencies ─────────────────────────────────────────────────────
echo "→ Installing Python dependencies..."

if [ -d ".venv" ]; then
  echo "  (Using existing virtual environment at .venv)"
  PYTHON=".venv/bin/python"
else
  echo "  (No .venv found — using system Python)"
  echo "  Tip: Run 'python3 -m venv .venv && source .venv/bin/activate' first"
  PYTHON=$(which python3 2>/dev/null || which python 2>/dev/null)
  if [ -z "$PYTHON" ]; then
    echo "✗ Python not found. Please install Python 3.11+."
    exit 1
  fi
fi

$PYTHON -m pip install -r requirements.txt --quiet
echo "✓ Python dependencies installed."
echo ""

# ─── Storage directory ────────────────────────────────────────────────────────
echo "→ Creating storage directory..."
mkdir -p storage
echo "✓ Storage directory ready."
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Installation complete."
echo "  Run 'scripts/start-dev.sh' to launch NotesFlare."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
```

### scripts/install.bat (Windows)

```batch
@echo off
setlocal

echo.
echo ════════════════════════════════════════
echo   NotesFlare — Installation
echo ════════════════════════════════════════
echo.

:: Navigate to project root
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
cd /d "%PROJECT_ROOT%"

:: Node dependencies
echo ^→ Installing Node.js dependencies...
call npm install
if errorlevel 1 (
    echo X npm install failed. Is Node.js 20+ installed?
    exit /b 1
)
echo v Node.js dependencies installed.
echo.

:: Python detection
IF EXIST ".venv\Scripts\python.exe" (
    echo ^→ Using virtual environment at .venv
    set PYTHON=.venv\Scripts\python.exe
) ELSE (
    echo ^→ No .venv found — using system Python
    set PYTHON=python
)

:: Python dependencies
echo ^→ Installing Python dependencies...
%PYTHON% -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo X pip install failed. Is Python 3.11+ installed?
    exit /b 1
)
echo v Python dependencies installed.
echo.

:: Storage directory
echo ^→ Creating storage directory...
if not exist "storage" mkdir storage
echo v Storage directory ready.
echo.

echo ════════════════════════════════════════
echo   Installation complete.
echo   Run 'scripts\start-dev.bat' to launch.
echo ════════════════════════════════════════
echo.
```

---

## 6. DEVELOPMENT STARTUP SCRIPTS

These scripts start all three processes: Python backend, Next.js frontend (dev server or static build), and Electron.

### scripts/start-dev.sh (macOS/Linux)

```bash
#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# ─── Python detection ─────────────────────────────────────────────────────────
if [ -d ".venv" ]; then
  PYTHON=".venv/bin/python"
else
  PYTHON=$(which python3 2>/dev/null || which python 2>/dev/null)
fi

if [ -z "$PYTHON" ]; then
  echo "✗ Python not found. Run scripts/install.sh first."
  exit 1
fi

# ─── Cleanup function ─────────────────────────────────────────────────────────
# Kill child processes when the script exits (Ctrl+C or error)
cleanup() {
  echo ""
  echo "→ Shutting down NotesFlare..."
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "$FRONTEND_PID" ]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  echo "✓ Stopped."
  exit 0
}
trap cleanup EXIT INT TERM

# ─── Build frontend (static export) ───────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  NotesFlare — Starting Dev Environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "→ Building frontend..."
npm run build:frontend
echo "✓ Frontend built to frontend/out/"
echo ""

# ─── Build Electron TypeScript ─────────────────────────────────────────────────
echo "→ Compiling Electron TypeScript..."
npm run build:electron
echo "✓ Electron compiled to electron/dist/"
echo ""

# ─── Start Python backend ──────────────────────────────────────────────────────
echo "→ Starting Python backend on port 8000..."
cd "$PROJECT_ROOT/backend"
$PYTHON main.py &
BACKEND_PID=$!
cd "$PROJECT_ROOT"
echo "  Backend PID: $BACKEND_PID"

# ─── Wait for backend to be ready ─────────────────────────────────────────────
echo "→ Waiting for backend..."
MAX_WAIT=10
ELAPSED=0
until curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; do
  sleep 0.3
  ELAPSED=$((ELAPSED + 1))
  if [ $ELAPSED -ge $((MAX_WAIT * 3)) ]; then
    echo "✗ Backend did not start in ${MAX_WAIT} seconds. Check logs above."
    exit 1
  fi
done
echo "✓ Backend is ready."
echo ""

# ─── Launch Electron ───────────────────────────────────────────────────────────
echo "→ Launching Electron..."
echo ""
npx electron . &
FRONTEND_PID=$!

# Wait for Electron to exit
wait $FRONTEND_PID
```

### scripts/start-dev.bat (Windows)

```batch
@echo off
setlocal EnableDelayedExpansion

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
cd /d "%PROJECT_ROOT%"

echo.
echo ════════════════════════════════════════
echo   NotesFlare — Starting Dev Environment
echo ════════════════════════════════════════
echo.

:: Python detection
IF EXIST ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) ELSE (
    set PYTHON=python
)

:: Build frontend
echo ^→ Building frontend...
call npm run build:frontend
if errorlevel 1 ( echo X Frontend build failed. & exit /b 1 )
echo v Frontend built.
echo.

:: Build Electron TypeScript
echo ^→ Compiling Electron TypeScript...
call npm run build:electron
if errorlevel 1 ( echo X Electron compile failed. & exit /b 1 )
echo v Electron compiled.
echo.

:: Start Python backend in new window
echo ^→ Starting Python backend...
start "NotesFlare Backend" /min cmd /c "cd backend && %PYTHON% main.py"
echo   (Backend starting in background window)

:: Wait for backend
echo ^→ Waiting for backend...
:WAIT_LOOP
timeout /t 1 /nobreak >nul
curl -s http://127.0.0.1:8000/api/health >nul 2>&1
if errorlevel 1 goto WAIT_LOOP
echo v Backend is ready.
echo.

:: Launch Electron
echo ^→ Launching Electron...
echo.
npx electron .
```

---

## 7. HOT-RELOAD DEVELOPMENT MODE (OPTIONAL)

For rapid frontend development, run Next.js in dev server mode instead of building the static export. In this mode, Electron loads from `localhost:3000` instead of `frontend/out/`.

This requires a minor modification to `electron/main.ts`:

```typescript
// In createMainWindow(), change:
const indexPath = path.join(__dirname, "../../frontend/out/index.html");
win.loadFile(indexPath);

// To (for dev mode):
const isDev = process.env.NODE_ENV === "development";
if (isDev) {
  win.loadURL("http://localhost:3000");
} else {
  const indexPath = path.join(__dirname, "../../frontend/out/index.html");
  win.loadFile(indexPath);
}
```

Then run in separate terminals:
```bash
# Terminal 1
cd backend && python3 main.py

# Terminal 2
cd frontend && next dev

# Terminal 3 (after Next.js is ready)
NODE_ENV=development npx electron .
```

**This is optional.** The default startup scripts use the static build. Hot reload is only needed when doing rapid UI iteration.

---

## 8. README.md

Create this `README.md` at the project root. It is the entry point for any human or AI reading the repository.

```markdown
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
```

---

## 9. .GITIGNORE

```gitignore
# Dependencies
node_modules/
.venv/

# Build outputs
frontend/out/
frontend/.next/
electron/dist/

# Database (user data — do not commit)
storage/*.db
storage/*.db-shm
storage/*.db-wal

# Environment
.env

# OS
.DS_Store
Thumbs.db

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/

# Editor
.vscode/
.idea/
*.swp
*.swo
```

---

## 10. VERIFICATION CHECKLIST

Run through these in order on a fresh clone:

```
SETUP VERIFICATION
──────────────────
[ ] git clone works
[ ] scripts/install.sh exits with code 0
[ ] node_modules/ exists after install
[ ] requirements.txt packages install without errors

STARTUP VERIFICATION
────────────────────
[ ] scripts/start-dev.sh exits successfully at each step
[ ] Backend starts: curl http://127.0.0.1:8000/api/health returns {"status":"ok"}
[ ] Electron window opens (no white flash)
[ ] Frontend loads in Electron window
[ ] storage/notesflare.db exists after first run
[ ] App can create a Flareon on first launch
[ ] App restores last Flareon on relaunch

CROSS-PLATFORM (if applicable)
──────────────────────────────
[ ] start-dev.bat works on Windows
[ ] Venv detection works (test with and without .venv present)
```

---

## 11. COMMON SETUP FAILURES AND FIXES

| Failure | Likely Cause | Fix |
|---|---|---|
| `npm install` fails | Node.js version too old | Install Node 20+ |
| `pip install` fails | Python version too old | Install Python 3.11+ |
| Backend health check times out | Port 8000 occupied | Change `NOTESFLARE_PORT` in `.env` (and update backend + Electron configs) |
| Electron window is blank | Frontend build failed | Run `npm run build:frontend` manually and check for errors |
| `storage/` not created | Missing permissions or install script not run | Run install script first, or `mkdir storage` manually |
| `python3: command not found` on Windows | Python not in PATH | Set `PYTHON_PATH` in `.env` or create `.venv` |
| `electron: command not found` | npm dependencies not installed | Run install script |
