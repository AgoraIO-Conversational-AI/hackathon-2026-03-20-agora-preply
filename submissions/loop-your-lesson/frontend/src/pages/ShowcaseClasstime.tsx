import { useState } from "react";
import {
  ArrowLeft,
  Play,
  CheckCircle,
  GraduationCap,
} from "lucide-react";
import Button from "@/components/ui/Button";
import Pill from "@/components/ui/Pill";
import WidgetCard from "@/components/ui/WidgetCard";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ToolCallBlock } from "@/components/chat/ProcessTimeline";
import { PracticeModal } from "@/components/practice/PracticeModal";
import type { Message } from "@/lib/types";

// ---------------------------------------------------------------------------
// Session data
// ---------------------------------------------------------------------------

const PRACTICE_SESSIONS = [
  {
    code: "8KF8DTF7",
    studentName: "Klaus Weber",
    level: "B1",
    questionCount: 10,
    focusTopic: "German L1 transfer errors",
    goal: "Fix article overuse, false friends, and tense confusion from German",
    themes: ["Cooking vocabulary", "Food culture opinions"],
    errors: [
      { original: "I am very enjoying to cook", corrected: "I really enjoy cooking" },
      { original: "You need the pork", corrected: "You need pork" },
      { original: "I become very angry", corrected: "I get very angry" },
    ],
  },
  {
    code: "TQS977AR",
    studentName: "Maria Garcia",
    level: "B1",
    questionCount: 7,
    focusTopic: "Articles, pronouns & gerunds",
    goal: "Build accuracy with articles (a/an/the), subject pronouns, and gerund patterns",
    themes: ["Travel planning", "Booking and transport"],
    errors: [
      { original: "make a reservation in the hotel", corrected: "book a hotel" },
      { original: "a umbrella", corrected: "an umbrella" },
      { original: "I think is called the Tube", corrected: "I think it is called the Tube" },
    ],
  },
];

// ---------------------------------------------------------------------------
// Mock conversation for context
// ---------------------------------------------------------------------------

const INTRO_MESSAGE: Message = {
  id: "m0",
  role: "assistant",
  content:
    "Great lesson on cooking today! We've analyzed your conversation and noticed a few patterns worth practicing before your next class.\n\n" +
    "**3 key areas to focus on:**\n\n" +
    "- **Articles** - you tend to add *the* before general nouns (*\"the pork\"* instead of just *\"pork\"*). This is a common German transfer - in English, we skip the article when talking about things in general.\n" +
    "- **False friends** - *\"become\"* in English doesn't mean *\"bekommen\"*. When you want to say you get angry, use *\"get\"* not *\"become\"*.\n" +
    "- **Verb patterns** - after *enjoy*, English uses the -ing form: *\"enjoy cooking\"*, not *\"enjoy to cook\"*.\n\n" +
    "We've put together a short practice session targeting exactly these patterns. Give it a try when you have 5-10 minutes - it'll make a real difference in your next lesson.",
  timestamp: new Date(),
};

const TOOL_MESSAGE: Message = {
  id: "m1",
  role: "assistant",
  content: "",
  timestamp: new Date(),
  processSteps: [
    {
      type: "tool_call" as const,
      toolName: "get_practice_session",
      toolId: "tc-2",
      toolInput: { student_id: "klaus_004", focus: "top_errors", question_count: 10 },
      status: "completed" as const,
      result: {
        message: "Practice session ready.",
        data: {},
        executionTimeMs: 340,
      },
    },
  ],
};

// ---------------------------------------------------------------------------
// Practice card (blended Preply + Classtime preview)
// ---------------------------------------------------------------------------

function PracticePreviewCard({
  session,
  onStart,
}: {
  session: (typeof PRACTICE_SESSIONS)[0];
  onStart: () => void;
}) {
  return (
    <WidgetCard>
      {/* Header */}
      <div className="px-4 py-3">
        <div className="flex items-start justify-between">
          <div>
            <h4 className="text-sm font-semibold text-[color:var(--color-text-primary)]">
              Practice: {session.focusTopic}
            </h4>
            <p className="mt-0.5 text-xs text-[color:var(--color-text-secondary)]">
              {session.goal}
            </p>
          </div>
          <Pill>{session.questionCount} questions</Pill>
        </div>

        {/* Themes */}
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {session.themes.map((theme) => (
            <Pill key={theme}>{theme}</Pill>
          ))}
        </div>
      </div>

      {/* Errors to practice */}
      <div className="border-t border-[var(--color-border)] px-4 py-2.5">
        <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-text-muted)]">
          Errors to practice
        </p>
        {session.errors.map((err, i) => (
          <div key={i} className="py-0.5 text-xs">
            <span className="text-[color:var(--color-danger)] line-through">
              {err.original}
            </span>
            <span className="mx-1.5 text-[color:var(--color-text-muted)]">&rarr;</span>
            <span className="font-medium text-[color:var(--color-success)]">
              {err.corrected}
            </span>
          </div>
        ))}
      </div>

      {/* Action */}
      <div className="flex gap-2 border-t border-[var(--color-border)] px-4 py-3">
        <Button variant="secondary" size="sm" className="gap-1.5" onClick={onStart}>
          <Play className="h-4 w-4" fill="currentColor" />
          Start practice
        </Button>
      </div>
    </WidgetCard>
  );
}

// ---------------------------------------------------------------------------
// Completion card (shown after closing practice)
// ---------------------------------------------------------------------------

function PracticeCompletedCard({
  session,
}: {
  session: (typeof PRACTICE_SESSIONS)[0];
}) {
  return (
    <WidgetCard>
      <div className="px-4 py-3">
        <div className="flex items-start gap-3">
          <CheckCircle className="mt-0.5 h-5 w-5 shrink-0 text-[color:var(--color-success)]" />
          <div>
            <h4 className="text-sm font-semibold text-[color:var(--color-text-primary)]">
              Practice completed: {session.focusTopic}
            </h4>
            <p className="mt-1 text-xs text-[color:var(--color-text-secondary)]">
              {session.questionCount} questions · {session.errors.length} error patterns practiced
            </p>
          </div>
        </div>
      </div>

      {/* Error summary */}
      <div className="border-t border-[var(--color-border)] px-4 py-2.5">
        <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-text-muted)]">
          Patterns practiced
        </p>
        {session.errors.map((err, i) => (
          <div key={i} className="flex items-center gap-2 py-0.5 text-xs">
            <CheckCircle className="h-3 w-3 shrink-0 text-[color:var(--color-success)]" />
            <span className="text-[color:var(--color-text-secondary)]">
              <span className="line-through text-[color:var(--color-text-muted)]">{err.original}</span>
              <span className="mx-1.5">&rarr;</span>
              <span className="font-medium text-[color:var(--color-text-primary)]">{err.corrected}</span>
            </span>
          </div>
        ))}
      </div>

      {/* Next steps */}
      <div className="border-t border-[var(--color-border)] px-4 py-2.5">
        <p className="text-xs text-[color:var(--color-text-secondary)]">
          Your teacher will see the results before your next lesson.
          Focus areas will be adjusted based on your progress.
        </p>
      </div>
    </WidgetCard>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

type SessionState = "preview" | "practicing" | "completed";

export default function ShowcaseClasstime() {
  const [activeIdx, setActiveIdx] = useState(0);
  const [state, setState] = useState<SessionState>("preview");

  const session = PRACTICE_SESSIONS[activeIdx]!;

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
            Classtime practice flow
          </h1>
          <div className="ml-auto flex gap-1">
            {PRACTICE_SESSIONS.map((s, i) => (
              <button
                key={s.code}
                onClick={() => { setActiveIdx(i); setState("preview"); }}
                className={`flex items-center gap-1.5 rounded-[var(--radius-full)] border-2 px-3 py-1 text-xs transition-preply ${
                  activeIdx === i
                    ? "border-[var(--color-primary)] bg-[var(--color-primary-light)] text-[color:var(--color-primary)]"
                    : "border-[var(--color-border)] text-[color:var(--color-text-secondary)] hover:border-[var(--color-text-primary)]"
                }`}
              >
                <GraduationCap className="h-3 w-3" />
                {s.studentName}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Chat simulation */}
      <main className="mx-auto max-w-3xl space-y-5 px-4 py-8">
        {/* AI intro text */}
        <ChatMessage message={INTRO_MESSAGE} />

        {/* Tool calls + practice widget - continuation of same response, no extra avatar */}
        <div className="pl-11 space-y-2">
          {TOOL_MESSAGE.processSteps
            ?.filter((s): s is Extract<typeof s, { type: "tool_call" }> => s.type === "tool_call")
            .map((step) => (
              <ToolCallBlock key={step.toolId} step={step} />
            ))}

          {state === "preview" && (
            <PracticePreviewCard
              session={session}
              onStart={() => setState("practicing")}
            />
          )}

          {state === "completed" && (
            <PracticeCompletedCard session={session} />
          )}
        </div>

        {/* Follow-up message after completion */}
        {state === "completed" && (
          <ChatMessage
            message={{
              id: "m3",
              role: "assistant",
              content:
                "Nice work finishing the practice! A few things to keep in mind:\n\n" +
                "- **Articles**: remember, English drops *the* when talking about things in general (*\"pork\"* not *\"the pork\"*)\n" +
                "- **False friends**: *\"become\"* ≠ *\"bekommen\"* — use *\"get\"* for temporary states\n" +
                "- **Verb patterns**: after *enjoy*, always use the -ing form\n\n" +
                "Your results will be part of your next lesson prep. If any question felt confusing, just ask — I can break it down.",
              timestamp: new Date(),
            }}
          />
        )}

        {/* Empty bottom space */}
        <div className="h-8" />
      </main>

      {/* Practice modal */}
      {state === "practicing" && (
        <PracticeModal
          sessionCode={session.code}
          focusTopic={session.focusTopic}
          questionCount={session.questionCount}
          studentName={session.studentName}
          onClose={() => setState("completed")}
        />
      )}
    </div>
  );
}
