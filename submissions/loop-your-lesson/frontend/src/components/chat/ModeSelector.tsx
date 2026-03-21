import { useState, useRef, useEffect } from "react";
import { ChevronDown } from "lucide-react";
import Pill from "@/components/ui/Pill";
import { MODE_DEFINITIONS, type PreplyMode } from "@/lib/modes";

interface ModeSelectorProps {
  value: PreplyMode;
  onChange: (mode: PreplyMode) => void;
}

export function ModeSelector({ value, onChange }: ModeSelectorProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const activeDef = MODE_DEFINITIONS[value];
  const ActiveIcon = activeDef.icon;

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-haspopup="listbox"
        className="flex items-center gap-1.5 rounded-[var(--radius-sm)] border-2 border-[var(--color-border)] px-2 py-1 text-xs text-[color:var(--color-text-secondary)] transition-preply hover:border-[var(--color-text-primary)]"
      >
        <ActiveIcon className="h-3.5 w-3.5" />
        {activeDef.name}
        <ChevronDown className="h-3 w-3" />
      </button>

      {open && (
        <div className="absolute bottom-full left-0 mb-1 w-64 rounded-[var(--radius-lg)] border-2 border-[var(--color-border)] bg-[var(--color-surface)] shadow-lg animate-[fadeIn_0.1s_ease-out]">
          {(
            Object.entries(MODE_DEFINITIONS) as [
              PreplyMode,
              (typeof MODE_DEFINITIONS)[PreplyMode],
            ][]
          ).map(([key, def]) => {
            const Icon = def.icon;
            return (
              <button
                key={key}
                onClick={() => {
                  onChange(key);
                  setOpen(false);
                }}
                className={`w-full px-3 py-2.5 text-left transition-colors first:rounded-t-[var(--radius-lg)] last:rounded-b-[var(--radius-lg)] ${
                  key === value
                    ? "bg-[var(--color-primary-light)]"
                    : "hover:bg-[var(--color-surface-secondary)]"
                }`}
              >
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4 text-[color:var(--color-text-secondary)]" />
                  <div>
                    <p className="text-sm font-medium text-[color:var(--color-text-primary)]">
                      {def.name}
                    </p>
                    <p className="text-xs text-[color:var(--color-text-muted)]">
                      {def.description}
                    </p>
                  </div>
                </div>
                <div className="mt-1.5 ml-6 flex flex-wrap gap-1">
                  {def.tools.map((tool) => {
                    const ToolIcon = tool.icon;
                    return (
                      <Pill
                        key={tool.name}
                        variant="outline"
                        icon={<ToolIcon className="h-2.5 w-2.5" />}
                      >
                        {tool.name}
                      </Pill>
                    );
                  })}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
