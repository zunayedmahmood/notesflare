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
