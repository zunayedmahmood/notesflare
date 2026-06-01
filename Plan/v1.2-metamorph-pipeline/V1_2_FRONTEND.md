# NotesFlare V1.2 — Frontend Implementation Guide

> **AI Instruction File: V1.2 Frontend Changes**
> This file drives all Next.js/React/TypeScript changes required for V1.2 — the Formatting Pipeline.
> Read `01_BRAND_AND_ARCHITECTURE.md`, `03_FRONTEND.md`, `V1_1_FRONTEND.md`, and `V1_2_BACKEND.md` before this file.
> Every decision here supersedes the corresponding section in `V1_1_FRONTEND.md` where they conflict.
> Do not implement anything not described here. Do not skip verification steps.

---

## 0. PRE-IMPLEMENTATION CHECKLIST

Before writing any code, verify:

- [ ] You have read `01_BRAND_AND_ARCHITECTURE.md` (brand tokens, vocabulary, philosophy)
- [ ] You have read `03_FRONTEND.md` (base component structure)
- [ ] You have read `V1_1_FRONTEND.md` (stream page, archive page, component tree as of V1.1)
- [ ] You have read `V1_2_BACKEND.md` (new formatting endpoints and response shapes)
- [ ] The V1.1 frontend renders without TypeScript errors (`next dev` starts clean)
- [ ] The V1.2 backend is running and `POST /api/format/burst` returns a valid diff response

If any of the above is false, do NOT proceed. Fix the baseline first.

**Scope of changes in this file:**

1. New `lib/api.ts` additions — formatting endpoints (additive only)
2. New hook: `useFormatter.ts` — manages format request lifecycle and diff state
3. New hook: `useDiffReview.ts` — manages per-line accept/reject state machine
4. New component: `FormatButton.tsx` — triggers format request from stream/archive page
5. New component: `DiffReviewPanel.tsx` — side panel showing pending diffs with accept/reject UI
6. New component: `DiffLineItem.tsx` — single diff row with inline accept/reject controls
7. New component: `FormattedPreview.tsx` — renders the formatted version of a burst
8. New component: `LineStatusBadge.tsx` — visual indicator for line status (pending/accepted/rejected)
9. Updated component: `StreamShell.tsx` — integrates FormatButton and DiffReviewPanel
10. Updated component: `BurstTimeline.tsx` (archive) — shows formatted view toggle
11. Updated `app/flareon/[id]/page.tsx` — archive page gains formatting access
12. New types file: `types/formatting.ts` — all formatting-related TypeScript types
13. Updated `styles/globals.css` — new CSS variables for diff colors and panel styles
14. Verification checklist and performance targets

---

## 1. WHAT CHANGES AND WHY

### V1.1 Model
The V1.1 stream page had a single-line input and an archive page showing raw burst content. No processing of the text occurred.

### V1.2 Model
V1.2 introduces the **Formatting Pipeline** as a UI layer. The user can request formatting of the current burst's content. The system returns a set of structural diffs. The user reviews diffs line-by-line and accepts or rejects each one. The original text is NEVER mutated. The formatted version is stored separately.

### Core UI Philosophy for Formatting
- **Non-interrupting**: Formatting is always triggered manually. It never interrupts writing.
- **Non-destructive**: The original raw stream is always visible and accessible.
- **Reversible**: Every diff can be individually accepted or rejected, including after the fact.
- **Invisible when unused**: If the user never clicks Format, the UI looks identical to V1.1.

### What does NOT change
- `styles/globals.css` core writing tokens — unchanged
- `components/stream/StreamInput.tsx` — unchanged
- `hooks/useStreamBuffer.ts` — unchanged
- `hooks/useAutosave.ts` — unchanged
- `hooks/useSession.ts` — unchanged
- `lib/api.ts` V1 and V1.1 functions — all preserved, additions only
- Archive page routing — unchanged

---

## 2. UPDATED DIRECTORY STRUCTURE

Only new files are marked NEW. Everything else is from V1.1 and unchanged unless noted.

```
frontend/
├── app/
│   ├── layout.tsx                          # Unchanged
│   ├── page.tsx                            # MODIFIED — integrates FormatButton
│   └── flareon/
│       └── [id]/
│           └── page.tsx                    # MODIFIED — integrates formatting panel
│
├── components/
│   ├── sidebar/
│   │   └── Sidebar.tsx                     # Unchanged
│   │
│   ├── stream/
│   │   ├── StreamInput.tsx                 # Unchanged
│   │   ├── StreamShell.tsx                 # MODIFIED — adds FormatButton slot
│   │   ├── NavControls.tsx                 # Unchanged
│   │   └── SessionIndicator.tsx            # Unchanged
│   │
│   ├── archive/
│   │   ├── BurstBlock.tsx                  # Unchanged
│   │   ├── BurstDivider.tsx                # Unchanged
│   │   └── BurstTimeline.tsx               # MODIFIED — adds formatted view toggle
│   │
│   ├── formatting/                         # NEW directory
│   │   ├── FormatButton.tsx                # NEW
│   │   ├── DiffReviewPanel.tsx             # NEW
│   │   ├── DiffLineItem.tsx                # NEW
│   │   ├── FormattedPreview.tsx            # NEW
│   │   └── LineStatusBadge.tsx             # NEW
│   │
│   └── common/
│       ├── LoadingScreen.tsx               # Unchanged
│       └── EmptyState.tsx                  # Unchanged
│
├── hooks/
│   ├── useAutosave.ts                      # Unchanged
│   ├── useSession.ts                       # Unchanged
│   ├── useStreamBuffer.ts                  # Unchanged
│   ├── useFormatter.ts                     # NEW
│   └── useDiffReview.ts                    # NEW
│
├── lib/
│   └── api.ts                              # MODIFIED — new formatting endpoints added
│
├── types/
│   └── formatting.ts                       # NEW — all formatting TypeScript types
│
└── styles/
    └── globals.css                         # MODIFIED — new diff color variables
```

---

## 3. NEW TYPES FILE: `types/formatting.ts`

Create this file first. All other formatting modules import from here.

```typescript
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
```

---

## 4. UPDATED `lib/api.ts`

**Append** the following to the existing `api.ts`. Do not remove any existing functions.

```typescript
// ─── V1.2 Imports (add to existing imports at top of file) ───────────────────
// Add to imports:
// import type { FormatBurstResponse, DiffActionResponse, BulkDiffActionResponse, FormattedBurstResponse } from "@/types/formatting";

// ─── V1.2 API Functions (add inside the `api` object) ────────────────────────

// formatBurst: (burst_id: number) =>
//   post<FormatBurstResponse>("/format/burst", { burst_id }),
//
// acceptDiff: (diff_id: string) =>
//   post<DiffActionResponse>("/format/diff/accept", { diff_id }),
//
// rejectDiff: (diff_id: string) =>
//   post<DiffActionResponse>("/format/diff/reject", { diff_id }),
//
// acceptAllDiffs: (burst_id: number) =>
//   post<BulkDiffActionResponse>("/format/diff/accept-all", { burst_id }),
//
// rejectAllDiffs: (burst_id: number) =>
//   post<BulkDiffActionResponse>("/format/diff/reject-all", { burst_id }),
//
// getFormattedBurst: (burst_id: number) =>
//   get<FormattedBurstResponse>(`/format/burst/${burst_id}`),
```

Full updated `api` export block with V1.2 additions:

```typescript
// lib/api.ts — V1.2 version (full export block)

import type {
  FormatBurstResponse,
  DiffActionResponse,
  BulkDiffActionResponse,
  FormattedBurstResponse,
} from "@/types/formatting";

export const api = {
  // ─── V1 (unchanged) ────────────────────────────────────────────────────────
  health: () => get<{ status: string }>("/health"),
  getAppState: () => get<AppState>("/state"),
  listFlareons: () =>
    get<{ flareons: Flareon[] }>("/flareons").then((r) => r.flareons),
  createFlareon: (name: string) => post<Flareon>("/flareons", { name }),
  openFlareon: (id: number) => get<FlareonDetail>(`/flareons/${id}`),
  saveContent: (burst_id: number, content: string) =>
    post<{ success: boolean; burst_entry_id: number }>("/save", { burst_id, content }),

  // ─── V1.1 (unchanged) ──────────────────────────────────────────────────────
  resumeSession: () => get<SessionResumeResponse>("/session/resume"),
  switchFlareon: (flareonId: number) =>
    get<FlareonSwitchResponse>(`/session/switch/${flareonId}`),
  appendChunk: (burst_id: number, text: string) =>
    post<AppendChunkResponse>("/burst/append", { burst_id, text }),

  // ─── V1.2 Formatting (new) ──────────────────────────────────────────────────
  formatBurst: (burst_id: number) =>
    post<FormatBurstResponse>("/format/burst", { burst_id }),

  acceptDiff: (diff_id: string) =>
    post<DiffActionResponse>("/format/diff/accept", { diff_id }),

  rejectDiff: (diff_id: string) =>
    post<DiffActionResponse>("/format/diff/reject", { diff_id }),

  acceptAllDiffs: (burst_id: number) =>
    post<BulkDiffActionResponse>("/format/diff/accept-all", { burst_id }),

  rejectAllDiffs: (burst_id: number) =>
    post<BulkDiffActionResponse>("/format/diff/reject-all", { burst_id }),

  getFormattedBurst: (burst_id: number) =>
    get<FormattedBurstResponse>(`/format/burst/${burst_id}`),
};
```

---

## 5. NEW CSS VARIABLES IN `styles/globals.css`

**Append** these variables to the `:root` block. Do not remove any existing variables.

```css
/* ─── V1.2 Formatting / Diff Colors ─────────────────────────────── */
:root {
  /* Diff status colors */
  --diff-pending:        #4A9EFF;   /* Blue — matches accent-burst */
  --diff-pending-bg:     rgba(74, 158, 255, 0.06);
  --diff-accepted:       #4ACA8A;   /* Green */
  --diff-accepted-bg:    rgba(74, 202, 138, 0.06);
  --diff-rejected:       #FF6B6B;   /* Red */
  --diff-rejected-bg:    rgba(255, 107, 107, 0.06);

  /* Diff review panel */
  --panel-width:         360px;
  --panel-bg:            #121216;
  --panel-border:        #22222E;
  --panel-header-height: 52px;

  /* Format button */
  --format-btn-color:    #7C6AF7;   /* accent-flare */
  --format-btn-bg:       rgba(124, 106, 247, 0.08);
  --format-btn-hover:    rgba(124, 106, 247, 0.15);
}
```

Also append these utility classes for diff line highlighting:

```css
/* ─── Diff Line Highlights ───────────────────────────────────────── */
.diff-line-pending   { background: var(--diff-pending-bg);  }
.diff-line-accepted  { background: var(--diff-accepted-bg); }
.diff-line-rejected  { background: var(--diff-rejected-bg); }
```

---

## 6. NEW HOOK: `useFormatter.ts`

This hook manages the full lifecycle of a format request for one burst.

```typescript
// hooks/useFormatter.ts
"use client";

import { useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { DiffReviewState, FormattingDiff, BurstLine } from "@/types/formatting";

const INITIAL_STATE: DiffReviewState = {
  burstId: null,
  isLoading: false,
  isOpen: false,
  diffs: [],
  lines: [],
  error: null,
  processedAt: null,
};

export function useFormatter() {
  const [state, setState] = useState<DiffReviewState>(INITIAL_STATE);

  /**
   * Trigger format request for a burst.
   * Opens the diff panel on success.
   */
  const requestFormat = useCallback(async (burstId: number) => {
    setState((prev) => ({
      ...prev,
      burstId,
      isLoading: true,
      error: null,
    }));

    try {
      const result = await api.formatBurst(burstId);
      setState({
        burstId,
        isLoading: false,
        isOpen: result.diff_count > 0,
        diffs: result.diffs,
        lines: result.lines,
        error: null,
        processedAt: result.processed_at,
      });

      // If no diffs found, briefly indicate to user
      if (result.diff_count === 0) {
        setState((prev) => ({
          ...prev,
          isOpen: false,
          error: null,
        }));
      }
    } catch (err) {
      console.error("[useFormatter] Format request failed:", err);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: "Formatting failed. Please try again.",
      }));
    }
  }, []);

  /**
   * Close the diff review panel without losing state.
   * The diffs remain in state so the panel can be reopened.
   */
  const closePaenl = useCallback(() => {
    setState((prev) => ({ ...prev, isOpen: false }));
  }, []);

  /**
   * Fully reset formatting state.
   * Called when switching to a different Flareon or Burst.
   */
  const resetFormatting = useCallback(() => {
    setState(INITIAL_STATE);
  }, []);

  /**
   * Optimistically update a diff's status in local state.
   * The backend persists the change; this keeps the UI snappy.
   */
  const updateDiffStatus = useCallback(
    (diffId: string, status: "accepted" | "rejected") => {
      setState((prev) => ({
        ...prev,
        diffs: prev.diffs.map((d) =>
          d.diff_id === diffId ? { ...d, status } : d
        ),
      }));
    },
    []
  );

  /**
   * Optimistically update all pending diffs to the given status.
   */
  const updateAllDiffStatus = useCallback(
    (status: "accepted" | "rejected") => {
      setState((prev) => ({
        ...prev,
        diffs: prev.diffs.map((d) =>
          d.status === "pending" ? { ...d, status } : d
        ),
      }));
    },
    []
  );

  const pendingCount = state.diffs.filter((d) => d.status === "pending").length;
  const acceptedCount = state.diffs.filter((d) => d.status === "accepted").length;
  const hasDiffs = state.diffs.length > 0;

  return {
    ...state,
    requestFormat,
    closePaenl,
    resetFormatting,
    updateDiffStatus,
    updateAllDiffStatus,
    pendingCount,
    acceptedCount,
    hasDiffs,
  };
}
```

---

## 7. NEW HOOK: `useDiffReview.ts`

Manages the accept/reject actions with optimistic UI + backend sync.

```typescript
// hooks/useDiffReview.ts
"use client";

import { useCallback } from "react";
import { api } from "@/lib/api";

interface UseDiffReviewOptions {
  burstId: number | null;
  onDiffUpdate: (diffId: string, status: "accepted" | "rejected") => void;
  onBulkUpdate: (status: "accepted" | "rejected") => void;
}

export function useDiffReview({
  burstId,
  onDiffUpdate,
  onBulkUpdate,
}: UseDiffReviewOptions) {
  /**
   * Accept a single diff.
   * Optimistic: updates UI first, then persists to backend.
   * On failure: logs error silently. The optimistic state stays.
   * The backend is the source of truth on next reload.
   */
  const acceptDiff = useCallback(
    async (diffId: string) => {
      onDiffUpdate(diffId, "accepted");
      try {
        await api.acceptDiff(diffId);
      } catch (err) {
        console.error("[useDiffReview] acceptDiff failed:", err);
      }
    },
    [onDiffUpdate]
  );

  /**
   * Reject a single diff.
   */
  const rejectDiff = useCallback(
    async (diffId: string) => {
      onDiffUpdate(diffId, "rejected");
      try {
        await api.rejectDiff(diffId);
      } catch (err) {
        console.error("[useDiffReview] rejectDiff failed:", err);
      }
    },
    [onDiffUpdate]
  );

  /**
   * Accept all pending diffs for the current burst.
   */
  const acceptAll = useCallback(async () => {
    if (!burstId) return;
    onBulkUpdate("accepted");
    try {
      await api.acceptAllDiffs(burstId);
    } catch (err) {
      console.error("[useDiffReview] acceptAll failed:", err);
    }
  }, [burstId, onBulkUpdate]);

  /**
   * Reject all pending diffs for the current burst.
   */
  const rejectAll = useCallback(async () => {
    if (!burstId) return;
    onBulkUpdate("rejected");
    try {
      await api.rejectAllDiffs(burstId);
    } catch (err) {
      console.error("[useDiffReview] rejectAll failed:", err);
    }
  }, [burstId, onBulkUpdate]);

  return { acceptDiff, rejectDiff, acceptAll, rejectAll };
}
```

---

## 8. NEW COMPONENT: `FormatButton.tsx`

Triggers formatting. Minimal, non-intrusive. Sits in the bottom-right of the stream shell.

```tsx
// components/formatting/FormatButton.tsx
"use client";

interface FormatButtonProps {
  onClick: () => void;
  isLoading: boolean;
  hasDiffs: boolean;
  pendingCount: number;
  disabled?: boolean;
}

export default function FormatButton({
  onClick,
  isLoading,
  hasDiffs,
  pendingCount,
  disabled = false,
}: FormatButtonProps) {
  const label = isLoading
    ? "Formatting..."
    : hasDiffs && pendingCount > 0
    ? `Review ${pendingCount} change${pendingCount !== 1 ? "s" : ""}`
    : "Format";

  return (
    <button
      data-testid="format-button"
      onClick={onClick}
      disabled={disabled || isLoading}
      style={{
        background: hasDiffs && pendingCount > 0
          ? "var(--format-btn-hover)"
          : "var(--format-btn-bg)",
        border: "1px solid",
        borderColor: hasDiffs && pendingCount > 0
          ? "var(--accent-flare)"
          : "var(--border-subtle)",
        borderRadius: "6px",
        color: hasDiffs && pendingCount > 0
          ? "var(--accent-flare)"
          : "var(--text-secondary)",
        cursor: disabled || isLoading ? "default" : "pointer",
        fontFamily: "var(--font-ui)",
        fontSize: "11px",
        letterSpacing: "0.04em",
        opacity: disabled ? 0.4 : 1,
        padding: "5px 10px",
        transition: "all 0.15s ease",
      }}
    >
      {label}
    </button>
  );
}
```

---

## 9. NEW COMPONENT: `LineStatusBadge.tsx`

Visual status indicator for a diff line.

```tsx
// components/formatting/LineStatusBadge.tsx

import type { LineStatus } from "@/types/formatting";

interface LineStatusBadgeProps {
  status: LineStatus;
}

const STATUS_STYLES: Record<LineStatus, { color: string; label: string }> = {
  untouched: { color: "var(--text-muted)", label: "" },
  pending:   { color: "var(--diff-pending)", label: "pending" },
  accepted:  { color: "var(--diff-accepted)", label: "accepted" },
  rejected:  { color: "var(--diff-rejected)", label: "rejected" },
};

export default function LineStatusBadge({ status }: LineStatusBadgeProps) {
  if (status === "untouched") return null;

  const { color, label } = STATUS_STYLES[status];

  return (
    <span
      data-testid={`line-status-badge-${status}`}
      style={{
        color,
        fontFamily: "var(--font-ui)",
        fontSize: "10px",
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        fontWeight: 500,
        opacity: 0.8,
      }}
    >
      {label}
    </span>
  );
}
```

---

## 10. NEW COMPONENT: `DiffLineItem.tsx`

A single row in the diff review panel. Shows the before/after with inline accept/reject buttons.

```tsx
// components/formatting/DiffLineItem.tsx
"use client";

import LineStatusBadge from "./LineStatusBadge";
import type { FormattingDiff } from "@/types/formatting";

interface DiffLineItemProps {
  diff: FormattingDiff;
  onAccept: (diffId: string) => void;
  onReject: (diffId: string) => void;
}

export default function DiffLineItem({
  diff,
  onAccept,
  onReject,
}: DiffLineItemProps) {
  const isPending = diff.status === "pending";

  return (
    <div
      data-testid="diff-line-item"
      style={{
        borderBottom: "1px solid var(--panel-border)",
        padding: "12px 16px",
        background: isPending
          ? "var(--diff-pending-bg)"
          : diff.status === "accepted"
          ? "var(--diff-accepted-bg)"
          : "var(--diff-rejected-bg)",
      }}
    >
      {/* Before */}
      <div
        style={{
          fontFamily: "var(--font-writing)",
          fontSize: "13px",
          lineHeight: 1.6,
          color: "var(--text-secondary)",
          marginBottom: "4px",
          textDecoration: diff.status === "accepted" ? "line-through" : "none",
          opacity: 0.7,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {diff.raw_before || <em style={{ opacity: 0.4 }}>(empty)</em>}
      </div>

      {/* After */}
      <div
        style={{
          fontFamily: "var(--font-writing)",
          fontSize: "13px",
          lineHeight: 1.6,
          color: "var(--text-primary)",
          marginBottom: "8px",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {diff.formatted_after}
      </div>

      {/* Controls row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <LineStatusBadge status={diff.status} />

        {isPending && (
          <div style={{ display: "flex", gap: "6px" }}>
            <button
              data-testid="diff-accept-btn"
              onClick={() => onAccept(diff.diff_id)}
              style={{
                background: "transparent",
                border: "1px solid var(--diff-accepted)",
                borderRadius: "4px",
                color: "var(--diff-accepted)",
                cursor: "pointer",
                fontFamily: "var(--font-ui)",
                fontSize: "11px",
                padding: "3px 8px",
              }}
            >
              Accept
            </button>
            <button
              data-testid="diff-reject-btn"
              onClick={() => onReject(diff.diff_id)}
              style={{
                background: "transparent",
                border: "1px solid var(--border-subtle)",
                borderRadius: "4px",
                color: "var(--text-secondary)",
                cursor: "pointer",
                fontFamily: "var(--font-ui)",
                fontSize: "11px",
                padding: "3px 8px",
              }}
            >
              Reject
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
```

---

## 11. NEW COMPONENT: `DiffReviewPanel.tsx`

The slide-in panel that shows all pending diffs. Appears from the right side of the writing area.

```tsx
// components/formatting/DiffReviewPanel.tsx
"use client";

import DiffLineItem from "./DiffLineItem";
import type { FormattingDiff } from "@/types/formatting";

interface DiffReviewPanelProps {
  isOpen: boolean;
  diffs: FormattingDiff[];
  pendingCount: number;
  onAccept: (diffId: string) => void;
  onReject: (diffId: string) => void;
  onAcceptAll: () => void;
  onRejectAll: () => void;
  onClose: () => void;
}

export default function DiffReviewPanel({
  isOpen,
  diffs,
  pendingCount,
  onAccept,
  onReject,
  onAcceptAll,
  onRejectAll,
  onClose,
}: DiffReviewPanelProps) {
  if (!isOpen) return null;

  return (
    <aside
      data-testid="diff-review-panel"
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        width: "var(--panel-width)",
        height: "100vh",
        background: "var(--panel-bg)",
        borderLeft: "1px solid var(--panel-border)",
        display: "flex",
        flexDirection: "column",
        zIndex: 100,
        overflowY: "hidden",
      }}
    >
      {/* Panel header */}
      <div
        style={{
          height: "var(--panel-header-height)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 16px",
          borderBottom: "1px solid var(--panel-border)",
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-ui)",
            fontSize: "12px",
            color: "var(--text-secondary)",
            letterSpacing: "0.05em",
            fontWeight: 500,
          }}
        >
          {pendingCount} pending change{pendingCount !== 1 ? "s" : ""}
        </span>
        <button
          data-testid="diff-panel-close"
          onClick={onClose}
          style={{
            background: "transparent",
            border: "none",
            color: "var(--text-muted)",
            cursor: "pointer",
            fontFamily: "var(--font-ui)",
            fontSize: "18px",
            lineHeight: 1,
            padding: "4px",
          }}
        >
          ×
        </button>
      </div>

      {/* Bulk actions */}
      {pendingCount > 0 && (
        <div
          style={{
            display: "flex",
            gap: "8px",
            padding: "10px 16px",
            borderBottom: "1px solid var(--panel-border)",
            flexShrink: 0,
          }}
        >
          <button
            data-testid="accept-all-btn"
            onClick={onAcceptAll}
            style={{
              flex: 1,
              background: "transparent",
              border: "1px solid var(--diff-accepted)",
              borderRadius: "5px",
              color: "var(--diff-accepted)",
              cursor: "pointer",
              fontFamily: "var(--font-ui)",
              fontSize: "11px",
              padding: "6px",
            }}
          >
            Accept all
          </button>
          <button
            data-testid="reject-all-btn"
            onClick={onRejectAll}
            style={{
              flex: 1,
              background: "transparent",
              border: "1px solid var(--border-subtle)",
              borderRadius: "5px",
              color: "var(--text-secondary)",
              cursor: "pointer",
              fontFamily: "var(--font-ui)",
              fontSize: "11px",
              padding: "6px",
            }}
          >
            Reject all
          </button>
        </div>
      )}

      {/* Diff list */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {diffs.length === 0 ? (
          <div
            style={{
              padding: "24px 16px",
              color: "var(--text-muted)",
              fontFamily: "var(--font-ui)",
              fontSize: "12px",
              textAlign: "center",
            }}
          >
            No formatting changes found.
          </div>
        ) : (
          diffs.map((diff) => (
            <DiffLineItem
              key={diff.diff_id}
              diff={diff}
              onAccept={onAccept}
              onReject={onReject}
            />
          ))
        )}
      </div>
    </aside>
  );
}
```

---

## 12. NEW COMPONENT: `FormattedPreview.tsx`

Renders a burst's accepted-formatted text in the archive view. Falls back to raw text if no formatting applied.

```tsx
// components/formatting/FormattedPreview.tsx
"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { FormattedBurstResponse } from "@/types/formatting";

interface FormattedPreviewProps {
  burstId: number;
  rawContent: string;   // Always available — used as fallback
}

export default function FormattedPreview({
  burstId,
  rawContent,
}: FormattedPreviewProps) {
  const [formatted, setFormatted] = useState<FormattedBurstResponse | null>(null);
  const [showFormatted, setShowFormatted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchFormatted() {
      setIsLoading(true);
      try {
        const result = await api.getFormattedBurst(burstId);
        if (!cancelled) {
          setFormatted(result);
          // Auto-show formatted if it exists and has accepted changes
          if (result.has_formatting) setShowFormatted(true);
        }
      } catch {
        // Silently ignore — formatted version may not exist yet
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    fetchFormatted();
    return () => { cancelled = true; };
  }, [burstId]);

  const displayText = showFormatted && formatted?.has_formatting
    ? formatted.formatted_text
    : rawContent;

  const hasFormattedVersion = formatted?.has_formatting ?? false;

  return (
    <div data-testid="formatted-preview">
      {/* Toggle — only shown if a formatted version exists */}
      {hasFormattedVersion && !isLoading && (
        <div
          style={{
            display: "flex",
            gap: "8px",
            marginBottom: "12px",
          }}
        >
          <button
            data-testid="view-raw-btn"
            onClick={() => setShowFormatted(false)}
            style={{
              background: "transparent",
              border: "none",
              color: showFormatted ? "var(--text-muted)" : "var(--accent-flare)",
              cursor: "pointer",
              fontFamily: "var(--font-ui)",
              fontSize: "11px",
              padding: 0,
              textDecoration: showFormatted ? "none" : "underline",
            }}
          >
            Raw
          </button>
          <span style={{ color: "var(--border-subtle)" }}>·</span>
          <button
            data-testid="view-formatted-btn"
            onClick={() => setShowFormatted(true)}
            style={{
              background: "transparent",
              border: "none",
              color: showFormatted ? "var(--accent-flare)" : "var(--text-muted)",
              cursor: "pointer",
              fontFamily: "var(--font-ui)",
              fontSize: "11px",
              padding: 0,
              textDecoration: showFormatted ? "underline" : "none",
            }}
          >
            Formatted
          </button>
        </div>
      )}

      {/* Content */}
      <p
        style={{
          fontFamily: "var(--font-writing)",
          fontSize: "var(--text-size-writing)",
          lineHeight: "var(--line-height-writing)",
          color: "var(--text-primary)",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          margin: 0,
        }}
      >
        {displayText || (
          <em style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
            Empty burst.
          </em>
        )}
      </p>
    </div>
  );
}
```

---

## 13. MODIFIED COMPONENT: `StreamShell.tsx`

Add the `FormatButton` and `DiffReviewPanel` to the stream shell. The formatting state is managed by `useFormatter` and `useDiffReview` hooks, initialized at the stream page level and passed as props.

Add `onFormatClick` and formatting-related props to the `StreamShellProps` interface:

```tsx
// Additions to components/stream/StreamShell.tsx

import FormatButton from "@/components/formatting/FormatButton";
import DiffReviewPanel from "@/components/formatting/DiffReviewPanel";
import type { FormattingDiff } from "@/types/formatting";

// Add to StreamShellProps:
interface StreamShellProps {
  // ... existing props unchanged ...
  activeFlareon: Flareon | null;
  burstId: number | null;
  initialContent: string;
  burstStartedAt: string | null;
  onOpenArchive: () => void;

  // NEW formatting props:
  isFormatLoading: boolean;
  hasDiffs: boolean;
  pendingDiffCount: number;
  isDiffPanelOpen: boolean;
  diffs: FormattingDiff[];
  onFormatClick: () => void;
  onDiffAccept: (diffId: string) => void;
  onDiffReject: (diffId: string) => void;
  onDiffAcceptAll: () => void;
  onDiffRejectAll: () => void;
  onDiffPanelClose: () => void;
}
```

In the JSX, insert `FormatButton` in the bottom controls row (replacing or extending the existing `NavControls` slot):

```tsx
{/* Bottom controls — session indicator + nav + format button */}
<div
  style={{
    padding: "16px var(--writing-padding-x)",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "12px",
  }}
>
  <SessionIndicator burstStartedAt={burstStartedAt} />
  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
    <NavControls onOpenArchive={onOpenArchive} flareonId={activeFlareon?.id} />
    <FormatButton
      onClick={onFormatClick}
      isLoading={isFormatLoading}
      hasDiffs={hasDiffs}
      pendingCount={pendingDiffCount}
      disabled={!burstId}
    />
  </div>
</div>

{/* Diff review panel — fixed position, overlays right side */}
<DiffReviewPanel
  isOpen={isDiffPanelOpen}
  diffs={diffs}
  pendingCount={pendingDiffCount}
  onAccept={onDiffAccept}
  onReject={onDiffReject}
  onAcceptAll={onDiffAcceptAll}
  onRejectAll={onDiffRejectAll}
  onClose={onDiffPanelClose}
/>
```

---

## 14. MODIFIED PAGE: `app/page.tsx` (Stream Page)

Wire `useFormatter` and `useDiffReview` into the stream page. These hooks live at the page level because they span both the format button and the diff panel.

```tsx
// app/page.tsx — additions to existing stream page

"use client";

// Add these imports to the existing import block:
import { useFormatter } from "@/hooks/useFormatter";
import { useDiffReview } from "@/hooks/useDiffReview";

// Inside the StreamPage component, after existing hook calls:

const formatter = useFormatter();

const { acceptDiff, rejectDiff, acceptAll, rejectAll } = useDiffReview({
  burstId: session.activeBurstId,
  onDiffUpdate: formatter.updateDiffStatus,
  onBulkUpdate: formatter.updateAllDiffStatus,
});

// Reset formatting when burst changes (Flareon switch):
// Add to the Flareon switch handler:
// formatter.resetFormatting();

// Pass to StreamShell:
// isFormatLoading={formatter.isLoading}
// hasDiffs={formatter.hasDiffs}
// pendingDiffCount={formatter.pendingCount}
// isDiffPanelOpen={formatter.isOpen}
// diffs={formatter.diffs}
// onFormatClick={() => session.activeBurstId && formatter.requestFormat(session.activeBurstId)}
// onDiffAccept={acceptDiff}
// onDiffReject={rejectDiff}
// onDiffAcceptAll={acceptAll}
// onDiffRejectAll={rejectAll}
// onDiffPanelClose={formatter.closePaenl}
```

**Note on Flareon switching:** Call `formatter.resetFormatting()` inside `handleSwitchFlareon` in the stream page. The diff panel for one Flareon should not remain visible when the user switches to another.

---

## 15. MODIFIED PAGE: `app/flareon/[id]/page.tsx` (Archive Page)

Replace raw `BurstBlock` usage with `FormattedPreview` in the archive page. This gives users access to the formatted version when viewing burst history.

```tsx
// In app/flareon/[id]/page.tsx

// Replace:
// <BurstBlock content={burst.content} />

// With:
import FormattedPreview from "@/components/formatting/FormattedPreview";

// In the burst list render:
<FormattedPreview
  key={burst.id}
  burstId={burst.id}
  rawContent={burst.content}
/>
```

---

## 16. DATA-TESTID REQUIREMENTS

All new V1.2 components must have these `data-testid` attributes:

| Component | Element | data-testid |
|---|---|---|
| `FormatButton` | Button | `format-button` |
| `DiffReviewPanel` | Root aside | `diff-review-panel` |
| `DiffReviewPanel` | Close button | `diff-panel-close` |
| `DiffReviewPanel` | Accept all button | `accept-all-btn` |
| `DiffReviewPanel` | Reject all button | `reject-all-btn` |
| `DiffLineItem` | Root div | `diff-line-item` |
| `DiffLineItem` | Accept button | `diff-accept-btn` |
| `DiffLineItem` | Reject button | `diff-reject-btn` |
| `FormattedPreview` | Root div | `formatted-preview` |
| `FormattedPreview` | Raw toggle button | `view-raw-btn` |
| `FormattedPreview` | Formatted toggle button | `view-formatted-btn` |
| `LineStatusBadge` | Span | `line-status-badge-{status}` |

---

## 17. IMPLEMENTATION ORDER AND VERIFICATION

Follow this order exactly. Verify each step with `npx tsc --noEmit` before proceeding.

### Step 1 — Types file
**Do:** Create `types/formatting.ts`
**Verify:** `npx tsc --noEmit` — no errors

### Step 2 — CSS variables
**Do:** Append diff color variables to `styles/globals.css`
**Verify:** Open app in browser, inspect `:root`, confirm `--diff-pending` exists

### Step 3 — Update `lib/api.ts`
**Do:** Add V1.2 formatting functions
**Verify:** `npx tsc --noEmit` — no errors; check that `api.formatBurst` is callable

### Step 4 — New hooks
**Do:** Create `useFormatter.ts` and `useDiffReview.ts`
**Verify:** `npx tsc --noEmit` — no errors

### Step 5 — New components (leaf components first)
**Do:** Create `LineStatusBadge.tsx`, `DiffLineItem.tsx`, `FormatButton.tsx`
**Verify:** `npx tsc --noEmit` — no errors

### Step 6 — Composite components
**Do:** Create `DiffReviewPanel.tsx`, `FormattedPreview.tsx`
**Verify:** `npx tsc --noEmit` — no errors

### Step 7 — Modify StreamShell
**Do:** Update `StreamShell.tsx` with new props and children
**Verify:** `npx tsc --noEmit` — no errors; `next dev` starts clean

### Step 8 — Modify stream page
**Do:** Wire `useFormatter` and `useDiffReview` into `app/page.tsx`
**Verify:**
- `next dev` starts without errors
- Format button visible in bottom controls
- Clicking Format with backend running opens diff panel
- Accept/Reject buttons function per diff
- Accept All / Reject All work

### Step 9 — Modify archive page
**Do:** Replace `BurstBlock` with `FormattedPreview` in `app/flareon/[id]/page.tsx`
**Verify:** Archive page shows raw/formatted toggle for bursts that have been formatted

### Step 10 — Full regression
**Verify all V1.1 behaviors still work:**
- Session resume (stream input focused immediately)
- Flareon switching (stream resets, formatting state resets)
- Append save (1 second after typing)
- Archive navigation

---

## 18. PERFORMANCE REQUIREMENTS

| Operation | Target |
|---|---|
| Format button click → diff panel open | < 2s (spaCy parse is local; allow up to 3s first call) |
| Accept/Reject single diff | < 50ms (optimistic UI; backend is fire-and-forget) |
| Accept All / Reject All | < 50ms (optimistic) |
| Diff panel render (50 diffs) | < 100ms |
| FormattedPreview fetch and render | < 500ms |

---

## 19. COMMON MISTAKES TO AVOID

**Do not:**
- Use `useState` for the diff list — use the `useFormatter` hook
- Make formatting requests automatically — always require user action via `FormatButton`
- Mutate the `raw_line` field anywhere — it is read-only by architecture
- Render `DiffReviewPanel` inside `StreamInput` — it is a sibling of `StreamShell`
- Forget to call `formatter.resetFormatting()` on Flareon switch

**Do:**
- Keep `DiffReviewPanel` as a fixed-position overlay — do not push the stream layout
- Always pass `burstId` as the `key` prop to `StreamInput` and `StreamShell` for proper reset on switch
- Use optimistic updates for all diff accept/reject actions for instant feel
- Test with an empty burst (0 diffs found) — `FormatButton` should show "Format" without a count badge
