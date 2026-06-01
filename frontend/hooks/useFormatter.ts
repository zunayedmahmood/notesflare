// hooks/useFormatter.ts
"use client";

import { useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { DiffReviewState, FormattingDiff, BurstLine } from "@/types/formatting";

const INITIAL_STATE: DiffReviewState = {
  burstId: null,
  isLoading: false,
  isOpen: false,
  diffs: [],
  lines: [],
  error: null,
  processedAt: null,
};

export function useFormatter() {
  const [state, setState] = useState<DiffReviewState>(INITIAL_STATE);

  /**
   * Trigger format request for a burst.
   * Opens the diff panel on success.
   */
  const requestFormat = useCallback(async (burstId: number) => {
    setState((prev) => ({
      ...prev,
      burstId,
      isLoading: true,
      error: null,
    }));

    try {
      const result = await api.formatBurst(burstId);
      const lineCount = result.lines.length;
      const noDiffsMsg =
        lineCount === 0
          ? "Nothing to format — burst has no content."
          : `Already clean — checked ${lineCount} line${lineCount !== 1 ? "s" : ""}, no changes needed.`;
      setState({
        burstId,
        isLoading: false,
        isOpen: result.diff_count > 0,
        diffs: result.diffs,
        lines: result.lines,
        error: result.diff_count === 0 ? noDiffsMsg : null,
        processedAt: result.processed_at,
      });
    } catch (err: unknown) {
      console.error("[useFormatter] Format request failed:", err);
      const msg = err instanceof Error ? err.message : "Formatting failed. Please try again.";
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: msg,
      }));
    }
  }, []);

  /**
   * Close the diff review panel without losing state.
   * The diffs remain in state so the panel can be reopened.
   */
  const closePaenl = useCallback(() => {
    setState((prev) => ({ ...prev, isOpen: false }));
  }, []);

  /**
   * Fully reset formatting state.
   * Called when switching to a different Flareon or Burst.
   */
  const resetFormatting = useCallback(() => {
    setState(INITIAL_STATE);
  }, []);

  /**
   * Optimistically update a diff's status in local state.
   * The backend persists the change; this keeps the UI snappy.
   */
  const updateDiffStatus = useCallback(
    (diffId: string, status: "accepted" | "rejected") => {
      setState((prev) => ({
        ...prev,
        diffs: prev.diffs.map((d) =>
          d.diff_id === diffId ? { ...d, status } : d
        ),
      }));
    },
    []
  );

  /**
   * Optimistically update all pending diffs to the given status.
   */
  const updateAllDiffStatus = useCallback(
    (status: "accepted" | "rejected") => {
      setState((prev) => ({
        ...prev,
        diffs: prev.diffs.map((d) =>
          d.status === "pending" ? { ...d, status } : d
        ),
      }));
    },
    []
  );

  const pendingCount = state.diffs.filter((d) => d.status === "pending").length;
  const acceptedCount = state.diffs.filter((d) => d.status === "accepted").length;
  const hasDiffs = state.diffs.length > 0;

  return {
    ...state,
    requestFormat,
    closePaenl,
    resetFormatting,
    updateDiffStatus,
    updateAllDiffStatus,
    pendingCount,
    acceptedCount,
    hasDiffs,
  };
}
