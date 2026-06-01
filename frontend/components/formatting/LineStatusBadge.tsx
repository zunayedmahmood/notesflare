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
