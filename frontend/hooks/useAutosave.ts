// hooks/useAutosave.ts

import { useEffect, useRef } from "react";
import { api } from "@/lib/api";

const SAVE_DELAY_MS = 1000; // 1 second after typing stops

export function useAutosave(burstId: number | null, content: string) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedRef = useRef<string>("");
  const lastBurstIdRef = useRef<number | null>(null);

  // If the active burst has changed (switching Flareons),
  // align lastSavedRef with the incoming content and track the new ID.
  if (burstId !== lastBurstIdRef.current) {
    lastBurstIdRef.current = burstId;
    lastSavedRef.current = content;
  }

  useEffect(() => {
    // Don't save if no active burst or content hasn't changed
    if (burstId === null) return;
    if (content === lastSavedRef.current) return;

    // Clear any pending save
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    // Schedule save after SAVE_DELAY_MS of inactivity
    timerRef.current = setTimeout(async () => {
      try {
        await api.saveContent(burstId, content);
        lastSavedRef.current = content;
      } catch (err) {
        console.error("Autosave failed:", err);
        // Do not surface this error to the user in V1.
        // Silently retry on next keystroke.
      }
    }, SAVE_DELAY_MS);

    // Cleanup timer on unmount or next effect run
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [burstId, content]);
}
