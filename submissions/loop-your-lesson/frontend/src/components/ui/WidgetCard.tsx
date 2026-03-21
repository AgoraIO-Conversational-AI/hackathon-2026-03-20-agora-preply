import { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type WidgetCardProps = HTMLAttributes<HTMLDivElement>;

export default function WidgetCard({
  className,
  children,
  ...props
}: WidgetCardProps) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-lg)] border-2 border-[var(--color-border)] bg-[var(--color-surface)]",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
