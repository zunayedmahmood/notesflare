// components/stream/StreamInput.tsx
"use client";

import { useRef, useEffect, useCallback } from "react";
import { useStreamBuffer } from "@/hooks/useStreamBuffer";
import { useAutosave } from "@/hooks/useAutosave";

interface StreamInputProps {
  burstId: number | null;
  initialContent: string;
  onContentLength?: (length: number) => void; // Optional: notify parent of length
}

export default function StreamInput({
  burstId,
  initialContent,
  onContentLength,
}: StreamInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const {
    bufferRef,
    setBuffer,
    getDeltaSinceLastSync,
    markSynced,
  } = useStreamBuffer(initialContent);

  const { scheduleAppend } = useAutosave({
    burstId,
    getDelta: getDeltaSinceLastSync,
    onSaveSuccess: markSynced,
  });

  // Auto-focus on mount and on burstId change
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.value = initialContent;
      inputRef.current.focus();
      // Place cursor at end
      const len = inputRef.current.value.length;
      inputRef.current.setSelectionRange(len, len);
    }
    setBuffer(initialContent);
  }, [burstId, initialContent]); // Re-runs on Flareon switch

  const handleInput = useCallback(
    (e: React.FormEvent<HTMLInputElement>) => {
      const newValue = (e.currentTarget as HTMLInputElement).value;
      bufferRef.current = newValue;
      onContentLength?.(newValue.length);
      scheduleAppend();
    },
    [scheduleAppend, onContentLength, bufferRef]
  );

  return (
    <input
      ref={inputRef}
      type="text"
      onInput={handleInput}
      data-testid="stream-input"
      defaultValue={initialContent}
      placeholder="Start writing..."
      autoFocus
      autoComplete="off"
      autoCorrect="off"
      autoCapitalize="sentences"
      spellCheck={true}
      style={{
        // Full width, no visible border, no background
        width: "100%",
        background: "transparent",
        border: "none",
        outline: "none",

        // Stream-style typography
        fontFamily: "var(--font-writing)",
        fontSize: "var(--text-size-writing)",
        lineHeight: "var(--line-height-writing)",
        color: "var(--text-primary)",
        caretColor: "var(--cursor)",

        // Overflow: text scrolls left, no scrollbar visible
        overflow: "hidden",
        whiteSpace: "nowrap",
        textOverflow: "clip",

        // No padding so text aligns flush to the stream shell
        padding: 0,
      }}
    />
  );
}
