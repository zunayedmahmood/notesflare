// components/stream/NavControls.tsx
"use client";

import { useRouter } from "next/navigation";

interface NavControlsProps {
  flareonId: number | null;
  onOpenArchive: () => void;
}

export default function NavControls({ flareonId, onOpenArchive }: NavControlsProps) {
  const router = useRouter();

  function handleArchive() {
    if (flareonId !== null) {
      router.push(`/flareon/${flareonId}`);
    }
    onOpenArchive();
  }

  const btnStyle: React.CSSProperties = {
    background: "none",
    border: "none",
    cursor: "pointer",
    fontFamily: "var(--font-ui)",
    fontSize: "11px",
    color: "var(--text-secondary)",
    padding: "4px 8px",
    borderRadius: "4px",
    transition: "color 0.1s",
    letterSpacing: "0.03em",
  };

  return (
    <nav
      data-testid="nav-controls"
      style={{ display: "flex", gap: "4px", alignItems: "center" }}
    >
      <button
        style={btnStyle}
        data-testid="nav-archive"
        onClick={handleArchive}
        onMouseEnter={(e) =>
          ((e.currentTarget as HTMLButtonElement).style.color =
            "var(--text-primary)")
        }
        onMouseLeave={(e) =>
          ((e.currentTarget as HTMLButtonElement).style.color =
            "var(--text-secondary)")
        }
      >
        Archive
      </button>
    </nav>
  );
}
