# NotesFlare StabilisationModule — Accepted-Only Usage Learning

This module turns NotesFlare's deterministic formatter into a generic old-data study loop for better future diff suggestions.

## Principle

Accepted diffs are learning evidence.

Rejected diffs are audit evidence only.

The system deliberately does **not** learn from rejection, because a user may reject a good suggestion by mistake. Rejections are still stored in `stabilisation_usage_events`, but they never update the hidden stabilisation profile.

## Runtime integration

The existing NLP pipeline remains the same:

```text
raw Burst
→ lexer_service
→ parser_service
→ chunker_service
→ optional embedding_service
→ formatter_service.generate_operations
→ diff_service.store_diffs
→ user accepts/rejects
```

The new integration happens after review:

```text
diff_service.accept_diff
→ usage_learning_service.record_diff_decision(decision="accepted")
→ usage_learning_service.update_profile_from_accepted_diff
→ reset_stabilisation_profile_cache
→ next format run sees updated profile
```

For rejection:

```text
diff_service.reject_diff
→ usage_learning_service.record_diff_decision(decision="rejected")
→ no profile update
```

## New DB tables

```text
stabilisation_usage_events
stabilisation_profile_events
```

These tables are created by `schema.sql` and also guarded in `usage_learning_service.ensure_usage_tables()`.

## What accepted diffs can teach

Accepted diffs can add evidence for:

- continuous list item phrases
- continuous list headers
- short tokens such as `np`, `asap`, `rn`, `api`, `db`, `n3`
- protected mixed-case terms
- compound terms used for safer splitting
- formatting preferences such as listing/line-break aggressiveness

## Progressive benchmark

Generated dataset:

```text
StabilisationModule/examples_1000_progressive_usage.json
```

Run:

```bash
./StabilisationModule/START_HERE.sh progressive
```

Outputs:

```text
StabilisationModule/outputs/formatted_results_progressive_usage.json
StabilisationModule/outputs/benchmark_summary_progressive_usage.json
StabilisationModule/outputs/stabilisation_benchmark_progressive_usage.db
StabilisationModule/outputs/stabilisation_profile.progressive.json
```

Latest local sandbox verification, without embeddings:

```json
{
  "examples_processed": 1000,
  "examples_with_diffs": 975,
  "total_diffs": 975,
  "decision_counts": {"accepted": 925, "rejected": 50},
  "usage_events": 975,
  "learned_events": 925
}
```

The difference between usage events and learned events proves the accepted-only rule is active.
