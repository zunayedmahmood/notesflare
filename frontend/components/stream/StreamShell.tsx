// components/stream/StreamShell.tsx
"use client";

import StreamInput from "@/components/stream/StreamInput";
import SessionIndicator from "@/components/stream/SessionIndicator";
import NavControls from "@/components/stream/NavControls";
import EmptyState from "@/components/common/EmptyState";
import FormatButton from "@/components/formatting/FormatButton";
import DiffReviewPanel from "@/components/formatting/DiffReviewPanel";
import type { Flareon } from "@/lib/api";
import type { FormattingDiff } from "@/types/formatting";

interface StreamShellProps {
  activeFlareon: Flareon | null;
  burstId: number | null;
  initialContent: string;
  burstStartedAt: string | null;
  onOpenArchive: () => void;

  // NEW formatting props:
  isFormatLoading: boolean;
  hasDiffs: boolean;
  pendingDiffCount: number;
  isDiffPanelOpen: boolean;
  diffs: FormattingDiff[];
  onFormatClick: () => void;
  onDiffAccept: (diffId: string) => void;
  onDiffReject: (diffId: string) => void;
  onDiffAcceptAll: () => void;
  onDiffRejectAll: () => void;
  onDiffPanelClose: () => void;
  formatError: string | null;
}

export default function StreamShell({
  activeFlareon,
  burstId,
  initialContent,
  burstStartedAt,
  onOpenArchive,
  isFormatLoading,
  hasDiffs,
  pendingDiffCount,
  isDiffPanelOpen,
  diffs,
  onFormatClick,
  onDiffAccept,
  onDiffReject,
  onDiffAcceptAll,
  onDiffRejectAll,
  onDiffPanelClose,
  formatError,
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

      {/* Stream input — top-aligned writing area */}
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "flex-start",
          paddingTop: "10vh",
          padding: "10vh var(--writing-padding-x) 0",
          maxWidth: "calc(var(--writing-max-width) + calc(var(--writing-padding-x) * 2))",
          width: "100%",
          alignSelf: "center",
          overflowY: "auto",
        }}
      >
        <StreamInput
          key={`${burstId}-${activeFlareon.id}`}
          burstId={burstId}
          initialContent={initialContent}
        />
      </div>

      {/* Bottom controls — session indicator + nav + format button */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px var(--writing-padding-x) 24px",
          borderTop: "1px solid var(--border-subtle)",
          opacity: 0.6,
          transition: "opacity 0.15s ease",
        }}
        onMouseEnter={(e) =>
          ((e.currentTarget as HTMLDivElement).style.opacity = "1")
        }
        onMouseLeave={(e) =>
          ((e.currentTarget as HTMLDivElement).style.opacity = "0.6")
        }
      >
        <SessionIndicator startedAt={burstStartedAt} />
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <NavControls onOpenArchive={onOpenArchive} flareonId={activeFlareon.id} />
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "4px" }}>
            {formatError && (
              <span
                style={{
                  fontFamily: "var(--font-ui)",
                  fontSize: "10px",
                  color: "var(--text-muted)",
                  letterSpacing: "0.03em",
                  whiteSpace: "nowrap",
                }}
              >
                {formatError}
              </span>
            )}
            <FormatButton
              onClick={onFormatClick}
              isLoading={isFormatLoading}
              hasDiffs={hasDiffs}
              pendingCount={pendingDiffCount}
              disabled={!burstId}
            />
          </div>
        </div>
      </div>

      {/* Diff review panel — fixed position, overlays right side */}
      <DiffReviewPanel
        isOpen={isDiffPanelOpen}
        diffs={diffs}
        pendingCount={pendingDiffCount}
        onAccept={onDiffAccept}
        onReject={onDiffReject}
        onAcceptAll={onDiffAcceptAll}
        onRejectAll={onDiffRejectAll}
        onClose={onDiffPanelClose}
      />
    </main>
  );
}
