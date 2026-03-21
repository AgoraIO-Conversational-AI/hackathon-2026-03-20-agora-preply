import { useState, memo } from "react";
import { Loader2, ThumbsUp, ThumbsDown } from "lucide-react";
import type { Message, ProcessStep } from "@/lib/types";
import { ThinkingBlock, ToolCallBlock } from "./ProcessTimeline";
import { WidgetRouter } from "./widgets/WidgetRouter";
import { ChatMarkdown } from "./ChatMarkdown";
import { PreplyLogo } from "@/components/ui/PreplyLogo";
import { Tooltip } from "@/components/ui/Tooltip";
import { CopyButton } from "@/components/ui/CopyButton";
import Spinner from "@/components/ui/Spinner";

interface ChatMessageProps {
  message: Message;
  isStreaming?: boolean;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/** Memoized process steps — prevents widget re-renders during text streaming */
const ProcessStepsFlow = memo(function ProcessStepsFlow({
  steps,
  isStreaming,
}: {
  steps: ProcessStep[];
  isStreaming: boolean;
}) {
  const hasThinking = steps.some((s) => s.type === "thinking");
  const filteredSteps = hasThinking
    ? steps.filter(
        (s) => !(s.type === "status" && s.message === "Thinking..."),
      )
    : steps;

  return (
    <>
      {filteredSteps.map((step, idx) => {
        const isLast = idx === filteredSteps.length - 1;
        const isActive = isStreaming && isLast;

        switch (step.type) {
          case "thinking":
            return (
              <ThinkingBlock
                key={`thinking-${idx}`}
                content={step.content}
                isActive={isActive}
                defaultExpanded={isActive}
              />
            );
          case "tool_call": {
            const hasWidget = !!step.result?.data?.widget_type;
            return (
              <div key={step.toolId} className="space-y-1.5">
                <ToolCallBlock
                  step={step}
                  defaultExpanded={isActive}
                  hideResultData={hasWidget}
                />
                {hasWidget && (
                  <WidgetRouter data={step.result!.data} />
                )}
              </div>
            );
          }
          case "status":
            if (!isActive) return null;
            return (
              <div
                key={`status-${idx}`}
                className="flex items-center gap-1.5 text-xs text-[color:var(--color-text-muted)]"
              >
                <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" />
                <span>{step.message}</span>
              </div>
            );
          default:
            return null;
        }
      })}
    </>
  );
});

function MessageActions({ content }: { content: string }) {
  const [rating, setRating] = useState<"up" | "down" | null>(null);

  return (
    <div className="flex items-center gap-0.5">
      <CopyButton text={content} tooltip="Copy response" />
      <Tooltip content="Good response">
        <button
          type="button"
          onClick={() => setRating(rating === "up" ? null : "up")}
          className={`rounded p-1 transition-colors ${
            rating === "up"
              ? "text-[color:var(--color-success)]"
              : "text-[color:var(--color-text-muted)] hover:bg-[var(--color-surface-secondary)] hover:text-[color:var(--color-text-secondary)]"
          }`}
        >
          <ThumbsUp className="h-3.5 w-3.5" fill={rating === "up" ? "currentColor" : "none"} />
        </button>
      </Tooltip>
      <Tooltip content="Bad response">
        <button
          type="button"
          onClick={() => setRating(rating === "down" ? null : "down")}
          className={`rounded p-1 transition-colors ${
            rating === "down"
              ? "text-[color:var(--color-danger)]"
              : "text-[color:var(--color-text-muted)] hover:bg-[var(--color-surface-secondary)] hover:text-[color:var(--color-text-secondary)]"
          }`}
        >
          <ThumbsDown className="h-3.5 w-3.5" fill={rating === "down" ? "currentColor" : "none"} />
        </button>
      </Tooltip>
    </div>
  );
}

export function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  const isUser = message.role === "user";

  // User messages: right-aligned coral bubble
  if (isUser) {
    return (
      <div className="flex justify-end animate-[fadeIn_0.2s_ease-out]">
        <div className="max-w-[75%]">
          <div className="mb-1 flex items-baseline justify-end gap-2">
            <span className="text-label text-[color:var(--color-text-muted)]">
              {formatTime(message.timestamp)}
            </span>
          </div>
          <div className="rounded-xl rounded-tr-sm bg-[var(--color-primary)] px-4 py-2.5 text-sm text-white">
            <p className="whitespace-pre-wrap">{message.content}</p>
          </div>
        </div>
      </div>
    );
  }

  // Assistant messages
  const steps = message.processSteps ?? [];
  const hasSteps = steps.length > 0;

  return (
    <div className="flex gap-3 animate-[fadeIn_0.2s_ease-out]">
      {/* Avatar */}
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full [background:var(--color-highlight-gradient)] text-[color:var(--color-text-primary)]">
        <PreplyLogo />
      </div>

      {/* Content column */}
      <div className="min-w-0 flex-1 space-y-1.5">
        {/* Name + timestamp */}
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-semibold text-[color:var(--color-text-primary)]">
            Preply AI
          </span>
          <span className="text-label text-[color:var(--color-text-muted)]">
            {formatTime(message.timestamp)}
          </span>
        </div>

        {/* Sequential flow: thinking → tool+widget → text bubble */}
        <div className="flex flex-col gap-2">
          {/* Process steps with inline widgets (memoized to prevent re-renders during streaming) */}
          {hasSteps && (
            <ProcessStepsFlow steps={steps} isStreaming={!!isStreaming} />
          )}

          {/* Fallback: streaming with no steps yet — show spinner */}
          {isStreaming && !hasSteps && !message.content && (
            <div className="flex items-center gap-2 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3">
              <Spinner size="small" />
            </div>
          )}

          {/* Text content — only this gets a bubble */}
          {message.content && (
            <div className={`rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-sm ${isStreaming ? "streaming-cursor" : ""}`}>
              <ChatMarkdown content={message.content} id={message.id} />
            </div>
          )}

          {/* Feedback actions — copy, thumbs up/down */}
          {!isStreaming && message.content && (
            <MessageActions content={message.content} />
          )}
        </div>
      </div>
    </div>
  );
}
