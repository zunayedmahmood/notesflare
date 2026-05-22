// app/flareon/[id]/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, FlareonDetail } from "@/lib/api";
import BurstTimeline from "@/components/archive/BurstTimeline";

// Required for static export with dynamic routes
export const dynamic = "force-static";

export default function ArchivePage() {
  const params = useParams();
  const router = useRouter();
  const flareonId = Number(params.id);

  const [detail, setDetail] = useState<FlareonDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!flareonId) return;
    api.openFlareon(flareonId).then((d) => {
      setDetail(d);
      setIsLoading(false);
    });
  }, [flareonId]);

  if (isLoading) {
    return (
      <div
        style={{
          height: "100vh",
          background: "var(--bg-base)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--text-muted)",
          fontFamily: "var(--font-ui)",
          fontSize: "13px",
        }}
      >
        Loading...
      </div>
    );
  }

  if (!detail) {
    return (
      <div
        style={{
          height: "100vh",
          background: "var(--bg-base)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--text-muted)",
          fontFamily: "var(--font-ui)",
          fontSize: "13px",
        }}
      >
        Flareon not found.
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
      {/* Back to stream */}
      <button
        onClick={() => router.push("/")}
        data-testid="back-to-stream"
        style={{
          position: "fixed",
          top: "20px",
          left: "20px",
          background: "none",
          border: "none",
          cursor: "pointer",
          fontFamily: "var(--font-ui)",
          fontSize: "11px",
          color: "var(--text-secondary)",
          letterSpacing: "0.03em",
          zIndex: 10,
        }}
      >
        ← Stream
      </button>

      <BurstTimeline
        flareonName={detail.flareon.name}
        bursts={detail.bursts}
        activeBurstId={detail.active_burst_id}
      />
    </div>
  );
}
