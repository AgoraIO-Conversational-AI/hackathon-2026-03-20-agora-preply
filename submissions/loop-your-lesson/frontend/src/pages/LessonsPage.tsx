import { Link } from "react-router-dom";
import { BookOpen, Calendar, User } from "lucide-react";
import { useContextOptions } from "@/api/hooks/useContextOptions";
import Spinner from "@/components/ui/Spinner";

interface LessonEntry {
  id: string;
  date: string;
  summary: string;
  studentName: string;
  studentId: string;
}

export default function LessonsPage() {
  const { data: contextOptions, isLoading } = useContextOptions();

  // Flatten lessons from all students
  const lessons: LessonEntry[] = [];
  if (contextOptions?.students) {
    for (const student of contextOptions.students) {
      for (const lesson of student.lessons) {
        lessons.push({
          id: lesson.id,
          date: lesson.date,
          summary: lesson.summary,
          studentName: student.name,
          studentId: student.id,
        });
      }
    }
  }
  // Sort by date descending
  lessons.sort((a, b) => b.date.localeCompare(a.date));

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-y-auto">
      <div className="border-b border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-5">
        <div className="flex items-center gap-2.5">
          <BookOpen className="h-5 w-5 text-[color:var(--color-text-muted)]" />
          <h1 className="text-lg font-semibold text-[color:var(--color-text-primary)]">
            Lessons
          </h1>
        </div>
        <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
          {lessons.length} lesson{lessons.length !== 1 ? "s" : ""} across all
          students
        </p>
      </div>

      <div className="p-6">
        {lessons.length === 0 ? (
          <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-12 text-center">
            <BookOpen className="mx-auto h-8 w-8 text-[color:var(--color-text-muted)]" />
            <p className="mt-3 text-sm text-[color:var(--color-text-muted)]">
              No lessons found
            </p>
          </div>
        ) : (
          <div className="grid gap-3">
            {lessons.map((lesson) => (
              <Link
                key={lesson.id}
                to={`/lessons/${lesson.id}`}
                className="group rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] px-5 py-4 transition-colors hover:border-[var(--color-text-muted)] hover:bg-[var(--color-surface-secondary)]"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1.5 text-sm font-medium text-[color:var(--color-text-primary)]">
                        <Calendar className="h-3.5 w-3.5 text-[color:var(--color-text-muted)]" />
                        {lesson.date}
                      </span>
                      <span className="flex items-center gap-1.5 text-sm text-[color:var(--color-text-secondary)]">
                        <User className="h-3.5 w-3.5 text-[color:var(--color-text-muted)]" />
                        {lesson.studentName}
                      </span>
                    </div>
                    {lesson.summary && (
                      <p className="mt-1.5 text-sm text-[color:var(--color-text-muted)]">
                        {lesson.summary}
                      </p>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
