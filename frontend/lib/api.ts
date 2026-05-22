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

// ─── V1.1 Types ──────────────────────────────────────────────────────────────

export interface SessionResumeResponse {
  has_session: boolean;
  flareon: Flareon | null;
  burst_id: number | null;
  stream_content: string;
  started_at: string | null;
}

export interface FlareonSwitchResponse {
  flareon: Flareon;
  burst_id: number;
  stream_content: string;
  started_at: string;
}

export interface AppendChunkResponse {
  success: boolean;
  sequence_number: number;
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
  // ─── V1 (unchanged) ────────────────────────────────────────────────────────
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

  // ─── V1.1 (new) ────────────────────────────────────────────────────────────
  resumeSession: () =>
    get<SessionResumeResponse>("/session/resume"),

  switchFlareon: (flareonId: number) =>
    get<FlareonSwitchResponse>(`/session/switch/${flareonId}`),

  appendChunk: (burst_id: number, text: string) =>
    post<AppendChunkResponse>("/burst/append", { burst_id, text }),
};

