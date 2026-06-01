// components/formatting/FormattedPreview.tsx
"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { FormattedBurstResponse } from "@/types/formatting";

interface FormattedPreviewProps {
  burstId: number;
  rawContent: string;   // Always available — used as fallback
}

export default function FormattedPreview({
  burstId,
  rawContent,
}: FormattedPreviewProps) {
  const [formatted, setFormatted] = useState<FormattedBurstResponse | null>(null);
  const [showFormatted, setShowFormatted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchFormatted() {
      setIsLoading(true);
      try {
        const result = await api.getFormattedBurst(burstId);
        if (!cancelled) {
          setFormatted(result);
          // Auto-show formatted if it exists and has accepted changes
          if (result.has_formatting) setShowFormatted(true);
        }
      } catch {
        // Silently ignore — formatted version may not exist yet
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    fetchFormatted();
    return () => { cancelled = true; };
  }, [burstId]);

  const displayText = showFormatted && formatted?.has_formatting
    ? formatted.formatted_text
    : rawContent;

  const hasFormattedVersion = formatted?.has_formatting ?? false;

  return (
    <div data-testid="formatted-preview">
      {/* Toggle — only shown if a formatted version exists */}
      {hasFormattedVersion && !isLoading && (
        <div
          style={{
            display: "flex",
            gap: "8px",
            marginBottom: "12px",
          }}
        >
          <button
            data-testid="view-raw-btn"
            onClick={() => setShowFormatted(false)}
            style={{
              background: "transparent",
              border: "none",
              color: showFormatted ? "var(--text-muted)" : "var(--accent-flare)",
              cursor: "pointer",
              fontFamily: "var(--font-ui)",
              fontSize: "11px",
              padding: 0,
              textDecoration: showFormatted ? "none" : "underline",
            }}
          >
            Raw
          </button>
          <span style={{ color: "var(--border-subtle)" }}>·</span>
          <button
            data-testid="view-formatted-btn"
            onClick={() => setShowFormatted(true)}
            style={{
              background: "transparent",
              border: "none",
              color: showFormatted ? "var(--accent-flare)" : "var(--text-muted)",
              cursor: "pointer",
              fontFamily: "var(--font-ui)",
              fontSize: "11px",
              padding: 0,
              textDecoration: showFormatted ? "underline" : "none",
            }}
          >
            Formatted
          </button>
        </div>
      )}

      {/* Content */}
      <p
        style={{
          fontFamily: "var(--font-writing)",
          fontSize: "var(--text-size-writing)",
          lineHeight: "var(--line-height-writing)",
          color: "var(--text-primary)",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          margin: 0,
        }}
      >
        {displayText || (
          <em style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
            Empty burst.
          </em>
        )}
      </p>
    </div>
  );
}
