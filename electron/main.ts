// electron/main.ts

import { app, BrowserWindow, shell } from "electron";
import { spawn, ChildProcess } from "child_process";
import path from "path";
import fs from "fs";
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

  // Smart resolution: use the virtual environment's Python if it exists,
  // falling back to the system's global Python.
  let pythonExecutable = process.platform === "win32" ? "python" : "python3";
  const venvPython = process.platform === "win32"
    ? path.join(projectRoot, ".venv", "Scripts", "python.exe")
    : path.join(projectRoot, ".venv", "bin", "python");

  if (fs.existsSync(venvPython)) {
    pythonExecutable = venvPython;
    console.log(`[Electron] Using virtualenv Python executable: ${pythonExecutable}`);
  } else {
    console.log(`[Electron] Virtualenv not found. Using system Python: ${pythonExecutable}`);
  }

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

  // Load the Next.js static build or dev server
  const isDev = process.env.NODE_ENV === "development";
  if (isDev) {
    win.loadURL("http://localhost:3000");
  } else {
    const indexPath = path.join(__dirname, "../../frontend/out/index.html");
    win.loadFile(indexPath);
  }

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

/**
 * Check if the backend is already running (e.g. started by scripts/start-dev.sh or external process)
 */
async function checkBackendRunning(): Promise<boolean> {
  const { healthCheckUrl } = BACKEND_CONFIG;
  try {
    const res = await fetch(healthCheckUrl, { signal: AbortSignal.timeout(200) });
    return res.ok;
  } catch {
    return false;
  }
}

// ─── App Lifecycle ───────────────────────────────────────────────────────────

app.on("ready", async () => {
  // 1. Check if backend is already running
  const alreadyRunning = await checkBackendRunning();
  if (alreadyRunning) {
    console.log("[Electron] Backend is already running on port 8000. Skipping spawn.");
  } else {
    // Spawn Python backend
    backendProcess = spawnBackend();
  }

  // 2. Wait for backend to be ready
  const backendReady = alreadyRunning || await waitForBackend();
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
