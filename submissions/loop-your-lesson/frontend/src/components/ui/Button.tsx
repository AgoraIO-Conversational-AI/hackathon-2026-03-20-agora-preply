import { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "tertiary" | "ghost";
  size?: "sm" | "md" | "lg";
}

export default function Button({
  variant = "primary",
  size = "md",
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center font-semibold border-2 transition-preply focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
        "rounded-[var(--radius-md)]",
        // Primary — pink bg, dark border, dark text
        variant === "primary" &&
          "border-[var(--color-text-primary)] bg-[var(--color-primary)] text-[color:var(--color-text-primary)] hover:bg-[var(--color-primary-hover)] active:bg-[var(--color-text-primary)] active:text-white focus-visible:ring-[var(--color-primary)] disabled:border-[var(--color-border)] disabled:bg-[var(--color-border)] disabled:text-[color:var(--color-text-muted)]",
        // Secondary — transparent bg, dark border always
        variant === "secondary" &&
          "border-[var(--color-text-primary)] bg-transparent text-[color:var(--color-text-primary)] hover:bg-[rgba(71,71,133,0.06)] active:bg-[rgba(92,92,138,0.12)] focus-visible:ring-[var(--color-text-primary)] disabled:border-[var(--color-border)] disabled:bg-[var(--color-border)] disabled:text-[color:var(--color-text-muted)]",
        // Tertiary — transparent bg, subtle border, gentle hover
        variant === "tertiary" &&
          "border-[rgba(20,20,82,0.15)] bg-transparent text-[color:var(--color-text-primary)] hover:bg-[rgba(71,71,133,0.06)] active:bg-[rgba(92,92,138,0.12)] focus-visible:ring-[var(--color-text-primary)] disabled:border-[var(--color-border)] disabled:bg-[var(--color-border)] disabled:text-[color:var(--color-text-muted)]",
        // Ghost — no border, no bg
        variant === "ghost" &&
          "border-transparent text-[color:var(--color-text-secondary)] hover:bg-[var(--color-surface-secondary)] focus-visible:ring-[var(--color-border)]",
        // Sizes — min-heights from Preply DS (40/48/56px)
        size === "sm" && "min-h-[40px] px-4 text-sm tracking-[0.0125em]",
        size === "md" && "min-h-[48px] px-6 text-[15px] tracking-[0.005em]",
        size === "lg" && "min-h-[56px] px-8 text-base",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
