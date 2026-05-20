# NotesFlare — Electron Shell Build Instructions

> **AI Instruction File 04 of 08**
> This file covers the complete Electron layer: window creation, startup sequence, IPC bridge, preload configuration, process lifecycle management, and how Electron glues together the Next.js frontend and the Python backend. Read `01_BRAND_AND_ARCHITECTURE.md`, `02_BACKEND.md`, and `03_FRONTEND.md` before this file.

---

## 1. ROLE OF ELECTRON

Electron is the desktop shell. Its responsibilities are:

1. **Window management** — Create and configure the main app window
2. **Backend lifecycle** — Spawn the Python backend process at startup and kill it at quit
3. **Frontend loading** — Load the Next.js static build via `file://` protocol
4. **Native OS integration** — Set window title, icon, and frame appearance
5. **Startup gating** — Wait for the Python backend to be ready before showing the window

Electron does NOT own any data, session, or UI logic. It is infrastructure.

---

## 2. TECHNOLOGY STACK

| Technology | Version | Purpose |
|---|---|---|
| Electron | 30+ | Desktop shell |
| TypeScript | 5+ | Type safety |
| electron-builder | 24+ | Packaging for distribution (future) |
| Node.js | 20+ | Runtime (comes with Electron) |

**No additional Electron plugins in V1.** Do not add `electron-store`, `electron-log`, or any other Electron utility libraries. Everything needed for V1 can be done with Electron's built-in APIs.

---

## 3. DIRECTORY STRUCTURE (ELECTRON ONLY)

```
electron/
├── main.ts        # Entry point: window creation, backend spawn, app lifecycle
├── preload.ts     # Sandboxed bridge: exposes safe APIs to renderer
└── window.ts      # Window size and appearance constants
```

---

## 4. WINDOW CONSTANTS

### electron/window.ts

Define all window configuration in one place. Do not scatter magic numbers through `main.ts`.

```typescript
// electron/window.ts

export const WINDOW_CONFIG = {
  width: 1200,
  minWidth: 800,
  height: 800,
  minHeight: 600,
  title: "NotesFlare",
  backgroundColor: "#0E0E10", // Matches --bg-base; prevents white flash on load
  titleBarStyle: "hiddenInset" as const, // macOS: native traffic lights, hidden bar
  // On Windows/Linux, use default frame (no custom titlebar in V1)
  frame: true,
  webPreferences: {
    nodeIntegration: false,    // Security: no Node.js in renderer
    contextIsolation: true,    // Security: isolate preload from renderer
    sandbox: false,            // Allow preload to use Node.js APIs
  },
} as const;

export const BACKEND_CONFIG = {
  host: "127.0.0.1",
  port: 8000,
  healthCheckUrl: "http://127.0.0.1:8000/api/health",
  maxWaitMs: 10000,     // Max time to wait for backend: 10 seconds
  pollIntervalMs: 200,  // Poll health endpoint every 200ms
} as const;
```

---

## 5. MAIN PROCESS

### electron/main.ts

This is the Electron entry point. It runs in the Node.js main process (not the browser context).

```typescript
// electron/main.ts

import { app, BrowserWindow, shell } from "electron";
import { spawn, ChildProcess } from "child_process";
import path from "path";
import { WINDOW_CONFIG, BACKEND_CONFIG } from "./window";

let mainWindow: BrowserWindow | null = null;
let backendProcess: ChildProcess | null = null;

// ─── Backend Spawning ────────────────────────────────────────────────────────

/**
 * Spawn the Python FastAPI backend as a child process.
 * The backend's stdout/stderr are piped to the main process console.
 * This makes debugging much easier during development.
 */
function spawnBackend(): ChildProcess {
  const projectRoot = path.resolve(__dirname, "../../");
  const backendMain = path.join(projectRoot, "backend", "main.py");

  // In development: use the system Python / venv
  // In production: would use a bundled Python — not needed for V1
  const pythonExecutable = process.platform === "win32" ? "python" : "python3";

  console.log(`[Electron] Spawning backend: ${pythonExecutable} ${backendMain}`);

  const proc = spawn(pythonExecutable, [backendMain], {
    cwd: path.join(projectRoot, "backend"),
    env: { ...process.env },
    stdio: ["ignore", "pipe", "pipe"],
  });

  proc.stdout?.on("data", (data: Buffer) => {
    process.stdout.write(`[Backend] ${data}`);
  });

  proc.stderr?.on("data", (data: Buffer) => {
    process.stderr.write(`[Backend] ${data}`);
  });

  proc.on("exit", (code) => {
    console.log(`[Electron] Backend exited with code ${code}`);
    backendProcess = null;
  });

  return proc;
}

// ─── Health Polling ──────────────────────────────────────────────────────────

/**
 * Poll the backend health endpoint until it responds or timeout expires.
 * Returns true if backend is ready, false if timeout exceeded.
 *
 * This is critical for startup UX: we don't show the window until
 * the backend is ready to accept requests.
 */
async function waitForBackend(): Promise<boolean> {
  const { healthCheckUrl, maxWaitMs, pollIntervalMs } = BACKEND_CONFIG;
  const deadline = Date.now() + maxWaitMs;

  while (Date.now() < deadline) {
    try {
      // Node 18+ has built-in fetch
      const res = await fetch(healthCheckUrl, { signal: AbortSignal.timeout(500) });
      if (res.ok) {
        console.log("[Electron] Backend is ready.");
        return true;
      }
    } catch {
      // Backend not ready yet — continue polling
    }
    await sleep(pollIntervalMs);
  }

  console.error("[Electron] Backend did not start within the timeout.");
  return false;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ─── Window Creation ─────────────────────────────────────────────────────────

function createMainWindow(): BrowserWindow {
  const win = new BrowserWindow({
    ...WINDOW_CONFIG,
    show: false, // Don't show until content is ready — prevents white flash
    webPreferences: {
      ...WINDOW_CONFIG.webPreferences,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  // Load the Next.js static build
  // In dev, we could point to localhost:3000, but for simplicity we
  // always load the static export in /frontend/out
  const indexPath = path.join(__dirname, "../../frontend/out/index.html");
  win.loadFile(indexPath);

  // Show window once content has loaded — prevents blank frame flash
  win.once("ready-to-show", () => {
    win.show();
    // Focus window on show — critical for "cursor ready immediately" UX
    win.focus();
  });

  // Open DevTools only in development
  if (process.env.NODE_ENV === "development") {
    win.webContents.openDevTools({ mode: "detach" });
  }

  // Prevent navigation to external URLs (security)
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  win.on("closed", () => {
    mainWindow = null;
  });

  return win;
}

// ─── App Lifecycle ───────────────────────────────────────────────────────────

app.on("ready", async () => {
  // 1. Spawn Python backend
  backendProcess = spawnBackend();

  // 2. Wait for backend to be ready
  const backendReady = await waitForBackend();
  if (!backendReady) {
    // If backend fails to start, show an error dialog and quit
    const { dialog } = await import("electron");
    dialog.showErrorBox(
      "NotesFlare — Startup Error",
      "The backend service failed to start. Please check that Python 3.11+ is installed and run 'pip install -r requirements.txt'."
    );
    app.quit();
    return;
  }

  // 3. Create and show window
  mainWindow = createMainWindow();
});

app.on("window-all-closed", () => {
  // On macOS, apps typically stay open until explicitly quit
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  // macOS: re-create window when dock icon clicked and no windows are open
  if (mainWindow === null) {
    mainWindow = createMainWindow();
  }
});

app.on("quit", () => {
  // Kill Python backend when app quits
  if (backendProcess && !backendProcess.killed) {
    console.log("[Electron] Terminating backend process.");
    backendProcess.kill("SIGTERM");
    backendProcess = null;
  }
});

// Handle uncaught exceptions — log and continue rather than crashing
process.on("uncaughtException", (err) => {
  console.error("[Electron] Uncaught exception:", err);
});
```

**Critical notes:**

- `show: false` + `ready-to-show` event: This prevents the window from appearing as a blank white frame before the frontend loads. The window becomes visible only when it has content. This is a key part of the "instant feel."
- `backgroundColor: "#0E0E10"`: Even with `show: false`, setting the background color prevents the OS from drawing a white rectangle. This matters on slower machines.
- Backend health polling: We do not show the window until the backend health check passes. This ensures the frontend never makes API calls to a backend that isn't ready.

---

## 6. PRELOAD SCRIPT

### electron/preload.ts

The preload script runs in a special context — it has access to Node.js APIs but runs in the renderer process's JavaScript environment. It uses `contextBridge` to safely expose specific functions to the frontend.

In V1, the preload is minimal because the frontend communicates with the backend via HTTP, not via Electron IPC. However, the preload is still needed to expose the platform and any future IPC channels.

```typescript
// electron/preload.ts

import { contextBridge } from "electron";

/**
 * Expose safe APIs to the renderer process via window.electronAPI.
 * Do NOT expose ipcRenderer directly — use contextBridge for security.
 *
 * In V1, we expose only the platform string so the frontend can
 * make platform-specific layout decisions (e.g., titlebar inset on macOS).
 */
contextBridge.exposeInMainWorld("electronAPI", {
  platform: process.platform,
});
```

In the frontend, the exposed object is accessible as `window.electronAPI.platform`.

**TypeScript types for the frontend:** Add this to `frontend/lib/electron.d.ts`:

```typescript
// frontend/lib/electron.d.ts
interface Window {
  electronAPI: {
    platform: NodeJS.Platform;
  };
}
```

---

## 7. PACKAGE.JSON (COMPLETE)

The full `package.json` at the project root. This handles both Electron and Next.js.

```json
{
  "name": "notesflare",
  "version": "1.0.0",
  "description": "Thought capture with near-zero cognitive friction.",
  "main": "electron/dist/main.js",
  "private": true,
  "scripts": {
    "dev": "concurrently \"npm run dev:frontend\" \"npm run dev:electron\"",
    "dev:frontend": "next dev frontend",
    "dev:electron": "wait-on http://localhost:3000 && tsc -p tsconfig.electron.json && electron .",
    "build:frontend": "next build frontend",
    "build:electron": "tsc -p tsconfig.electron.json",
    "build": "npm run build:frontend && npm run build:electron",
    "start": "electron ."
  },
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "concurrently": "^8.2.0",
    "electron": "^30.0.0",
    "electron-builder": "^24.13.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.4.0",
    "wait-on": "^7.2.0"
  }
}
```

---

## 8. TYPESCRIPT CONFIG FOR ELECTRON

### tsconfig.electron.json

The Electron main + preload files need a separate TypeScript config because they target Node.js, not the browser.

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "./electron/dist",
    "rootDir": "./electron",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true
  },
  "include": ["electron/**/*.ts"],
  "exclude": ["node_modules"]
}
```

Output goes to `electron/dist/`. The `main` field in `package.json` points to `electron/dist/main.js`.

---

## 9. STARTUP SEQUENCE (DETAILED)

Understanding this sequence is important for debugging. This is what happens when the user launches NotesFlare:

```
1. OS launches Electron
   └── Electron reads package.json "main": "electron/dist/main.js"

2. electron/main.ts: app "ready" event fires
   └── spawnBackend() called
       └── Python process starts: python3 backend/main.py
           └── FastAPI app initializes
           └── init_db() runs — creates/validates SQLite tables
           └── Uvicorn starts listening on 127.0.0.1:8000

3. waitForBackend() polls GET /api/health every 200ms
   └── Once returns {"status": "ok"}: proceed
   └── If 10 seconds pass with no response: show error dialog + quit

4. createMainWindow() called
   └── BrowserWindow created with show: false
   └── mainWindow.loadFile("frontend/out/index.html")
   └── Next.js static HTML loads
   └── React hydrates

5. React: useSession() hook runs
   └── GET /api/state — get last-opened Flareon
   └── GET /api/flareons — load sidebar
   └── If last Flareon exists: GET /api/flareons/{id} — open it

6. "ready-to-show" event fires
   └── mainWindow.show() called
   └── mainWindow.focus()
   └── User sees the app with content already loaded
   └── Cursor is focused in the textarea

7. User starts typing immediately.
```

Total target time from step 1 to step 7: **under 2 seconds** on a modern machine.

---

## 10. DEVELOPMENT VS PRODUCTION

### Development Mode

In development, Next.js runs its dev server on `localhost:3000` and Electron loads from there. This enables hot reload.

To run in development:
```bash
# Terminal 1: Start Python backend
cd backend && python3 main.py

# Terminal 2: Start Next.js dev server
cd frontend && next dev

# Terminal 3: Start Electron (after Next.js is ready)
npx electron .
```

Or use the unified dev script: `npm run dev` (requires `concurrently` and `wait-on`).

### Production Mode

In production, Next.js is built to a static export in `frontend/out/`, and Electron loads from the filesystem. No Next.js server is needed.

To build and run:
```bash
npm run build        # Builds both frontend and electron TypeScript
npm start            # Launches Electron (loads frontend/out/index.html)
```

**For V1, prioritize making development mode work cleanly. Production packaging (electron-builder) is optional for V1.**

---

## 11. SECURITY NOTES

The following security settings are non-negotiable in Electron:

| Setting | Value | Why |
|---|---|---|
| `nodeIntegration` | `false` | Renderer cannot access Node.js APIs directly |
| `contextIsolation` | `true` | Preload script is isolated from renderer context |
| External URLs | Blocked via `setWindowOpenHandler` | Prevent renderer from opening arbitrary URLs |
| CORS | Backend allows `*` | Acceptable for localhost-only communication in V1 |

---

## 12. VERIFICATION CHECKLIST

- [ ] `npm run build` compiles `electron/dist/main.js` and `electron/dist/preload.js`
- [ ] `npm start` launches the app without errors
- [ ] Backend Python process appears in Activity Monitor / Task Manager after launch
- [ ] Backend process is killed when the app quits
- [ ] The window does NOT appear as a blank white frame — it shows content immediately
- [ ] DevTools open automatically in development mode
- [ ] `window.electronAPI.platform` is accessible in the browser console
- [ ] Closing the window on macOS keeps the app in the dock; re-clicking opens a new window

---

## 13. COMMON MISTAKES TO AVOID

**Do not:**
- Set `nodeIntegration: true` — this is a security risk
- Call `win.show()` before `ready-to-show` event — causes white flash
- Hardcode the Python executable path — use `process.platform` detection
- Forget to kill the backend process on app quit — leaves zombie processes
- Load `localhost:3000` in production — always use the static build
- Use `process.env.NODE_ENV === 'production'` to detect Electron build — it may not be set correctly; check for the `out` directory existence instead

**Do:**
- Always gate window creation on backend health check
- Always spawn backend before creating the window
- Pipe backend stdout/stderr to the Electron console during development
- Use `AbortSignal.timeout()` on health check fetch calls to prevent hanging
