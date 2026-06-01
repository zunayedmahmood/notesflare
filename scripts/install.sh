#!/usr/bin/env bash
set -e

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  NotesFlare — Installation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "→ Installing Node.js dependencies..."
npm install
echo "✓ Node.js dependencies installed."
echo ""

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

echo "→ Preparing optional V1.2 NLP models..."
if $PYTHON -c "import spacy" >/dev/null 2>&1; then
  if $PYTHON -c "import spacy; spacy.load('en_core_web_sm')" >/dev/null 2>&1; then
    echo "  spaCy en_core_web_sm already available."
  else
    echo "  Downloading spaCy en_core_web_sm..."
    if $PYTHON -m spacy download en_core_web_sm --quiet; then
      echo "  ✓ spaCy model ready."
    else
      echo "  ! spaCy model download failed. NotesFlare will use fallback parser heuristics."
    fi
  fi
else
  echo "  ! spaCy is unavailable. NotesFlare will skip NLP parsing until installed."
fi

if $PYTHON -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')" >/dev/null 2>&1; then
  echo "  ✓ MiniLM embedding model ready."
else
  echo "  ! MiniLM model not cached/available. Formatting still works; semantic paragraph detection is skipped."
fi

if $PYTHON -c "import onnxruntime as ort; assert 'CPUExecutionProvider' in ort.get_available_providers()" >/dev/null 2>&1; then
  echo "  ✓ ONNX Runtime verified."
else
  echo "  ! ONNX Runtime unavailable. Formatting still works without accelerator support."
fi

echo ""
echo "→ Creating storage directory..."
mkdir -p storage
echo "✓ Storage directory ready."
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Installation complete."
echo "  Run 'scripts/start-dev.sh' to launch NotesFlare."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
