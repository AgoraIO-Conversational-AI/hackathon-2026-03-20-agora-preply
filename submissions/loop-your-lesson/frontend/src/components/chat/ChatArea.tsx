import { useEffect, useMemo, useRef } from "react";
import type { ChatStatus, Message, ProcessStep, ApprovalRequest } from "@/lib/types";
import { processThread } from "@/lib/threadProcessing";
import { PreplyLogo } from "@/components/ui/PreplyLogo";
import { MODE_DEFINITIONS, MODES, getStudentChips, type PreplyMode } from "@/lib/modes";
import { ChatMessage } from "./ChatMessage";
import { ContextDetailPanel } from "./ContextHeader";
import type { ContextInfo } from "./ContextHeader";
import Button from "@/components/ui/Button";
import { AlertCircle } from "lucide-react";

interface ChatAreaProps {
  messages: Message[];
  status: ChatStatus;
  statusMessage: string;
  streamingContent: string;
  currentProcessSteps: ProcessStep[];
  approvalRequest: ApprovalRequest | null;
  error: string | null;
  onRetry: () => void;
  onSuggest?: (message: string) => void;
  mode: PreplyMode;
  contextInfo?: ContextInfo;
}

function DateSeparator({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center py-2">
      <span className="rounded-[var(--radius-full)] border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-0.5 text-label text-[color:var(--color-text-muted)]">
        {label}
      </span>
    </div>
  );
}

export function ChatArea({
  messages,
  status,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  statusMessage: _statusMessage,
  streamingContent,
  currentProcessSteps,
  approvalRequest,
  error,
  onRetry,
  onSuggest,
  mode,
  contextInfo,
}: ChatAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const modeDef = MODE_DEFINITIONS[mode];

  // Localize chips/headline for student practice mode
  const localized =
    mode === MODES.STUDENT_PRACTICE
      ? getStudentChips(contextInfo?.subjectConfig?.l1)
      : null;
  const chips = localized?.chips ?? modeDef.suggestionChips;
  const headline = localized?.headline ?? modeDef.headline;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent, status]);

  // Process raw messages: filter empty + merge consecutive assistant messages
  const processedMessages = useMemo(() => processThread(messages), [messages]);

  const showThinking =
    status === "connecting" ||
    status === "thinking" ||
    status === "executing_tool";

  const showStreaming = status === "streaming" && streamingContent;

  return (
    <div className="flex-1 overflow-y-auto bg-[var(--color-surface)]">
      {/* Inline context detail - scrolls with messages */}
      {contextInfo && <ContextDetailPanel mode={mode} ctx={contextInfo} />}

      <div className="mx-auto max-w-3xl space-y-5 px-4 py-6">
        {/* Empty state */}
        {messages.length === 0 && status === "idle" && (
          <div className={`flex flex-col items-center ${contextInfo ? "py-8" : "py-16"}`}>
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full [background:var(--color-highlight-gradient)]">
              <PreplyLogo className="h-6 w-6" />
            </div>
            <p className="mb-6 text-center text-display text-[color:var(--color-text-secondary)]">
              {headline}
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {chips.map((chip) => (
                <button
                  key={chip}
                  onClick={() => onSuggest?.(chip)}
                  className="cursor-pointer rounded-[var(--radius-full)] border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2 text-sm text-[color:var(--color-text-secondary)] transition-preply hover:border-[var(--color-text-primary)] hover:text-[color:var(--color-text-primary)]"
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Date separator for first message */}
        {messages.length > 0 && (
          <DateSeparator label="Today" />
        )}

        {/* Message list (processed: filtered + merged) */}
        {processedMessages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}

        {/* Streaming message — no toolResults here (they show inside ProcessTimeline) */}
        {showStreaming && (
          <ChatMessage
            message={{
              id: "streaming",
              role: "assistant",
              content: streamingContent,
              timestamp: new Date(),
              processSteps: currentProcessSteps.length > 0 ? currentProcessSteps : undefined,
            }}
            isStreaming
          />
        )}

        {/* Thinking/processing state — unified with ChatMessage for inline widgets */}
        {showThinking && !showStreaming && (
          <ChatMessage
            message={{
              id: "thinking",
              role: "assistant",
              content: "",
              timestamp: new Date(),
              processSteps: currentProcessSteps.length > 0 ? currentProcessSteps : undefined,
            }}
            isStreaming
          />
        )}

        {/* Approval dialog */}
        {status === "awaiting_approval" && approvalRequest && (
          <div className="rounded-[var(--radius-xl)] border-2 border-[var(--color-warning)] bg-[var(--color-warning-light)] p-4">
            <p className="text-sm font-medium text-[color:var(--color-text-primary)]">
              Approval needed: {approvalRequest.toolName}
            </p>
            <p className="mt-1 text-xs text-[color:var(--color-text-secondary)]">
              {approvalRequest.description}
            </p>
          </div>
        )}

        {/* Error state */}
        {status === "error" && error && (
          <div className="rounded-[var(--radius-xl)] border-2 border-[var(--color-danger)] bg-[var(--color-danger-light)] p-4">
            <div className="flex items-start gap-2">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[color:var(--color-danger)]" />
              <p className="text-sm text-[color:var(--color-danger)]">{error}</p>
            </div>
            <Button variant="tertiary" size="sm" className="mt-2" onClick={onRetry}>
              Retry
            </Button>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
