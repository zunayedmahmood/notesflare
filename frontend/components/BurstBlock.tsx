// components/BurstBlock.tsx

interface BurstBlockProps {
  startedAt: string;
  content: string;
}

function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function BurstBlock({ startedAt, content }: BurstBlockProps) {
  if (!content.trim()) return null; // Don't show empty historical bursts

  return (
    <div data-testid="burst-block" style={{ marginBottom: "48px" }}>
      {/* Burst timestamp label */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          marginBottom: "20px",
        }}
      >
        <span
          data-testid="burst-timestamp"
          style={{
            fontSize: "11px",
            color: "var(--accent-burst)",
            fontFamily: "var(--font-ui)",
            letterSpacing: "0.05em",
            opacity: 0.7,
          }}
        >
          {formatTimestamp(startedAt)}
        </span>
        <div
          style={{
            flex: 1,
            height: "1px",
            background: "var(--border-subtle)",
            opacity: 0.5,
          }}
        />
      </div>

      {/* Past burst content — read-only */}
      <div
        style={{
          fontFamily: "var(--font-writing)",
          fontSize: "var(--text-size-writing)",
          lineHeight: "var(--line-height-writing)",
          color: "var(--text-secondary)",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {content}
      </div>
    </div>
  );
}
