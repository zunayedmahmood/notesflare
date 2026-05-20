#!/bin/bash
# scripts/test-backend.sh
# Run all backend tests with coverage report.
# Usage: ./scripts/test-backend.sh
# Usage (specific file): ./scripts/test-backend.sh backend/tests/test_burst_service.py
# Usage (specific marker): ./scripts/test-backend.sh -m "unit"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     NotesFlare — Backend Test Suite          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Activate virtual environment if present
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
    echo "✓ Virtual environment activated"
else
    echo "⚠ No .venv found — using system Python"
fi

# Verify pytest is installed
if ! python -m pytest --version > /dev/null 2>&1; then
    echo ""
    echo "✗ ERROR: pytest not found."
    echo "  Run: pip install -r requirements.txt"
    echo "  Or:  pip install pytest pytest-asyncio httpx freezegun pytest-cov"
    exit 1
fi

echo "✓ pytest found: $(python -m pytest --version 2>&1 | head -1)"
echo ""

cd "$PROJECT_ROOT"

# Run pytest with extra verbosity for error diagnosis
python -m pytest "$@" \
    --tb=long \
    --showlocals \
    -v \
    --cov=backend \
    --cov-report=term-missing \
    --cov-report=html:coverage/backend \
    2>&1

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ All backend tests passed."
    echo "  Coverage report: coverage/backend/index.html"
else
    echo "✗ Backend tests FAILED (exit code: $EXIT_CODE)"
    echo ""
    echo "  Diagnostic guide:"
    echo "  ─────────────────────────────────────────────"
    echo "  ImportError on service modules  → Check sys.path in conftest.py"
    echo "  sqlite3 OperationalError        → schema.sql has a syntax error"
    echo "  freezegun has no effect         → datetime.now() not imported correctly"
    echo "  httpx transport error           → FastAPI app failed to start in test mode"
    echo "  AssertionError with no message  → Test was written without a message arg"
    echo "  Full output above. Start with the FIRST failure — later failures are often cascades."
fi

exit $EXIT_CODE
