// frontend/tests/hooks/useStreamBuffer.test.ts

import { renderHook, act } from "@testing-library/react";
import { useStreamBuffer } from "@/hooks/useStreamBuffer";
import { describe, it, expect } from "vitest";

describe("useStreamBuffer", () => {
  it("initializes buffer with provided content", () => {
    const { result } = renderHook(() => useStreamBuffer("Hello world"));
    expect(result.current.getBuffer()).toBe("Hello world");
  });

  it("getDeltaSinceLastSync returns empty string when nothing has changed", () => {
    const { result } = renderHook(() => useStreamBuffer("Hello"));
    // lastSyncedLength starts at initialContent.length = 5
    const delta = result.current.getDeltaSinceLastSync();
    expect(delta).toBe("");
  });

  it("getDeltaSinceLastSync returns only new characters after setBuffer", () => {
    const { result } = renderHook(() => useStreamBuffer("Hello"));

    act(() => {
      result.current.setBuffer("Hello world");
    });

    const delta = result.current.getDeltaSinceLastSync();
    expect(delta).toBe(
      " world",
      `[useStreamBuffer] getDeltaSinceLastSync must return only characters added since last sync. ` +
        `Initial length was 5. Buffer is now 'Hello world' (length 11). ` +
        `Expected delta: ' world'. Got: '${delta}'.`
    );
  });

  it("markSynced advances lastSyncedLength to current buffer length", () => {
    const { result } = renderHook(() => useStreamBuffer("Hello"));

    act(() => {
      result.current.setBuffer("Hello world");
      result.current.markSynced();
    });

    // After marking synced, delta should be empty again
    const delta = result.current.getDeltaSinceLastSync();
    expect(delta).toBe(
      "",
      `[useStreamBuffer] After markSynced(), getDeltaSinceLastSync must return ''. ` +
        `Got: '${delta}'. Fix: markSynced must set lastSyncedLength to bufferRef.current.length.`
    );
  });

  it("delta accumulates correctly across multiple setBuffer calls without sync", () => {
    const { result } = renderHook(() => useStreamBuffer(""));

    act(() => result.current.setBuffer("First "));
    act(() => result.current.setBuffer("First Second "));
    act(() => result.current.setBuffer("First Second Third"));

    // No markSynced called — delta should be the entire buffer
    const delta = result.current.getDeltaSinceLastSync();
    expect(delta).toBe(
      "First Second Third",
      `[useStreamBuffer] Accumulated delta without sync must equal full buffer when starting at ''. ` +
        `Got: '${delta}'.`
    );
  });

  it("setBuffer with shorter string than lastSyncedLength returns empty delta", () => {
    const { result } = renderHook(() => useStreamBuffer("Hello world"));
    // Simulate: user typed "Hello world", it was synced (lastSyncedLength = 11)
    act(() => result.current.markSynced());

    // User deletes everything
    act(() => result.current.setBuffer(""));

    const delta = result.current.getDeltaSinceLastSync();
    // "".slice(11) === "" — no new text, delta is empty
    expect(delta).toBe(
      "",
      `[useStreamBuffer] Deletion past sync point returns empty delta (known V1.1 limitation). ` +
        `Got: '${delta}'.`
    );
  });
});
