import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { Tooltip } from "./Tooltip";

interface CopyButtonProps {
  text: string;
  tooltip?: string;
}

/** Inline copy button — always visible, for action bars */
export function CopyButton({ text, tooltip = "Copy" }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <Tooltip content={copied ? "Copied" : tooltip}>
      <button
        type="button"
        onClick={handleCopy}
        className="rounded p-1 text-[color:var(--color-text-muted)] transition-colors hover:bg-[var(--color-surface-secondary)] hover:text-[color:var(--color-text-secondary)]"
      >
        {copied ? (
          <Check className="h-3.5 w-3.5 text-[color:var(--color-success)]" />
        ) : (
          <Copy className="h-3.5 w-3.5" />
        )}
      </button>
    </Tooltip>
  );
}

/** Overlay copy button — absolute positioned, shows on parent hover (parent needs group/pre) */
export function CopyButtonOverlay({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="absolute right-1.5 top-1.5 rounded p-1 text-[color:var(--color-text-muted)] opacity-0 transition-opacity hover:bg-[var(--color-border)] hover:text-[color:var(--color-text-primary)] group-hover/pre:opacity-100"
    >
      {copied ? (
        <Check className="h-3 w-3 text-[color:var(--color-success)]" />
      ) : (
        <Copy className="h-3 w-3" />
      )}
    </button>
  );
}
