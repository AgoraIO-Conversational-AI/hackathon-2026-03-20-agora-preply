import { useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  Lightbulb,
  ClipboardList,
  ChevronRight,
  Check,
  X,
  Loader2,
} from "lucide-react";
import { Tooltip } from "@/components/ui/Tooltip";
import { CopyButtonOverlay } from "@/components/ui/CopyButton";
import type { ProcessStep } from "@/lib/types";

// ---------------------------------------------------------------------------
// Human-readable tool labels
// ---------------------------------------------------------------------------

const TOOL_LABELS: Record<string, string> = {
  query_daily_overview: "Get daily overview",
  query_student_report: "Get student report",
  query_lesson_errors: "Get lesson errors",
  query_lesson_themes: "Get lesson themes",
  query_classtime_results: "Get practice results",
  get_practice_session: "Get practice session",
};

function getToolLabel(name: string): string {
  return (
    TOOL_LABELS[name] ||
    name
      .replace(/_/g, " ")
      .replace(/^\w/, (c) => c.toUpperCase())
  );
}

// ---------------------------------------------------------------------------
// ThinkingBlock
// ---------------------------------------------------------------------------

export function ThinkingBlock({
  content,
  isActive,
  defaultExpanded = false,
}: {
  content: string;
  isActive?: boolean;
  defaultExpanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div>
      <button
        type="button"
        className="flex items-center gap-1.5 text-left focus-ring rounded-[var(--radius-sm)]"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        <Lightbulb
          className={`h-3.5 w-3.5 shrink-0 ${isActive ? "text-[color:var(--color-text-secondary)]" : "text-[color:var(--color-text-muted)]"}`}
        />
        <span
          className={`text-xs font-medium ${isActive ? "text-[color:var(--color-text-secondary)]" : "text-[color:var(--color-text-muted)]"}`}
        >
          Thought
        </span>
        <ChevronRight
          className={`h-3 w-3 shrink-0 text-[color:var(--color-text-muted)] transition-transform ${expanded ? "rotate-90" : ""}`}
        />
      </button>
      {expanded && (
        <div className="ml-3 mt-1.5 border-l-2 border-[var(--color-border)] pl-3.5 animate-[fadeIn_0.15s_ease-out]">
          <div className="prose prose-xs max-w-none text-[color:var(--color-text-muted)] prose-p:my-1 prose-p:text-[11px] prose-p:leading-relaxed prose-ul:my-1 prose-ul:pl-4 prose-li:my-0 prose-li:text-[11px] prose-strong:text-[color:var(--color-text-secondary)]">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ToolCallBlock
// ---------------------------------------------------------------------------

export function ToolCallBlock({
  step,
  defaultExpanded = false,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  hideResultData: _hideResultData = false,
}: {
  step: Extract<ProcessStep, { type: "tool_call" }>;
  defaultExpanded?: boolean;
  hideResultData?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [showArgs, setShowArgs] = useState(false);
  const [showResult, setShowResult] = useState(false);

  const isRunning = step.status === "running";
  const isFailed = step.status === "failed";
  const hasArgs = step.toolInput && Object.keys(step.toolInput).length > 0;

  const resultPreview = step.result?.message
    ? step.result.message.length > 50
      ? step.result.message.slice(0, 50) + "..."
      : step.result.message
    : null;

  return (
    <div>
      <button
        type="button"
        className="flex items-center gap-1.5 text-left focus-ring rounded-[var(--radius-sm)]"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        <ClipboardList className="h-3.5 w-3.5 shrink-0 text-[color:var(--color-text-muted)]" />
        <span className="text-xs font-medium text-[color:var(--color-text-secondary)]">
          {getToolLabel(step.toolName)}
        </span>
        <ChevronRight
          className={`h-3 w-3 shrink-0 text-[color:var(--color-text-muted)] transition-transform ${expanded ? "rotate-90" : ""}`}
        />
        <Tooltip content={isRunning ? "Running" : isFailed ? "Failed" : "Completed"}>
          {isRunning ? (
            <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-[color:var(--color-primary)]" />
          ) : isFailed ? (
            <X className="h-3.5 w-3.5 shrink-0 text-[color:var(--color-danger)]" />
          ) : (
            <Check className="h-3.5 w-3.5 shrink-0 text-[color:var(--color-success)]" />
          )}
        </Tooltip>
      </button>

      {expanded && (
        <div className="ml-3 mt-1 space-y-1 border-l-2 border-[var(--color-border)] pl-3.5 animate-[fadeIn_0.15s_ease-out]">
          {/* Tool called — expandable only if has args */}
          <div>
            {hasArgs ? (
              <button
                type="button"
                className="flex items-center gap-1.5 text-xs text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-secondary)]"
                onClick={(e) => {
                  e.stopPropagation();
                  setShowArgs(!showArgs);
                }}
              >
                <span className="font-medium">Tool called:</span>
                <span>{step.toolName}</span>
                <ChevronRight
                  className={`h-3 w-3 shrink-0 text-[color:var(--color-text-muted)] transition-transform ${showArgs ? "rotate-90" : ""}`}
                />
              </button>
            ) : (
              <p className="text-xs text-[color:var(--color-text-muted)]">
                <span className="font-medium">Tool called:</span> {step.toolName}
              </p>
            )}
            {showArgs && hasArgs && (() => {
              const text = JSON.stringify(step.toolInput, null, 2);
              return (
                <div className="group/pre relative mt-1">
                  <pre className="overflow-x-auto rounded-[var(--radius-md)] bg-[var(--color-code-bg)] p-2 pr-7 text-micro text-[color:var(--color-code-text)]">
                    {text}
                  </pre>
                  <CopyButtonOverlay text={text} />
                </div>
              );
            })()}
          </div>

          {/* Tool result — summary always visible, expandable JSON */}
          {step.result && (
            <div>
              <button
                type="button"
                className="flex items-center gap-1.5 text-xs text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-secondary)]"
                onClick={(e) => {
                  e.stopPropagation();
                  setShowResult(!showResult);
                }}
              >
                <span className="font-medium">Tool result:</span>
                {resultPreview && <span>{resultPreview}</span>}
                <ChevronRight
                  className={`h-3 w-3 shrink-0 text-[color:var(--color-text-muted)] transition-transform ${showResult ? "rotate-90" : ""}`}
                />
              </button>
              {showResult && (() => {
                const text = step.result.data && Object.keys(step.result.data).length > 0
                  ? JSON.stringify(step.result.data, null, 2)
                  : step.result.message;
                return (
                  <div className="group/pre relative mt-1">
                    <pre className="overflow-x-auto rounded-[var(--radius-md)] bg-[var(--color-code-bg)] p-2 pr-7 text-micro text-[color:var(--color-code-text)]">
                      {text}
                    </pre>
                    <CopyButtonOverlay text={text} />
                  </div>
                );
              })()}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ProcessTimeline
// ---------------------------------------------------------------------------

interface ProcessTimelineProps {
  steps: ProcessStep[];
  isStreaming?: boolean;
}

export function ProcessTimeline({ steps, isStreaming }: ProcessTimelineProps) {
  if (steps.length === 0) return null;

  const hasThinking = steps.some((s) => s.type === "thinking");
  const filteredSteps = hasThinking
    ? steps.filter(
        (s) => !(s.type === "status" && s.message === "Thinking..."),
      )
    : steps;

  return (
    <div className="space-y-2">
      {filteredSteps.map((step, idx) => {
        const isLast = idx === filteredSteps.length - 1;
        const isActive = isStreaming && isLast;

        switch (step.type) {
          case "thinking":
            return (
              <ThinkingBlock
                key={idx}
                content={step.content}
                isActive={isActive}
                defaultExpanded={isActive}
              />
            );
          case "tool_call":
            return (
              <ToolCallBlock
                key={step.toolId}
                step={step}
                defaultExpanded={isActive}
              />
            );
          case "status":
            if (!isActive) return null;
            return (
              <div
                key={idx}
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
    </div>
  );
}
