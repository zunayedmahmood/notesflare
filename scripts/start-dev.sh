#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# ─── Python detection ─────────────────────────────────────────────────────────
if [ -d ".venv" ]; then
  PYTHON="$PROJECT_ROOT/.venv/bin/python"
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
