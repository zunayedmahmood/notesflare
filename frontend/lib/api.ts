// lib/api.ts

const BASE_URL = "http://127.0.0.1:8000/api";

// ─── Types (mirroring backend Pydantic models) ───────────────────────────────

export interface Flareon {
  id: number;
  name: string;
  created_at: string;
  last_opened_at: string | null;
}

export interface Burst {
  id: number;
  flareon_id: number;
  started_at: string;
  content: string;
}

export interface FlareonDetail {
  flareon: Flareon;
  bursts: Burst[];
  active_burst_id: number;
}

export interface AppState {
  last_opened_flareon_id: number | null;
  last_opened_burst_id: number | null;
}

// ─── Request helpers ─────────────────────────────────────────────────────────

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json();
}

// ─── API Functions ────────────────────────────────────────────────────────────

export const api = {
  health: () => get<{ status: string }>("/health"),

  getAppState: () => get<AppState>("/state"),

  listFlareons: () =>
    get<{ flareons: Flareon[] }>("/flareons").then((r) => r.flareons),

  createFlareon: (name: string) =>
    post<Flareon>("/flareons", { name }),

  openFlareon: (id: number) =>
    get<FlareonDetail>(`/flareons/${id}`),

  saveContent: (burst_id: number, content: string) =>
    post<{ success: boolean; burst_entry_id: number }>("/save", {
      burst_id,
      content,
    }),
};
