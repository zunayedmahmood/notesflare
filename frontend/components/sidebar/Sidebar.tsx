// components/sidebar/Sidebar.tsx
"use client";

import { useState } from "react";
import type { Flareon } from "@/lib/api";

interface SidebarProps {
  flareons: Flareon[];
  activeFlareonId: number | null;
  onSelectFlareon: (id: number) => void;
  onCreateFlareon: (name: string) => Promise<void>;
}

export default function Sidebar({
  flareons,
  activeFlareonId,
  onSelectFlareon,
  onCreateFlareon,
}: SidebarProps) {
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleCreate() {
    const trimmed = newName.trim();
    if (!trimmed) return;
    setError(null);
    try {
      await onCreateFlareon(trimmed);
      setNewName("");
      setCreating(false);
    } catch (err) {
      console.error("Failed to create Flareon:", err);
      setError("Already exists.");
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") handleCreate();
    if (e.key === "Escape") {
      setCreating(false);
      setNewName("");
      setError(null);
    }
  }

  return (
    <aside
      data-testid="sidebar"
      style={{
        width: "var(--sidebar-width)",
        minWidth: "var(--sidebar-width)",
        height: "100vh",
        background: "var(--bg-surface)",
        borderRight: "1px solid var(--border-subtle)",
        display: "flex",
        flexDirection: "column",
        padding: "24px 0",
        overflow: "hidden",
      }}
    >
      {/* App name */}
      <div
        style={{
          padding: "0 16px 20px",
          color: "var(--text-secondary)",
          fontSize: "11px",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          fontWeight: 500,
        }}
      >
        NotesFlare
      </div>

      {/* Flareon list */}
      <nav style={{ flex: 1, overflowY: "auto", padding: "0 8px" }}>
        {flareons.map((f) => (
          <button
            key={f.id}
            data-testid="flareon-item"
            className={f.id === activeFlareonId ? "active" : ""}
            onClick={() => onSelectFlareon(f.id)}
            style={{
              display: "block",
              width: "100%",
              textAlign: "left",
              padding: "8px 10px",
              borderRadius: "6px",
              border: "none",
              cursor: "pointer",
              fontSize: "var(--text-size-ui)",
              fontFamily: "var(--font-ui)",
              color:
                f.id === activeFlareonId
                  ? "var(--text-primary)"
                  : "var(--text-secondary)",
              background:
                f.id === activeFlareonId
                  ? "var(--accent-flare-dim)"
                  : "transparent",
              marginBottom: "2px",
              transition: "background 0.1s, color 0.1s",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
            onMouseEnter={(e) => {
              if (f.id !== activeFlareonId) {
                (e.currentTarget as HTMLButtonElement).style.background =
                  "var(--bg-elevated)";
              }
            }}
            onMouseLeave={(e) => {
              if (f.id !== activeFlareonId) {
                (e.currentTarget as HTMLButtonElement).style.background =
                  "transparent";
              }
            }}
          >
            {f.name}
          </button>
        ))}
      </nav>

      {/* Create Flareon */}
      <div style={{ padding: "12px 8px 0" }}>
        {creating ? (
          <div style={{ display: "flex", flexDirection: "column" }}>
            <input
              autoFocus
              data-testid="new-flareon-input"
              value={newName}
              onChange={(e) => {
                setNewName(e.target.value);
                if (error) setError(null);
              }}
              onKeyDown={handleKeyDown}
              onBlur={() => {
                // If input is empty and we blur, close creation mode
                if (!newName.trim()) {
                  setCreating(false);
                  setError(null);
                }
              }}
              placeholder="Flareon name..."
              style={{
                width: "100%",
                background: "var(--bg-elevated)",
                border: error
                  ? "1px solid #FF6B6B"
                  : "1px solid var(--accent-flare)",
                borderRadius: "6px",
                padding: "7px 10px",
                color: "var(--text-primary)",
                fontSize: "var(--text-size-ui)",
                fontFamily: "var(--font-ui)",
                outline: "none",
              }}
            />
            {error && (
              <div
                data-testid="flareon-name-error"
                style={{
                  fontSize: "11px",
                  color: "#FF6B6B",
                  padding: "6px 10px 0",
                  fontFamily: "var(--font-ui)",
                  lineHeight: "1.3",
                }}
              >
                {error}
              </div>
            )}
          </div>
        ) : (
          <button
            onClick={() => setCreating(true)}
            data-testid="new-flareon-button"
            style={{
              width: "100%",
              padding: "7px 10px",
              background: "transparent",
              border: "1px dashed var(--border-subtle)",
              borderRadius: "6px",
              color: "var(--text-muted)",
              fontSize: "var(--text-size-ui)",
              fontFamily: "var(--font-ui)",
              cursor: "pointer",
              textAlign: "left",
              transition: "border-color 0.15s, color 0.15s",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.borderColor =
                "var(--accent-flare)";
              (e.currentTarget as HTMLButtonElement).style.color =
                "var(--text-secondary)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.borderColor =
                "var(--border-subtle)";
              (e.currentTarget as HTMLButtonElement).style.color =
                "var(--text-muted)";
            }}
          >
            + New Flareon
          </button>
        )}
      </div>
    </aside>
  );
}
