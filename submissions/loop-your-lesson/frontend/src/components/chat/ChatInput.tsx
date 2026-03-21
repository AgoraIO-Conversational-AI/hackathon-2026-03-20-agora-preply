import { useState, useRef, useEffect, type KeyboardEvent } from "react";
import { Square } from "lucide-react";
import IconButton from "@/components/ui/IconButton";
import { Tooltip } from "@/components/ui/Tooltip";
import { ModeSelector } from "./ModeSelector";
import type { PreplyMode } from "@/lib/modes";

function SendIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      className={className}
    >
      <path
        fillRule="evenodd"
        d="M5.447 3.105 4 2.382v19.236l1.447-.724 16-8 1.79-.894-1.79-.895zM6 11V5.618L16.764 11zm0 2v5.382L16.764 13z"
        clipRule="evenodd"
      />
    </svg>
  );
}

interface ChatInputProps {
  onSend: (message: string) => void;
  onCancel?: () => void;
  disabled?: boolean;
  placeholder?: string;
  queueLength?: number;
  mode: PreplyMode;
  onModeChange: (mode: PreplyMode) => void;
}

export function ChatInput({
  onSend,
  onCancel,
  disabled,
  placeholder,
  queueLength = 0,
  mode,
  onModeChange,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (trimmed) {
      onSend(trimmed);
      setValue("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 144)}px`;
    }
  };

  const hasText = value.trim().length > 0;

  return (
    <div className="shrink-0 bg-[var(--color-surface)] px-4 pb-4 pt-2">
      <div className="mx-auto max-w-3xl">
        <div className="relative flex flex-col rounded-[var(--radius-xl)] border-2 border-[var(--color-border)] bg-[var(--color-surface)] focus-within:border-[var(--color-border-focus)] focus-within:shadow-sm">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            placeholder={
              placeholder ?? (disabled ? "Type to queue a follow-up..." : "Your message")
            }
            rows={1}
            className="min-h-[2.75rem] resize-none bg-transparent px-4 pt-3 pb-1 text-sm text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] focus:outline-none"
          />
          <div className="flex items-center justify-between px-3 pb-2.5">
            <div className="flex items-center gap-1">
              <ModeSelector value={mode} onChange={onModeChange} />
            </div>
            <div className="ml-auto flex items-center gap-2">
              {disabled && queueLength > 0 && (
                <span className="text-label text-[color:var(--color-text-muted)]">
                  {queueLength} queued
                </span>
              )}
              {disabled && onCancel && (
                <Tooltip content="Stop generating">
                  <button
                    onClick={onCancel}
                    className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-md)] border-2 border-[var(--color-border)] transition-preply hover:border-[var(--color-text-muted)]"
                  >
                    <Square className="h-3.5 w-3.5 fill-[var(--color-danger)] text-[color:var(--color-danger)]" />
                  </button>
                </Tooltip>
              )}
              {!disabled && (
                <Tooltip content="Send message">
                  <IconButton
                    variant={hasText ? "primary" : "muted"}
                    onClick={handleSubmit}
                    disabled={!hasText}
                  >
                    <SendIcon className="h-5 w-5" />
                  </IconButton>
                </Tooltip>
              )}
            </div>
          </div>
        </div>
        <p className="mt-1.5 text-center text-[11px] text-[color:var(--color-text-muted)]">
          AI can make mistakes. Please double-check responses.
        </p>
      </div>
    </div>
  );
}
