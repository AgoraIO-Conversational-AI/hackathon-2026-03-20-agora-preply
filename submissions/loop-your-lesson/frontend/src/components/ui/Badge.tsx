import { Sparkles } from "lucide-react";

interface BadgeProps {
  variant?: "default" | "success" | "warning" | "error" | "highlight";
  children: React.ReactNode;
}

const variants = {
  default: "bg-[var(--color-surface-secondary)] text-[color:var(--color-text-secondary)]",
  success: "bg-[var(--color-success-light)] text-[color:var(--color-success)]",
  warning: "bg-[var(--color-warning-light)] text-[color:var(--color-warning)]",
  error: "bg-[var(--color-danger-light)] text-[color:var(--color-danger)]",
  highlight: "text-[color:var(--color-text-primary)] [background:var(--color-highlight-gradient)]",
};

export default function Badge({ variant = "default", children }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-[var(--radius-md)] px-2.5 py-1 text-[length:var(--text-label)] leading-[var(--lh-label)] tracking-[var(--ls-label)] font-medium ${variants[variant]}`}
    >
      {variant === "highlight" && (
        <Sparkles className="h-3 w-3 text-[color:var(--color-primary)]" />
      )}
      {children}
    </span>
  );
}
