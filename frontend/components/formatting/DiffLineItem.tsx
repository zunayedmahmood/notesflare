// components/formatting/DiffLineItem.tsx
"use client";

import LineStatusBadge from "./LineStatusBadge";
import type { FormattingDiff } from "@/types/formatting";

interface DiffLineItemProps {
  diff: FormattingDiff;
  onAccept: (diffId: string) => void;
  onReject: (diffId: string) => void;
}

function getOperationLabel(operation: FormattingDiff["operation"]): string {
  switch (operation) {
    case "insert_line_break":
      return "Semantic structure";
    case "insert_paragraph_break":
      return "Topic shift detected";
    case "format_as_list_item":
      return "List cleanup";
    case "format_as_heading":
      return "Heading candidate";
    case "format_as_quote":
      return "Quote cleanup";
    case "normalize_spacing":
      return "Spacing cleanup";
    default:
      return "Formatting change";
  }
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
      <div
        style={{
          color: diff.operation === "insert_paragraph_break"
            ? "var(--diff-pending)"
            : "var(--accent-flare)",
          fontFamily: "var(--font-ui)",
          fontSize: "10px",
          letterSpacing: "0.08em",
          marginBottom: "8px",
          textTransform: "uppercase",
        }}
      >
        {getOperationLabel(diff.operation)}
      </div>

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
