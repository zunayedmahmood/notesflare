# NotesFlare NLP Pipeline Review & Robustness Plan

Generated after reviewing the user-run benchmark outputs from `benchmark_summary.json`, `formatted_results.json`, and `stabilisation_benchmark.db`.

## 1. What the benchmark showed before this patch

User-run benchmark summary:

- Examples processed: 1000
- Examples with diffs: 916
- Examples without diffs: 84
- Total diffs: 1192
- Average diffs per example: 1.192
- Embedding status: 1000 ok

Operation distribution before patch:

```json
{
  "format_as_heading": 299,
  "insert_line_break": 659,
  "insert_paragraph_break": 234
}
```

The high-level signal was good: the pipeline was running end-to-end and embeddings were available. The quality signal was mixed: the pipeline was producing many suggestions, but some suggestions were structurally wrong.

## 2. Major problems found

### Problem A — list blocks were not understood

Example before:

```text
need:
raw note fidelity
query drift
chunking
```

Old output:

```text
need:
Raw Note Fidelity
Query Drift

chunking
```

This was wrong because the pipeline treated short list items as headings or paragraph breaks. It should recognize `need:` as a list header and convert following short lines into list items.

### Problem B — heading formatting changed the user's wording

Old heading behavior title-cased the line:

```text
dataset bias thoughts
```

became:

```text
Dataset Bias Thoughts
```

This violates the NotesFlare/MetaMorph principle that tokens are sacred. Structure may change, but the user's words and casing should not be rewritten.

### Problem C — quote-like notes were ignored

Examples like:

```text
quote from supervisor says structure precedes retrieval
```

were usually left as normal text. The pipeline needed a deterministic quote detector for common raw-note wording.

### Problem D — embedding-based paragraph breaks were too eager

`insert_paragraph_break` appeared 234 times. Some were useful, but many were caused by low semantic similarity between short lines that were actually list-like fragments. Embeddings should be a supporting signal, not the only reason to break structure.

### Problem E — compound research terms were sometimes split

Example risk:

```text
paper structure weakens boundary quality ablation study depends on false positives
```

The old subject+verb splitting logic could split between `ablation` and `study`, which is structurally wrong because `ablation study` is one compound term.

## 3. What changed in this patch

### Change 1 — context-aware implicit list detection

The formatter now detects list headers such as:

```text
need:
ideas:
questions:
steps:
requirements:
```

Then it treats following short non-empty lines as implicit list items.

New output:

```text
need:
- raw note fidelity
- query drift
- chunking
```

### Change 2 — heading formatting is structural, not stylistic

The formatter no longer title-cases headings. Instead, it adds a heading marker while preserving the exact user wording:

```text
## dataset bias thoughts
```

This gives the benchmark visible structure without rewriting casing.

### Change 3 — quote detection added

Common note patterns now become quote blocks:

```text
quote from supervisor says structure precedes retrieval
```

becomes:

```text
> quote from supervisor says structure precedes retrieval
```

### Change 4 — paragraph breaks are more conservative

The embedding threshold was tightened and constrained. Embedding distance only triggers a paragraph break when both neighboring lines are substantial enough. This reduces random breaks between short fragments.

### Change 5 — compound term guard added

The formatter now avoids subject+verb splits inside common compound terms such as:

- ablation study
- semantic search
- paper structure
- method section
- dataset bias
- literature review
- citation mapping
- model comparison
- embedding cache

## 4. Benchmark after patch in this environment

This environment did not have `sentence-transformers`, so the after-patch benchmark was run with `--no-embeddings`. Your local machine can run it with embeddings enabled.

After-patch summary:

- Examples processed: 1000
- Examples with diffs: 815
- Examples without diffs: 185
- Total diffs: 1086
- Embedding status: skipped

Operation distribution after patch:

```json
{
  "format_as_heading": 107,
  "format_as_list_item": 234,
  "format_as_quote": 34,
  "insert_line_break": 635,
  "insert_paragraph_break": 76
}
```

This is healthier than before because:

- heading suggestions dropped sharply from 299 to 107
- list suggestions now exist and correctly cover list-seed examples
- quote suggestions now exist
- paragraph breaks dropped from 234 to 76, reducing noise
- internal semantic splitting remains active

## 5. Current pipeline after patch

```text
raw Burst
↓
stream_service.reconstruct_burst
↓
lexer_service.normalize_text
↓
lexer_service.split_into_lines
↓
lineage_service.get_or_create_lines
↓
parser_service.parse_lines
↓
chunker_service.chunk_lines
↓
embedding_service.embed_lines optional
↓
embedding_service.compute_similarity_sequence optional
↓
formatter_service.generate_operations
↓
diff_service.store_diffs
↓
user review / benchmark auto-accept
↓
diff_service.get_formatted_burst
```

The biggest change is inside `formatter_service.generate_operations`, which now has contextual awareness of neighboring lines.

## 6. Next robustness plan

### Phase 1 — Deterministic stabilisation hardening

Add more high-quality golden examples for:

- list blocks
- quote blocks
- heading blocks
- short thought fragments
- compound technical terms
- punctuated paragraph dumps
- unpunctuated raw thought dumps

Success target: fewer false headings, more correct list/quote recognition.

### Phase 2 — Benchmark scoring layer

The benchmark should not only count diffs. It should score the type of diff against tags.

Examples:

- `list_seed` should usually produce `format_as_list_item`
- `topic_marker` should usually produce `insert_line_break`
- quote-like raw lines should produce `format_as_quote`
- protected-token examples should never alter protected casing

### Phase 3 — Intensity profiles

Add formatter modes:

- `minimal`: only obvious list/quote/topic changes
- `balanced`: default NotesFlare behavior
- `strong`: more aggressive paragraph segmentation

This prevents one formatter personality from trying to satisfy every user.

### Phase 4 — Reason metadata

Each operation should eventually include:

```json
{
  "reason": "implicit_list_after_colon_header",
  "confidence": 0.91
}
```

This will make the diff panel much easier to debug and will create better future training data for MetaMorph.

### Phase 5 — Accepted/rejected feedback dataset

Accepted and rejected diffs should become training examples:

- accepted diff = positive structural label
- rejected diff = negative structural label

This is the bridge from deterministic V1.2 stabilisation to the later MetaMorph structural transformer.

## 7. What should not be added yet

Do not add generative rewriting.
Do not add grammar correction.
Do not add summarization.
Do not add cloud AI.
Do not let the model produce replacement prose.

NotesFlare's structural intelligence should reveal the structure already present in the user's thought, not replace the user's thought.
