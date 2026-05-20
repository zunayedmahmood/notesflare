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
      const val = activeBurst?.content ?? "";
      onContentChange(val);

      // Auto-resize on initial mount to match pre-existing content height
      setTimeout(() => {
        if (textareaRef.current) {
          autoResize(textareaRef.current);
        }
      }, 0);
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
        data-testid="writing-area-placeholder"
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
      data-testid="writing-area"
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
          data-testid="writing-textarea"
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
