import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../client";
import type { ContextOptions } from "@/lib/types";

export function useContextOptions() {
  return useQuery({
    queryKey: ["contextOptions"],
    queryFn: () => apiFetch<ContextOptions>("/context/"),
    staleTime: 60_000,
  });
}
