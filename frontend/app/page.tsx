// app/page.tsx
"use client";

import { useSession } from "@/hooks/useSession";
import { useFormatter } from "@/hooks/useFormatter";
import { useDiffReview } from "@/hooks/useDiffReview";
import Sidebar from "@/components/sidebar/Sidebar";
import StreamShell from "@/components/stream/StreamShell";
import LoadingScreen from "@/components/common/LoadingScreen";

export default function StreamPage() {
  const {
    flareons,
    activeFlareon,
    activeBurstId,
    streamContent,
    burstStartedAt,
    isLoading,
    error,
    initSession,
    switchFlareon,
    createFlareon,
  } = useSession();

  const formatter = useFormatter();

  const { acceptDiff, rejectDiff, acceptAll, rejectAll } = useDiffReview({
    burstId: activeBurstId,
    onDiffUpdate: formatter.updateDiffStatus,
    onBulkUpdate: formatter.updateAllDiffStatus,
  });

  if (isLoading) {
    return <LoadingScreen />;
  }

  if (error) {
    return (
      <div
        style={{
          height: "100vh",
          background: "var(--bg-base)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--text-primary)",
          fontFamily: "var(--font-ui)",
          padding: "20px",
          textAlign: "center",
        }}
      >
        <div
          style={{
            maxWidth: "400px",
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "12px",
            padding: "32px",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.2)",
          }}
        >
          <div
            style={{
              fontSize: "24px",
              marginBottom: "16px",
              color: "var(--accent-flare)",
              fontWeight: 600,
            }}
          >
            Connection Issue
          </div>
          <p
            style={{
              fontSize: "13px",
              color: "var(--text-secondary)",
              marginBottom: "24px",
              lineHeight: "1.6",
            }}
          >
            {error}
          </p>
          <button
            onClick={() => initSession()}
            style={{
              background: "var(--accent-flare)",
              color: "#FFF",
              border: "none",
              borderRadius: "6px",
              padding: "10px 20px",
              fontSize: "12px",
              cursor: "pointer",
              fontFamily: "var(--font-ui)",
              fontWeight: 500,
              transition: "opacity 0.15s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.85")}
            onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        height: "100vh",
        background: "var(--bg-base)",
        overflow: "hidden",
      }}
    >
      <Sidebar
        flareons={flareons}
        activeFlareonId={activeFlareon?.id ?? null}
        onSelectFlareon={(id) => {
          formatter.resetFormatting();
          switchFlareon(id);
        }}
        onCreateFlareon={createFlareon}
      />
      <StreamShell
        key={`${activeFlareon?.id ?? "empty"}-${activeBurstId ?? "none"}`}
        activeFlareon={activeFlareon}
        burstId={activeBurstId}
        initialContent={streamContent}
        burstStartedAt={burstStartedAt}
        onOpenArchive={() => {}}
        isFormatLoading={formatter.isLoading}
        hasDiffs={formatter.hasDiffs}
        pendingDiffCount={formatter.pendingCount}
        isDiffPanelOpen={formatter.isOpen}
        diffs={formatter.diffs}
        onFormatClick={() => {
          if (activeBurstId !== null) formatter.requestFormat(activeBurstId);
        }}
        onDiffAccept={acceptDiff}
        onDiffReject={rejectDiff}
        onDiffAcceptAll={acceptAll}
        onDiffRejectAll={rejectAll}
        onDiffPanelClose={formatter.closePaenl}
        formatError={formatter.error}
      />
    </div>
  );
}
