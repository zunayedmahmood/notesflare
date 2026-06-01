#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

if [ -d ".venv" ]; then
  PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
  PYTHON=$(which python3 2>/dev/null || which python 2>/dev/null)
fi

if [ -z "$PYTHON" ]; then
  echo "✗ Python not found. Run scripts/install.sh first."
  exit 1
fi

kill_port() {
  local port=$1
  local found=0

  # Method 1: lsof with TCP:LISTEN — catches both IPv4 and IPv6 bound processes
  if command -v lsof >/dev/null 2>&1; then
    local pids
    pids=$(lsof -t -i TCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
    if [ -n "$pids" ]; then
      echo "  → lsof: killing PIDs $pids on port $port"
      kill -9 $pids 2>/dev/null || true
      found=1
    fi
  fi

  # Method 2: ss — reliable fallback, also sees IPv6
  if command -v ss >/dev/null 2>&1; then
    local pids
    pids=$(ss -tlnp "sport = :$port" 2>/dev/null | grep -oP 'pid=\K[0-9]+' || true)
    if [ -n "$pids" ]; then
      echo "  → ss: killing PIDs $pids on port $port"
      kill -9 $pids 2>/dev/null || true
      found=1
    fi
  fi

  # Method 3: fuser — last resort
  if command -v fuser >/dev/null 2>&1; then
    if fuser "$port"/tcp >/dev/null 2>&1; then
      echo "  → fuser: killing processes on port $port"
      fuser -k -9 "$port"/tcp >/dev/null 2>&1 || true
      found=1
    fi
  fi

  [ "$found" -eq 1 ] && sleep 0.5
  return 0
}

# Block until a port is confirmed free (or abort after timeout)
wait_port_free() {
  local port=$1
  for i in {1..10}; do
    local in_use=0
    # Check via lsof
    if command -v lsof >/dev/null 2>&1; then
      lsof -t -i TCP:"$port" -sTCP:LISTEN >/dev/null 2>&1 && in_use=1
    fi
    # Check via ss — ss formats wildcard-bound sockets as '*:PORT'
    if command -v ss >/dev/null 2>&1; then
      ss -tlnp "sport = :$port" 2>/dev/null | grep -qP ":\b$port\b" && in_use=1
    fi
    [ "$in_use" -eq 0 ] && return 0
    sleep 0.3
  done
  echo "✗ Port $port is STILL in use after cleanup — cannot start safely."
  echo "  Run: kill -9 \$(ss -tlnp 'sport = :$port' | grep -oP 'pid=\K[0-9]+')"
  exit 1
}

cleanup() {
  echo ""
  echo "→ Shutting down NotesFlare..."
  if [ -n "${ELECTRON_PID:-}" ]; then kill "$ELECTRON_PID" 2>/dev/null || true; fi
  if [ -n "${FRONTEND_PID:-}" ]; then kill "$FRONTEND_PID" 2>/dev/null || true; fi
  if [ -n "${BACKEND_PID:-}" ]; then kill "$BACKEND_PID" 2>/dev/null || true; fi
  kill_port 8000
  kill_port 3000
  echo "✓ Stopped."
  exit 0
}
trap cleanup EXIT INT TERM

echo "→ Cleaning up any stale NotesFlare instances..."
# Kill any lingering Next.js / uvicorn worker processes by name first
pkill -9 -f "next-server" 2>/dev/null || true
pkill -9 -f "next dev" 2>/dev/null || true
pkill -9 -f "uvicorn" 2>/dev/null || true
sleep 0.5
# Then clean up by port (catches anything not matched by name)
kill_port 8000
kill_port 3000
# Verify ports are actually free before proceeding
wait_port_free 8000
wait_port_free 3000
echo "✓ Ports 8000 and 3000 are free."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  NotesFlare — Starting Dev Environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "→ Checking V1.2 optional NLP dependencies..."
$PYTHON - <<'PY' || true
missing = []
try:
    import spacy
    try:
        spacy.load('en_core_web_sm')
    except OSError:
        missing.append('spaCy en_core_web_sm model (parser will use fallback heuristics)')
except ImportError:
    missing.append('spaCy (parser will use fallback heuristics if spaCy is installed later)')
try:
    import sentence_transformers  # noqa: F401
except ImportError:
    missing.append('sentence-transformers (semantic similarity will be skipped)')
try:
    import onnxruntime  # noqa: F401
except ImportError:
    missing.append('onnxruntime (accelerator unavailable)')

if missing:
    print('  Optional NLP items missing:')
    for item in missing:
        print('   - ' + item)
    print('  NotesFlare will still run; install full requirements for the complete NLP path.')
else:
    print('  Full NLP stack available.')
PY
echo ""

echo "→ Starting Python backend on port 8000..."
cd "$PROJECT_ROOT/backend"
$PYTHON main.py &
BACKEND_PID=$!
cd "$PROJECT_ROOT"
echo "  Backend PID: $BACKEND_PID"

echo "→ Waiting for backend..."
for i in {1..40}; do
  if curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
    echo "✓ Backend is ready."
    break
  fi
  sleep 0.25
  if [ "$i" = "40" ]; then
    echo "✗ Backend did not start. Check logs above."
    exit 1
  fi
done

echo "→ Starting Next.js frontend on port 3000..."
# -p 3000 forces the port — Next.js will error out loudly instead of silently
# bumping to 3001/3002/etc., which would break Electron's hardcoded target.
NEXT_TELEMETRY_DISABLED=1 NEXT_PORT=3000 npm run dev:frontend -- -p 3000 &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"

echo "→ Waiting for frontend to serve HTTP 200..."
for i in {1..120}; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    echo "✓ Frontend is ready (HTTP 200)."
    break
  fi
  sleep 0.25
  if [ "$i" = "120" ]; then
    echo "✗ Frontend did not start on port 3000 after 30s. Last status: $STATUS."
    echo "  Check above for Next.js errors."
    exit 1
  fi
done

echo "→ Compiling Electron TypeScript..."
npm run build:electron
echo "✓ Electron compiled."

echo "→ Launching Electron..."
NODE_ENV=development npx electron . --no-sandbox &
ELECTRON_PID=$!
wait "$ELECTRON_PID"
