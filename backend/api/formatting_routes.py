# api/formatting_routes.py

from fastapi import APIRouter, HTTPException
from models.formatting_schemas import (
    FormatBurstRequest, FormatBurstResponse,
    BurstLineResponse, FormattingDiffResponse,
    DiffActionRequest, DiffActionResponse,
    BulkDiffActionRequest, BulkDiffActionResponse,
    FormattedBurstResponse,
)
from services import stream_service
from services.formatting import (
    lexer_service, parser_service, chunker_service,
    embedding_service, formatter_service, diff_service, lineage_service,
)
from datetime import datetime, timezone

formatting_router = APIRouter(prefix="/format")


@formatting_router.post("/burst", response_model=FormatBurstResponse)
def format_burst(body: FormatBurstRequest):
    """
    Run the formatting pipeline on a burst.

    Pipeline stages:
    1. Reconstruct raw text from burst_entries
    2. Lexical normalization
    3. Line splitting + stable ID assignment
    4. spaCy NLP parsing
    5. Chunking
    6. Embedding (semantic similarity)
    7. Rule-driven operation generation
    8. Diff storage (replaces pending diffs only)

    Returns all lines and diffs for the burst.
    """
    burst_id = body.burst_id

    # Stage 1: Reconstruct raw text
    raw_text = stream_service.reconstruct_burst(burst_id)
    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Burst is empty — nothing to format.")

    # Stage 2: Lexical normalization
    normalized = lexer_service.normalize_text(raw_text)
    raw_lines = lexer_service.split_into_lines(normalized)

    print(f"[format_burst] burst_id={burst_id} | chars={len(raw_text)} | lines={len(raw_lines)}")

    # Stage 3: Stable line IDs
    line_records = lineage_service.get_or_create_lines(burst_id, raw_lines)

    # Stage 4: NLP parsing
    line_signals = parser_service.parse_lines(raw_lines)

    # Stage 5: Chunking (used for embedding coherence)
    chunks = chunker_service.chunk_lines(raw_lines)

    # Stage 6: Embeddings + similarity (only if lines exist)
    similarity_scores = None
    if len(raw_lines) > 1:
        try:
            embeddings = embedding_service.embed_lines(raw_lines)
            similarity_scores = embedding_service.compute_similarity_sequence(embeddings)
        except Exception as e:
            # Embedding is optional — fall back to rule-only formatting
            print(f"[format_burst] Embedding skipped: {e}")

    # Stage 7: Generate formatting operations
    operations = formatter_service.generate_operations(line_signals, similarity_scores)

    print(f"[format_burst] burst_id={burst_id} | operations={len(operations)}")

    # Stage 8: Store diffs
    diffs = diff_service.store_diffs(burst_id, line_records, operations)

    return FormatBurstResponse(
        burst_id=burst_id,
        lines=[BurstLineResponse(**l) for l in line_records],
        diffs=[FormattingDiffResponse(**d) for d in diffs],
        diff_count=len(diffs),
        processed_at=datetime.now(timezone.utc).isoformat(),
    )


@formatting_router.post("/diff/accept", response_model=DiffActionResponse)
def accept_diff(body: DiffActionRequest):
    """Accept a single formatting diff."""
    try:
        result = diff_service.accept_diff(body.diff_id)
        return DiffActionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@formatting_router.post("/diff/reject", response_model=DiffActionResponse)
def reject_diff(body: DiffActionRequest):
    """Reject a single formatting diff."""
    try:
        result = diff_service.reject_diff(body.diff_id)
        return DiffActionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@formatting_router.post("/diff/accept-all", response_model=BulkDiffActionResponse)
def accept_all_diffs(body: BulkDiffActionRequest):
    """Accept all pending diffs for a burst."""
    results = diff_service.accept_all_pending(body.burst_id)
    return BulkDiffActionResponse(
        updated_count=len(results),
        diffs=[DiffActionResponse(**r) for r in results],
    )


@formatting_router.post("/diff/reject-all", response_model=BulkDiffActionResponse)
def reject_all_diffs(body: BulkDiffActionRequest):
    """Reject all pending diffs for a burst."""
    results = diff_service.reject_all_pending(body.burst_id)
    return BulkDiffActionResponse(
        updated_count=len(results),
        diffs=[DiffActionResponse(**r) for r in results],
    )


@formatting_router.get("/burst/{burst_id}", response_model=FormattedBurstResponse)
def get_formatted_burst(burst_id: int):
    """
    Return the formatted version of a burst.
    If no accepted diffs exist, returns raw text with has_formatting=False.
    """
    raw_text = stream_service.reconstruct_burst(burst_id)
    result = diff_service.get_formatted_burst(burst_id, raw_text)
    return FormattedBurstResponse(
        burst_id=result["burst_id"],
        has_formatting=result["has_formatting"],
        lines=[BurstLineResponse(**l) for l in result["lines"]],
        formatted_text=result["formatted_text"],
        raw_text=result["raw_text"],
    )
