// components/stream/SessionIndicator.tsx

interface SessionIndicatorProps {
  startedAt: string | null;
}

export default function SessionIndicator({ startedAt }: SessionIndicatorProps) {
  if (!startedAt) return null;

  const formatted = new Date(startedAt).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

  return (
    <span
      data-testid="session-indicator"
      style={{
        fontFamily: "var(--font-ui)",
        fontSize: "11px",
        color: "var(--accent-burst)",
        letterSpacing: "0.04em",
      }}
    >
      Burst since {formatted}
    </span>
  );
}
