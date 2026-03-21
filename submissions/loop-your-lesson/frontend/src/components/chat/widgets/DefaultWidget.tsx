export function DefaultWidget({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="rounded-[var(--radius-lg)] border-2 border-[var(--color-border)] bg-[var(--color-surface)]">
      <div className="px-4 py-3">
        <h4 className="text-xs font-medium text-[color:var(--color-text-muted)]">
          Tool result
          {typeof data.widget_type === "string" && (
            <span className="ml-1.5 rounded bg-[var(--color-surface-secondary)] px-1.5 py-0.5 font-mono">
              {data.widget_type}
            </span>
          )}
        </h4>
      </div>
      <pre className="border-t border-[var(--color-border)] px-4 py-3 text-[11px] text-[color:var(--color-text-muted)] overflow-x-auto">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}
