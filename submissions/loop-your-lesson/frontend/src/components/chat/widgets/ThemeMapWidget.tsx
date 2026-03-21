import { useState } from "react";
import { ChevronDown, ChevronRight, Clock } from "lucide-react";
import Pill from "@/components/ui/Pill";
import WidgetCard from "@/components/ui/WidgetCard";
import type { ThemeMapData, ThemeItem } from "@/lib/types";

function ThemeCard({ theme }: { theme: ThemeItem }) {
  const [expanded, setExpanded] = useState(false);

  const allVocab = [
    ...(theme.vocabulary_active ?? []),
    ...(theme.vocabulary_passive ?? []),
  ];
  const hasDetail = allVocab.length > 0 || (theme.chunks ?? []).length > 0;

  return (
    <div className="border-b border-[var(--color-border)] last:border-0">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between px-3 py-2 text-left transition-colors hover:bg-[var(--color-surface-hover)] focus-ring"
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[color:var(--color-text-primary)]">
            {theme.topic}
          </span>
          {theme.communicative_function && (
            <Pill>{theme.communicative_function}</Pill>
          )}
          {theme.initiated_by && (
            <span className="text-xs text-[color:var(--color-text-muted)]">
              by {theme.initiated_by}
            </span>
          )}
        </div>
        {hasDetail ? (
          expanded ? (
            <ChevronDown className="h-4 w-4 shrink-0 text-[color:var(--color-text-muted)]" />
          ) : (
            <ChevronRight className="h-4 w-4 shrink-0 text-[color:var(--color-text-muted)]" />
          )
        ) : null}
      </button>
      {expanded && hasDetail && (
        <div className="px-3 pb-2 animate-[expandDown_0.15s_ease-out]">
          {(theme.vocabulary_active ?? []).length > 0 && (
            <div className="mb-1.5">
              <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-success)]">
                Active
              </p>
              <div className="flex flex-wrap gap-1.5">
                {theme.vocabulary_active!.map((word) => (
                  <span
                    key={word}
                    className="rounded-[var(--radius-full)] bg-[var(--color-primary-light)] px-2.5 py-1 text-xs text-[color:var(--color-primary)]"
                  >
                    {word}
                  </span>
                ))}
              </div>
            </div>
          )}
          {(theme.vocabulary_passive ?? []).length > 0 && (
            <div className="mb-1.5">
              <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-text-muted)]">
                Passive
              </p>
              <div className="flex flex-wrap gap-1.5">
                {theme.vocabulary_passive!.map((word) => (
                  <Pill key={word} variant="outline">{word}</Pill>
                ))}
              </div>
            </div>
          )}
          {(theme.chunks ?? []).length > 0 && (
            <div className="mb-1.5">
              <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-primary)]">
                Chunks
              </p>
              <div className="flex flex-wrap gap-1.5">
                {theme.chunks!.map((chunk) => (
                  <Pill key={chunk}>{chunk}</Pill>
                ))}
              </div>
            </div>
          )}
          {theme.transcript_range.start && (
            <div className="mt-1.5 flex items-center gap-1 text-micro text-[color:var(--color-text-muted)]">
              <Clock className="h-3 w-3" />
              {theme.transcript_range.start} &ndash; {theme.transcript_range.end}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ThemeMapWidget({ data }: { data: Record<string, unknown> }) {
  const widgetData = data as unknown as ThemeMapData;
  const themes = widgetData.themes ?? [];

  return (
    <WidgetCard>
      <div className="px-3 py-2">
        <h4 className="text-sm font-semibold text-[color:var(--color-text-primary)]">
          Lesson themes
        </h4>
        <p className="text-xs text-[color:var(--color-text-muted)]">
          {themes.length} topic{themes.length !== 1 ? "s" : ""} identified
        </p>
      </div>
      <div className="border-t border-[var(--color-border)]">
        {themes.map((theme, i) => (
          <ThemeCard key={i} theme={theme} />
        ))}
      </div>
    </WidgetCard>
  );
}
