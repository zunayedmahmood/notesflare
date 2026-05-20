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
