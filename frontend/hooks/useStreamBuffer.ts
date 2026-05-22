// hooks/useStreamBuffer.ts
"use client";

import { useRef, useState, useCallback } from "react";

interface StreamBufferState {
  lastSyncedLength: number;   // How many chars were in the buffer on last save
  isSaving: boolean;
}

export function useStreamBuffer(initialContent: string) {
  // The actual text lives in a mutable ref — not React state.
  // This is critical. If we used useState, every keystroke would re-render
  // the entire stream page. With a ref, only the input's own DOM updates.
  const bufferRef = useRef<string>(initialContent);

  // React state only holds UI metadata
  const [bufferState, setBufferState] = useState<StreamBufferState>({
    lastSyncedLength: initialContent.length,
    isSaving: false,
  });

  const getBuffer = useCallback(() => bufferRef.current, []);

  const appendToBuffer = useCallback((newChar: string) => {
    bufferRef.current += newChar;
  }, []);

  const setBuffer = useCallback((text: string) => {
    bufferRef.current = text;
  }, []);

  const getDeltaSinceLastSync = useCallback(() => {
    return bufferRef.current.slice(bufferState.lastSyncedLength);
  }, [bufferState.lastSyncedLength]);

  const markSynced = useCallback(() => {
    setBufferState((prev) => ({
      ...prev,
      lastSyncedLength: bufferRef.current.length,
      isSaving: false,
    }));
  }, []);

  const setIsSaving = useCallback((saving: boolean) => {
    setBufferState((prev) => ({ ...prev, isSaving: saving }));
  }, []);

  return {
    bufferRef,
    getBuffer,
    appendToBuffer,
    setBuffer,
    getDeltaSinceLastSync,
    markSynced,
    isSaving: bufferState.isSaving,
    setIsSaving,
    lastSyncedLength: bufferState.lastSyncedLength,
  };
}
