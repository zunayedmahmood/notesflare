// components/stream/NavControls.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

interface NavControlsProps {
  flareonId: number | null;
  onOpenArchive: () => void;
}

export default function NavControls({ flareonId, onOpenArchive }: NavControlsProps) {
  const router = useRouter();

  const [isHovered, setIsHovered] = useState(false);

  function handleArchive() {
    if (flareonId !== null) {
      router.push(`/flareon/${flareonId}`);
      onOpenArchive();
    }
  }

  const btnStyle: React.CSSProperties = {
    background: "none",
    border: "none",
    cursor: "pointer",
    fontFamily: "var(--font-ui)",
    fontSize: "11px",
    color: isHovered ? "var(--text-primary)" : "var(--text-secondary)",
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
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        Archive
      </button>
    </nav>
  );
}
