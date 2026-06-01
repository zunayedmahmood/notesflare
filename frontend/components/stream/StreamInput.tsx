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
  const inputRef = useRef<HTMLTextAreaElement>(null);

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

  // Resize textarea to fit its content (no fixed height, grows with text)
  function autoResize(el: HTMLTextAreaElement) {
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }

  // Auto-focus on mount and on burstId change
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.value = initialContent;
      autoResize(inputRef.current);
      inputRef.current.focus();
      // Place cursor at end
      const len = inputRef.current.value.length;
      inputRef.current.setSelectionRange(len, len);
    }
    setBuffer(initialContent);
  }, [burstId, initialContent]); // Re-runs on Flareon switch

  const handleInput = useCallback(
    (e: React.FormEvent<HTMLTextAreaElement>) => {
      const el = e.currentTarget as HTMLTextAreaElement;
      const newValue = el.value;
      bufferRef.current = newValue;
      autoResize(el);
      onContentLength?.(newValue.length);
      scheduleAppend();
    },
    [scheduleAppend, onContentLength, bufferRef]
  );

  return (
    <textarea
      ref={inputRef}
      onInput={handleInput}
      data-testid="stream-input"
      defaultValue={initialContent}
      placeholder="Start writing..."
      autoFocus
      autoComplete="off"
      autoCorrect="off"
      autoCapitalize="sentences"
      spellCheck={true}
      rows={1}
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

        // Textarea-specific: no scrollbar, grows to content
        resize: "none",
        overflow: "hidden",

        // No padding so text aligns flush to the stream shell
        padding: 0,
      }}
    />
  );
}
