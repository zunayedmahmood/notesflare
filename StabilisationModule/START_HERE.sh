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
  echo "Python not found. Please install Python 3.11+ or create .venv first."
  exit 1
fi

"$PYTHON" StabilisationModule/run_stabilisation_benchmark.py "$@"
