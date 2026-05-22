// components/archive/BurstDivider.tsx

interface BurstDividerProps {
  startedAt: string;
  isActive: boolean;
}

export default function BurstDivider({ startedAt, isActive }: BurstDividerProps) {
  const formatted = new Date(startedAt).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

  return (
    <div
      data-testid="burst-divider"
      style={{
        display: "flex",
        alignItems: "center",
        gap: "12px",
        marginBottom: "20px",
      }}
    >
      <span
        style={{
          fontSize: "11px",
          color: isActive ? "var(--accent-burst)" : "var(--text-secondary)",
          fontFamily: "var(--font-ui)",
          letterSpacing: "0.05em",
          whiteSpace: "nowrap",
          opacity: isActive ? 1 : 0.7,
        }}
      >
        {formatted}{isActive ? " · active" : ""}
      </span>
      <div
        style={{
          flex: 1,
          height: "1px",
          background: isActive ? "var(--accent-flare-dim)" : "var(--border-subtle)",
        }}
      />
    </div>
  );
}
