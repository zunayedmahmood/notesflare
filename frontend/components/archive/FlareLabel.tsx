// components/archive/FlareLabel.tsx

interface FlareLabelProps {
  name: string;
}

export default function FlareLabel({ name }: FlareLabelProps) {
  return (
    <div
      data-testid="flareon-label"
      style={{
        fontSize: "11px",
        color: "var(--text-muted)",
        fontFamily: "var(--font-ui)",
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        marginBottom: "48px",
        fontWeight: 500,
      }}
    >
      {name}
    </div>
  );
}
