import { useState, useRef, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  MessageSquare,
  BookOpen,
  Users,
  PanelLeftClose,
  ChevronDown,
  Palette,
  GraduationCap,
} from "lucide-react";
import { Tooltip } from "@/components/ui/Tooltip";
import { PreplyLogo } from "@/components/ui/PreplyLogo";
import { ConversationList } from "./ConversationList";

const NAV_ITEMS = [
  { path: "/students", label: "Students", icon: Users },
  { path: "/chat", label: "Chat", icon: MessageSquare },
  { path: "/lessons", label: "Lessons", icon: BookOpen },
  { path: "/showcase", label: "Design system", icon: Palette },
  { path: "/showcase-classtime", label: "Practice flow", icon: GraduationCap },
];

interface AppSidebarProps {
  onCollapse: () => void;
}

function SectionDropdown() {
  const location = useLocation();
  const navigate = useNavigate();

  const active = (
    NAV_ITEMS.find((item) => location.pathname.startsWith(item.path)) ??
    NAV_ITEMS[0]
  )!;

  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

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
    <div ref={ref} className="relative border-t border-[var(--color-border)] px-3 pb-4 pt-2">
      <p className="mb-1.5 px-1 text-[11px] font-medium uppercase tracking-wide text-[color:var(--color-text-muted)]">
        Navigate
      </p>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 rounded-[var(--radius-md)] border border-[var(--color-border)] px-2.5 py-1.5 text-sm text-[color:var(--color-text-secondary)] transition-colors hover:border-[var(--color-text-muted)] hover:text-[color:var(--color-text-primary)]"
      >
        <active.icon className="h-4 w-4 shrink-0" />
        <span className="flex-1 text-left font-medium">{active.label}</span>
        <ChevronDown
          className={`h-3.5 w-3.5 shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="absolute bottom-full left-3 right-3 z-30 mb-1 overflow-hidden rounded-[var(--radius-lg)] border-2 border-[var(--color-border)] bg-[var(--color-surface)] shadow-lg animate-[fadeIn_0.1s_ease-out]">
          {NAV_ITEMS.map(({ path, label, icon: Icon }) => {
            const isActive = location.pathname.startsWith(path);
            return (
              <button
                key={path}
                onClick={() => {
                  navigate(path);
                  setOpen(false);
                }}
                className={`flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm transition-colors first:rounded-t-[calc(var(--radius-lg)-2px)] last:rounded-b-[calc(var(--radius-lg)-2px)] ${
                  isActive
                    ? "bg-[var(--color-surface-secondary)] font-medium text-[color:var(--color-text-primary)]"
                    : "text-[color:var(--color-text-secondary)] hover:bg-[var(--color-surface-secondary)] hover:text-[color:var(--color-text-primary)]"
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function AppSidebar({ onCollapse }: AppSidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const isChatSection = location.pathname.startsWith("/chat");
  const isStudentsSection = location.pathname.startsWith("/students");

  return (
    <div className="flex h-full flex-col">
      {/* Header — matches ContextHeader height */}
      <div className="flex h-11 items-center justify-between border-b border-[var(--color-border)] px-4">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-full [background:var(--color-highlight-gradient)]">
            <PreplyLogo className="h-3.5 w-3.5" />
          </div>
          <h1 className="text-sm font-semibold text-[color:var(--color-text-primary)]">
            Lesson Intelligence
          </h1>
        </div>
        <Tooltip content="Collapse sidebar" placement="bottom">
          <button
            onClick={onCollapse}
            className="rounded p-1 text-[color:var(--color-text-muted)] hover:bg-[var(--color-surface-secondary)] hover:text-[color:var(--color-text-secondary)]"
          >
            <PanelLeftClose className="h-4 w-4" />
          </button>
        </Tooltip>
      </div>

      {/* Top nav links — always visible */}
      <div className="border-b border-[var(--color-border)]">
        <button
          onClick={() => navigate("/students")}
          className={`flex w-full items-center gap-2 px-4 py-2 text-left text-sm transition-colors ${
            isStudentsSection
              ? "bg-[var(--color-surface-secondary)] font-medium text-[color:var(--color-text-primary)]"
              : "text-[color:var(--color-text-secondary)] hover:bg-[var(--color-surface-secondary)] hover:text-[color:var(--color-text-primary)]"
          }`}
        >
          <Users className="h-4 w-4 shrink-0" />
          Students
        </button>
        <button
          onClick={() => navigate("/chat")}
          className={`flex w-full items-center gap-2 px-4 py-2 text-left text-sm transition-colors ${
            isChatSection
              ? "bg-[var(--color-surface-secondary)] font-medium text-[color:var(--color-text-primary)]"
              : "text-[color:var(--color-text-secondary)] hover:bg-[var(--color-surface-secondary)] hover:text-[color:var(--color-text-primary)]"
          }`}
        >
          <MessageSquare className="h-4 w-4 shrink-0" />
          Chat
        </button>
      </div>

      {/* Context panel - conversation list when in chat section */}
      <div className="flex-1 overflow-y-auto">
        {isChatSection && <ConversationList />}
      </div>

      {/* Section dropdown — bottom */}
      <SectionDropdown />
    </div>
  );
}
