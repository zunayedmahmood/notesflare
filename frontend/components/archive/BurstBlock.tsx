// components/archive/BurstBlock.tsx

interface BurstBlockProps {
  content: string;
  isActive?: boolean;
}

export default function BurstBlock({ content, isActive = false }: BurstBlockProps) {
  if (!content.trim()) {
    return (
      <p
        data-testid="burst-block"
        style={{
          fontFamily: "var(--font-writing)",
          fontSize: "var(--text-size-writing)",
          lineHeight: "var(--line-height-writing)",
          color: "var(--text-muted)",
          fontStyle: "italic",
        }}
      >
        {isActive ? "Typing..." : "Empty burst."}
      </p>
    );
  }

  return (
    <p
      data-testid="burst-block"
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
      {content}
    </p>
  );
}
