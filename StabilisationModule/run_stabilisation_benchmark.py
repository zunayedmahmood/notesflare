#!/usr/bin/env python3
"""
NotesFlare StabilisationModule benchmark runner.

Developer-only harness for testing deterministic structure stabilisation.
It uses the existing backend V1.2 NLP/formatting pipeline and writes formatted
outputs mapped to the original dataset IDs.

Modes:
- standard benchmark: auto-accepts all generated diffs in an isolated DB
- progressive benchmark: simulates accept/reject decisions, tracks every usage
  event, and updates a temporary user profile ONLY from accepted diffs
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
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
from services.formatting.stabilisation_profile_service import (  # noqa: E402
    MODULE_DEFAULT_PROFILE,
    reset_profile_cache,
)
from services.formatting.usage_learning_service import ensure_usage_tables, study_accepted_usage  # noqa: E402

DEFAULT_INPUT = MODULE_DIR / "examples_1000.json"
DEFAULT_OUTPUT = MODULE_DIR / "outputs" / "formatted_results.json"
DEFAULT_SUMMARY = MODULE_DIR / "outputs" / "benchmark_summary.json"
DEFAULT_BENCHMARK_DB = MODULE_DIR / "outputs" / "stabilisation_benchmark.db"
DEFAULT_PROGRESSIVE_PROFILE = MODULE_DIR / "outputs" / "stabilisation_profile.progressive.json"


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


def prepare_progressive_profile(path: Path, reset: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if reset or not path.exists():
        if MODULE_DEFAULT_PROFILE.exists():
            shutil.copyfile(MODULE_DEFAULT_PROFILE, path)
        else:
            path.write_text(json.dumps({"version": 1, "profile_name": "progressive-benchmark"}, indent=2), encoding="utf-8")
    os.environ["NOTESFLARE_STABILISATION_PROFILE"] = str(path)
    reset_profile_cache()


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
    db_module._connection = conn  # type: ignore[attr-defined]
    ensure_usage_tables()
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
    except Exception as exc:  # noqa: BLE001
        return None, "fallback_rule_only", f"{exc.__class__.__name__}: {exc}"


def run_pipeline_no_db(raw_text: str, use_embeddings: bool = True) -> dict[str, Any]:
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
        "rejected_diffs": [],
        "auto_accept_status": "accepted_in_memory_only",
    }


def should_accept_diff(diff: dict[str, Any], example: dict[str, Any], simulate_decisions: bool) -> bool:
    if not simulate_decisions:
        return True
    simulation = example.get("simulation", {}) if isinstance(example.get("simulation", {}), dict) else {}
    operation = str(diff.get("operation", ""))
    formatted = str(diff.get("formatted_after", ""))
    raw = str(diff.get("raw_before", ""))
    haystack = f"{raw}\n{formatted}".lower()

    for text in simulation.get("reject_if_contains", []):
        if str(text).lower() in haystack:
            return False
    for text in simulation.get("accept_if_contains", []):
        if str(text).lower() in haystack:
            return True
    if operation in set(simulation.get("reject_operations", [])):
        return False
    if operation in set(simulation.get("accept_operations", [])):
        return True
    return simulation.get("default_decision", "accept") == "accept"


def run_pipeline_with_benchmark_db(
    conn: sqlite3.Connection,
    flareon_id: int,
    example: dict[str, Any],
    use_embeddings: bool = True,
    simulate_decisions: bool = False,
) -> dict[str, Any]:
    """Run the same line/diff database flow used by the NotesFlare backend."""
    raw_text = example["raw_text"]
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

    accepted_diffs: list[dict[str, Any]] = []
    rejected_diffs: list[dict[str, Any]] = []
    for diff in stored_diffs:
        if should_accept_diff(diff, example, simulate_decisions):
            accepted_diffs.append(diff_service.accept_diff(diff["diff_id"]))
        else:
            rejected_diffs.append(diff_service.reject_diff(diff["diff_id"]))

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
        "rejected_diffs": rejected_diffs,
        "auto_accept_status": "simulated_accept_reject" if simulate_decisions else "accepted_in_benchmark_database",
    }


def profile_snapshot(profile_path: Path | None) -> dict[str, Any] | None:
    if profile_path is None or not profile_path.exists():
        return None
    data = json.loads(profile_path.read_text(encoding="utf-8"))
    learned = data.get("learned_from_accepts", {}) if isinstance(data, dict) else {}
    return {
        "profile_path": str(profile_path),
        "preferences": data.get("formatting_preferences", {}),
        "short_token_count": len(data.get("short_tokens", [])),
        "protected_term_count": len(data.get("protected_terms", [])),
        "continuous_header_count": len(data.get("continuous_list_headers", [])),
        "continuous_item_phrase_count": len(data.get("continuous_list_item_phrases", [])),
        "learned_from_accepts": learned,
    }


def usage_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT decision, operation, COUNT(*) as count, SUM(learned) as learned_count
        FROM stabilisation_usage_events
        GROUP BY decision, operation
        ORDER BY decision, operation
        """
    ).fetchall()
    by_decision: dict[str, dict[str, int]] = defaultdict(dict)
    learned_total = 0
    for row in rows:
        by_decision[row["decision"]][row["operation"]] = int(row["count"])
        learned_total += int(row["learned_count"] or 0)
    total = conn.execute("SELECT COUNT(*) AS c FROM stabilisation_usage_events").fetchone()["c"]
    return {"total_usage_events": int(total), "learned_events": learned_total, "by_decision": dict(by_decision)}


def run_benchmark(
    input_path: Path,
    output_path: Path,
    summary_path: Path,
    benchmark_db_path: Path,
    limit: int | None = None,
    use_embeddings: bool = True,
    use_database_pipeline: bool = True,
    profile_path: Path | None = None,
    simulate_decisions: bool = False,
    reset_profile: bool = False,
    study_old_data: bool = False,
) -> dict[str, Any]:
    progressive_profile = profile_path if simulate_decisions else None
    if profile_path is not None:
        if simulate_decisions:
            prepare_progressive_profile(profile_path, reset_profile)
        else:
            os.environ["NOTESFLARE_STABILISATION_PROFILE"] = str(profile_path)
            reset_profile_cache()

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
    tag_counter: Counter[str] = Counter()
    diff_by_tag: defaultdict[str, int] = defaultdict(int)
    changed_by_tag: Counter[str] = Counter()
    operation_by_tag: defaultdict[str, Counter[str]] = defaultdict(Counter)
    diff_distribution: Counter[str] = Counter()
    decision_counter: Counter[str] = Counter()
    snapshots: list[dict[str, Any]] = []

    for idx, example in enumerate(examples, start=1):
        if use_database_pipeline:
            assert conn is not None and flareon_id is not None
            pipeline_result = run_pipeline_with_benchmark_db(
                conn, flareon_id, example, use_embeddings, simulate_decisions
            )
        else:
            pipeline_result = run_pipeline_no_db(example["raw_text"], use_embeddings)

        genre = example.get("genre", "unknown")
        genre_counter[genre] += 1
        diff_by_genre[genre] += pipeline_result["diff_count"]
        embedding_counter[pipeline_result["embedding_status"]] += 1
        diff_distribution[str(pipeline_result["diff_count"])] += 1
        decision_counter["accepted"] += len(pipeline_result.get("accepted_diffs", []))
        decision_counter["rejected"] += len(pipeline_result.get("rejected_diffs", []))

        tags = example.get("tags", [])
        for tag in tags:
            tag_counter[tag] += 1
            diff_by_tag[tag] += pipeline_result["diff_count"]
            if pipeline_result["diff_count"] > 0:
                changed_by_tag[tag] += 1

        for op in pipeline_result["operations"]:
            op_name = str(op.get("operation", "unknown"))
            operation_counter[op_name] += 1
            for tag in tags:
                operation_by_tag[tag][op_name] += 1

        result_item = {
            "id": example["id"],
            "genre": genre,
            "tags": example.get("tags", []),
            "phase": example.get("phase"),
            "simulation": example.get("simulation"),
            "benchmark_burst_id": pipeline_result["burst_id"],
            "raw_text": example["raw_text"],
            "normalized_text": pipeline_result["normalized_text"],
            "formatted_text": pipeline_result["formatted_text"],
            "expected_profile_effect": example.get("expected_profile_effect"),
            "diff_count": pipeline_result["diff_count"],
            "operations": pipeline_result["operations"],
            "stored_diffs": pipeline_result["stored_diffs"],
            "accepted_diffs": pipeline_result["accepted_diffs"],
            "rejected_diffs": pipeline_result.get("rejected_diffs", []),
            "line_count": pipeline_result["line_count"],
            "chunk_count": pipeline_result["chunk_count"],
            "embedding_status": pipeline_result["embedding_status"],
            "embedding_error": pipeline_result["embedding_error"],
            "auto_accept_status": pipeline_result["auto_accept_status"],
        }
        results.append(result_item)

        if progressive_profile and (idx % 100 == 0 or idx == len(examples)):
            snap = profile_snapshot(progressive_profile)
            if snap:
                snap["after_examples"] = idx
                snapshots.append(snap)

        if idx % 100 == 0 or idx == len(examples):
            print(f"Processed {idx}/{len(examples)} examples...")

    if study_old_data and conn is not None:
        study_summary = study_accepted_usage(progressive_profile)
    else:
        study_summary = None

    completed_at = datetime.now(timezone.utc).isoformat()
    changed_count = sum(1 for item in results if item["diff_count"] > 0)
    total_diffs = sum(item["diff_count"] for item in results)
    usage = usage_summary(conn) if conn is not None else None

    output_payload = {
        "dataset": str(input_path.relative_to(PROJECT_ROOT) if input_path.is_relative_to(PROJECT_ROOT) else input_path),
        "processed_at": completed_at,
        "count": len(results),
        "auto_accept_mode": "simulated_accept_reject" if simulate_decisions else ("benchmark_database" if use_database_pipeline else "memory_only"),
        "benchmark_database": str(benchmark_db_path) if use_database_pipeline else None,
        "progressive_profile": str(progressive_profile) if progressive_profile else None,
        "profile_snapshots": snapshots,
        "pipeline": [
            "stream_service.reconstruct_burst" if use_database_pipeline else "raw_text from examples JSON",
            "lexer_service.normalize_text",
            "lexer_service.split_into_lines",
            "lineage_service.get_or_create_lines" if use_database_pipeline else "lineage skipped in memory-only mode",
            "parser_service.parse_lines",
            "chunker_service.chunk_lines",
            "embedding_service.embed_lines optional",
            "embedding_service.compute_similarity_sequence optional",
            "formatter_service.generate_operations(profile-aware)",
            "diff_service.store_diffs",
            "diff_service.accept_diff/reject_diff simulated" if simulate_decisions else "diff_service.accept_all_pending equivalent",
            "usage_learning_service.record_diff_decision",
            "usage_learning_service.update_profile_from_accepted_diff accepted-only",
            "diff_service.get_formatted_burst",
        ],
        "results": results,
    }

    summary_payload = {
        "started_at": started_at,
        "completed_at": completed_at,
        "input": str(input_path),
        "output": str(output_path),
        "benchmark_database": str(benchmark_db_path) if use_database_pipeline else None,
        "mode": "progressive_usage_learning" if simulate_decisions else ("database_pipeline" if use_database_pipeline else "memory_only"),
        "examples_processed": len(results),
        "examples_with_diffs": changed_count,
        "examples_without_diffs": len(results) - changed_count,
        "total_diffs": total_diffs,
        "average_diffs_per_example": round(total_diffs / len(results), 4) if results else 0,
        "decision_counts": dict(sorted(decision_counter.items())),
        "genre_counts": dict(sorted(genre_counter.items())),
        "diffs_by_genre": dict(sorted(diff_by_genre.items())),
        "operation_counts": dict(sorted(operation_counter.items())),
        "diff_count_distribution": dict(sorted(diff_distribution.items(), key=lambda item: int(item[0]))),
        "tag_counts": dict(sorted(tag_counter.items())),
        "diffs_by_tag": dict(sorted(diff_by_tag.items())),
        "changed_examples_by_tag": dict(sorted(changed_by_tag.items())),
        "operation_counts_by_tag": {
            tag: dict(sorted(counter.items()))
            for tag, counter in sorted(operation_by_tag.items())
        },
        "embedding_status_counts": dict(sorted(embedding_counter.items())),
        "stabilisation_profile": str(profile_path) if profile_path is not None else "default",
        "profile_snapshots": snapshots,
        "usage_summary": usage,
        "study_old_data_summary": study_summary,
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
    parser.add_argument("--profile", type=Path, default=None, help="Optional stabilisation profile JSON path.")
    parser.add_argument("--simulate-decisions", action="store_true", help="Use per-example accept/reject simulation and usage learning.")
    parser.add_argument("--progressive-profile", type=Path, default=DEFAULT_PROGRESSIVE_PROFILE, help="Writable profile used by --simulate-decisions.")
    parser.add_argument("--reset-progressive-profile", action="store_true", help="Reset progressive profile from default before running.")
    parser.add_argument("--study-old-data", action="store_true", help="After the run, rebuild profile from accepted usage events only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profile_path = args.profile
    if args.simulate_decisions and profile_path is None:
        profile_path = args.progressive_profile

    summary = run_benchmark(
        input_path=args.input,
        output_path=args.output,
        summary_path=args.summary,
        benchmark_db_path=args.benchmark_db,
        limit=args.limit,
        use_embeddings=not args.no_embeddings,
        use_database_pipeline=not args.memory_only,
        profile_path=profile_path,
        simulate_decisions=args.simulate_decisions,
        reset_profile=args.reset_progressive_profile,
        study_old_data=args.study_old_data,
    )

    print("\nNotesFlare StabilisationModule benchmark complete.")
    print(f"Mode: {summary['mode']}")
    print(f"Examples processed: {summary['examples_processed']}")
    print(f"Examples with diffs: {summary['examples_with_diffs']}")
    print(f"Total diffs: {summary['total_diffs']}")
    if summary.get("decision_counts"):
        print(f"Decisions: {summary['decision_counts']}")
    print(f"Results written to: {args.output}")
    print(f"Summary written to: {args.summary}")
    if summary.get("benchmark_database"):
        print(f"Benchmark DB written to: {summary['benchmark_database']}")
    if summary.get("stabilisation_profile"):
        print(f"Profile: {summary['stabilisation_profile']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
