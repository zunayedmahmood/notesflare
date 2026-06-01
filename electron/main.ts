// electron/main.ts

import { app, BrowserWindow, shell, protocol, net } from "electron";
import { spawn, ChildProcess } from "child_process";
import path from "path";
import fs from "fs";
import { pathToFileURL } from "url";

// ─── Hardware Acceleration (Linux VSync fix) ──────────────────────────────────
// On Linux, Chromium's GPU presentation helper attempts to retrieve VSync
// parameters from the display compositor. When this fails (common with certain
// GPU/driver combinations and Wayland/X11 configurations), it logs:
//   "GetVSyncParametersIfAvailable() failed for N times!"
// Disabling hardware acceleration prevents the GPU process from ever attempting
// VSync queries, eliminating the error at its root. NotesFlare is a text-focused
// app with no GPU-intensive rendering, so this has zero user-visible impact.
if (process.platform === "linux") {
  app.disableHardwareAcceleration();
}

// ─── Linux MIME Cache Workaround ─────────────────────────────────────────────
// Prevents the annoying Chromium warning:
// "Invalid mime.cache file does not contain null prior to ALIAS_LIST_OFFSET"
// This occurs when a system or local mime.cache is malformed or incompatible.
if (process.platform === "linux") {
  const checkMimeDir = (dirPath: string): boolean => {
    try {
      const cachePath = path.join(dirPath, "mime", "mime.cache");
      if (!fs.existsSync(cachePath)) return true; // No cache file, no warning

      const stat = fs.statSync(cachePath);
      if (stat.size < 40) return false;

      const fd = fs.openSync(cachePath, "r");
      const header = Buffer.alloc(40);
      fs.readSync(fd, header, 0, 40, 0);
      fs.closeSync(fd);

      const major = header.readUInt16BE(0);
      const minor = header.readUInt16BE(2);
      if (major !== 1 || minor !== 2) return false;

      const aliasListOffset = header.readUInt32BE(4);
      if (aliasListOffset >= stat.size) return false;

      // Verify that there is at least one null byte prior to ALIAS_LIST_OFFSET
      const checkLen = Math.min(stat.size, aliasListOffset);
      const fdVerify = fs.openSync(cachePath, "r");
      const verifyBuf = Buffer.alloc(checkLen);
      fs.readSync(fdVerify, verifyBuf, 0, checkLen, 0);
      fs.closeSync(fdVerify);

      if (!verifyBuf.includes(0)) return false;
      return true;
    } catch {
      return false; // Handle any read error as invalid
    }
  };

  // Filter XDG_DATA_DIRS
  const xdgDataDirs = process.env.XDG_DATA_DIRS || "/usr/local/share:/usr/share";
  const validDirs = xdgDataDirs
    .split(":")
    .filter((dir) => dir && checkMimeDir(dir));
  process.env.XDG_DATA_DIRS = validDirs.join(":") || "/usr/local/share";

  // Filter XDG_DATA_HOME
  const homeDir = process.env.HOME || "/home/" + (process.env.USER || "user");
  const defaultDataHome = path.join(homeDir, ".local", "share");
  const dataHome = process.env.XDG_DATA_HOME || defaultDataHome;
  if (!checkMimeDir(dataHome)) {
    process.env.XDG_DATA_HOME = path.join(homeDir, ".local", "share", "notesflare-empty-xdg");
  }
}

// Suppress noisy internal Chromium logs (e.g. GPU, VSync, MIME database checks) on stdout/stderr
app.commandLine.appendSwitch("log-level", "3");
// Disable renderer & utility process sandboxing to avoid Linux SUID sandbox helper requirements
app.commandLine.appendSwitch("no-sandbox");

import { WINDOW_CONFIG, BACKEND_CONFIG } from "./window";

protocol.registerSchemesAsPrivileged([
  { scheme: "notesflare", privileges: { standard: true, secure: true, supportFetchAPI: true } }
]);

let mainWindow: BrowserWindow | null = null;
let backendProcess: ChildProcess | null = null;
let frontendProcess: ChildProcess | null = null;

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

  // Load the Next.js dev/server runtime if available. For packaged/static
  // builds, prefer frontend/out via the custom notesflare:// protocol.
  const isDev = process.env.NODE_ENV === "development";
  const projectRoot = path.resolve(__dirname, "../../");
  const staticIndex = path.join(projectRoot, "frontend", "out", "index.html");

  if (!isDev && fs.existsSync(staticIndex)) {
    win.loadURL("notesflare://index.html");
  } else {
    win.loadURL("http://127.0.0.1:3000");
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
    // Use a generous timeout: 200ms was too short when the shell-script backend
    // was still warming up, causing Electron to spawn a second instance that
    // then crashed with "address already in use".
    const res = await fetch(healthCheckUrl, { signal: AbortSignal.timeout(1500) });
    return res.ok;
  } catch {
    return false;
  }
}


function getProjectRoot(): string {
  return path.resolve(__dirname, "../../");
}

function staticFrontendExists(): boolean {
  return fs.existsSync(path.join(getProjectRoot(), "frontend", "out", "index.html"));
}

function spawnFrontendServer(): ChildProcess {
  const projectRoot = getProjectRoot();
  const nextBin = process.platform === "win32"
    ? path.join(projectRoot, "node_modules", ".bin", "next.cmd")
    : path.join(projectRoot, "node_modules", ".bin", "next");

  const command = fs.existsSync(nextBin) ? nextBin : (process.platform === "win32" ? "npx.cmd" : "npx");
  const args = fs.existsSync(nextBin)
    ? ["start", "frontend", "-p", "3000"]
    : ["next", "start", "frontend", "-p", "3000"];

  console.log(`[Electron] Spawning frontend server: ${command} ${args.join(" ")}`);
  const proc = spawn(command, args, {
    cwd: projectRoot,
    env: { ...process.env, NODE_ENV: "production" },
    stdio: ["ignore", "pipe", "pipe"],
  });

  proc.stdout?.on("data", (data: Buffer) => {
    process.stdout.write(`[Frontend] ${data}`);
  });

  proc.stderr?.on("data", (data: Buffer) => {
    process.stderr.write(`[Frontend] ${data}`);
  });

  proc.on("exit", (code) => {
    console.log(`[Electron] Frontend server exited with code ${code}`);
    frontendProcess = null;
  });

  return proc;
}

async function checkFrontendRunning(): Promise<boolean> {
  try {
    await fetch("http://127.0.0.1:3000", { signal: AbortSignal.timeout(300) });
    return true;
  } catch {
    return false;
  }
}

async function waitForFrontend(): Promise<boolean> {
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    if (await checkFrontendRunning()) {
      console.log("[Electron] Frontend is ready.");
      return true;
    }
    await sleep(250);
  }
  console.error("[Electron] Frontend did not start within the timeout.");
  return false;
}

// ─── App Lifecycle ───────────────────────────────────────────────────────────

app.on("ready", async () => {
  // Register custom notesflare protocol handler
  protocol.handle("notesflare", (request) => {
    const url = new URL(request.url);
    let pathname = url.pathname;

    if (pathname === "/" || pathname === "") {
      pathname = "/index.html";
    }

    const outDir = path.resolve(__dirname, "../../frontend/out");
    const resolvedPath = path.join(outDir, decodeURIComponent(pathname));

    if (fs.existsSync(resolvedPath) && fs.statSync(resolvedPath).isFile()) {
      return net.fetch(pathToFileURL(resolvedPath).toString());
    }

    // Next.js dynamic routing fallback
    const htmlPath = resolvedPath + ".html";
    if (fs.existsSync(htmlPath) && fs.statSync(htmlPath).isFile()) {
      return net.fetch(pathToFileURL(htmlPath).toString());
    }

    const indexHtmlPath = path.join(resolvedPath, "index.html");
    if (fs.existsSync(indexHtmlPath) && fs.statSync(indexHtmlPath).isFile()) {
      return net.fetch(pathToFileURL(indexHtmlPath).toString());
    }

    return net.fetch(pathToFileURL(path.join(outDir, "index.html")).toString());
  });

  // 1. Check if backend is already running
  const alreadyRunning = await checkBackendRunning();
  if (alreadyRunning) {
    console.log("[Electron] Backend is already running on port 8000. Skipping spawn.");
  } else {
    backendProcess = spawnBackend();
  }

  // 2. Wait for backend to be ready
  const backendReady = alreadyRunning || await waitForBackend();
  if (!backendReady) {
    const { dialog } = await import("electron");
    dialog.showErrorBox(
      "NotesFlare — Startup Error",
      "The backend service failed to start. Please check that Python 3.11+ is installed and run 'pip install -r requirements.txt'."
    );
    app.quit();
    return;
  }

  // 3. In development or non-static production builds, ensure Next.js is running.
  const isDev = process.env.NODE_ENV === "development";
  const needsFrontendServer = isDev || !staticFrontendExists();
  if (needsFrontendServer) {
    const frontendAlreadyRunning = await checkFrontendRunning();
    if (!frontendAlreadyRunning) {
      if (isDev) {
        console.log("[Electron] Waiting for externally started Next.js dev server on port 3000.");
      } else {
        frontendProcess = spawnFrontendServer();
      }
    }

    const frontendReady = frontendAlreadyRunning || await waitForFrontend();
    if (!frontendReady) {
      const { dialog } = await import("electron");
      dialog.showErrorBox(
        "NotesFlare — Startup Error",
        "The frontend service failed to start on port 3000. Run 'npm run dev:frontend' or rebuild the frontend."
      );
      app.quit();
      return;
    }
  }

  // 4. Create and show window
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
  // Kill child processes when app quits
  if (backendProcess && !backendProcess.killed) {
    console.log("[Electron] Terminating backend process.");
    backendProcess.kill("SIGTERM");
    backendProcess = null;
  }
  if (frontendProcess && !frontendProcess.killed) {
    console.log("[Electron] Terminating frontend process.");
    frontendProcess.kill("SIGTERM");
    frontendProcess = null;
  }
});

// Handle uncaught exceptions — log and continue rather than crashing
process.on("uncaughtException", (err) => {
  console.error("[Electron] Uncaught exception:", err);
});
