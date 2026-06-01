#!/usr/bin/env python3
"""
NotesFlare StabilisationModule benchmark runner.

Developer-only harness for testing deterministic structure stabilisation.
It uses the existing backend V1.2 NLP/formatting pipeline and writes formatted
outputs mapped to the original dataset IDs.

Default mode uses a dedicated benchmark SQLite database inside
`StabilisationModule/outputs/`, runs the same lineage/diff services as the app,
and auto-accepts pending diffs there. It never writes to the user's real
`storage/notesflare.db`.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import db as db_module  # noqa: E402
from services import stream_service  # noqa: E402
from services.formatting import (  # noqa: E402
    chunker_service,
    diff_service,
    embedding_service,
    formatter_service,
    lexer_service,
    lineage_service,
    parser_service,
)

DEFAULT_INPUT = MODULE_DIR / "examples_1000.json"
DEFAULT_OUTPUT = MODULE_DIR / "outputs" / "formatted_results.json"
DEFAULT_SUMMARY = MODULE_DIR / "outputs" / "benchmark_summary.json"
DEFAULT_BENCHMARK_DB = MODULE_DIR / "outputs" / "stabilisation_benchmark.db"


def load_examples(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    examples = payload.get("examples", payload if isinstance(payload, list) else [])
    if not isinstance(examples, list):
        raise ValueError("Input JSON must be a list or an object containing an 'examples' list.")

    seen: set[str] = set()
    for index, item in enumerate(examples):
        if not isinstance(item, dict):
            raise ValueError(f"Example at index {index} must be an object.")
        if not item.get("id"):
            raise ValueError(f"Example at index {index} is missing a unique 'id'.")
        if item["id"] in seen:
            raise ValueError(f"Duplicate example id found: {item['id']}")
        if "raw_text" not in item:
            raise ValueError(f"Example {item['id']} is missing 'raw_text'.")
        seen.add(item["id"])
    return examples


def prepare_benchmark_database(path: Path) -> sqlite3.Connection:
    """Create an isolated benchmark DB and route backend db.get_db() to it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    for candidate in (path, path.with_suffix(path.suffix + "-wal"), path.with_suffix(path.suffix + "-shm")):
        if candidate.exists():
            candidate.unlink()

    db_module.close_all_connections()
    conn = sqlite3.connect(str(path), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    schema_path = BACKEND_DIR / "database" / "schema.sql"
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.commit()

    # Deliberately use the backend's test/global override so lineage_service,
    # stream_service, and diff_service all use this benchmark DB.
    db_module._connection = conn  # type: ignore[attr-defined]
    return conn


def create_benchmark_flareon(conn: sqlite3.Connection) -> int:
    cur = conn.execute("INSERT INTO flareons (name) VALUES (?)", ("Stabilisation Benchmark",))
    conn.commit()
    return int(cur.lastrowid)


def create_benchmark_burst(conn: sqlite3.Connection, flareon_id: int, raw_text: str) -> int:
    burst_cur = conn.execute("INSERT INTO bursts (flareon_id) VALUES (?)", (flareon_id,))
    burst_id = int(burst_cur.lastrowid)
    conn.execute(
        "INSERT INTO burst_entries (burst_id, content_chunk, sequence_number) VALUES (?, ?, 0)",
        (burst_id, raw_text),
    )
    conn.commit()
    return burst_id


def apply_operations(lines: list[str], operations: list[dict[str, Any]]) -> list[str]:
    """Auto-accept formatter operations in memory for no-db benchmark output."""
    formatted_lines = list(lines)
    for op in sorted(operations, key=lambda item: (item.get("line_index", 0), item.get("operation", ""))):
        line_index = int(op.get("line_index", -1))
        if 0 <= line_index < len(formatted_lines):
            formatted_lines[line_index] = str(op.get("formatted_after", formatted_lines[line_index]))
    return formatted_lines


def compute_similarity(lines: list[str], use_embeddings: bool) -> tuple[list[float] | None, str, str | None]:
    if not use_embeddings:
        return None, "skipped", None

    try:
        embeddings = embedding_service.embed_lines(lines)
        return embedding_service.compute_similarity_sequence(embeddings), "ok", None
    except Exception as exc:  # noqa: BLE001 - benchmark must never fail because optional embeddings are unavailable
        return None, "fallback_rule_only", f"{exc.__class__.__name__}: {exc}"


def run_pipeline_no_db(raw_text: str, use_embeddings: bool = True) -> dict[str, Any]:
    """Run the existing parser/chunker/formatter services without DB writes."""
    normalized_text = lexer_service.normalize_text(raw_text)
    lines = lexer_service.split_into_lines(normalized_text)
    line_signals = parser_service.parse_lines(lines)
    chunks = chunker_service.chunk_lines(lines)
    similarity_scores, embedding_status, embedding_error = compute_similarity(lines, use_embeddings)
    operations = formatter_service.generate_operations(line_signals, similarity_scores)
    formatted_lines = apply_operations(lines, operations)

    return {
        "burst_id": None,
        "normalized_text": normalized_text,
        "formatted_text": "\n".join(formatted_lines),
        "line_count": len(lines),
        "chunk_count": len(chunks),
        "embedding_status": embedding_status,
        "embedding_error": embedding_error,
        "similarity_scores": similarity_scores,
        "diff_count": len(operations),
        "operations": operations,
        "stored_diffs": [],
        "accepted_diffs": [],
        "auto_accept_status": "accepted_in_memory_only",
    }


def run_pipeline_with_benchmark_db(
    conn: sqlite3.Connection,
    flareon_id: int,
    raw_text: str,
    use_embeddings: bool = True,
) -> dict[str, Any]:
    """Run the same line/diff database flow used by the NotesFlare backend."""
    burst_id = create_benchmark_burst(conn, flareon_id, raw_text)
    reconstructed = stream_service.reconstruct_burst(burst_id)

    normalized_text = lexer_service.normalize_text(reconstructed)
    lines = lexer_service.split_into_lines(normalized_text)
    line_records = lineage_service.get_or_create_lines(burst_id, lines)
    line_signals = parser_service.parse_lines(lines)
    chunks = chunker_service.chunk_lines(lines)
    similarity_scores, embedding_status, embedding_error = compute_similarity(lines, use_embeddings)
    operations = formatter_service.generate_operations(line_signals, similarity_scores)
    stored_diffs = diff_service.store_diffs(burst_id, line_records, operations)
    accepted_diffs = diff_service.accept_all_pending(burst_id)
    formatted_result = diff_service.get_formatted_burst(burst_id, reconstructed)

    return {
        "burst_id": burst_id,
        "normalized_text": normalized_text,
        "formatted_text": formatted_result["formatted_text"],
        "has_formatting": formatted_result["has_formatting"],
        "line_count": len(lines),
        "chunk_count": len(chunks),
        "embedding_status": embedding_status,
        "embedding_error": embedding_error,
        "similarity_scores": similarity_scores,
        "diff_count": len(stored_diffs),
        "operations": operations,
        "stored_diffs": stored_diffs,
        "accepted_diffs": accepted_diffs,
        "auto_accept_status": "accepted_in_benchmark_database",
    }


def run_benchmark(
    input_path: Path,
    output_path: Path,
    summary_path: Path,
    benchmark_db_path: Path,
    limit: int | None = None,
    use_embeddings: bool = True,
    use_database_pipeline: bool = True,
) -> dict[str, Any]:
    examples = load_examples(input_path)
    if limit is not None:
        examples = examples[:limit]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    conn = None
    flareon_id = None
    if use_database_pipeline:
        conn = prepare_benchmark_database(benchmark_db_path)
        flareon_id = create_benchmark_flareon(conn)

    started_at = datetime.now(timezone.utc).isoformat()
    results: list[dict[str, Any]] = []
    genre_counter: Counter[str] = Counter()
    operation_counter: Counter[str] = Counter()
    embedding_counter: Counter[str] = Counter()
    diff_by_genre: defaultdict[str, int] = defaultdict(int)

    for idx, example in enumerate(examples, start=1):
        if use_database_pipeline:
            assert conn is not None and flareon_id is not None
            pipeline_result = run_pipeline_with_benchmark_db(conn, flareon_id, example["raw_text"], use_embeddings)
        else:
            pipeline_result = run_pipeline_no_db(example["raw_text"], use_embeddings)

        genre = example.get("genre", "unknown")
        genre_counter[genre] += 1
        diff_by_genre[genre] += pipeline_result["diff_count"]
        embedding_counter[pipeline_result["embedding_status"]] += 1

        for op in pipeline_result["operations"]:
            operation_counter[str(op.get("operation", "unknown"))] += 1

        results.append({
            "id": example["id"],
            "genre": genre,
            "tags": example.get("tags", []),
            "benchmark_burst_id": pipeline_result["burst_id"],
            "raw_text": example["raw_text"],
            "normalized_text": pipeline_result["normalized_text"],
            "formatted_text": pipeline_result["formatted_text"],
            "diff_count": pipeline_result["diff_count"],
            "operations": pipeline_result["operations"],
            "stored_diffs": pipeline_result["stored_diffs"],
            "accepted_diffs": pipeline_result["accepted_diffs"],
            "line_count": pipeline_result["line_count"],
            "chunk_count": pipeline_result["chunk_count"],
            "embedding_status": pipeline_result["embedding_status"],
            "embedding_error": pipeline_result["embedding_error"],
            "auto_accept_status": pipeline_result["auto_accept_status"],
        })

        if idx % 100 == 0 or idx == len(examples):
            print(f"Processed {idx}/{len(examples)} examples...")

    completed_at = datetime.now(timezone.utc).isoformat()
    changed_count = sum(1 for item in results if item["diff_count"] > 0)
    total_diffs = sum(item["diff_count"] for item in results)

    output_payload = {
        "dataset": str(input_path.relative_to(PROJECT_ROOT) if input_path.is_relative_to(PROJECT_ROOT) else input_path),
        "processed_at": completed_at,
        "count": len(results),
        "auto_accept_mode": "benchmark_database" if use_database_pipeline else "memory_only",
        "benchmark_database": str(benchmark_db_path) if use_database_pipeline else None,
        "pipeline": [
            "stream_service.reconstruct_burst" if use_database_pipeline else "raw_text from examples_1000.json",
            "lexer_service.normalize_text",
            "lexer_service.split_into_lines",
            "lineage_service.get_or_create_lines" if use_database_pipeline else "lineage skipped in memory-only mode",
            "parser_service.parse_lines",
            "chunker_service.chunk_lines",
            "embedding_service.embed_lines optional",
            "embedding_service.compute_similarity_sequence optional",
            "formatter_service.generate_operations",
            "diff_service.store_diffs" if use_database_pipeline else "operations kept in memory",
            "diff_service.accept_all_pending" if use_database_pipeline else "StabilisationModule.apply_operations",
            "diff_service.get_formatted_burst" if use_database_pipeline else "formatted lines joined in memory",
        ],
        "results": results,
    }

    summary_payload = {
        "started_at": started_at,
        "completed_at": completed_at,
        "input": str(input_path),
        "output": str(output_path),
        "benchmark_database": str(benchmark_db_path) if use_database_pipeline else None,
        "mode": "database_pipeline" if use_database_pipeline else "memory_only",
        "examples_processed": len(results),
        "examples_with_diffs": changed_count,
        "examples_without_diffs": len(results) - changed_count,
        "total_diffs": total_diffs,
        "average_diffs_per_example": round(total_diffs / len(results), 4) if results else 0,
        "genre_counts": dict(sorted(genre_counter.items())),
        "diffs_by_genre": dict(sorted(diff_by_genre.items())),
        "operation_counts": dict(sorted(operation_counter.items())),
        "embedding_status_counts": dict(sorted(embedding_counter.items())),
    }

    output_path.write_text(json.dumps(output_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run NotesFlare structure stabilisation benchmark.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input examples JSON path.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output formatted results JSON path.")
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY, help="Output summary JSON path.")
    parser.add_argument("--benchmark-db", type=Path, default=DEFAULT_BENCHMARK_DB, help="Isolated benchmark SQLite database path.")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N examples.")
    parser.add_argument("--no-embeddings", action="store_true", help="Skip optional embedding similarity stage.")
    parser.add_argument("--memory-only", action="store_true", help="Skip lineage/diff DB services and auto-accept in memory only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_benchmark(
        input_path=args.input,
        output_path=args.output,
        summary_path=args.summary,
        benchmark_db_path=args.benchmark_db,
        limit=args.limit,
        use_embeddings=not args.no_embeddings,
        use_database_pipeline=not args.memory_only,
    )

    print("\nNotesFlare StabilisationModule benchmark complete.")
    print(f"Mode: {summary['mode']}")
    print(f"Examples processed: {summary['examples_processed']}")
    print(f"Examples with diffs: {summary['examples_with_diffs']}")
    print(f"Total diffs: {summary['total_diffs']}")
    print(f"Results written to: {args.output}")
    print(f"Summary written to: {args.summary}")
    if summary.get("benchmark_database"):
        print(f"Benchmark DB written to: {summary['benchmark_database']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
