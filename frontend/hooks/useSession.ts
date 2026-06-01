// hooks/useSession.ts
"use client";

import { useState, useEffect } from "react";
import { api, Flareon, SessionResumeResponse, FlareonSwitchResponse } from "@/lib/api";

interface SessionState {
  flareons: Flareon[];
  activeFlareon: Flareon | null;
  activeBurstId: number | null;
  streamContent: string;
  burstStartedAt: string | null;
  isLoading: boolean;
  error: string | null;
}

export function useSession() {
  const [state, setState] = useState<SessionState>({
    flareons: [],
    activeFlareon: null,
    activeBurstId: null,
    streamContent: "",
    burstStartedAt: null,
    isLoading: true,
    error: null,
  });

  useEffect(() => {
    initSession();
  }, []);

  async function initSession() {
    try {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));
      const [flareons, resume] = await Promise.all([
        api.listFlareons(),
        api.resumeSession(),
      ]);

      setState({
        flareons,
        activeFlareon: resume.flareon,
        activeBurstId: resume.burst_id,
        streamContent: resume.stream_content,
        burstStartedAt: resume.started_at,
        isLoading: false,
        error: null,
      });
    } catch (err: any) {
      console.error("[useSession] Init failed:", err);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err?.message || "Could not connect to backend.",
      }));
    }
  }

  async function switchFlareon(flareonId: number) {
    try {
      const result: FlareonSwitchResponse = await api.switchFlareon(flareonId);
      // Refresh flareon list to update ordering
      const flareons = await api.listFlareons();
      setState((prev) => ({
        ...prev,
        flareons,
        activeFlareon: result.flareon,
        activeBurstId: result.burst_id,
        streamContent: result.stream_content,
        burstStartedAt: result.started_at,
        error: null,
      }));
    } catch (err: any) {
      console.error("[useSession] Switch failed:", err);
      setState((prev) => ({
        ...prev,
        error: err?.message || "Failed to switch Flareon.",
      }));
    }
  }

  async function createFlareon(name: string): Promise<void> {
    try {
      await api.createFlareon(name);
      // After creation, switch to the new Flareon using the standard switch path
      const flareons = await api.listFlareons();
      const created = flareons.find((f) => f.name === name);
      if (created) {
        await switchFlareon(created.id);
      } else {
        setState((prev) => ({
          ...prev,
          flareons,
          error: null,
        }));
      }
    } catch (err: any) {
      console.error("[useSession] Create failed:", err);
      setState((prev) => ({
        ...prev,
        error: err?.message || "Failed to create Flareon.",
      }));
      throw err;
    }
  }

  return {
    ...state,
    initSession,
    switchFlareon,
    createFlareon,
  };
}
