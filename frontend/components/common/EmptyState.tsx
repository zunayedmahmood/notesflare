// components/common/EmptyState.tsx

export default function EmptyState() {
  return (
    <main
      data-testid="empty-state"
      style={{
        flex: 1,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "var(--text-muted)",
        fontFamily: "var(--font-ui)",
        fontSize: "13px",
      }}
    >
      Select a Flareon to begin.
    </main>
  );
}
