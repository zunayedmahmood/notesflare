// hooks/useDiffReview.ts
"use client";

import { useCallback } from "react";
import { api } from "@/lib/api";

interface UseDiffReviewOptions {
  burstId: number | null;
  onDiffUpdate: (diffId: string, status: "accepted" | "rejected") => void;
  onBulkUpdate: (status: "accepted" | "rejected") => void;
}

export function useDiffReview({
  burstId,
  onDiffUpdate,
  onBulkUpdate,
}: UseDiffReviewOptions) {
  /**
   * Accept a single diff.
   * Optimistic: updates UI first, then persists to backend.
   * On failure: logs error silently. The optimistic state stays.
   * The backend is the source of truth on next reload.
   */
  const acceptDiff = useCallback(
    async (diffId: string) => {
      onDiffUpdate(diffId, "accepted");
      try {
        await api.acceptDiff(diffId);
      } catch (err) {
        console.error("[useDiffReview] acceptDiff failed:", err);
      }
    },
    [onDiffUpdate]
  );

  /**
   * Reject a single diff.
   */
  const rejectDiff = useCallback(
    async (diffId: string) => {
      onDiffUpdate(diffId, "rejected");
      try {
        await api.rejectDiff(diffId);
      } catch (err) {
        console.error("[useDiffReview] rejectDiff failed:", err);
      }
    },
    [onDiffUpdate]
  );

  /**
   * Accept all pending diffs for the current burst.
   */
  const acceptAll = useCallback(async () => {
    if (!burstId) return;
    onBulkUpdate("accepted");
    try {
      await api.acceptAllDiffs(burstId);
    } catch (err) {
      console.error("[useDiffReview] acceptAll failed:", err);
    }
  }, [burstId, onBulkUpdate]);

  /**
   * Reject all pending diffs for the current burst.
   */
  const rejectAll = useCallback(async () => {
    if (!burstId) return;
    onBulkUpdate("rejected");
    try {
      await api.rejectAllDiffs(burstId);
    } catch (err) {
      console.error("[useDiffReview] rejectAll failed:", err);
    }
  }, [burstId, onBulkUpdate]);

  return { acceptDiff, rejectDiff, acceptAll, rejectAll };
}
