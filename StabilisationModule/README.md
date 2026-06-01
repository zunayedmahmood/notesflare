# NotesFlare StabilisationModule

Developer-only benchmark harness for deterministic structure stabilisation.

This module does **not** change the NotesFlare product flow. It is a local benchmark area for testing how the existing V1.2 NLP formatting pipeline handles many raw thought examples.

## Files

- `examples_1000.json` — 1,000 small raw NotesFlare-style paragraphs across research, brainstorming, class notes, meeting notes, developer notes, reading notes, lab notes, personal thinking, architecture notes, and language-learning notes.
- `run_stabilisation_benchmark.py` — single execution script that runs the existing backend NLP pipeline over the dataset.
- `START_HERE.sh` — Unix/macOS launcher.
- `START_HERE.bat` — Windows launcher.
- `outputs/` — generated benchmark outputs.

## What the runner does

For every example:

1. Loads `raw_text` from `examples_1000.json`.
2. Runs existing backend services:
   - `lexer_service.normalize_text`
   - `lexer_service.split_into_lines`
   - `parser_service.parse_lines`
   - `chunker_service.chunk_lines`
   - `embedding_service.embed_lines` and `compute_similarity_sequence` when available
   - `formatter_service.generate_operations`
3. Creates a dedicated benchmark SQLite database at `outputs/stabilisation_benchmark.db`.
4. Uses `lineage_service` and `diff_service` to store pending diffs.
5. Auto-accepts pending diffs inside the benchmark database only.
6. Stores the formatted text mapped to the original example ID.
7. Writes output JSON to `outputs/formatted_results.json`.
8. Writes a compact summary to `outputs/benchmark_summary.json`.

## Run

From project root:

```bash
python StabilisationModule/run_stabilisation_benchmark.py
```

Or:

```bash
./StabilisationModule/START_HERE.sh
```

Windows:

```bat
StabilisationModule\START_HERE.bat
```

## Optional flags

```bash
python StabilisationModule/run_stabilisation_benchmark.py --limit 50
python StabilisationModule/run_stabilisation_benchmark.py --no-embeddings
python StabilisationModule/run_stabilisation_benchmark.py --memory-only
python StabilisationModule/run_stabilisation_benchmark.py --input StabilisationModule/examples_1000.json --output StabilisationModule/outputs/my_results.json
```

## Output shape

Each item in `formatted_results.json` looks like:

```json
{
  "id": "nf-stab-0001",
  "genre": "research_notes",
  "raw_text": "...",
  "formatted_text": "...",
  "diff_count": 2,
  "operations": [
    {
      "line_index": 0,
      "operation": "insert_line_break",
      "raw_before": "...",
      "formatted_after": "..."
    }
  ],
  "auto_accept_status": "accepted_in_benchmark_only"
}
```

## Important

This is not an import/export feature and not a user-facing NotesFlare feature. It is a developer evaluation tool for measuring formatter behavior against a broad raw-note dataset. The default database mode uses an isolated benchmark DB and does not touch `storage/notesflare.db`.
