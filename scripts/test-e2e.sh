#!/bin/bash
# scripts/test-e2e.sh
# Start the app stack (backend + frontend) then run Playwright E2E tests.
# Requires: backend running, frontend built or dev server running.
# Usage: ./scripts/test-e2e.sh
# Usage (headed, for debug): ./scripts/test-e2e.sh --headed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     NotesFlare — E2E Test Suite              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

cd "$PROJECT_ROOT"

# Start Python backend in test mode
echo "→ Starting backend in test mode..."
NOTESFLARE_ENV=test "$PROJECT_ROOT/.venv/bin/python" backend/main.py &
BACKEND_PID=$!

# Wait for backend health
echo "→ Waiting for backend to be ready..."
for i in $(seq 1 20); do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "✓ Backend ready (took ${i} attempts)"
        break
    fi
    if [ $i -eq 20 ]; then
        echo "✗ ERROR: Backend did not start within 20 attempts."
        echo "  Check: python backend/main.py starts without errors"
        echo "  Check: Port 8000 is not occupied by another process"
        echo "  Run: lsof -i :8000"
        kill $BACKEND_PID 2>/dev/null
        exit 1
    fi
    sleep 0.5
done

# Run E2E tests
echo "→ Running Playwright tests..."
npx playwright test --config e2e/playwright.config.ts "$@" 2>&1
E2E_EXIT=$?

# Cleanup
echo "→ Stopping backend (PID: $BACKEND_PID)"
kill $BACKEND_PID 2>/dev/null

echo ""
if [ $E2E_EXIT -eq 0 ]; then
    echo "✓ All E2E tests passed."
    echo "  HTML report: coverage/e2e/index.html"
else
    echo "✗ E2E tests FAILED (exit code: $E2E_EXIT)"
    echo ""
    echo "  Diagnostic guide:"
    echo "  ─────────────────────────────────────────────"
    echo "  Timeout waiting for element  → Add data-testid attributes to all components"
    echo "  Cannot reset test DB         → Ensure /api/test/reset exists in backend"
    echo "  App loads but sidebar empty  → GET /api/flareons returning error or empty"
    echo "  Autosave test fails          → Check browser network tab in --headed mode"
    echo ""
    echo "  Re-run with screenshots: ./scripts/test-e2e.sh --headed"
    echo "  View last failure screenshots: ls coverage/e2e/test-results/"
fi

exit $E2E_EXIT
