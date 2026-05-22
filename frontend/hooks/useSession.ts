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
      // Single call replaces the V1 two-step startup
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
    } catch (err) {
      console.error("[useSession] Init failed:", err);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: "Could not connect to backend.",
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
      }));
    } catch (err) {
      console.error("[useSession] Switch failed:", err);
    }
  }

  async function createFlareon(name: string): Promise<void> {
    await api.createFlareon(name);
    // After creation, switch to the new Flareon using the standard switch path
    const flareons = await api.listFlareons();
    const created = flareons.find((f) => f.name === name);
    if (created) {
      await switchFlareon(created.id);
    }
  }

  return {
    ...state,
    switchFlareon,
    createFlareon,
  };
}
