import { HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  padding?: "sm" | "md" | "lg";
  interactive?: boolean;
}

export default function Card({
  padding = "md",
  interactive = false,
  className = "",
  children,
  ...props
}: CardProps) {
  const paddings = {
    sm: "p-3",
    md: "p-4",
    lg: "p-6",
  };

  return (
    <div
      className={`bg-[var(--color-surface)] rounded-[var(--radius-md)] border-2 border-[var(--color-border)] shadow-sm ${interactive ? "transition-shadow hover:shadow-md" : ""} ${paddings[padding]} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
