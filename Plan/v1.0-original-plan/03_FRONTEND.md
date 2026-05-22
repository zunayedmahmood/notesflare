# NotesFlare — Frontend Build Instructions (Next.js + React + Tailwind)

> **AI Instruction File 03 of 08**
> This file covers the complete frontend: Next.js configuration, all React components, custom hooks, the API client module, and state management. Read `01_BRAND_AND_ARCHITECTURE.md` and `02_BACKEND.md` before this file. The frontend is a rendering layer — it holds no business logic. All decisions about sessions, bursts, and continuity are delegated to the backend.

---

## 1. ROLE OF THE FRONTEND

The frontend does exactly four things:

1. **Renders** the Flareon list and the writing area
2. **Forwards** user actions to the backend (open Flareon, save content)
3. **Debounces** saves — it does NOT decide when to create a new burst
4. **Restores** the last session on startup by calling `/api/state`

The frontend has no knowledge of the 30-minute continuity rule. That is the backend's job. The frontend simply opens whatever the backend says is the active burst.

---

## 2. TECHNOLOGY STACK

| Technology | Version | Purpose |
|---|---|---|
| Next.js | 14+ (App Router) | Framework + SSR capability |
| React | 18+ | Component model |
| TypeScript | 5+ | Type safety |
| Tailwind CSS | 3+ | Utility styling |
| CSS Variables | N/A | Design token system (from `01_BRAND_AND_ARCHITECTURE.md`) |

**No state management library.** React's `useState` and `useReducer` are sufficient for V1. Do not add Redux, Zustand, Jotai, or any other state library.

**No rich text editor library.** The writing area is a `textarea`. Do not add ProseMirror, TipTap, Lexical, Slate, or any editor library.

---

## 3. DIRECTORY STRUCTURE (FRONTEND ONLY)

```
frontend/
├── app/
│   ├── layout.tsx        # Root layout — fonts, global CSS, HTML shell
│   └── page.tsx          # Main app page — assembles layout, handles top-level state
├── components/
│   ├── Sidebar.tsx       # Left panel: Flareon list + create button
│   ├── WritingArea.tsx   # Right panel: burst display + textarea
│   ├── BurstBlock.tsx    # Individual past burst (read-only display)
│   └── FlareLabel.tsx    # Flareon name shown above writing area
├── hooks/
│   ├── useAutosave.ts    # Debounced save hook
│   └── useSession.ts     # Startup session restore hook
├── lib/
│   └── api.ts            # All HTTP calls to the Python backend
└── styles/
    └── globals.css       # CSS variables, base styles, typography
```

---

## 4. GLOBAL STYLES

### styles/globals.css

This file defines the entire design token system. All colors, fonts, and spacing come from CSS variables defined here. Components must use these variables — never hardcode hex values in component files.

```css
/* styles/globals.css */

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500&display=swap');

/* ─── Design Tokens ─────────────────────────────── */
:root {
  /* Backgrounds */
  --bg-base:         #0E0E10;
  --bg-surface:      #16161A;
  --bg-elevated:     #1C1C22;
  --border-subtle:   #2A2A35;

  /* Text */
  --text-primary:    #E8E8F0;
  --text-secondary:  #6B6B80;
  --text-muted:      #3A3A50;

  /* Accent */
  --accent-flare:    #7C6AF7;
  --accent-flare-dim:#3D356B;
  --accent-burst:    #4A9EFF;

  /* Typography */
  --font-writing:    'iA Writer Quattro', 'Courier Prime', 'Courier New', monospace;
  --font-ui:         'Inter', system-ui, -apple-system, sans-serif;
  --text-size-writing: 18px;
  --text-size-ui:    13px;
  --line-height-writing: 1.85;

  /* Layout */
  --sidebar-width:   220px;
  --writing-max-width: 680px;
  --writing-padding-x: 60px;
  --writing-padding-y: 80px;
}

/* ─── Reset ──────────────────────────────────────── */
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body {
  height: 100%;
  background-color: var(--bg-base);
  color: var(--text-primary);
  font-family: var(--font-ui);
  font-size: var(--text-size-ui);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Prevent default scrollbar style from conflicting */
::-webkit-scrollbar {
  width: 4px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: var(--border-subtle);
  border-radius: 2px;
}

/* ─── Selection ──────────────────────────────────── */
::selection {
  background: var(--accent-flare-dim);
  color: var(--text-primary);
}
```

---

## 5. API CLIENT

### lib/api.ts

This is the only file allowed to make HTTP calls. All components and hooks must import from here.

```typescript
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
```

---

## 6. CUSTOM HOOKS

### hooks/useAutosave.ts

Debounced autosave. Called every time the writing area content changes.

```typescript
// hooks/useAutosave.ts

import { useEffect, useRef } from "react";
import { api } from "@/lib/api";

const SAVE_DELAY_MS = 1000; // 1 second after typing stops

export function useAutosave(burstId: number | null, content: string) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedRef = useRef<string>("");

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
```

**Implementation notes:**
- `lastSavedRef` prevents redundant saves when content hasn't changed
- Errors are caught and logged but NOT shown to the user — the app must never interrupt writing
- `burstId === null` guard prevents calling save before a Flareon is open

### hooks/useSession.ts

Session restore hook. Runs once on app mount.

```typescript
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
        activeFlareon = await api.openFlareon(appState.last_opened_flareon_id);
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
```

---

## 7. COMPONENTS

### app/layout.tsx

```tsx
// app/layout.tsx
import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "NotesFlare",
  description: "Thought capture with near-zero cognitive friction.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

### app/page.tsx

The root page. Assembles the full layout. Holds the active content state that flows down to the writing area.

```tsx
// app/page.tsx
"use client";

import { useState } from "react";
import { useSession } from "@/hooks/useSession";
import { useAutosave } from "@/hooks/useAutosave";
import Sidebar from "@/components/Sidebar";
import WritingArea from "@/components/WritingArea";

export default function HomePage() {
  const { flareons, activeFlareon, isLoading, openFlareon, createFlareon } =
    useSession();

  // The content state lives here so both WritingArea and useAutosave share it
  const [content, setContent] = useState<string>("");

  // When activeFlareon changes, initialize content from the active burst
  const activeBurst = activeFlareon?.bursts.find(
    (b) => b.id === activeFlareon.active_burst_id
  );

  // Sync content when switching Flareons
  // We use a key prop on WritingArea to reset its internal state on Flareon switch
  useAutosave(activeFlareon?.active_burst_id ?? null, content);

  if (isLoading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          background: "var(--bg-base)",
          color: "var(--text-muted)",
          fontFamily: "var(--font-ui)",
          fontSize: "13px",
        }}
      >
        {/* Silent loading — no spinner, no text in the final version */}
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        height: "100vh",
        background: "var(--bg-base)",
        overflow: "hidden",
      }}
    >
      <Sidebar
        flareons={flareons}
        activeFlareonId={activeFlareon?.flareon.id ?? null}
        onSelectFlareon={openFlareon}
        onCreateFlareon={createFlareon}
      />
      <WritingArea
        key={activeFlareon?.flareon.id ?? "empty"}
        activeFlareon={activeFlareon}
        content={content}
        onContentChange={setContent}
      />
    </div>
  );
}
```

**Why `key={activeFlareon?.flareon.id}`:** Changing the `key` prop forces React to unmount and remount `WritingArea` when switching Flareons. This resets the `textarea` focus and scroll position cleanly without complex imperative logic.

### components/Sidebar.tsx

```tsx
// components/Sidebar.tsx
"use client";

import { useState } from "react";
import type { Flareon } from "@/lib/api";

interface SidebarProps {
  flareons: Flareon[];
  activeFlareonId: number | null;
  onSelectFlareon: (id: number) => void;
  onCreateFlareon: (name: string) => void;
}

export default function Sidebar({
  flareons,
  activeFlareonId,
  onSelectFlareon,
  onCreateFlareon,
}: SidebarProps) {
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");

  function handleCreate() {
    const trimmed = newName.trim();
    if (!trimmed) return;
    onCreateFlareon(trimmed);
    setNewName("");
    setCreating(false);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") handleCreate();
    if (e.key === "Escape") {
      setCreating(false);
      setNewName("");
    }
  }

  return (
    <aside
      style={{
        width: "var(--sidebar-width)",
        minWidth: "var(--sidebar-width)",
        height: "100vh",
        background: "var(--bg-surface)",
        borderRight: "1px solid var(--border-subtle)",
        display: "flex",
        flexDirection: "column",
        padding: "24px 0",
        overflow: "hidden",
      }}
    >
      {/* App name */}
      <div
        style={{
          padding: "0 16px 20px",
          color: "var(--text-secondary)",
          fontSize: "11px",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          fontWeight: 500,
        }}
      >
        NotesFlare
      </div>

      {/* Flareon list */}
      <nav style={{ flex: 1, overflowY: "auto", padding: "0 8px" }}>
        {flareons.map((f) => (
          <button
            key={f.id}
            onClick={() => onSelectFlareon(f.id)}
            style={{
              display: "block",
              width: "100%",
              textAlign: "left",
              padding: "8px 10px",
              borderRadius: "6px",
              border: "none",
              cursor: "pointer",
              fontSize: "var(--text-size-ui)",
              fontFamily: "var(--font-ui)",
              color:
                f.id === activeFlareonId
                  ? "var(--text-primary)"
                  : "var(--text-secondary)",
              background:
                f.id === activeFlareonId
                  ? "var(--accent-flare-dim)"
                  : "transparent",
              marginBottom: "2px",
              transition: "background 0.1s, color 0.1s",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
            onMouseEnter={(e) => {
              if (f.id !== activeFlareonId) {
                (e.currentTarget as HTMLButtonElement).style.background =
                  "var(--bg-elevated)";
              }
            }}
            onMouseLeave={(e) => {
              if (f.id !== activeFlareonId) {
                (e.currentTarget as HTMLButtonElement).style.background =
                  "transparent";
              }
            }}
          >
            {f.name}
          </button>
        ))}
      </nav>

      {/* Create Flareon */}
      <div style={{ padding: "12px 8px 0" }}>
        {creating ? (
          <input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={() => {
              if (!newName.trim()) {
                setCreating(false);
              }
            }}
            placeholder="Flareon name..."
            style={{
              width: "100%",
              background: "var(--bg-elevated)",
              border: "1px solid var(--accent-flare)",
              borderRadius: "6px",
              padding: "7px 10px",
              color: "var(--text-primary)",
              fontSize: "var(--text-size-ui)",
              fontFamily: "var(--font-ui)",
              outline: "none",
            }}
          />
        ) : (
          <button
            onClick={() => setCreating(true)}
            style={{
              width: "100%",
              padding: "7px 10px",
              background: "transparent",
              border: "1px dashed var(--border-subtle)",
              borderRadius: "6px",
              color: "var(--text-muted)",
              fontSize: "var(--text-size-ui)",
              fontFamily: "var(--font-ui)",
              cursor: "pointer",
              textAlign: "left",
              transition: "border-color 0.15s, color 0.15s",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.borderColor =
                "var(--accent-flare)";
              (e.currentTarget as HTMLButtonElement).style.color =
                "var(--text-secondary)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.borderColor =
                "var(--border-subtle)";
              (e.currentTarget as HTMLButtonElement).style.color =
                "var(--text-muted)";
            }}
          >
            + New Flareon
          </button>
        )}
      </div>
    </aside>
  );
}
```

### components/BurstBlock.tsx

Renders a single historical burst (read-only).

```tsx
// components/BurstBlock.tsx

interface BurstBlockProps {
  startedAt: string;
  content: string;
}

function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function BurstBlock({ startedAt, content }: BurstBlockProps) {
  if (!content.trim()) return null; // Don't show empty historical bursts

  return (
    <div style={{ marginBottom: "48px" }}>
      {/* Burst timestamp label */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          marginBottom: "20px",
        }}
      >
        <span
          style={{
            fontSize: "11px",
            color: "var(--accent-burst)",
            fontFamily: "var(--font-ui)",
            letterSpacing: "0.05em",
            opacity: 0.7,
          }}
        >
          {formatTimestamp(startedAt)}
        </span>
        <div
          style={{
            flex: 1,
            height: "1px",
            background: "var(--border-subtle)",
            opacity: 0.5,
          }}
        />
      </div>

      {/* Past burst content — read-only */}
      <div
        style={{
          fontFamily: "var(--font-writing)",
          fontSize: "var(--text-size-writing)",
          lineHeight: "var(--line-height-writing)",
          color: "var(--text-secondary)",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {content}
      </div>
    </div>
  );
}
```

### components/FlareLabel.tsx

Shows the current Flareon name above the writing area.

```tsx
// components/FlareLabel.tsx

interface FlareLabelProps {
  name: string;
}

export default function FlareLabel({ name }: FlareLabelProps) {
  return (
    <div
      style={{
        fontSize: "11px",
        color: "var(--text-muted)",
        fontFamily: "var(--font-ui)",
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        marginBottom: "48px",
        fontWeight: 500,
      }}
    >
      {name}
    </div>
  );
}
```

### components/WritingArea.tsx

The most important component. Contains all past bursts + the active textarea.

```tsx
// components/WritingArea.tsx
"use client";

import { useEffect, useRef } from "react";
import type { FlareonDetail } from "@/lib/api";
import BurstBlock from "./BurstBlock";
import FlareLabel from "./FlareLabel";

interface WritingAreaProps {
  activeFlareon: FlareonDetail | null;
  content: string;
  onContentChange: (content: string) => void;
}

export default function WritingArea({
  activeFlareon,
  content,
  onContentChange,
}: WritingAreaProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-focus textarea when Flareon loads
  useEffect(() => {
    if (activeFlareon && textareaRef.current) {
      textareaRef.current.focus();
      // Place cursor at end of content
      const len = textareaRef.current.value.length;
      textareaRef.current.setSelectionRange(len, len);
    }
  }, [activeFlareon]);

  // Initialize content from active burst when Flareon opens
  useEffect(() => {
    if (activeFlareon) {
      const activeBurst = activeFlareon.bursts.find(
        (b) => b.id === activeFlareon.active_burst_id
      );
      onContentChange(activeBurst?.content ?? "");
    }
  }, [activeFlareon?.active_burst_id]);

  // Auto-resize textarea to fit content
  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    onContentChange(e.target.value);
    autoResize(e.target);
  }

  function autoResize(el: HTMLTextAreaElement) {
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }

  // Empty state
  if (!activeFlareon) {
    return (
      <main
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--text-muted)",
          fontFamily: "var(--font-ui)",
          fontSize: "13px",
        }}
      >
        Select a Flareon to begin.
      </main>
    );
  }

  const pastBursts = activeFlareon.bursts.filter(
    (b) => b.id !== activeFlareon.active_burst_id
  );

  return (
    <main
      style={{
        flex: 1,
        overflowY: "auto",
        padding: `var(--writing-padding-y) var(--writing-padding-x)`,
      }}
    >
      <div
        style={{
          maxWidth: "var(--writing-max-width)",
          margin: "0 auto",
        }}
      >
        <FlareLabel name={activeFlareon.flareon.name} />

        {/* Historical bursts (read-only) */}
        {pastBursts.map((burst) => (
          <BurstBlock
            key={burst.id}
            startedAt={burst.started_at}
            content={burst.content}
          />
        ))}

        {/* Active burst divider — only show if there are past bursts */}
        {pastBursts.length > 0 && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              marginBottom: "24px",
            }}
          >
            <span
              style={{
                fontSize: "11px",
                color: "var(--accent-burst)",
                fontFamily: "var(--font-ui)",
                letterSpacing: "0.05em",
                opacity: 0.9,
              }}
            >
              {new Date(
                activeFlareon.bursts.find(
                  (b) => b.id === activeFlareon.active_burst_id
                )?.started_at ?? ""
              ).toLocaleString(undefined, {
                month: "short",
                day: "numeric",
                hour: "numeric",
                minute: "2-digit",
              })}
            </span>
            <div
              style={{
                flex: 1,
                height: "1px",
                background: "var(--accent-flare-dim)",
              }}
            />
          </div>
        )}

        {/* Active writing textarea */}
        <textarea
          ref={textareaRef}
          value={content}
          onChange={handleChange}
          placeholder="Start writing..."
          rows={1}
          style={{
            width: "100%",
            background: "transparent",
            border: "none",
            outline: "none",
            resize: "none",
            overflow: "hidden",
            fontFamily: "var(--font-writing)",
            fontSize: "var(--text-size-writing)",
            lineHeight: "var(--line-height-writing)",
            color: "var(--text-primary)",
            caretColor: "var(--cursor)",
            padding: 0,
            minHeight: "60vh", // Ensure the writing area feels spacious
          }}
          spellCheck={true}
          autoCorrect="on"
          autoCapitalize="sentences"
        />
      </div>
    </main>
  );
}
```

---

## 8. NEXT.JS CONFIGURATION

### next.config.js

```javascript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Required for Electron — disables image optimization that needs a server
  output: "export",
  // Electron loads the app from the filesystem, not a web server
  trailingSlash: true,
  // Disable telemetry
  experimental: {},
};

module.exports = nextConfig;
```

**Important:** `output: "export"` generates a static build in `/out`. Electron loads this via `file://` protocol. This means:
- No server-side data fetching (`getServerSideProps` is unavailable)
- All data fetching happens client-side via `useEffect` and `api.ts`
- This is correct for our architecture

### tailwind.config.js

```javascript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
```

Tailwind is available but should be used sparingly. CSS variables in `globals.css` are the primary styling system. Use Tailwind only for layout utilities where convenient.

### tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./frontend/*"]
    }
  },
  "include": ["frontend/**/*.ts", "frontend/**/*.tsx"],
  "exclude": ["node_modules"]
}
```

---

## 9. PACKAGE.JSON (PARTIAL — FRONTEND DEPS)

```json
{
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.4.0"
  }
}
```

Full `package.json` including Electron dependencies is in `05_ELECTRON_SHELL.md`.

---

## 10. VERIFICATION CHECKLIST

Before moving to the Electron shell integration, verify:

- [ ] `next dev` starts without TypeScript errors
- [ ] The app loads in the browser at `localhost:3000`
- [ ] With the backend running, the Flareon list appears in the sidebar
- [ ] Creating a new Flareon via the sidebar creates it and opens it immediately
- [ ] Typing in the writing area triggers autosave after 1 second
- [ ] Switching between Flareons switches the writing area content correctly
- [ ] Past bursts appear above the active textarea in chronological order
- [ ] Refreshing the page restores the last-opened Flareon

---

## 11. COMMON MISTAKES TO AVOID

**Do not:**
- Use `localStorage` for any state — this is not a browser app; use the backend
- Use `useEffect` to poll the backend for content changes — there are no real-time updates in V1
- Make HTTP calls outside of `lib/api.ts`
- Add any UI for formatting (bold button, header levels, etc.)
- Show a save status indicator (saving must be invisible)
- Show loading spinners for any operation that takes < 300ms

**Do:**
- Use `key` prop changes to reset component state when Flareon switches
- Auto-resize the textarea so it never shows a scrollbar
- Focus the textarea immediately on Flareon load
- Place cursor at the end of existing content, not the beginning
