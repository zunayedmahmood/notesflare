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

run_original() {
  "$PYTHON" StabilisationModule/run_stabilisation_benchmark.py "$@"
}

run_continuous() {
  "$PYTHON" StabilisationModule/run_stabilisation_benchmark.py \
    --input StabilisationModule/examples_1000_continuous_stream.json \
    --output StabilisationModule/outputs/formatted_results_continuous.json \
    --summary StabilisationModule/outputs/benchmark_summary_continuous.json \
    --benchmark-db StabilisationModule/outputs/stabilisation_benchmark_continuous.db "$@"
}

run_progressive() {
  "$PYTHON" StabilisationModule/generate_progressive_usage_examples.py
  "$PYTHON" StabilisationModule/run_stabilisation_benchmark.py \
    --input StabilisationModule/examples_1000_progressive_usage.json \
    --output StabilisationModule/outputs/formatted_results_progressive_usage.json \
    --summary StabilisationModule/outputs/benchmark_summary_progressive_usage.json \
    --benchmark-db StabilisationModule/outputs/stabilisation_benchmark_progressive_usage.db \
    --simulate-decisions \
    --reset-progressive-profile \
    --study-old-data "$@"
}

case "${1:-all}" in
  original)
    shift || true
    run_original "$@"
    ;;
  continuous)
    shift || true
    run_continuous "$@"
    ;;
  progressive)
    shift || true
    run_progressive "$@"
    ;;
  all)
    shift || true
    run_original "$@"
    run_continuous "$@"
    run_progressive "$@"
    ;;
  *)
    # Backward-compatible pass-through to the benchmark runner.
    "$PYTHON" StabilisationModule/run_stabilisation_benchmark.py "$@"
    ;;
esac
