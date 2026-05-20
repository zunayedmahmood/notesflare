// hooks/useSession.ts

import { useState, useEffect } from "react";
import { api, FlareonDetail, Flareon } from "@/lib/api";

interface SessionState {
  flareons: Flareon[];
  activeFlareon: FlareonDetail | null;
  isLoading: boolean;
}

export function useSession() {
  const [state, setState] = useState<SessionState>({
    flareons: [],
    activeFlareon: null,
    isLoading: true,
  });

  useEffect(() => {
    initSession();
  }, []);

  async function initSession() {
    try {
      // Load all Flareons for sidebar
      const flareons = await api.listFlareons();

      // Check if there's a previous session to restore
      const appState = await api.getAppState();

      let activeFlareon: FlareonDetail | null = null;
      if (appState.last_opened_flareon_id !== null) {
        try {
          activeFlareon = await api.openFlareon(appState.last_opened_flareon_id);
        } catch (openErr) {
          console.error("Failed to restore last opened Flareon:", openErr);
        }
      }

      setState({ flareons, activeFlareon, isLoading: false });
    } catch (err) {
      console.error("Session init failed:", err);
      setState((prev) => ({ ...prev, isLoading: false }));
    }
  }

  async function openFlareon(id: number) {
    const detail = await api.openFlareon(id);
    const flareons = await api.listFlareons(); // Refresh to update last_opened_at order
    setState((prev) => ({ ...prev, flareons, activeFlareon: detail }));
  }

  async function createFlareon(name: string) {
    const newFlareon = await api.createFlareon(name);
    // Immediately open the newly created Flareon
    await openFlareon(newFlareon.id);
  }

  return {
    ...state,
    openFlareon,
    createFlareon,
  };
}
