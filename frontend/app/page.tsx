// app/page.tsx
"use client";

import { useSession } from "@/hooks/useSession";
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
    switchFlareon,
    createFlareon,
  } = useSession();

  if (isLoading) {
    return <LoadingScreen />;
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
        onSelectFlareon={switchFlareon}
        onCreateFlareon={createFlareon}
      />
      <StreamShell
        key={`${activeFlareon?.id ?? "empty"}-${activeBurstId ?? "none"}`}
        activeFlareon={activeFlareon}
        burstId={activeBurstId}
        initialContent={streamContent}
        burstStartedAt={burstStartedAt}
        onOpenArchive={() => {}}
      />
    </div>
  );
}
