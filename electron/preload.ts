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
