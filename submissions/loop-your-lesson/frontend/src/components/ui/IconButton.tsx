import { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "danger" | "muted";
}

export default function IconButton({
  variant = "primary",
  className,
  children,
  ...props
}: IconButtonProps) {
  return (
    <button
      className={cn(
        "flex h-10 w-10 items-center justify-center rounded-[var(--radius-md)] border-2 transition-preply",
        variant === "primary" &&
          "border-[var(--color-text-primary)] bg-[var(--color-primary)] text-[color:var(--color-text-primary)] hover:bg-[var(--color-primary-hover)]",
        variant === "danger" &&
          "border-[var(--color-text-primary)] bg-[var(--color-danger)] text-[color:var(--color-text-primary)] hover:opacity-90",
        variant === "muted" &&
          "border-[var(--color-border)] bg-[var(--color-surface-secondary)] text-[color:var(--color-text-muted)]",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
