// app/page.tsx
"use client";

import { useState } from "react";
import { useSession } from "@/hooks/useSession";
import { useAutosave } from "@/hooks/useAutosave";
import Sidebar from "@/components/Sidebar";
import WritingArea from "@/components/WritingArea";

export default function HomePage() {
  const { flareons, activeFlareon, isLoading, openFlareon, createFlareon } =
    useSession();

  // The content state lives here so both WritingArea and useAutosave share it
  const [content, setContent] = useState<string>("");

  // Sync content when switching Flareons
  useAutosave(activeFlareon?.active_burst_id ?? null, content);

  if (isLoading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          background: "var(--bg-base)",
          color: "var(--text-muted)",
          fontFamily: "var(--font-ui)",
          fontSize: "13px",
        }}
      >
        {/* Silent loading — no spinner, no text in the final version */}
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
        activeFlareonId={activeFlareon?.flareon.id ?? null}
        onSelectFlareon={openFlareon}
        onCreateFlareon={createFlareon}
      />
      <WritingArea
        key={activeFlareon?.flareon.id ?? "empty"}
        activeFlareon={activeFlareon}
        content={content}
        onContentChange={setContent}
      />
    </div>
  );
}
