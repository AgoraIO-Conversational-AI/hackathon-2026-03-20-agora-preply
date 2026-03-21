import { useState } from "react";
import { AlertCircle, ArrowLeft } from "lucide-react";
import { PreplyLogo } from "@/components/ui/PreplyLogo";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ContextHeader } from "@/components/chat/ContextHeader";
import { ProcessTimeline } from "@/components/chat/ProcessTimeline";
import { ChatInput } from "@/components/chat/ChatInput";
import { ModeSelector } from "@/components/chat/ModeSelector";
import { WidgetRouter } from "@/components/chat/widgets/WidgetRouter";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Spinner from "@/components/ui/Spinner";
import type { Message, ProcessStep, ContextStudent } from "@/lib/types";
import { MODES, type PreplyMode } from "@/lib/modes";

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const ERROR_WIDGET_DATA = {
  widget_type: "error_analysis",
  student_id: "maria_42",
  total_errors: 9,
  errors: [
    {
      type: "grammar",
      severity: "moderate",
      original: "I go to the store yesterday",
      corrected: "I went to the store yesterday",
      explanation: "Past simple required for completed past action",
      transcript_position: { utterance: 34, timestamp: "12:45" },
      reasoning:
        "Error taxonomy: morphological > verb tense. B1 should have acquired past simple (CEFR B1: 'can narrate past events'). Marked moderate.",
    },
    {
      type: "grammar",
      severity: "moderate",
      original: "She have two brothers",
      corrected: "She has two brothers",
      explanation: "Subject-verb agreement: third person singular",
      transcript_position: { utterance: 52, timestamp: "18:20" },
      reasoning:
        "Subject-verb agreement error. Expected at A2, persistent at B1 suggests fossilization risk.",
    },
    {
      type: "vocabulary",
      severity: "minor",
      original: "I made a travel to Spain",
      corrected: "I took a trip to Spain",
      explanation: "Collocation: 'take a trip', not 'make a travel'",
      transcript_position: { utterance: 12, timestamp: "04:30" },
      reasoning:
        "L1 transfer from Spanish 'hacer un viaje'. Common at B1, minor impact on communication.",
    },
    {
      type: "pronunciation",
      severity: "minor",
      original: "comfortable /komfor-TAH-bleh/",
      corrected: "comfortable /KUMF-ter-bul/",
      explanation: "Stress on first syllable, schwa in second",
      transcript_position: { utterance: 67, timestamp: "24:10" },
      reasoning:
        "Spanish stress pattern applied to English. Does not block communication.",
    },
  ],
};

const THEME_WIDGET_DATA = {
  widget_type: "theme_map",
  themes: [
    {
      topic: "Travel planning",
      vocabulary: [
        "airport",
        "boarding pass",
        "gate",
        "departure",
        "arrival",
        "luggage",
        "terminal",
      ],
      utterance_count: 42,
      transcript_range: { start: "2:00", end: "18:30" },
    },
    {
      topic: "Restaurant vocabulary",
      vocabulary: ["reservation", "appetizer", "bill", "tip", "waiter"],
      utterance_count: 31,
      transcript_range: { start: "19:00", end: "32:15" },
    },
    {
      topic: "Giving directions",
      vocabulary: ["turn left", "straight ahead", "roundabout", "intersection"],
      utterance_count: 24,
      transcript_range: { start: "33:00", end: "45:00" },
    },
  ],
};

const PRACTICE_WIDGET_DATA = {
  widget_type: "practice_card",
  question_count: 10,
  question_types: { FILL_GAP: 6, SINGLE_CHOICE: 1, BOOLEAN: 1, SORTER: 1, CATEGORIZER: 1 },
  focus_topic: "German L1 transfer errors",
  source_errors: [
    { timestamp: "12:45", original: "I am very enjoying to cook" },
    { timestamp: "18:20", original: "You need the pork" },
    { timestamp: "24:10", original: "I become very angry" },
  ],
  session_url: "https://www.classtime.com/code/8KF8DTF7",
};

const MOCK_THINKING: ProcessStep[] = [
  {
    type: "thinking",
    content:
      "Analyzing the student's error patterns to identify the highest-priority areas for improvement...",
  },
  {
    type: "tool_call",
    toolName: "query_lesson_errors",
    toolId: "t-1",
    toolInput: { student_id: "maria_42", severity: "moderate" },
    status: "completed",
    result: {
      message: "Found 4 moderate+ errors",
      data: {},
      executionTimeMs: 15,
    },
  },
  {
    type: "tool_call",
    toolName: "query_classtime_results",
    toolId: "t-2",
    toolInput: { student_id: "maria_42" },
    status: "running",
  },
];

const MOCK_STUDENTS: ContextStudent[] = [
  {
    id: "s1",
    name: "Maria Garcia",
    level: "B1",
    goal: "Conversational fluency for travel",
    total_lessons: 12,
    subject_config: { l1: "Spanish", l2: "English", language_pair: "es-en" },
    lessons: [
      { id: "l1", date: "2026-03-14", summary: "Travel planning to London, booking, transport" },
      { id: "l2", date: "2026-03-12", summary: "Daily routines, morning habits, commuting" },
    ],
  },
  {
    id: "s2",
    name: "Alex Chen",
    level: "A2",
    goal: "Business English for meetings",
    total_lessons: 8,
    subject_config: { l1: "Mandarin Chinese", l2: "English", language_pair: "zh-en" },
    lessons: [
      { id: "l3", date: "2026-03-13", summary: "Introductions, greetings, and small talk" },
      { id: "l4", date: "2026-03-11", summary: "Shopping vocabulary and transactions" },
    ],
  },
  {
    id: "s3",
    name: "Sophie Martin",
    level: "B2",
    goal: "Academic writing for university",
    total_lessons: 16,
    subject_config: { l1: "French", l2: "English", language_pair: "fr-en" },
    lessons: [
      { id: "l5", date: "2026-03-14", summary: "Academic writing, thesis statements, hedging" },
      { id: "l6", date: "2026-03-10", summary: "Debate skills, opinions, counterarguments" },
    ],
  },
  {
    id: "s4",
    name: "Klaus Weber",
    level: "B1",
    goal: "Conversational English with confidence and humor",
    total_lessons: 10,
    subject_config: { l1: "German", l2: "English", language_pair: "de-en" },
    lessons: [
      { id: "l7", date: "2026-03-15", summary: "Cooking vocabulary, recipes, food culture opinions" },
      { id: "l8", date: "2026-03-13", summary: "Sports, gym stories, exercise vocabulary" },
    ],
  },
];

const MOCK_CONVO: Message[] = [
  {
    id: "fc-u1",
    role: "user",
    content: "Show today's overview",
    timestamp: new Date(),
  },
  {
    id: "fc-a1",
    role: "assistant",
    content:
      "You have 5 lessons today. Overview:\n\n" +
      "- **Maria Garcia** (B1, 10:00) — practice 75%, past tense persistent ⚠\n" +
      "- **Alex Chen** (A2, 11:00) — practice 90%, improving across the board ✓\n" +
      "- **Yuki Tanaka** (B2, 13:00) — practice not started ✗\n" +
      "- **Pierre Dubois** (B1, 14:00) — practice 60%, articles still weak ⚠\n" +
      "- **Ana Silva** (A2, 15:00) — first lesson, no history\n\n" +
      "Yuki hasn't started practice. Maria and Pierre need targeted focus.",
    timestamp: new Date(),
    processSteps: [
      {
        type: "thinking",
        content:
          "Teacher wants today's overview. I'll query the daily overview tool to get all students scheduled for today with their practice status.",
      },
      {
        type: "tool_call",
        toolName: "query_daily_overview",
        toolId: "fc-t1",
        toolInput: { teacher_id: "teacher_1", date: "2026-03-14" },
        status: "completed",
        result: {
          message: "Found 5 students for today",
          data: {},
          executionTimeMs: 23,
        },
      },
    ],
  },
  {
    id: "fc-u2",
    role: "user",
    content: "Show her errors",
    timestamp: new Date(),
  },
  {
    id: "fc-a2",
    role: "assistant",
    content:
      "4 grammar errors, most significant:\n\n" +
      "**1.** At 12:45:\n" +
      '> *"I go to the store yesterday"* → **"I went to the store yesterday"**\n' +
      "> Past simple required for completed past action\n\n" +
      "**2.** At 18:20:\n" +
      '> *"She have two brothers"* → **"She has two brothers"**\n' +
      "> Subject-verb agreement: third person singular\n\n" +
      "The past tense errors are the priority — they've been consistent across lessons and her practice scores confirm she needs more work on sentence-level application.",
    timestamp: new Date(),
    processSteps: [
      {
        type: "tool_call",
        toolName: "query_lesson_errors",
        toolId: "fc-t2",
        toolInput: { student_id: "maria_42" },
        status: "completed",
        result: {
          message: "Found 9 errors",
          data: ERROR_WIDGET_DATA,
          executionTimeMs: 18,
        },
      },
    ],
    toolResults: [
      {
        toolName: "query_lesson_errors",
        toolId: "fc-t2",
        message: "Found 9 errors for Maria",
        executionTimeMs: 18,
        data: ERROR_WIDGET_DATA,
      },
    ],
  },
];

// ---------------------------------------------------------------------------
// Layout helpers
// ---------------------------------------------------------------------------

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-4">
      <h2 className="border-b border-[var(--color-border)] pb-2 text-title font-semibold text-[color:var(--color-text-primary)]">
        {title}
      </h2>
      {children}
    </section>
  );
}

function Sub({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-[color:var(--color-text-secondary)]">
        {title}
      </h3>
      {children}
    </div>
  );
}

function DateSeparator({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center py-2">
      <span className="rounded-[var(--radius-full)] border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-0.5 text-xs text-[color:var(--color-text-muted)]">
        {label}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Showcase
// ---------------------------------------------------------------------------

export default function Showcase() {
  const [mode, setMode] = useState<PreplyMode>(MODES.DAILY_BRIEFING);
  const [ctxStudentId, setCtxStudentId] = useState<string | null>(null);
  const [ctxLessonId, setCtxLessonId] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-[var(--color-surface-secondary)]">
      {/* Header */}
      <header className="sticky top-0 z-20 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center gap-3">
          <a
            href="/"
            className="flex items-center gap-1.5 text-sm text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-primary)]"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to app
          </a>
          <div className="h-4 w-px bg-[var(--color-border)]" />
          <h1 className="text-lg font-semibold text-[color:var(--color-text-primary)]">
            Design system
          </h1>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-12 px-6 py-8">
        {/* ============================================================= */}
        {/* 1. Primitives                                                  */}
        {/* ============================================================= */}
        <Section title="Primitives">
          <div className="grid grid-cols-2 gap-8">
            <Sub title="Colors">
              <div className="grid grid-cols-4 gap-2">
                {[
                  { name: "Primary", var: "--color-primary" },
                  { name: "Primary hover", var: "--color-primary-hover" },
                  { name: "Primary light", var: "--color-primary-light" },
                  { name: "Accent", var: "--color-accent" },
                  { name: "Accent hover", var: "--color-accent-hover" },
                  { name: "Accent light", var: "--color-accent-light" },
                  { name: "Success", var: "--color-success" },
                  { name: "Success light", var: "--color-success-light" },
                  { name: "Warning", var: "--color-warning" },
                  { name: "Warning light", var: "--color-warning-light" },
                  { name: "Danger", var: "--color-danger" },
                  { name: "Danger light", var: "--color-danger-light" },
                  { name: "Code bg", var: "--color-code-bg" },
                  { name: "Code text", var: "--color-code-text" },
                  { name: "Surface", var: "--color-surface" },
                  { name: "Surface 2", var: "--color-surface-secondary" },
                  { name: "Message bg", var: "--color-message-other" },
                  { name: "Border", var: "--color-border" },
                  { name: "Text primary", var: "--color-text-primary" },
                  { name: "Text secondary", var: "--color-text-secondary" },
                  { name: "Text muted", var: "--color-text-muted" },
                ].map(({ name, var: v }) => (
                  <div key={v} className="text-center">
                    <div
                      className="mx-auto h-10 w-10 rounded-[var(--radius-md)] border-2 border-[var(--color-border)]"
                      style={{ backgroundColor: `var(${v})` }}
                    />
                    <p className="mt-1 text-micro text-[color:var(--color-text-muted)]">
                      {name}
                    </p>
                  </div>
                ))}
              </div>
            </Sub>

            <div className="space-y-6">
              <Sub title="Badges">
                <div className="flex flex-wrap gap-2">
                  <Badge>default</Badge>
                  <Badge variant="success">success</Badge>
                  <Badge variant="warning">warning</Badge>
                  <Badge variant="error">error</Badge>
                  <Badge variant="highlight">Encouraging and engaging</Badge>
                </div>
              </Sub>
              <Sub title="Buttons">
                <div className="flex flex-wrap items-center gap-2">
                  <Button variant="primary" size="sm">
                    Primary sm
                  </Button>
                  <Button variant="primary">Primary md</Button>
                  <Button variant="secondary">Secondary</Button>
                  <Button variant="tertiary">Tertiary</Button>
                  <Button variant="ghost">Ghost</Button>
                  <Button disabled>Disabled</Button>
                </div>
              </Sub>
              <Sub title="Spinners">
                <div className="flex items-center gap-4">
                  <Spinner size="small" />
                  <Spinner size="medium" />
                  <Spinner size="large" />
                </div>
              </Sub>
            </div>
          </div>

          <Sub title="Cards">
            <div className="grid grid-cols-3 gap-3">
              <Card padding="sm">
                <p className="text-sm text-[color:var(--color-text-secondary)]">
                  Small padding
                </p>
              </Card>
              <Card padding="md">
                <p className="text-sm text-[color:var(--color-text-secondary)]">
                  Medium padding
                </p>
              </Card>
              <Card padding="lg">
                <p className="text-sm text-[color:var(--color-text-secondary)]">
                  Large padding
                </p>
              </Card>
            </div>
            <div className="mt-3 grid grid-cols-3 gap-3">
              <Card interactive>
                <p className="text-sm text-[color:var(--color-text-secondary)]">
                  Interactive (hover me)
                </p>
              </Card>
            </div>
          </Sub>

          <Sub title="Animations">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-[var(--radius-lg)] border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4 animate-[fadeIn_0.5s_ease-out]">
                <p className="text-sm text-[color:var(--color-text-secondary)]">fadeIn — messages, dropdowns</p>
              </div>
              <div className="rounded-[var(--radius-lg)] border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4 animate-[expandDown_0.5s_ease-out]">
                <p className="text-sm text-[color:var(--color-text-secondary)]">expandDown — collapsible sections</p>
              </div>
            </div>
          </Sub>
        </Section>

        {/* ============================================================= */}
        {/* 2. Mode selector                                               */}
        {/* ============================================================= */}
        <Section title="Mode selector">
          <div className="flex items-end gap-6">
            <div>
              <p className="mb-2 text-xs text-[color:var(--color-text-muted)]">
                Interactive — click to switch
              </p>
              <ModeSelector value={mode} onChange={setMode} />
            </div>
            <p className="text-sm text-[color:var(--color-text-secondary)]">
              Current:{" "}
              <span className="font-medium text-[color:var(--color-text-primary)]">
                {mode}
              </span>
            </p>
          </div>
        </Section>

        {/* ============================================================= */}
        {/* 3. Context header                                              */}
        {/* ============================================================= */}
        <Section title="Context header">
          <div className="space-y-6">
            <Sub title="Student practice (loaded, full context)">
              <div className="overflow-hidden rounded-[var(--radius-lg)] border-2 border-[var(--color-border)]">
                <ContextHeader
                  mode={MODES.STUDENT_PRACTICE}
                  isNewConversation={false}
                  context={{
                    studentName: "Maria Garcia",
                    studentLevel: "B1",
                    subjectConfig: { l1: "Spanish", l2: "English" },
                    totalLessons: 12,
                    studentGoal: "Conversational fluency for travel",
                    lessonDate: "2026-03-14",
                    lessonDuration: 50,
                    lessonSummary: "Travel planning to London, booking, transport",
                  }}
                />
              </div>
            </Sub>

            <Sub title="Student practice (loaded, minimal context)">
              <div className="overflow-hidden rounded-[var(--radius-lg)] border-2 border-[var(--color-border)]">
                <ContextHeader
                  mode={MODES.STUDENT_PRACTICE}
                  isNewConversation={false}
                  context={{
                    studentName: "Alex Chen",
                    studentLevel: "A2",
                    subjectConfig: { l1: "Mandarin Chinese", l2: "English" },
                  }}
                />
              </div>
            </Sub>

            <Sub title="Daily briefing (loaded)">
              <div className="overflow-hidden rounded-[var(--radius-lg)] border-2 border-[var(--color-border)]">
                <ContextHeader
                  mode={MODES.DAILY_BRIEFING}
                  isNewConversation={false}
                  context={{
                    teacherName: "Sarah Johnson",
                    studentCount: 5,
                  }}
                />
              </div>
            </Sub>

            <Sub title="Daily briefing (new conversation)">
              <div className="rounded-[var(--radius-lg)] border-2 border-[var(--color-border)]">
                <ContextHeader
                  mode={MODES.DAILY_BRIEFING}
                  isNewConversation={true}
                  context={{}}
                  students={MOCK_STUDENTS}
                />
              </div>
            </Sub>

            <Sub title="Student practice (new — interactive, select a student)">
              <div className="rounded-[var(--radius-lg)] border-2 border-[var(--color-border)]">
                <ContextHeader
                  mode={MODES.STUDENT_PRACTICE}
                  isNewConversation={true}
                  context={
                    ctxStudentId
                      ? {
                          studentName: MOCK_STUDENTS.find((s) => s.id === ctxStudentId)?.name,
                          studentLevel: MOCK_STUDENTS.find((s) => s.id === ctxStudentId)?.level,
                          studentGoal: MOCK_STUDENTS.find((s) => s.id === ctxStudentId)?.goal,
                          totalLessons: MOCK_STUDENTS.find((s) => s.id === ctxStudentId)?.total_lessons,
                          subjectConfig: MOCK_STUDENTS.find((s) => s.id === ctxStudentId)?.subject_config,
                          lessonDate: MOCK_STUDENTS.find((s) => s.id === ctxStudentId)?.lessons.find((l) => l.id === ctxLessonId)?.date,
                          lessonSummary: MOCK_STUDENTS.find((s) => s.id === ctxStudentId)?.lessons.find((l) => l.id === ctxLessonId)?.summary,
                        }
                      : {}
                  }
                  students={MOCK_STUDENTS}
                  selectedStudentId={ctxStudentId}
                  selectedLessonId={ctxLessonId}
                  onStudentChange={setCtxStudentId}
                  onLessonChange={setCtxLessonId}
                />
              </div>
              <p className="mt-1 text-xs text-[color:var(--color-text-muted)]">
                Selected: student={ctxStudentId ?? "none"}, lesson={ctxLessonId ?? "none"}
              </p>
            </Sub>
          </div>
        </Section>

        {/* ============================================================= */}
        {/* 4. Chat input                                                  */}
        {/* ============================================================= */}
        <Section title="Chat input">
          <div className="grid grid-cols-2 gap-4">
            <Sub title="Idle">
              <div className="rounded-[var(--radius-xl)] border-2 border-[var(--color-border)] bg-[var(--color-surface)]">
                <ChatInput
                  onSend={() => {}}
                  mode={mode}
                  onModeChange={setMode}
                />
              </div>
            </Sub>
            <Sub title="Processing (disabled)">
              <div className="rounded-[var(--radius-xl)] border-2 border-[var(--color-border)] bg-[var(--color-surface)]">
                <ChatInput
                  onSend={() => {}}
                  onCancel={() => {}}
                  disabled
                  mode={mode}
                  onModeChange={setMode}
                  queueLength={2}
                />
              </div>
            </Sub>
          </div>
        </Section>

        {/* ============================================================= */}
        {/* 4. Messages                                                    */}
        {/* ============================================================= */}
        <Section title="Messages">
          <div className="space-y-5 rounded-[var(--radius-xl)] bg-[var(--color-surface)] p-6">
            {/* Date separator */}
            <DateSeparator label="Wed, 11 Mar" />

            {/* User message */}
            <ChatMessage
              message={{
                id: "demo-u1",
                role: "user",
                content: "How did Maria do?",
                timestamp: new Date(),
              }}
            />

            {/* Assistant with thinking + tool + answer */}
            <ChatMessage
              message={{
                id: "demo-a1",
                role: "assistant",
                content:
                  "Maria Garcia — last lesson March 11:\n\n" +
                  "**Errors:** 9 found (4 grammar, 3 vocabulary, 2 pronunciation)\n\n" +
                  "**Key pattern:** past tense (3 occurrences, moderate severity)\n\n" +
                  "The most significant error at 12:45:\n\n" +
                  "> *\"I go to the store yesterday\"*\n>\n> → should be **\"I went to the store yesterday\"**\n\n" +
                  "**Practice:** 75% — 6/8 correct\n\n" +
                  "- Strong: conjugation (fill-in-gap 3/3)\n" +
                  "- Weak: word order with time expressions (sorter 0/2)\n\n" +
                  "**Suggested focus:** past tense in narrative contexts.",
                timestamp: new Date(),
                processSteps: [
                  {
                    type: "thinking",
                    content:
                      "Pulling Maria's student report: errors, practice results, suggested focus areas.",
                  },
                  {
                    type: "tool_call",
                    toolName: "query_student_report",
                    toolId: "demo-t1",
                    toolInput: { student_id: "maria_42" },
                    status: "completed",
                    result: {
                      message: "Found report for Maria Garcia",
                      data: {},
                      executionTimeMs: 12,
                    },
                  },
                ],
              }}
            />

            {/* Streaming message */}
            <ChatMessage
              message={{
                id: "demo-stream",
                role: "assistant",
                content:
                  "Maria's practice results show she scored 75% overall. Her strongest area was verb conjugation where she got 3/3 on fill-in-the-gap exercises. The area needing work is",
                timestamp: new Date(),
              }}
              isStreaming
            />
          </div>
        </Section>

        {/* ============================================================= */}
        {/* 5. Conversation states                                         */}
        {/* ============================================================= */}
        <Section title="Conversation states">
          <div className="grid grid-cols-2 gap-4">
            {/* Empty state */}
            <Sub title="Empty (suggestion chips)">
              <div className="flex flex-col items-center rounded-[var(--radius-xl)] bg-[var(--color-surface)] p-8">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full [background:var(--color-highlight-gradient)]">
                  <PreplyLogo className="h-5 w-5" />
                </div>
                <p className="mb-4 text-center text-[color:var(--color-text-secondary)]">
                  Good morning! Ready to prep for today&apos;s lessons.
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                  {[
                    "Show today's overview",
                    "How did Maria do?",
                    "Who needs attention?",
                  ].map((chip) => (
                    <button
                      key={chip}
                      className="cursor-pointer rounded-[var(--radius-full)] border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-sm text-[color:var(--color-text-secondary)] transition-preply hover:border-[var(--color-text-primary)] hover:text-[color:var(--color-text-primary)]"
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              </div>
            </Sub>

            {/* Connecting */}
            <Sub title="Connecting">
              <div className="flex gap-3 rounded-[var(--radius-xl)] bg-[var(--color-surface)] p-6">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full [background:var(--color-highlight-gradient)] text-[color:var(--color-text-secondary)]">
                  <PreplyLogo />
                </div>
                <div>
                  <div className="mb-1 text-sm font-semibold text-[color:var(--color-text-primary)]">
                    Preply AI
                  </div>
                  <div className="rounded-[var(--radius-xl)] bg-[var(--color-message-other)] px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Spinner size="small" />
                      <span className="text-sm text-[color:var(--color-text-muted)]">
                        Connecting...
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </Sub>

            {/* Thinking */}
            <Sub title="Thinking (process timeline)">
              <div className="flex gap-3 rounded-[var(--radius-xl)] bg-[var(--color-surface)] p-6">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full [background:var(--color-highlight-gradient)] text-[color:var(--color-text-secondary)]">
                  <PreplyLogo />
                </div>
                <div>
                  <div className="mb-1 text-sm font-semibold text-[color:var(--color-text-primary)]">
                    Preply AI
                  </div>
                  <div className="rounded-[var(--radius-xl)] bg-[var(--color-message-other)] px-4 py-3">
                    <ProcessTimeline steps={MOCK_THINKING} isStreaming />
                  </div>
                </div>
              </div>
            </Sub>

            {/* Error */}
            <Sub title="Error">
              <div className="rounded-[var(--radius-xl)] border-2 border-[var(--color-danger)] bg-[var(--color-danger-light)] p-4">
                <div className="flex items-start gap-2">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[color:var(--color-danger)]" />
                  <p className="text-sm text-[color:var(--color-danger)]">
                    Connection failed: server returned 503
                  </p>
                </div>
                <Button variant="tertiary" size="sm" className="mt-2">
                  Retry
                </Button>
              </div>
            </Sub>

            {/* Approval */}
            <Sub title="Approval needed">
              <div className="rounded-[var(--radius-xl)] border-2 border-[var(--color-warning)] bg-[var(--color-warning-light)] p-4">
                <p className="text-sm font-medium text-[color:var(--color-text-primary)]">
                  Approval needed: send_practice_session
                </p>
                <p className="mt-1 text-xs text-[color:var(--color-text-secondary)]">
                  Send a Classtime practice session to Maria Garcia (8 exercises
                  on past tense)
                </p>
                <div className="mt-3 flex gap-2">
                  <Button variant="primary" size="sm">Approve</Button>
                  <Button variant="tertiary" size="sm">Deny</Button>
                </div>
              </div>
            </Sub>
          </div>
        </Section>

        {/* ============================================================= */}
        {/* 6. Widgets                                                     */}
        {/* ============================================================= */}
        <Section title="Widgets">
          <div className="grid grid-cols-2 gap-6">
            <Sub title="ErrorAnalysisWidget">
              <WidgetRouter data={ERROR_WIDGET_DATA} />
            </Sub>
            <Sub title="ThemeMapWidget">
              <WidgetRouter data={THEME_WIDGET_DATA} />
            </Sub>
            <Sub title="PracticeCardWidget">
              <WidgetRouter data={PRACTICE_WIDGET_DATA} />
            </Sub>
            <Sub title="DefaultWidget (unknown type)">
              <WidgetRouter
                data={{
                  widget_type: "unknown_future_widget",
                  score: 0.85,
                  label: "Confidence",
                }}
              />
            </Sub>
          </div>
        </Section>

        {/* ============================================================= */}
        {/* 7. Full conversation                                           */}
        {/* ============================================================= */}
        <Section title="Full conversation (teacher daily briefing)">
          <div className="space-y-5 rounded-[var(--radius-xl)] bg-[var(--color-surface)] p-6">
            <DateSeparator label="Today" />
            {MOCK_CONVO.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
          </div>
        </Section>
      </main>
    </div>
  );
}
