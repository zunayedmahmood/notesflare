// app/flareon/[id]/ArchivePageClient.tsx
"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, FlareonDetail } from "@/lib/api";
import BurstTimeline from "@/components/archive/BurstTimeline";

export default function ArchivePageClient() {
  const params = useParams();
  const router = useRouter();
  const flareonId = Number(params.id);

  const [detail, setDetail] = useState<FlareonDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function loadArchive() {
    if (!flareonId) return;
    setIsLoading(true);
    setError(null);
    api.openFlareon(flareonId)
      .then((d) => {
        setDetail(d);
        setIsLoading(false);
      })
      .catch((err: any) => {
        console.error("Failed to load archive:", err);
        setError(err.message || "Failed to load archive details.");
        setIsLoading(false);
      });
  }

  useEffect(() => {
    loadArchive();
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
            Archive Error
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
          <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
            <button
              onClick={() => router.push("/")}
              style={{
                background: "transparent",
                color: "var(--text-secondary)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "6px",
                padding: "10px 20px",
                fontSize: "12px",
                cursor: "pointer",
                fontFamily: "var(--font-ui)",
                fontWeight: 500,
                transition: "background 0.15s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-elevated)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              ← Stream
            </button>
            <button
              onClick={loadArchive}
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
              Retry
            </button>
          </div>
        </div>
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
