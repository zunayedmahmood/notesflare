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

## Dynamic stabilisation profile

The formatter now reads a hidden local profile before generating structural diffs.
Load order:

1. `NOTESFLARE_STABILISATION_PROFILE=/path/to/profile.json`
2. `storage/stabilisation_profile.json`
3. `StabilisationModule/stabilisation_profile.default.json`
4. built-in defaults

The profile can define:

- `short_tokens`: raw user shorthand such as `np`, `asap`, `rn`, `API`, `MVP`
- `protected_terms`: product/domain words that should be treated as sacred tokens
- `continuous_list_item_phrases`: phrases used to recognize compact one-line list streams
- `compound_terms`: word pairs that should not be split internally
- `formatting_preferences.paragraph_density`: `longer`, `balanced`, `shorter`
- `formatting_preferences.line_break_aggressiveness`: `conservative`, `balanced`, `aggressive`
- `formatting_preferences.listing_aggressiveness`: `conservative`, `moderate`, `aggressive`

Example:

```bash
python StabilisationModule/run_stabilisation_benchmark.py \
  --input StabilisationModule/examples_1000_continuous_stream.json \
  --profile StabilisationModule/stabilisation_profile.user.example.json
```

## Continuous-stream benchmark

A second benchmark dataset now exists:

```text
StabilisationModule/examples_1000_continuous_stream.json
```

It focuses on raw one-line note streams that should become structure, for example:

```text
need raw note fidelity query drift and chunking
```

Expected structural output:

```text
need:
- raw note fidelity
- query drift
- chunking
```

Run it with:

```bash
npm run stabilisation:continuous
```

or without embeddings:

```bash
npm run stabilisation:continuous:no-embeddings
```

## Progressive accepted-only usage learning

This module now supports a generic "study old data for better diff suggestions" loop.

The important rule is:

> Rejected diffs are tracked for audit, but they are never used to update the stabilisation profile.

This prevents accidental rejection from poisoning future formatting behaviour.

### New progressive dataset

```text
StabilisationModule/examples_1000_progressive_usage.json
```

The dataset contains 1,000 progressive one-stream cases with short tokens, custom user/domain keywords, and simulated accept/reject decisions. It is designed to show whether accepted diffs gradually improve the hidden profile.

### Run progressive benchmark

```bash
./StabilisationModule/START_HERE.sh progressive
```

Windows:

```bat
StabilisationModule\START_HERE.bat progressive
```

Or with npm:

```bash
npm run stabilisation:progressive
```

Without embeddings:

```bash
npm run stabilisation:progressive:no-embeddings
```

### Run all benchmark sets

```bash
./StabilisationModule/START_HERE.sh all
```

This runs:

1. `examples_1000.json`
2. `examples_1000_continuous_stream.json`
3. `examples_1000_progressive_usage.json`

### Progressive outputs

```text
StabilisationModule/outputs/formatted_results_progressive_usage.json
StabilisationModule/outputs/benchmark_summary_progressive_usage.json
StabilisationModule/outputs/stabilisation_benchmark_progressive_usage.db
StabilisationModule/outputs/stabilisation_profile.progressive.json
```

### Usage-tracking tables

The existing diff pipeline now records accept/reject usage events in the benchmark/app DB:

```text
stabilisation_usage_events
stabilisation_profile_events
```

Accepted diffs update the file-backed stabilisation profile through:

```text
backend/services/formatting/usage_learning_service.py
```

Rejected diffs call the same tracker, but the tracker does not learn from them.
