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
