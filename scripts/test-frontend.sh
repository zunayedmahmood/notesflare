#!/bin/bash
# scripts/test-frontend.sh
# Run all frontend tests with coverage.
# Usage: ./scripts/test-frontend.sh
# Usage (watch mode): ./scripts/test-frontend.sh --watch
# Usage (single file): ./scripts/test-frontend.sh frontend/tests/hooks/useAutosave.test.ts

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     NotesFlare — Frontend Test Suite         ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

cd "$PROJECT_ROOT"

if [ ! -d "node_modules" ]; then
    echo "✗ ERROR: node_modules not found."
    echo "  Run: npm install"
    exit 1
fi

if ! npx vitest --version > /dev/null 2>&1; then
    echo "✗ ERROR: vitest not found in node_modules."
    echo "  Run: npm install --save-dev vitest"
    exit 1
fi

echo "✓ vitest found: $(npx vitest --version 2>&1 | head -1)"
echo ""

npx vitest run "$@" \
    --reporter=verbose \
    --coverage \
    2>&1

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ All frontend tests passed."
    echo "  Coverage report: coverage/frontend/index.html"
else
    echo "✗ Frontend tests FAILED (exit code: $EXIT_CODE)"
    echo ""
    echo "  Diagnostic guide:"
    echo "  ─────────────────────────────────────────────"
    echo "  Cannot find module '@/...'  → Check vitest.config.ts alias for '@'"
    echo "  fetch is not defined        → Add global fetch polyfill in setup.ts"
    echo "  MSW handler not matched     → Check BASE URL in handlers.ts matches api.ts"
    echo "  act() warning               → Wrap state updates in act() in test"
    echo "  Timer not advancing         → Must call vi.useFakeTimers() in beforeEach"
fi

exit $EXIT_CODE
