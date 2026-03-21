import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import WidgetCard from "@/components/ui/WidgetCard";
import type { ErrorItem, ErrorAnalysisData } from "@/lib/types";

const MAX_VISIBLE = 5;

const SEVERITY_DOT: Record<string, string> = {
  minor: "bg-[var(--color-text-muted)]",
  moderate: "bg-amber-400",
  major: "bg-[var(--color-danger)]",
};

const TYPE_CONF: Record<string, { label: string; color: string; bg: string }> = {
  grammar:       { label: "Grammar",       color: "text-blue-600",    bg: "bg-blue-50" },
  vocabulary:    { label: "Vocabulary",     color: "text-violet-600",  bg: "bg-violet-50" },
  pronunciation: { label: "Pronunciation",  color: "text-amber-600",   bg: "bg-amber-50" },
  fluency:       { label: "Fluency",        color: "text-emerald-600", bg: "bg-emerald-50" },
};

function CompactErrorRow({ error }: { error: ErrorItem }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetails = !!error.reasoning;
  const timestamp = error.position?.timestamp ?? error.transcript_position?.timestamp;

  return (
    <div>
      <button
        type="button"
        onClick={() => hasDetails && setExpanded(!expanded)}
        className={`flex w-full items-start gap-2 py-1 text-left ${hasDetails ? "cursor-pointer" : "cursor-default"}`}
      >
        <span
          className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${SEVERITY_DOT[error.severity] ?? SEVERITY_DOT.minor}`}
          title={error.severity}
        />
        <div className="min-w-0 flex-1">
          <p className="text-xs leading-snug">
            <span className="text-[color:var(--color-danger)] line-through decoration-[color:var(--color-danger)]/40">
              {error.original}
            </span>
            <span className="mx-1 text-[color:var(--color-text-muted)]">&rarr;</span>
            <span className="font-medium text-[color:var(--color-success)]">
              {error.corrected}
            </span>
          </p>
          <p className="text-[11px] leading-snug text-[color:var(--color-text-muted)]">
            {error.explanation}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {timestamp && (
            <span className="text-[10px] tabular-nums text-[color:var(--color-text-muted)] opacity-60">
              {timestamp}
            </span>
          )}
          {hasDetails && (
            <ChevronRight className={`h-2.5 w-2.5 text-[color:var(--color-text-muted)] transition-transform ${expanded ? "rotate-90" : ""}`} />
          )}
        </div>
      </button>
      {expanded && error.reasoning && (
        <p className="mb-1 ml-[14px] rounded bg-[var(--color-surface-secondary)] px-2 py-1 text-[11px] leading-relaxed text-[color:var(--color-text-muted)]">
          {error.reasoning}
        </p>
      )}
    </div>
  );
}

export function ErrorAnalysisWidget({
  data,
}: {
  data: Record<string, unknown>;
}) {
  const widgetData = data as unknown as ErrorAnalysisData;
  const errors = widgetData.errors ?? [];
  const [expanded, setExpanded] = useState(true);

  // Group by type, sort major-first within each group
  const grouped: Record<string, ErrorItem[]> = {};
  for (const err of errors) {
    (grouped[err.type] ??= []).push(err);
  }
  const severityOrder: Record<string, number> = { major: 0, moderate: 1, minor: 2 };
  for (const type of Object.keys(grouped)) {
    grouped[type]!.sort((a, b) => (severityOrder[a.severity] ?? 3) - (severityOrder[b.severity] ?? 3));
  }

  const types = Object.keys(grouped);
  const [activeType, setActiveType] = useState(types[0] ?? "");
  const [showAll, setShowAll] = useState(false);

  const activeErrors = grouped[activeType] ?? [];
  const visibleErrors = showAll ? activeErrors : activeErrors.slice(0, MAX_VISIBLE);
  const hiddenCount = activeErrors.length - MAX_VISIBLE;

  // Summary
  const majorTotal = errors.filter((e) => e.severity === "major").length;

  return (
    <WidgetCard>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between px-3 py-2 text-left focus-ring rounded-t-[var(--radius-lg)]"
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-2">
          <h4 className="text-xs font-semibold text-[color:var(--color-text-primary)]">
            Error analysis
          </h4>
          <span className="text-[10px] text-[color:var(--color-text-muted)]">
            {errors.length}
          </span>
          {majorTotal > 0 && (
            <span className="flex items-center gap-0.5 rounded-full bg-[var(--color-danger-light)] px-1.5 py-0.5 text-[10px] leading-none text-[color:var(--color-danger)]">
              {majorTotal} major
            </span>
          )}
        </div>
        {expanded ? (
          <ChevronDown className="h-3.5 w-3.5 text-[color:var(--color-text-muted)]" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 text-[color:var(--color-text-muted)]" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-[var(--color-border)] animate-[expandDown_0.15s_ease-out]">
          {/* Type tabs */}
          {types.length > 1 && (
            <div className="flex gap-0.5 border-b border-[var(--color-border)] px-3 pt-1">
              {types.map((type) => {
                const conf = TYPE_CONF[type] ?? { label: type, color: "text-[color:var(--color-text-muted)]", bg: "bg-[var(--color-surface-secondary)]" };
                const isActive = activeType === type;
                const count = grouped[type]!.length;
                return (
                  <button
                    key={type}
                    onClick={() => { setActiveType(type); setShowAll(false); }}
                    className={`flex items-center gap-1 border-b-2 px-2 py-1.5 text-[11px] font-medium transition-colors ${
                      isActive
                        ? `border-current ${conf.color}`
                        : "border-transparent text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-secondary)]"
                    }`}
                  >
                    {conf.label}
                    <span className={`rounded-full px-1 py-0.5 text-[9px] leading-none ${
                      isActive ? `${conf.bg}` : "bg-[var(--color-surface-secondary)]"
                    }`}>
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>
          )}

          {/* Error list */}
          <div className="divide-y divide-[var(--color-border)]/50 px-3">
            {visibleErrors.map((err, i) => (
              <CompactErrorRow key={i} error={err} />
            ))}
          </div>

          {/* Show more */}
          {!showAll && hiddenCount > 0 && (
            <div className="border-t border-[var(--color-border)] px-3 py-1.5">
              <button
                onClick={() => setShowAll(true)}
                className="text-[11px] font-medium text-[color:var(--color-primary)] hover:underline"
              >
                +{hiddenCount} more
              </button>
            </div>
          )}
        </div>
      )}
    </WidgetCard>
  );
}
