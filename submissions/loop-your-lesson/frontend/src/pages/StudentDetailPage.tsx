import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  GraduationCap,
  Calendar,
} from "lucide-react";
import { useContextOptions } from "@/api/hooks/useContextOptions";
import Badge from "@/components/ui/Badge";
import Spinner from "@/components/ui/Spinner";

export default function StudentDetailPage() {
  const { studentId } = useParams();
  const { data: contextOptions, isLoading } = useContextOptions();

  const student = contextOptions?.students?.find((s) => s.id === studentId);

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  if (!student) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3">
        <p className="text-sm text-[color:var(--color-text-muted)]">
          Student not found
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

  return (
    <div className="flex flex-1 flex-col overflow-y-auto">
      {/* Header */}
      <div className="border-b border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-5">
        <Link
          to="/students"
          className="mb-3 inline-flex items-center gap-1.5 text-sm text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-primary)]"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to students
        </Link>

        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--color-surface-secondary)]">
              <GraduationCap className="h-5 w-5 text-[color:var(--color-text-muted)]" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-[color:var(--color-text-primary)]">
                {student.name}
              </h1>
              <div className="mt-0.5 flex items-center gap-2">
                {student.level && (
                  <Badge>{student.level}</Badge>
                )}
                <span className="text-sm text-[color:var(--color-text-muted)]">
                  {student.lessons.length} lesson
                  {student.lessons.length !== 1 ? "s" : ""}
                </span>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* Lessons list */}
      <div className="p-6">
        <h2 className="mb-3 text-sm font-medium text-[color:var(--color-text-primary)]">
          Recent lessons
        </h2>

        {student.lessons.length === 0 ? (
          <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-12 text-center">
            <p className="text-sm text-[color:var(--color-text-muted)]">
              No lessons recorded yet
            </p>
          </div>
        ) : (
          <div className="grid gap-3">
            {student.lessons.map((lesson) => (
              <Link
                key={lesson.id}
                to={`/lessons/${lesson.id}`}
                className="group rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] px-5 py-4 transition-colors hover:border-[var(--color-text-muted)] hover:bg-[var(--color-surface-secondary)]"
              >
                <div className="flex items-center gap-2">
                  <Calendar className="h-3.5 w-3.5 text-[color:var(--color-text-muted)]" />
                  <span className="text-sm font-medium text-[color:var(--color-text-primary)]">
                    {lesson.date}
                  </span>
                </div>
                {lesson.summary && (
                  <p className="mt-1.5 text-sm text-[color:var(--color-text-muted)]">
                    {lesson.summary}
                  </p>
                )}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
