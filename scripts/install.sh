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
  PYTHON="$PROJECT_ROOT/.venv/bin/python"
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
