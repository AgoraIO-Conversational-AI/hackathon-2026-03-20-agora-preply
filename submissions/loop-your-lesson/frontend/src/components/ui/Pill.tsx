import { cn } from "@/lib/utils";

interface PillProps {
  children: React.ReactNode;
  icon?: React.ReactNode;
  variant?: "default" | "outline";
  className?: string;
}

export default function Pill({
  children,
  icon,
  variant = "default",
  className,
}: PillProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-[var(--radius-full)] px-2 py-0.5 text-micro text-[color:var(--color-text-muted)]",
        variant === "default" && "bg-[var(--color-surface-secondary)]",
        variant === "outline" &&
          "border-2 border-[var(--color-border)] bg-[var(--color-surface)]",
        className,
      )}
    >
      {icon}
      {children}
    </span>
  );
}
