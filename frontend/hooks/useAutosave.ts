// hooks/useAutosave.ts
"use client";

import { useEffect, useRef } from "react";
import { api } from "@/lib/api";

const SAVE_DELAY_MS = 1000;

interface AutosaveOptions {
  burstId: number | null;
  getDelta: () => string;         // Returns only new text since last sync
  onSaveSuccess: () => void;      // Called after successful save — marks buffer synced
}

export function useAutosave({ burstId, getDelta, onSaveSuccess }: AutosaveOptions) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Reset timer whenever burstId changes (Flareon switch)
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [burstId]);

  function scheduleAppend() {
    if (burstId === null) return;

    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(async () => {
      const delta = getDelta();
      if (!delta) return; // Nothing new to save

      try {
        await api.appendChunk(burstId, delta);
        onSaveSuccess();
      } catch (err) {
        console.error("[useAutosave] Append failed:", err);
        // Silent failure. Next keystroke will schedule another attempt.
        // The delta accumulates, so no content is lost — just delayed.
      }
    }, SAVE_DELAY_MS);
  }

  return { scheduleAppend };
}
