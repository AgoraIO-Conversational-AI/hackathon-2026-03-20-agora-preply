/**
 * Thread processing pipeline for message consolidation.
 *
 * Adapted from PostHog's threadGrouped selector pattern:
 * raw messages → filter empty → merge consecutive assistant → renderable thread.
 *
 * The backend agent loop creates separate DB messages per LLM call
 * (tool-use turn + final text turn). This pipeline consolidates them
 * into a unified view on the frontend.
 */

import type { Message, ProcessStep } from "./types";

/**
 * Process raw messages into a renderable thread.
 *
 * 1. Filter empty assistant messages (no content, no tool calls)
 * 2. Merge consecutive assistant messages into one unified message
 */
export function processThread(messages: Message[]): Message[] {
  // Step 1: Filter empty assistant messages
  const filtered = messages.filter((msg) => {
    if (msg.role !== "assistant") return true;
    const hasContent = msg.content.trim().length > 0;
    const hasProcessSteps = msg.processSteps && msg.processSteps.length > 0;
    const hasToolResults = msg.toolResults && msg.toolResults.length > 0;
    return hasContent || hasProcessSteps || hasToolResults;
  });

  // Step 2: Merge consecutive assistant messages
  const merged: Message[] = [];
  for (const msg of filtered) {
    const prev = merged[merged.length - 1];
    if (msg.role === "assistant" && prev?.role === "assistant") {
      merged[merged.length - 1] = {
        ...prev,
        content: msg.content || prev.content,
        processSteps: deduplicateProcessSteps(
          prev.processSteps ?? [],
          msg.processSteps ?? [],
        ),
        toolResults: [
          ...(prev.toolResults ?? []),
          ...(msg.toolResults ?? []),
        ],
      };
    } else {
      merged.push({ ...msg });
    }
  }

  return merged;
}

/**
 * Deduplicate process steps by toolId when merging consecutive messages.
 * Later entries (from metadata.process_steps) win over earlier synthesized ones
 * since they have the full result data from the agent loop.
 */
function deduplicateProcessSteps(
  prevSteps: ProcessStep[],
  newSteps: ProcessStep[],
): ProcessStep[] {
  const allSteps = [...prevSteps, ...newSteps];
  const seen = new Set<string>();
  const deduped: ProcessStep[] = [];

  // Iterate in reverse so later (more complete) entries win
  for (let i = allSteps.length - 1; i >= 0; i--) {
    const step = allSteps[i]!;
    const key = step.type === "tool_call" ? step.toolId : null;
    if (key && seen.has(key)) continue;
    if (key) seen.add(key);
    deduped.unshift(step);
  }

  return deduped;
}
