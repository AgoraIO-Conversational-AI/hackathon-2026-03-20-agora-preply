import { useState } from "react";
import { Play } from "lucide-react";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import Pill from "@/components/ui/Pill";
import WidgetCard from "@/components/ui/WidgetCard";
import { PracticeModal } from "@/components/practice/PracticeModal";
import type { PracticeCardData } from "@/lib/types";

function extractSessionCode(url: string): string {
  return url.split("/").pop() ?? "";
}

export function PracticeCardWidget({
  data,
}: {
  data: Record<string, unknown>;
}) {
  const widgetData = data as unknown as PracticeCardData;
  const [showModal, setShowModal] = useState(false);

  const sessionCode =
    widgetData.session_code ||
    (widgetData.session_url ? extractSessionCode(widgetData.session_url) : "");

  return (
    <>
      <WidgetCard>
        {/* Header */}
        <div className="px-4 py-3">
          <div className="flex items-start justify-between">
            <div>
              <h4 className="text-sm font-semibold text-[color:var(--color-text-primary)]">
                Practice: {widgetData.focus_topic}
              </h4>
              {widgetData.goal && (
                <p className="mt-0.5 text-xs text-[color:var(--color-text-secondary)]">
                  {widgetData.goal}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Pill>{widgetData.question_count} questions</Pill>
              {widgetData.session_url && (
                <Badge variant="success">Ready</Badge>
              )}
            </div>
          </div>

          {/* Themes */}
          {widgetData.themes && widgetData.themes.length > 0 && (
            <div className="mt-2.5 flex flex-wrap gap-1.5">
              {widgetData.themes.map((theme) => (
                <Pill key={theme}>{theme}</Pill>
              ))}
            </div>
          )}

          {/* Question types */}
          {Object.keys(widgetData.question_types ?? {}).length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {Object.entries(widgetData.question_types ?? {}).map(([type, count]) => (
                <Pill key={type}>
                  {count}&times; {type.toLowerCase().replace("_", " ")}
                </Pill>
              ))}
            </div>
          )}
        </div>

        {/* Source errors */}
        {widgetData.source_errors && widgetData.source_errors.length > 0 && (
          <div className="border-t border-[var(--color-border)] px-4 py-2.5">
            <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-text-muted)]">
              Errors to practice
            </p>
            {widgetData.source_errors.map((err, i) => (
              <div key={i} className="py-0.5 text-xs">
                <span className="text-[color:var(--color-danger)] line-through">
                  {err.original}
                </span>
                {err.corrected && (
                  <>
                    <span className="mx-1.5 text-[color:var(--color-text-muted)]">
                      &rarr;
                    </span>
                    <span className="font-medium text-[color:var(--color-success)]">
                      {err.corrected}
                    </span>
                  </>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Action */}
        <div className="flex gap-2 border-t border-[var(--color-border)] px-4 py-3">
          {sessionCode && (
            <Button
              variant="secondary"
              size="sm"
              className="gap-1.5"
              onClick={() => setShowModal(true)}
            >
              <Play className="h-4 w-4" fill="currentColor" />
              Start practice
            </Button>
          )}
        </div>
      </WidgetCard>

      {/* Practice modal with Classtime iframe + Agora avatar */}
      {showModal && sessionCode && (
        <PracticeModal
          sessionCode={sessionCode}
          focusTopic={widgetData.focus_topic}
          questionCount={widgetData.question_count}
          studentName={widgetData.student_name}
          studentId={widgetData.student_id}
          lessonId={widgetData.lesson_id}
          onClose={() => setShowModal(false)}
        />
      )}
    </>
  );
}
