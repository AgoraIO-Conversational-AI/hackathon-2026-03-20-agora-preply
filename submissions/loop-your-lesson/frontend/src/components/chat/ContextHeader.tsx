import { useState, useRef, useEffect } from "react";
import {
  Sun,
  GraduationCap,
  BookOpen,
  UserRound,
  ChevronDown,
  Globe,
  Target,
  Calendar,
} from "lucide-react";
import type { PreplyMode } from "@/lib/modes";
import { MODE_DEFINITIONS, MODES } from "@/lib/modes";
import type { ContextStudent, SubjectConfig } from "@/lib/types";
import Badge from "@/components/ui/Badge";
import WidgetCard from "@/components/ui/WidgetCard";
import { Tooltip } from "@/components/ui/Tooltip";

// ---------------------------------------------------------------------------
// Shared context shape
// ---------------------------------------------------------------------------

export interface ContextInfo {
  teacherName?: string;
  studentName?: string;
  studentLevel?: string;
  studentGoal?: string;
  totalLessons?: number;
  subjectConfig?: SubjectConfig;
  lessonDate?: string;
  lessonSummary?: string;
  lessonDuration?: number;
  studentCount?: number;
}

// ---------------------------------------------------------------------------
// Separator dot
// ---------------------------------------------------------------------------

function Dot() {
  return (
    <span className="text-[color:var(--color-text-muted)] select-none">
      &middot;
    </span>
  );
}

// ---------------------------------------------------------------------------
// Context detail row (icon + label + value)
// ---------------------------------------------------------------------------

function DetailRow({
  icon: Icon,
  label,
  children,
  tooltip,
}: {
  icon: typeof Globe;
  label: string;
  children: React.ReactNode;
  tooltip?: string;
}) {
  const row = (
    <div className="overflow-hidden py-1">
      <div className="flex items-center gap-1.5">
        <Icon className="h-3 w-3 shrink-0 text-[color:var(--color-text-muted)]" />
        <span className="text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-text-muted)]">
          {label}
        </span>
      </div>
      <p className="mt-0.5 overflow-hidden text-ellipsis whitespace-nowrap pl-[18px] text-xs text-[color:var(--color-text-secondary)]">
        {children}
      </p>
    </div>
  );

  if (tooltip) {
    return <Tooltip content={tooltip} placement="bottom" className="block overflow-hidden">{row}</Tooltip>;
  }
  return row;
}

// ---------------------------------------------------------------------------
// Context panel (collapsible bar + compact detail)
// ---------------------------------------------------------------------------

function ContextBar({ mode, ctx }: { mode: PreplyMode; ctx: ContextInfo }) {
  const modeDef = MODE_DEFINITIONS[mode];
  const ModeIcon = mode === MODES.DAILY_BRIEFING ? Sun : GraduationCap;

  return (
    <div className="flex h-11 items-center gap-3 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4">
      <ModeIcon className="h-4 w-4 shrink-0 text-[color:var(--color-primary)]" />
      <span className="text-sm font-medium text-[color:var(--color-text-primary)]">
        {modeDef.name}
      </span>

      {ctx.studentName && (
        <>
          <Dot />
          <span className="text-sm text-[color:var(--color-text-secondary)]">
            {ctx.studentName}
          </span>
          {ctx.studentLevel && (
            <Badge variant="default">{ctx.studentLevel}</Badge>
          )}
        </>
      )}

      {!ctx.studentName && ctx.teacherName && (
        <>
          <Dot />
          <span className="flex items-center gap-1.5 text-sm text-[color:var(--color-text-secondary)]">
            <UserRound className="h-3.5 w-3.5 shrink-0 text-[color:var(--color-text-muted)]" />
            {ctx.teacherName}
          </span>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Inline context detail (rendered inside chat scroll area)
// ---------------------------------------------------------------------------

export function ContextDetailPanel({
  mode,
  ctx,
}: {
  mode: PreplyMode;
  ctx: ContextInfo;
}) {
  const l1 = ctx.subjectConfig?.l1;
  const l2 = ctx.subjectConfig?.l2;

  const hasDetail =
    (mode === MODES.STUDENT_PRACTICE &&
      (l1 || ctx.totalLessons || ctx.studentGoal || ctx.lessonDate || ctx.lessonSummary)) ||
    (mode === MODES.DAILY_BRIEFING && ctx.studentCount);

  if (!hasDetail) return null;

  const title = mode === MODES.STUDENT_PRACTICE ? "Lesson context" : "Session overview";

  return (
    <div className="mx-auto max-w-3xl px-4 pt-6">
      <WidgetCard>
        {/* Title */}
        <div className="border-b border-[var(--color-border)] px-4 py-2.5">
          <h3 className="flex items-center gap-2 text-xs font-semibold text-[color:var(--color-text-primary)]">
            {title}
            {mode === MODES.STUDENT_PRACTICE && ctx.totalLessons != null && ctx.totalLessons > 0 && (
              <span className="font-normal text-[color:var(--color-text-muted)]">
                · {ctx.totalLessons} lesson{ctx.totalLessons !== 1 ? "s" : ""}
              </span>
            )}
          </h3>
        </div>

        {/* Details */}
        <div className="px-4 py-2">
          {mode === MODES.STUDENT_PRACTICE && (
            <div className="grid grid-cols-2 gap-x-6 overflow-hidden">
              {/* Left column */}
              <div className="overflow-hidden">
                {l1 && l2 && (
                  <DetailRow icon={Globe} label="Language">
                    <Tooltip content="Native language" placement="bottom">
                      <span>{l1}</span>
                    </Tooltip>
                    {" → "}
                    <Tooltip content="Learning" placement="bottom">
                      <span>{l2}</span>
                    </Tooltip>
                  </DetailRow>
                )}
                {ctx.studentGoal && (
                  <DetailRow icon={Target} label="Goal" tooltip={ctx.studentGoal}>
                    {ctx.studentGoal}
                  </DetailRow>
                )}
              </div>

              {/* Right column */}
              <div className="overflow-hidden">
                {ctx.lessonDate && (
                  <DetailRow icon={Calendar} label="Lesson">
                    {ctx.lessonDate}
                    {ctx.lessonDuration ? ` · ${ctx.lessonDuration} min` : ""}
                  </DetailRow>
                )}
                {ctx.lessonSummary && (
                  <DetailRow icon={BookOpen} label="Summary" tooltip={ctx.lessonSummary}>
                    {ctx.lessonSummary}
                  </DetailRow>
                )}
              </div>
            </div>
          )}

          {mode === MODES.DAILY_BRIEFING && (
            <DetailRow icon={GraduationCap} label="Students">
              {ctx.studentCount} student{ctx.studentCount !== 1 ? "s" : ""} today
            </DetailRow>
          )}
        </div>
      </WidgetCard>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Dropdown primitive
// ---------------------------------------------------------------------------

function Dropdown<T extends string>({
  value,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  onChange: _onChange,
  placeholder,
  children,
  buttonLabel,
}: {
  value: T | null;
  onChange: (val: T | null) => void;
  placeholder: string;
  children: (props: {
    close: () => void;
    isSelected: (val: T) => boolean;
  }) => React.ReactNode;
  buttonLabel?: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-haspopup="listbox"
        className={`flex items-center gap-1.5 rounded-[var(--radius-md)] border px-2.5 py-1 text-sm transition-preply ${
          open
            ? "border-[var(--color-text-secondary)] text-[color:var(--color-text-primary)]"
            : value
              ? "border-[var(--color-border)] text-[color:var(--color-text-secondary)]"
              : "border-[var(--color-border)] text-[color:var(--color-text-muted)]"
        } hover:border-[var(--color-text-secondary)]`}
      >
        {buttonLabel ?? placeholder}
        <ChevronDown
          className={`h-3 w-3 shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="absolute left-0 top-full z-30 mt-1 min-w-72 overflow-hidden rounded-[var(--radius-lg)] border-2 border-[var(--color-border)] bg-[var(--color-surface)] shadow-lg animate-[fadeIn_0.1s_ease-out]">
          {children({
            close: () => setOpen(false),
            isSelected: (val) => val === value,
          })}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Student dropdown item (reused in selector)
// ---------------------------------------------------------------------------

function StudentDropdownItem({
  student,
  isSelected,
  onClick,
}: {
  student: ContextStudent;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors first:rounded-t-[calc(var(--radius-lg)-2px)] last:rounded-b-[calc(var(--radius-lg)-2px)] ${
        isSelected
          ? "bg-[var(--color-surface-secondary)]"
          : "hover:bg-[var(--color-surface-secondary)]"
      }`}
    >
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--color-surface-secondary)] text-xs font-medium text-[color:var(--color-text-muted)]">
        {student.name
          .split(" ")
          .map((w) => w[0])
          .join("")}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[color:var(--color-text-primary)]">
            {student.name}
          </span>
          {student.level && <Badge variant="default">{student.level}</Badge>}
        </div>
        <p className="text-xs text-[color:var(--color-text-muted)]">
          {student.lessons.length} lesson
          {student.lessons.length !== 1 ? "s" : ""}
          {student.subject_config?.l1 &&
            student.subject_config?.l2 &&
            ` · ${student.subject_config.l1} → ${student.subject_config.l2}`}
        </p>
      </div>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Context selector (for new conversations)
// ---------------------------------------------------------------------------

interface ContextSelectorProps {
  mode: PreplyMode;
  students: ContextStudent[];
  selectedStudentId: string | null;
  selectedLessonId: string | null;
  onStudentChange: (id: string | null) => void;
  onLessonChange: (id: string | null) => void;
  selectedStudentCtx: ContextInfo;
}

function ContextSelector({
  mode,
  students,
  selectedStudentId,
  selectedLessonId,
  onStudentChange,
  onLessonChange,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  selectedStudentCtx: _selectedStudentCtx,
}: ContextSelectorProps) {
  const modeDef = MODE_DEFINITIONS[mode];
  const ModeIcon = mode === MODES.DAILY_BRIEFING ? Sun : GraduationCap;
  const selectedStudent = students.find((s) => s.id === selectedStudentId);
  const selectedLesson = selectedStudent?.lessons.find(
    (l) => l.id === selectedLessonId,
  );

  return (
    <div>
      {/* Top bar with dropdowns */}
      <div className="flex h-11 items-center gap-3 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4">
        <ModeIcon className="h-4 w-4 shrink-0 text-[color:var(--color-primary)]" />
        <span className="text-sm font-medium text-[color:var(--color-text-primary)]">
          {modeDef.name}
        </span>

        {mode === MODES.DAILY_BRIEFING && (
          <>
            <Dot />
            <span className="text-sm text-[color:var(--color-text-muted)]">
              All students
            </span>
          </>
        )}

        {mode === MODES.STUDENT_PRACTICE && (
          <>
            <Dot />

            <Dropdown<string>
              value={selectedStudentId}
              onChange={(val) => {
                onStudentChange(val);
                onLessonChange(null);
              }}
              placeholder="Select student..."
              buttonLabel={
                selectedStudent ? (
                  <span className="flex items-center gap-1.5">
                    <GraduationCap className="h-3.5 w-3.5" />
                    {selectedStudent.name}
                    {selectedStudent.level && (
                      <Badge variant="default">{selectedStudent.level}</Badge>
                    )}
                  </span>
                ) : undefined
              }
            >
              {({ close, isSelected }) =>
                students.map((s) => (
                  <StudentDropdownItem
                    key={s.id}
                    student={s}
                    isSelected={isSelected(s.id)}
                    onClick={() => {
                      onStudentChange(s.id);
                      onLessonChange(null);
                      close();
                    }}
                  />
                ))
              }
            </Dropdown>

            {selectedStudent && selectedStudent.lessons.length > 0 && (
              <>
                <Dot />
                <Dropdown<string>
                  value={selectedLessonId}
                  onChange={onLessonChange}
                  placeholder="Select lesson..."
                  buttonLabel={
                    selectedLesson ? (
                      <span className="flex items-center gap-1.5">
                        <BookOpen className="h-3.5 w-3.5" />
                        {selectedLesson.date}
                      </span>
                    ) : undefined
                  }
                >
                  {({ close, isSelected }) =>
                    selectedStudent.lessons.map((l) => (
                      <button
                        key={l.id}
                        onClick={() => {
                          onLessonChange(l.id);
                          close();
                        }}
                        className={`w-full px-3 py-2.5 text-left transition-colors first:rounded-t-[calc(var(--radius-lg)-2px)] last:rounded-b-[calc(var(--radius-lg)-2px)] ${
                          isSelected(l.id)
                            ? "bg-[var(--color-surface-secondary)]"
                            : "hover:bg-[var(--color-surface-secondary)]"
                        }`}
                      >
                        <p className="text-sm font-medium text-[color:var(--color-text-primary)]">
                          {l.date}
                        </p>
                        <p className="mt-0.5 truncate text-xs text-[color:var(--color-text-muted)]">
                          {l.summary}
                        </p>
                      </button>
                    ))
                  }
                </Dropdown>
              </>
            )}
          </>
        )}
      </div>

      {/* Detail rendered inline in ChatArea via ContextDetailPanel */}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Exported wrapper
// ---------------------------------------------------------------------------

export interface ContextHeaderProps {
  mode: PreplyMode;
  context: ContextInfo;
  isNewConversation: boolean;
  students?: ContextStudent[];
  selectedStudentId?: string | null;
  selectedLessonId?: string | null;
  onStudentChange?: (id: string | null) => void;
  onLessonChange?: (id: string | null) => void;
}

export function ContextHeader({
  mode,
  context,
  isNewConversation,
  students = [],
  selectedStudentId = null,
  selectedLessonId = null,
  onStudentChange,
  onLessonChange,
}: ContextHeaderProps) {
  if (isNewConversation) {
    return (
      <ContextSelector
        mode={mode}
        students={students}
        selectedStudentId={selectedStudentId}
        selectedLessonId={selectedLessonId}
        onStudentChange={onStudentChange ?? (() => {})}
        onLessonChange={onLessonChange ?? (() => {})}
        selectedStudentCtx={context}
      />
    );
  }

  return <ContextBar mode={mode} ctx={context} />;
}
