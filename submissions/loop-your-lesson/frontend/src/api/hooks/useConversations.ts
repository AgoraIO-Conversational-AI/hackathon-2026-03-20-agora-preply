import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../client";
import type { ConversationSummary } from "@/lib/types";

export function useConversations() {
  return useQuery({
    queryKey: ["conversations"],
    queryFn: async () => {
      const res = await apiFetch<{ conversations: ConversationSummary[] }>(
        "/conversations/list/",
      );
      return res.conversations;
    },
    staleTime: 30_000,
    retry: 1,
  });
}
