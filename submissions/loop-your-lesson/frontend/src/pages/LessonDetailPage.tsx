import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  ArrowLeft,
  Calendar,
  User,
  MessageSquare,
  AlertTriangle,
  BookOpen,
  BarChart3,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Clock,
  Loader2,
  TrendingUp,
  Repeat,
  Sparkles,
  Zap,
  Play,
} from "lucide-react";
import { useContextOptions } from "@/api/hooks/useContextOptions";
import { useSkillResults } from "@/api/hooks/useSkillResults";
import type {
  SkillResultError,
  SkillResultTheme,
  SkillResultErrorPattern,
} from "@/api/hooks/useSkillResults";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Pill from "@/components/ui/Pill";
import Spinner from "@/components/ui/Spinner";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const PATTERN_STATUS_VARIANT: Record<string, "default" | "success" | "warning" | "error"> = {
  new: "warning",
  recurring: "error",
  improving: "default",
  mastered: "success",
};

const PATTERN_STATUS_ICON: Record<string, typeof Zap> = {
  new: Zap,
  recurring: Repeat,
  improving: TrendingUp,
  mastered: CheckCircle2,
};

function SectionHeading({ icon: Icon, title, count }: { icon: typeof BookOpen; title: string; count?: number }) {
  return (
    <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-[color:var(--color-text-primary)]">
      <Icon className="h-4 w-4 text-[color:var(--color-text-muted)]" />
      {title}
      {count != null && (
        <span className="text-xs font-normal text-[color:var(--color-text-muted)]">({count})</span>
      )}
    </h2>
  );
}

// ---------------------------------------------------------------------------
// Skill status row
// ---------------------------------------------------------------------------

const SKILL_LABELS: Record<string, string> = {
  "analyze-lesson-errors": "Error analysis",
  "analyze-lesson-themes": "Theme extraction",
  "analyze-lesson-level": "Level assessment",
  "generate-classtime-questions": "Practice questions",
};

function SkillStatusRow({ skillStatus }: { skillStatus: Record<string, string> }) {
  if (Object.keys(skillStatus).length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {Object.entries(skillStatus).map(([skill, status]) => {
        const label = SKILL_LABELS[skill] ?? skill;
        const isCompleted = status === "completed";
        const isFailed = status === "failed";
        const isRunning = status === "running" || status === "pending";

        return (
          <div
            key={skill}
            className={`flex items-center gap-1.5 rounded-[var(--radius-md)] px-2.5 py-1 text-xs font-medium ${
              isCompleted
                ? "bg-[var(--color-success-light)] text-[color:var(--color-success)]"
                : isFailed
                  ? "bg-[var(--color-danger-light)] text-[color:var(--color-danger)]"
                  : "bg-[var(--color-surface-secondary)] text-[color:var(--color-text-muted)]"
            }`}
          >
            {isCompleted && <CheckCircle2 className="h-3 w-3" />}
            {isFailed && <AlertTriangle className="h-3 w-3" />}
            {isRunning && <Loader2 className="h-3 w-3 animate-spin" />}
            {label}
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Level assessment card
// ---------------------------------------------------------------------------

function LevelCard({ level }: { level: NonNullable<import("@/api/hooks/useSkillResults").SkillResults["level"]> }) {
  const dimensions: Array<{ key: string; label: string; color: string; bg: string }> = [
    { key: "range", label: "Range", color: "text-blue-700", bg: "bg-blue-50" },
    { key: "accuracy", label: "Accuracy", color: "text-emerald-700", bg: "bg-emerald-50" },
    { key: "fluency", label: "Fluency", color: "text-violet-700", bg: "bg-violet-50" },
    { key: "interaction", label: "Interaction", color: "text-amber-700", bg: "bg-amber-50" },
    { key: "coherence", label: "Coherence", color: "text-rose-700", bg: "bg-rose-50" },
  ];

  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-[color:var(--color-text-muted)]">
            Overall level
          </p>
          <p className="mt-1 text-2xl font-bold text-[color:var(--color-text-primary)]">{level.overall}</p>
          {level.zpd.lower && level.zpd.upper && (
            <p className="mt-0.5 text-xs text-[color:var(--color-text-muted)]">
              ZPD: {level.zpd.lower} - {level.zpd.upper}
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {dimensions.map(({ key, label, color, bg }) => {
            const val = level.dimensions[key as keyof typeof level.dimensions];
            if (!val) return null;
            return (
              <div key={key} className="text-center">
                <p className={`text-[10px] font-medium uppercase tracking-wider ${color}`}>
                  {label}
                </p>
                <span className={`mt-0.5 inline-flex items-center rounded-[var(--radius-md)] px-2.5 py-1 text-[length:var(--text-label)] leading-[var(--lh-label)] tracking-[var(--ls-label)] font-semibold ${bg} ${color}`}>
                  {val}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {(level.strengths.length > 0 || level.gaps.length > 0) && (
        <div className="mt-3 grid grid-cols-2 gap-4 border-t border-[var(--color-border)] pt-3">
          {level.strengths.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium text-[color:var(--color-success)]">Strengths</p>
              <ul className="space-y-0.5">
                {level.strengths.map((s, i) => (
                  <li key={i} className="text-xs text-[color:var(--color-text-secondary)]">
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {level.gaps.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium text-[color:var(--color-danger)]">Gaps</p>
              <ul className="space-y-0.5">
                {level.gaps.map((g, i) => (
                  <li key={i} className="text-xs text-[color:var(--color-text-secondary)]">
                    {g}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {level.suggestions && level.suggestions.length > 0 && (
        <div className="mt-3 border-t border-[var(--color-border)] pt-3">
          <p className="mb-1 text-xs font-medium text-[color:var(--color-primary)]">Suggestions</p>
          <ul className="space-y-0.5">
            {level.suggestions.map((s, i) => (
              <li key={i} className="text-xs text-[color:var(--color-text-secondary)]">
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Error row (lightweight, expandable)
// ---------------------------------------------------------------------------

const SEVERITY_DOT: Record<string, string> = {
  minor: "bg-[var(--color-text-muted)]",
  moderate: "bg-amber-400",
  major: "bg-[var(--color-danger)]",
};

function ErrorRow({ error }: { error: SkillResultError }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetails = error.reasoning || (error.l1_transfer && error.l1_transfer_explanation) || error.correction_strategy;

  return (
    <div className="group">
      <button
        type="button"
        onClick={() => hasDetails && setExpanded(!expanded)}
        className={`flex w-full items-start gap-2.5 py-2 text-left ${hasDetails ? "cursor-pointer" : "cursor-default"}`}
      >
        {/* Severity dot */}
        <span
          className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${SEVERITY_DOT[error.severity] ?? SEVERITY_DOT.minor}`}
          title={error.severity}
        />

        <div className="min-w-0 flex-1">
          <p className="text-sm leading-snug">
            <span className="text-[color:var(--color-danger)] line-through decoration-[color:var(--color-danger)]/40">
              {error.original}
            </span>
            <span className="mx-1.5 text-[color:var(--color-text-muted)]">&rarr;</span>
            <span className="font-medium text-[color:var(--color-success)]">
              {error.corrected}
            </span>
          </p>
          <p className="mt-0.5 text-xs text-[color:var(--color-text-muted)]">
            {error.explanation}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {error.l1_transfer && (
            <span title="L1 transfer"><Sparkles className="h-3 w-3 text-amber-400" /></span>
          )}
          {error.timestamp && (
            <span className="text-xs tabular-nums text-[color:var(--color-text-muted)] opacity-60">
              {error.timestamp}
            </span>
          )}
          {hasDetails && (
            <ChevronRight className={`h-3 w-3 text-[color:var(--color-text-muted)] transition-transform ${expanded ? "rotate-90" : ""}`} />
          )}
        </div>
      </button>

      {expanded && (
        <div className="mb-1.5 ml-[18px] space-y-1.5 rounded-[var(--radius-md)] bg-[var(--color-surface-secondary)] px-3 py-2">
          {error.reasoning && (
            <p className="text-xs leading-relaxed text-[color:var(--color-text-secondary)]">
              {error.reasoning}
            </p>
          )}
          {error.l1_transfer && error.l1_transfer_explanation && (
            <p className="text-xs leading-relaxed text-[color:var(--color-text-secondary)]">
              <span className="font-medium text-amber-600">L1 transfer:</span> {error.l1_transfer_explanation}
            </p>
          )}
          {error.correction_strategy && (
            <div className="flex gap-1.5">
              <Pill>{error.correction_strategy}</Pill>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Error subtabs: by type + patterns
// ---------------------------------------------------------------------------

const ERROR_TYPES: Record<string, { label: string; color: string; bg: string }> = {
  grammar:       { label: "Grammar",       color: "text-blue-600",    bg: "bg-blue-50" },
  vocabulary:    { label: "Vocabulary",     color: "text-violet-600",  bg: "bg-violet-50" },
  pronunciation: { label: "Pronunciation",  color: "text-amber-600",   bg: "bg-amber-50" },
  fluency:       { label: "Fluency",        color: "text-emerald-600", bg: "bg-emerald-50" },
};

const PATTERNS_SUBTAB = { label: "Patterns", color: "text-rose-600", bg: "bg-rose-50" };

// Collapsible group of errors by subtype within a type tab
function ErrorSubtypeGroup({ subtype, errors }: { subtype: string; errors: SkillResultError[] }) {
  const [collapsed, setCollapsed] = useState(false);
  const majorCount = errors.filter((e) => e.severity === "major").length;
  const moderateCount = errors.filter((e) => e.severity === "moderate").length;
  const Chevron = collapsed ? ChevronRight : ChevronDown;

  return (
    <div>
      <button
        type="button"
        onClick={() => setCollapsed(!collapsed)}
        className="flex w-full items-center gap-2 py-2 text-left"
      >
        <Chevron className="h-3 w-3 shrink-0 text-[color:var(--color-text-muted)]" />
        <span className="text-xs font-semibold uppercase tracking-wider text-[color:var(--color-text-secondary)]">
          {subtype || "Other"}
        </span>
        <span className="text-[10px] text-[color:var(--color-text-muted)]">
          {errors.length}
        </span>
        {majorCount > 0 && (
          <span className="flex items-center gap-0.5 rounded-full bg-[var(--color-danger-light)] px-1.5 py-0.5 text-[10px] leading-none text-[color:var(--color-danger)]">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-danger)]" />
            {majorCount} major
          </span>
        )}
        {moderateCount > 0 && (
          <span className="flex items-center gap-0.5 rounded-full bg-[var(--color-warning-light)] px-1.5 py-0.5 text-[10px] leading-none text-amber-700">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            {moderateCount} moderate
          </span>
        )}
      </button>
      {!collapsed && (
        <div className="ml-5 divide-y divide-[var(--color-border)]">
          {errors.map((error, i) => (
            <ErrorRow key={i} error={error} />
          ))}
        </div>
      )}
    </div>
  );
}

function ErrorsTabContent({ errors, patterns }: { errors: SkillResultError[]; patterns: SkillResultErrorPattern[] }) {
  // Group errors by type
  const grouped: Record<string, SkillResultError[]> = {};
  for (const e of errors) {
    (grouped[e.type] ??= []).push(e);
  }

  const types = Object.keys(grouped);

  // Sort: major errors first within each group
  const severityOrder: Record<string, number> = { major: 0, moderate: 1, minor: 2 };
  for (const type of types) {
    grouped[type]!.sort((a, b) => (severityOrder[a.severity] ?? 3) - (severityOrder[b.severity] ?? 3));
  }

  // Subtab IDs: error types + "patterns" if available
  const subtabIds = [...types, ...(patterns.length > 0 ? ["_patterns"] : [])];
  const [activeSubtab, setActiveSubtab] = useState(subtabIds[0] ?? "");

  const isPatterns = activeSubtab === "_patterns";
  const activeErrors = !isPatterns ? (grouped[activeSubtab] ?? []) : [];
  const majorCount = activeErrors.filter((e) => e.severity === "major").length;

  // Group active errors by subtype for categorized view
  const subtypeGroups: Record<string, SkillResultError[]> = {};
  for (const e of activeErrors) {
    const key = e.subtype || "other";
    (subtypeGroups[key] ??= []).push(e);
  }
  // Sort subtype groups: groups with major errors first, then by count
  const subtypeKeys = Object.keys(subtypeGroups).sort((a, b) => {
    const aMajor = subtypeGroups[a]!.some((e) => e.severity === "major") ? 0 : 1;
    const bMajor = subtypeGroups[b]!.some((e) => e.severity === "major") ? 0 : 1;
    if (aMajor !== bMajor) return aMajor - bMajor;
    return subtypeGroups[b]!.length - subtypeGroups[a]!.length;
  });
  const hasMultipleSubtypes = subtypeKeys.length > 1;

  return (
    <div>
      {/* Subtabs */}
      <div className="mb-4 flex flex-wrap gap-1.5">
        {subtabIds.map((id) => {
          const isActive = activeSubtab === id;
          const isPatternsTab = id === "_patterns";
          const conf = isPatternsTab ? PATTERNS_SUBTAB : (ERROR_TYPES[id] ?? { label: id, color: "text-[color:var(--color-text-primary)]", bg: "bg-[var(--color-surface-secondary)]" });
          const count = isPatternsTab ? patterns.length : (grouped[id]?.length ?? 0);

          return (
            <button
              key={id}
              onClick={() => setActiveSubtab(id)}
              className={`flex items-center gap-1.5 rounded-[var(--radius-full)] px-3 py-1.5 text-xs font-medium transition-preply ${
                isActive
                  ? `${conf.bg} ${conf.color}`
                  : "text-[color:var(--color-text-muted)] hover:bg-[var(--color-surface-secondary)]"
              }`}
            >
              {conf.label}
              <span className={`rounded-full px-1.5 py-0.5 text-[10px] leading-none ${
                isActive ? "bg-white/60" : "bg-[var(--color-surface-secondary)]"
              }`}>
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Error type content */}
      {!isPatterns && (
        <>
          {majorCount > 0 && (
            <div className="mb-3 flex items-center gap-1.5 text-xs text-[color:var(--color-danger)]">
              <AlertTriangle className="h-3 w-3" />
              {majorCount} major error{majorCount !== 1 ? "s" : ""} - impacts communication
            </div>
          )}

          {hasMultipleSubtypes ? (
            <div className="space-y-1">
              {subtypeKeys.map((subtype) => (
                <ErrorSubtypeGroup
                  key={subtype}
                  subtype={subtype}
                  errors={subtypeGroups[subtype]!}
                />
              ))}
            </div>
          ) : (
            <div className="divide-y divide-[var(--color-border)]">
              {activeErrors.map((error, i) => (
                <ErrorRow key={i} error={error} />
              ))}
            </div>
          )}
        </>
      )}

      {/* Patterns content */}
      {isPatterns && <PatternsTabContent patterns={patterns} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Error patterns section
// ---------------------------------------------------------------------------

const PATTERN_STATUS_ORDER: Record<string, number> = {
  recurring: 0,
  new: 1,
  improving: 2,
  mastered: 3,
};

const PATTERN_STATUS_LABEL: Record<string, string> = {
  recurring: "Needs attention",
  new: "First seen",
  improving: "Getting better",
  mastered: "Well done",
};

function MasteryBar({ score, tested }: { score: number | null; tested: number }) {
  if (tested === 0 || score == null) return null;
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? "bg-[var(--color-success)]" : pct >= 50 ? "bg-amber-400" : "bg-[var(--color-danger)]";

  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-[var(--color-surface-secondary)]">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] tabular-nums text-[color:var(--color-text-muted)]">
        {pct}%
      </span>
    </div>
  );
}

function ErrorPatternCard({ pattern }: { pattern: SkillResultErrorPattern }) {
  const StatusIcon = PATTERN_STATUS_ICON[pattern.status] ?? Zap;
  const typeConf = ERROR_TYPES[pattern.error_type] ?? { label: pattern.error_type, color: "text-[color:var(--color-text-muted)]", bg: "bg-[var(--color-surface-secondary)]" };

  return (
    <div className="flex items-start gap-3 py-2.5">
      <StatusIcon className={`mt-0.5 h-4 w-4 shrink-0 ${
        pattern.status === "recurring" ? "text-[color:var(--color-danger)]" :
        pattern.status === "mastered" ? "text-[color:var(--color-success)]" :
        "text-[color:var(--color-text-muted)]"
      }`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[color:var(--color-text-primary)]">
            {pattern.label}
          </span>
          <Badge variant={PATTERN_STATUS_VARIANT[pattern.status] ?? "default"}>
            {pattern.status}
          </Badge>
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className={`text-[10px] font-medium ${typeConf.color}`}>
            {typeConf.label}
          </span>
          {pattern.error_subtype && (
            <Pill>{pattern.error_subtype}</Pill>
          )}
          <span className="text-[10px] tabular-nums text-[color:var(--color-text-muted)]">
            {pattern.occurrence_count}&times; in {pattern.lesson_count} lesson{pattern.lesson_count !== 1 ? "s" : ""}
          </span>
          {pattern.times_tested > 0 && (
            <span className="text-[10px] tabular-nums text-[color:var(--color-text-muted)]">
              {pattern.times_correct}/{pattern.times_tested} correct
            </span>
          )}
        </div>
        <div className="mt-1.5">
          <MasteryBar score={pattern.mastery_score} tested={pattern.times_tested} />
        </div>
      </div>
    </div>
  );
}

function PatternsTabContent({ patterns }: { patterns: SkillResultErrorPattern[] }) {
  // Group by status
  const grouped: Record<string, SkillResultErrorPattern[]> = {};
  for (const p of patterns) {
    (grouped[p.status] ??= []).push(p);
  }

  const statusKeys = Object.keys(grouped).sort(
    (a, b) => (PATTERN_STATUS_ORDER[a] ?? 9) - (PATTERN_STATUS_ORDER[b] ?? 9),
  );

  return (
    <div className="space-y-4">
      {statusKeys.map((status) => {
        const StatusIcon = PATTERN_STATUS_ICON[status] ?? Zap;
        const items = grouped[status]!;
        return (
          <div key={status}>
            <div className="mb-1 flex items-center gap-1.5">
              <StatusIcon className={`h-3.5 w-3.5 ${
                status === "recurring" ? "text-[color:var(--color-danger)]" :
                status === "mastered" ? "text-[color:var(--color-success)]" :
                status === "improving" ? "text-[color:var(--color-primary)]" :
                "text-amber-500"
              }`} />
              <span className="text-xs font-semibold uppercase tracking-wider text-[color:var(--color-text-secondary)]">
                {PATTERN_STATUS_LABEL[status] ?? status}
              </span>
              <span className="text-[10px] text-[color:var(--color-text-muted)]">{items.length}</span>
            </div>
            <div className="divide-y divide-[var(--color-border)]">
              {items.map((pattern, i) => (
                <ErrorPatternCard key={i} pattern={pattern} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Theme card
// ---------------------------------------------------------------------------

function ThemeCard({ theme }: { theme: SkillResultTheme }) {
  const [expanded, setExpanded] = useState(false);
  const Chevron = expanded ? ChevronDown : ChevronRight;

  const hasVocab =
    (theme.vocabulary_active?.length ?? 0) > 0 ||
    (theme.vocabulary_passive?.length ?? 0) > 0 ||
    (theme.chunks?.length ?? 0) > 0;

  return (
    <Card padding="sm" interactive>
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-start gap-2 text-left"
      >
        <Chevron className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[color:var(--color-text-muted)]" />
        <div className="min-w-0 flex-1">
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
        </div>
        {theme.range.start && (
          <span className="flex shrink-0 items-center gap-1 text-xs text-[color:var(--color-text-muted)]">
            <Clock className="h-3 w-3" />
            {theme.range.start} - {theme.range.end}
          </span>
        )}
      </button>

      {expanded && hasVocab && (
        <div className="mt-2 space-y-2 border-t border-[var(--color-border)] pl-5.5 pt-2">
          {(theme.vocabulary_active?.length ?? 0) > 0 && (
            <div>
              <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-success)]">
                Active vocabulary
              </p>
              <div className="flex flex-wrap gap-1">
                {theme.vocabulary_active!.map((w, i) => (
                  <Pill key={i}>{typeof w === "string" ? w : (w as { term: string }).term}</Pill>
                ))}
              </div>
            </div>
          )}
          {(theme.vocabulary_passive?.length ?? 0) > 0 && (
            <div>
              <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-text-muted)]">
                Passive vocabulary
              </p>
              <div className="flex flex-wrap gap-1">
                {theme.vocabulary_passive!.map((w, i) => (
                  <Pill key={i} variant="outline">{typeof w === "string" ? w : (w as { term: string }).term}</Pill>
                ))}
              </div>
            </div>
          )}
          {(theme.chunks?.length ?? 0) > 0 && (
            <div>
              <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-primary)]">
                Chunks
              </p>
              <div className="flex flex-wrap gap-1">
                {theme.chunks!.map((c, i) => (
                  <Pill key={i}>{typeof c === "string" ? c : (c as { term: string }).term}</Pill>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Practice section
// ---------------------------------------------------------------------------

function PracticeSection({
  session,
}: {
  session: NonNullable<import("@/api/hooks/useSkillResults").SkillResults["classtime_session"]>;
}) {
  const typeCount: Record<string, number> = {};
  for (const q of session.questions) {
    typeCount[q.question_type] = (typeCount[q.question_type] ?? 0) + 1;
  }

  const correctCount = session.results.filter((r) => r.is_correct).length;

  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-[color:var(--color-text-primary)]">
            Practice session
          </p>
          <p className="mt-0.5 text-xs text-[color:var(--color-text-muted)]">
            {session.questions.length} question{session.questions.length !== 1 ? "s" : ""}
            {session.completed && ` - ${correctCount}/${session.results.length} correct`}
          </p>
        </div>
        {session.completed ? (
          <Badge variant="success">Completed</Badge>
        ) : session.student_url ? (
          <Button
            variant="primary"
            size="sm"
            className="gap-1.5"
            onClick={() => window.open(session.student_url, "_blank")}
          >
            <ExternalLink className="h-3 w-3" />
            Start practice
          </Button>
        ) : (
          <Badge>Created</Badge>
        )}
      </div>

      {Object.keys(typeCount).length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {Object.entries(typeCount).map(([type, count]) => (
            <Pill key={type}>
              {count}&times; {type.replace("_", " ")}
            </Pill>
          ))}
        </div>
      )}

      {session.completed && session.results.length > 0 && (
        <div className="mt-3 border-t border-[var(--color-border)] pt-3">
          <div className="grid gap-1">
            {session.questions.map((q) => {
              const result = session.results.find((r) => r.question_index === q.question_index);
              return (
                <div key={q.question_index} className="flex items-center gap-2 text-xs">
                  {result ? (
                    result.is_correct ? (
                      <CheckCircle2 className="h-3 w-3 shrink-0 text-[color:var(--color-success)]" />
                    ) : (
                      <AlertTriangle className="h-3 w-3 shrink-0 text-[color:var(--color-danger)]" />
                    )
                  ) : (
                    <Clock className="h-3 w-3 shrink-0 text-[color:var(--color-text-muted)]" />
                  )}
                  <span className="truncate text-[color:var(--color-text-secondary)]">{q.stem}</span>
                  <Pill>{q.question_type.replace("_", " ")}</Pill>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

type TabId = "overview" | "errors" | "themes" | "practice";
const VALID_TABS = new Set<string>(["overview", "errors", "themes", "practice"]);

export default function LessonDetailPage() {
  const { lessonId, tab } = useParams();
  const navigate = useNavigate();
  const { data: contextOptions, isLoading } = useContextOptions();
  const { data: skillResults, isLoading: isLoadingSkills } = useSkillResults(lessonId);

  const activeTab: TabId = tab && VALID_TABS.has(tab) ? (tab as TabId) : "overview";
  const setActiveTab = (t: TabId) => navigate(`/lessons/${lessonId}/${t}`, { replace: true });

  // Find lesson and student from context options
  let lesson: { id: string; date: string; summary: string } | null = null;
  let student: import("@/lib/types").ContextStudent | null = null;

  if (contextOptions?.students) {
    for (const s of contextOptions.students) {
      const found = s.lessons.find((l) => l.id === lessonId);
      if (found) {
        lesson = found;
        student = s;
        break;
      }
    }
  }

  const studentName = student?.name ?? "";
  const studentId = student?.id ?? "";
  const l1 = student?.subject_config?.l1;
  const l2 = student?.subject_config?.l2;

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  if (!lesson) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3">
        <p className="text-sm text-[color:var(--color-text-muted)]">
          Lesson not found
        </p>
        <Link
          to="/students"
          className="text-sm text-[color:var(--color-primary)] hover:underline"
        >
          Back to students
        </Link>
      </div>
    );
  }

  const hasResults =
    skillResults &&
    (skillResults.errors.length > 0 ||
      skillResults.themes.length > 0 ||
      skillResults.level ||
      skillResults.error_patterns.length > 0 ||
      skillResults.classtime_session);

  // Tab definitions with counts
  const tabs: Array<{ id: TabId; label: string; icon: typeof BarChart3; count?: number; available: boolean }> = [
    {
      id: "overview",
      label: "Overview",
      icon: BarChart3,
      available: !!skillResults?.level || Object.keys(skillResults?.skill_status ?? {}).length > 0,
    },
    {
      id: "errors",
      label: "Errors",
      icon: AlertTriangle,
      count: (skillResults?.errors.length ?? 0) + (skillResults?.error_patterns.length ?? 0),
      available: (skillResults?.errors.length ?? 0) > 0 || (skillResults?.error_patterns.length ?? 0) > 0,
    },
    {
      id: "themes",
      label: "Themes",
      icon: BookOpen,
      count: skillResults?.themes.length,
      available: (skillResults?.themes.length ?? 0) > 0,
    },
    {
      id: "practice",
      label: "Practice",
      icon: Play,
      count: skillResults?.classtime_session?.questions.length,
      available: !!skillResults?.classtime_session,
    },
  ];

  const availableTabs = tabs.filter((t) => t.available);

  return (
    <div className="flex flex-1 flex-col overflow-y-auto">
      {/* Header */}
      <div className="bg-[var(--color-surface)] px-6 py-5">
        <Link
          to={studentId ? `/students/${studentId}` : "/students"}
          className="mb-3 inline-flex items-center gap-1.5 text-sm text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-primary)]"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          {studentName || "Back to students"}
        </Link>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-semibold text-[color:var(--color-text-primary)]">
              <Calendar className="h-5 w-5 text-[color:var(--color-text-muted)]" />
              {lesson.date}
            </h1>
            <div className="mt-1.5 flex items-center gap-2">
              <Link
                to={`/students/${studentId}`}
                className="flex items-center gap-1.5 text-sm text-[color:var(--color-primary)] hover:underline"
              >
                <User className="h-3.5 w-3.5" />
                {studentName}
              </Link>
              {student?.level && <Badge>{student.level}</Badge>}
              {l1 && l2 && (
                <span className="text-xs text-[color:var(--color-text-muted)]">
                  {l1} &rarr; {l2}
                </span>
              )}
            </div>
          </div>

          <Button
            variant="secondary"
            size="sm"
            className="shrink-0 gap-2"
            onClick={() =>
              navigate(
                `/chat?mode=student_practice&studentId=${studentId}&lessonId=${lessonId}`,
              )
            }
          >
            <MessageSquare className="h-4 w-4" />
            Chat about this lesson
          </Button>
        </div>
      </div>

      {/* Loading */}
      {isLoadingSkills && (
        <div className="flex flex-1 items-center justify-center">
          <Spinner />
        </div>
      )}

      {/* Empty state */}
      {!isLoadingSkills && !hasResults && (
        <div className="flex flex-1 items-center justify-center p-6">
          <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-12 text-center">
            <p className="text-sm text-[color:var(--color-text-muted)]">
              Skill results will appear here once the lesson has been analyzed
            </p>
          </div>
        </div>
      )}

      {/* Tabs */}
      {!isLoadingSkills && hasResults && (
        <>
          {/* Tab bar */}
          <div className="flex gap-1 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-6 pt-1">
            {availableTabs.map((tab) => {
              const TabIcon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 rounded-t-[var(--radius-md)] border-b-2 px-4 py-2.5 text-sm font-medium transition-preply ${
                    isActive
                      ? "border-[var(--color-primary)] text-[color:var(--color-primary)]"
                      : "border-transparent text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-secondary)]"
                  }`}
                >
                  <TabIcon className="h-4 w-4" />
                  {tab.label}
                  {tab.count != null && tab.count > 0 && (
                    <span
                      className={`rounded-[var(--radius-full)] px-1.5 py-0.5 text-[10px] leading-none ${
                        isActive
                          ? "bg-[var(--color-primary-light)] text-[color:var(--color-primary)]"
                          : "bg-[var(--color-surface-secondary)]"
                      }`}
                    >
                      {tab.count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Tab content */}
          <div className="space-y-6 p-6">
            {/* Overview tab */}
            {activeTab === "overview" && (
              <>
                {skillResults && Object.keys(skillResults.skill_status).length > 0 && (
                  <SkillStatusRow skillStatus={skillResults.skill_status} />
                )}
                {skillResults?.level && (
                  <section>
                    <SectionHeading icon={BarChart3} title="Level assessment" />
                    <LevelCard level={skillResults.level} />
                  </section>
                )}
              </>
            )}

            {/* Errors tab (includes patterns as subtab) */}
            {activeTab === "errors" && skillResults && (
              <ErrorsTabContent
                errors={skillResults.errors}
                patterns={skillResults.error_patterns}
              />
            )}

            {/* Themes tab */}
            {activeTab === "themes" && skillResults && skillResults.themes.length > 0 && (
              <div className="grid gap-2">
                {skillResults.themes.map((theme, i) => (
                  <ThemeCard key={i} theme={theme} />
                ))}
              </div>
            )}

            {/* Practice tab */}
            {activeTab === "practice" && skillResults?.classtime_session && (
              <PracticeSection session={skillResults.classtime_session} />
            )}
          </div>
        </>
      )}
    </div>
  );
}
