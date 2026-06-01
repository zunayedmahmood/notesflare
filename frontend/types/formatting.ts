// types/formatting.ts

/**
 * All TypeScript types for the V1.2 formatting pipeline.
 * These mirror the Pydantic models in backend/models/formatting_schemas.py.
 * Keep these in sync with backend changes.
 */

// ─── Line Status ─────────────────────────────────────────────────────────────

export type LineStatus = "untouched" | "pending" | "accepted" | "rejected";

// ─── Diff Operation Types ─────────────────────────────────────────────────────

export type DiffOperationType =
  | "insert_paragraph_break"
  | "insert_line_break"
  | "format_as_list_item"
  | "format_as_heading"
  | "format_as_quote"
  | "normalize_spacing";

// ─── A single line in a burst with its formatting state ──────────────────────

export interface BurstLine {
  line_id: string;           // Stable UUID from backend
  line_index: number;        // 0-based position in burst
  raw_line: string;          // Original text — NEVER changes
  formatted_line: string;    // Backend's formatted proposal (may equal raw_line)
  status: LineStatus;
  checksum: string;          // SHA256 of raw_line — used for integrity checks
}

// ─── A single formatting diff ─────────────────────────────────────────────────

export interface FormattingDiff {
  diff_id: string;
  line_id: string;
  operation: DiffOperationType;
  status: "pending" | "accepted" | "rejected";
  raw_before: string;        // What the line looked like before
  formatted_after: string;   // What the line will look like if accepted
}

// ─── Format request response ─────────────────────────────────────────────────

export interface FormatBurstResponse {
  burst_id: number;
  lines: BurstLine[];
  diffs: FormattingDiff[];
  diff_count: number;
  processed_at: string;      // ISO timestamp
}

// ─── Accept/Reject response ──────────────────────────────────────────────────

export interface DiffActionResponse {
  diff_id: string;
  status: "accepted" | "rejected";
  line_id: string;
  updated_formatted_line: string;
}

// ─── Bulk action response ────────────────────────────────────────────────────

export interface BulkDiffActionResponse {
  updated_count: number;
  diffs: DiffActionResponse[];
}

// ─── Formatted burst fetch ────────────────────────────────────────────────────

export interface FormattedBurstResponse {
  burst_id: number;
  has_formatting: boolean;
  lines: BurstLine[];
  formatted_text: string;    // Full text with all accepted changes applied
  raw_text: string;          // Full original text
}

// ─── Frontend-only diff review state ─────────────────────────────────────────

export interface DiffReviewState {
  burstId: number | null;
  isLoading: boolean;
  isOpen: boolean;
  diffs: FormattingDiff[];
  lines: BurstLine[];
  error: string | null;
  processedAt: string | null;
}
