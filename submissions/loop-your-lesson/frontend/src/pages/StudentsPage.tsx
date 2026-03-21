import { Link } from "react-router-dom";
import { Users, GraduationCap, BookOpen } from "lucide-react";
import { useContextOptions } from "@/api/hooks/useContextOptions";
import Spinner from "@/components/ui/Spinner";
import Badge from "@/components/ui/Badge";


export default function StudentsPage() {
  const { data: contextOptions, isLoading } = useContextOptions();
  const students = contextOptions?.students ?? [];

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
          <Users className="h-5 w-5 text-[color:var(--color-text-muted)]" />
          <h1 className="text-lg font-semibold text-[color:var(--color-text-primary)]">
            Students
          </h1>
        </div>
        <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
          {students.length} active student{students.length !== 1 ? "s" : ""}
        </p>
      </div>

      <div className="p-6">
        {students.length === 0 ? (
          <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-12 text-center">
            <Users className="mx-auto h-8 w-8 text-[color:var(--color-text-muted)]" />
            <p className="mt-3 text-sm text-[color:var(--color-text-muted)]">
              No students found
            </p>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {students.map((student) => (
              <Link
                key={student.id}
                to={`/students/${student.id}`}
                className="group rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] px-5 py-4 transition-colors hover:border-[var(--color-text-muted)] hover:bg-[var(--color-surface-secondary)]"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--color-surface-secondary)]">
                      <GraduationCap className="h-4.5 w-4.5 text-[color:var(--color-text-muted)]" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[color:var(--color-text-primary)]">
                        {student.name}
                      </p>
                      <div className="mt-0.5 flex items-center gap-1.5 text-xs text-[color:var(--color-text-muted)]">
                        <BookOpen className="h-3 w-3" />
                        {student.lessons.length} lesson
                        {student.lessons.length !== 1 ? "s" : ""}
                      </div>
                    </div>
                  </div>
                  {student.level && (
                    <Badge>{student.level}</Badge>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
