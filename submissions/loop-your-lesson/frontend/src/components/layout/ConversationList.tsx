import { useParams, useNavigate } from "react-router-dom";
import { Plus, Sun, GraduationCap } from "lucide-react";
import { useConversations } from "@/api/hooks/useConversations";
import { formatRelativeTime } from "@/lib/utils";
import Button from "@/components/ui/Button";
import Spinner from "@/components/ui/Spinner";
import { Tooltip } from "@/components/ui/Tooltip";
import type { ConversationSummary } from "@/lib/types";
import { MODES } from "@/lib/modes";

function ConversationItem({
  conversation,
  isActive,
  onClick,
}: {
  conversation: ConversationSummary;
  isActive: boolean;
  onClick: () => void;
}) {
  const title = conversation.title || "New conversation";

  return (
    <button
      onClick={onClick}
      className={`w-full px-2.5 py-2 text-left transition-colors ${
        isActive
          ? "border-l-2 border-l-[var(--color-primary)] bg-[var(--color-surface-secondary)]"
          : "border-l-2 border-l-transparent hover:bg-[var(--color-surface-secondary)]"
      }`}
    >
      <div className="flex items-center gap-2">
        <Tooltip
          content={
            conversation.mode === MODES.DAILY_BRIEFING
              ? "Daily briefing"
              : "Student practice"
          }
        >
          {conversation.mode === MODES.DAILY_BRIEFING ? (
            <Sun className="h-3.5 w-3.5 shrink-0 text-[color:var(--color-text-muted)]" />
          ) : (
            <GraduationCap className="h-3.5 w-3.5 shrink-0 text-[color:var(--color-text-muted)]" />
          )}
        </Tooltip>
        <Tooltip content={title} placement="right" className="min-w-0 flex-1">
          <p className="truncate text-sm text-[color:var(--color-text-primary)]">
            {title}
          </p>
        </Tooltip>
        <Tooltip
          content={new Date(conversation.updated_at).toLocaleString()}
          placement="left"
        >
          <span className="shrink-0 text-xs text-[color:var(--color-text-muted)]">
            {formatRelativeTime(conversation.updated_at)}
          </span>
        </Tooltip>
      </div>
      {conversation.student_name && (
        <p className="mt-0.5 truncate pl-5 text-xs text-[color:var(--color-text-muted)]">
          {conversation.student_name}
        </p>
      )}
    </button>
  );
}

export function ConversationList() {
  const { data: conversations, isLoading } = useConversations();
  const { conversationId } = useParams();
  const navigate = useNavigate();

  return (
    <div className="flex h-full flex-col">
      <div className="px-3 pt-3 pb-2">
        <Button
          variant="tertiary"
          size="sm"
          className="w-full gap-2"
          onClick={() => navigate("/chat")}
        >
          <Plus className="h-4 w-4" />
          New conversation
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {isLoading && (
          <div className="flex justify-center py-8">
            <Spinner size="small" />
          </div>
        )}

        {conversations && conversations.length === 0 && (
          <p className="py-8 text-center text-xs text-[color:var(--color-text-muted)]">
            No conversations yet
          </p>
        )}

        <div className="space-y-1">
          {conversations?.map((conv) => (
            <ConversationItem
              key={conv.id}
              conversation={conv}
              isActive={conv.id === conversationId}
              onClick={() => navigate(`/chat/${conv.id}`)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
