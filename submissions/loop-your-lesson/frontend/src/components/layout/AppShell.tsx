import { useState, useEffect, useRef } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  MessageSquare,
  BookOpen,
  Users,
  Palette,
  GraduationCap,
} from "lucide-react";
import { Tooltip } from "@/components/ui/Tooltip";
import { PreplyLogo } from "@/components/ui/PreplyLogo";
import { AppSidebar } from "./AppSidebar";

const STORAGE_KEY = "sidebar-collapsed";

const NAV_ITEMS = [
  { path: "/students", label: "Students", icon: Users },
  { path: "/chat", label: "Chat", icon: MessageSquare },
  { path: "/lessons", label: "Lessons", icon: BookOpen },
  { path: "/showcase", label: "Design system", icon: Palette },
  { path: "/showcase-classtime", label: "Practice flow", icon: GraduationCap },
];

function CollapsedSidebar({ onExpand }: { onExpand: () => void }) {
  const navigate = useNavigate();
  const location = useLocation();

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
    <aside className="flex shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-surface)]">
      {/* Header — same h-11 as expanded sidebar and context header */}
      <div className="flex h-11 items-center justify-center border-b border-[var(--color-border)] px-1.5">
        <Tooltip content="Expand sidebar" placement="right">
          <button
            onClick={onExpand}
            className="rounded p-1.5 text-[color:var(--color-text-muted)] hover:bg-[var(--color-surface-secondary)] hover:text-[color:var(--color-text-secondary)]"
          >
            <div className="flex h-6 w-6 items-center justify-center rounded-full [background:var(--color-highlight-gradient)]">
              <PreplyLogo className="h-3.5 w-3.5" />
            </div>
          </button>
        </Tooltip>
      </div>

      {/* Top nav icons */}
      <div className="flex flex-col items-center gap-1 border-b border-[var(--color-border)] px-1.5 py-2">
        <Tooltip content="Students" placement="right">
          <button
            onClick={() => navigate("/students")}
            className={`rounded-[var(--radius-md)] p-1.5 transition-colors ${
              location.pathname.startsWith("/students")
                ? "bg-[var(--color-surface-secondary)] text-[color:var(--color-text-primary)]"
                : "text-[color:var(--color-text-muted)] hover:bg-[var(--color-surface-secondary)] hover:text-[color:var(--color-text-secondary)]"
            }`}
          >
            <Users className="h-4 w-4" />
          </button>
        </Tooltip>
        <Tooltip content="Chat" placement="right">
          <button
            onClick={() => navigate("/chat")}
            className={`rounded-[var(--radius-md)] p-1.5 transition-colors ${
              location.pathname.startsWith("/chat")
                ? "bg-[var(--color-surface-secondary)] text-[color:var(--color-text-primary)]"
                : "text-[color:var(--color-text-muted)] hover:bg-[var(--color-surface-secondary)] hover:text-[color:var(--color-text-secondary)]"
            }`}
          >
            <MessageSquare className="h-4 w-4" />
          </button>
        </Tooltip>
      </div>

      <div className="flex-1" />

      {/* Section dropdown — bottom */}
      <div ref={ref} className="relative border-t border-[var(--color-border)] px-1.5 pb-4 pt-2">
        <div className="flex justify-center">
          <Tooltip content={active.label} placement="right">
            <button
              onClick={() => setOpen(!open)}
              className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-1.5 text-[color:var(--color-text-muted)] transition-colors hover:border-[var(--color-text-muted)] hover:text-[color:var(--color-text-secondary)]"
            >
              <active.icon className="h-4 w-4" />
            </button>
          </Tooltip>
        </div>

        {open && (
          <div className="absolute bottom-full left-full z-30 mb-1 ml-2 w-44 overflow-hidden rounded-[var(--radius-lg)] border-2 border-[var(--color-border)] bg-[var(--color-surface)] shadow-lg animate-[fadeIn_0.1s_ease-out]">
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
    </aside>
  );
}

export function AppShell() {
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem(STORAGE_KEY) === "true";
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(collapsed));
  }, [collapsed]);

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--color-surface-secondary)]">
      {collapsed ? (
        <CollapsedSidebar onExpand={() => setCollapsed(false)} />
      ) : (
        <aside className="flex w-64 shrink-0 flex-col overflow-hidden border-r border-[var(--color-border)] bg-[var(--color-surface)]">
          <AppSidebar onCollapse={() => setCollapsed(true)} />
        </aside>
      )}
      <main className="flex flex-1 flex-col overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
