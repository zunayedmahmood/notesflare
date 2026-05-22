// components/stream/StreamShell.tsx
"use client";

import StreamInput from "@/components/stream/StreamInput";
import SessionIndicator from "@/components/stream/SessionIndicator";
import NavControls from "@/components/stream/NavControls";
import EmptyState from "@/components/common/EmptyState";
import type { Flareon } from "@/lib/api";

interface StreamShellProps {
  activeFlareon: Flareon | null;
  burstId: number | null;
  initialContent: string;
  burstStartedAt: string | null;
  onOpenArchive: () => void;
}

export default function StreamShell({
  activeFlareon,
  burstId,
  initialContent,
  burstStartedAt,
  onOpenArchive,
}: StreamShellProps) {
  if (!activeFlareon) {
    return <EmptyState />;
  }

  return (
    <main
      data-testid="stream-shell"
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        overflow: "hidden",
        background: "var(--bg-base)",
      }}
    >
      {/* Flareon name — top, very subtle */}
      <div
        style={{
          padding: "28px var(--writing-padding-x) 0",
          color: "var(--text-secondary)",
          fontFamily: "var(--font-ui)",
          fontSize: "11px",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          fontWeight: 500,
          opacity: 0.7,
        }}
      >
        {activeFlareon.name}
      </div>

      {/* Stream input — vertically centered */}
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          padding: "0 var(--writing-padding-x)",
          maxWidth: "calc(var(--writing-max-width) + calc(var(--writing-padding-x) * 2))",
          width: "100%",
          alignSelf: "center",
        }}
      >
        <StreamInput
          key={`${burstId}-${activeFlareon.id}`}
          burstId={burstId}
          initialContent={initialContent}
        />
      </div>

      {/* Bottom controls — session indicator + nav */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px var(--writing-padding-x) 24px",
          borderTop: "1px solid var(--border-subtle)",
          opacity: 0.6,
        }}
        onMouseEnter={(e) =>
          ((e.currentTarget as HTMLDivElement).style.opacity = "1")
        }
        onMouseLeave={(e) =>
          ((e.currentTarget as HTMLDivElement).style.opacity = "0.6")
        }
      >
        <SessionIndicator startedAt={burstStartedAt} />
        <NavControls onOpenArchive={onOpenArchive} flareonId={activeFlareon.id} />
      </div>
    </main>
  );
}
