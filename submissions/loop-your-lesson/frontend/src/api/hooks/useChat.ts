import { useState, useCallback, useRef } from "react";
import type {
  ChatStatus,
  Message,
  ToolResult,
  ProcessStep,
  ApprovalRequest,
  UsageInfo,
} from "@/lib/types";
import { MODES, type PreplyMode } from "@/lib/modes";
import { streamChat, type StreamOptions } from "../stream";

interface UseChatReturn {
  messages: Message[];
  status: ChatStatus;
  statusMessage: string;
  streamingContent: string;
  currentToolResults: ToolResult[];
  currentProcessSteps: ProcessStep[];
  approvalRequest: ApprovalRequest | null;
  error: string | null;
  conversationId: string | null;
  usage: UsageInfo | null;
  queueLength: number;
  sendMessage: (message: string, options: StreamOptions) => void;
  cancel: () => void;
  retry: () => void;
  reset: () => void;
  loadConversation: (id: string, messages?: Message[]) => void;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<ChatStatus>("idle");
  const [statusMessage, setStatusMessage] = useState("");
  const [streamingContent, setStreamingContent] = useState("");
  const [currentToolResults, setCurrentToolResults] = useState<ToolResult[]>([]);
  const [currentProcessSteps, setCurrentProcessSteps] = useState<ProcessStep[]>([]);
  const [approvalRequest, setApprovalRequest] = useState<ApprovalRequest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [usage, setUsage] = useState<UsageInfo | null>(null);
  const [queue, setQueue] = useState<Array<{ message: string; options: StreamOptions }>>([]);

  const abortRef = useRef<AbortController | null>(null);
  const lastModeRef = useRef<PreplyMode>(MODES.DAILY_BRIEFING);

  // Refs to accumulate values during streaming (avoids stale closure in finalization)
  const contentRef = useRef("");
  const toolResultsRef = useRef<ToolResult[]>([]);
  const processStepsRef = useRef<ProcessStep[]>([]);

  // rAF buffering: accumulate stream chunks and flush at 60fps
  const rafRef = useRef<number | null>(null);
  const pendingFlush = useRef(false);

  const processStream = useCallback(
    async (message: string, options: StreamOptions, convoId: string) => {
      const abortController = new AbortController();
      abortRef.current = abortController;

      setStatus("connecting");
      setStatusMessage("Connecting...");
      setStreamingContent("");
      setCurrentToolResults([]);
      setCurrentProcessSteps([]);
      setError(null);

      // Reset refs for this stream
      contentRef.current = "";
      toolResultsRef.current = [];
      processStepsRef.current = [];

      // Add user message immediately
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        content: message,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);

      try {
        for await (const event of streamChat(convoId, message, options, abortController.signal)) {
          switch (event.type) {
            case "conversation":
              if (event.conversation_id) {
                setConversationId(event.conversation_id as string);
              }
              break;

            case "status":
              setStatus("thinking");
              setStatusMessage((event.message as string) ?? "Thinking...");
              break;

            case "thinking": {
              setStatus("thinking");
              const thinkingStep: ProcessStep = { type: "thinking", content: event.content as string };
              processStepsRef.current = [...processStepsRef.current, thinkingStep];
              setCurrentProcessSteps([...processStepsRef.current]);
              break;
            }

            case "tool_start": {
              setStatus("executing_tool");
              const toolStep: ProcessStep = {
                type: "tool_call",
                toolName: event.tool_name as string,
                toolId: event.tool_id as string,
                toolInput: (event.tool_input as Record<string, unknown>) ?? {},
                status: "running",
              };
              processStepsRef.current = [...processStepsRef.current, toolStep];
              setCurrentProcessSteps([...processStepsRef.current]);
              break;
            }

            case "tool_result": {
              const toolResult: ToolResult = {
                toolName: event.tool_name as string,
                toolId: event.tool_id as string,
                message: event.message as string,
                data: (event.data as Record<string, unknown>) ?? {},
                executionTimeMs: (event.execution_time_ms as number) ?? 0,
              };
              toolResultsRef.current = [...toolResultsRef.current, toolResult];
              setCurrentToolResults([...toolResultsRef.current]);
              processStepsRef.current = processStepsRef.current.map((step) =>
                step.type === "tool_call" && step.toolId === toolResult.toolId
                  ? { ...step, status: "completed" as const, result: toolResult }
                  : step,
              );
              setCurrentProcessSteps([...processStepsRef.current]);
              break;
            }

            case "stream": {
              setStatus("streaming");
              const chunk = (event.content as string) ?? "";
              contentRef.current += chunk;
              // Buffer updates and flush at animation frame rate for smooth rendering
              if (!pendingFlush.current) {
                pendingFlush.current = true;
                rafRef.current = requestAnimationFrame(() => {
                  pendingFlush.current = false;
                  setStreamingContent(contentRef.current);
                });
              }
              break;
            }

            case "approval":
              setStatus("awaiting_approval");
              setApprovalRequest({
                approvalId: event.approval_id as string,
                toolName: event.tool_name as string,
                toolInput: (event.tool_input as Record<string, unknown>) ?? {},
                description: event.description as string,
              });
              break;

            case "complete":
              if (event.usage) {
                const u = event.usage as { input_tokens: number; output_tokens: number; cost_usd?: number };
                setUsage({
                  totalInputTokens: u.input_tokens,
                  totalOutputTokens: u.output_tokens,
                  costUsd: u.cost_usd ?? 0,
                });
              }
              break;

            case "error":
              setStatus("error");
              setError((event.message as string) ?? "An error occurred");
              return;
          }
        }

        // Cancel any pending rAF and flush final content
        if (rafRef.current) {
          cancelAnimationFrame(rafRef.current);
          rafRef.current = null;
          pendingFlush.current = false;
        }

        // Finalize assistant message — read from refs (always current)
        const finalContent = contentRef.current;
        const finalToolResults = toolResultsRef.current;
        const finalProcessSteps = processStepsRef.current;

        setMessages((prev) => [
          ...prev,
          {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: finalContent,
            timestamp: new Date(),
            toolResults: finalToolResults.length > 0 ? finalToolResults : undefined,
            processSteps: finalProcessSteps.length > 0 ? finalProcessSteps : undefined,
          },
        ]);

        setStatus("idle");
        setStreamingContent("");
        setCurrentToolResults([]);
        setCurrentProcessSteps([]);
        contentRef.current = "";
        toolResultsRef.current = [];
        processStepsRef.current = [];
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          setStatus("idle");
        } else {
          setStatus("error");
          setError((err as Error).message);
        }
      }
    },
    [],
  );

  const sendMessage = useCallback(
    (message: string, options: StreamOptions) => {
      lastModeRef.current = options.mode;

      if (status !== "idle" && status !== "error" && status !== "complete") {
        setQueue((prev) => [...prev, { message, options }]);
        return;
      }

      const convoId = conversationId ?? crypto.randomUUID();
      if (!conversationId) setConversationId(convoId);

      processStream(message, options, convoId);
    },
    [status, conversationId, processStream],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
      pendingFlush.current = false;
    }
    setStatus("idle");
    setStreamingContent("");
  }, []);

  const retry = useCallback(() => {
    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
    if (lastUserMsg && conversationId) {
      setMessages((prev) => prev.filter((m) => m.id !== lastUserMsg.id));
      processStream(lastUserMsg.content, { mode: lastModeRef.current }, conversationId);
    }
  }, [messages, conversationId, processStream]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setStatus("idle");
    setStatusMessage("");
    setStreamingContent("");
    setCurrentToolResults([]);
    setCurrentProcessSteps([]);
    setApprovalRequest(null);
    setError(null);
    setConversationId(null);
    setUsage(null);
    setQueue([]);
  }, []);

  const loadConversation = useCallback((id: string, msgs?: Message[]) => {
    abortRef.current?.abort();
    setConversationId(id);
    setMessages(msgs ?? []);
    setStatus("idle");
    setStreamingContent("");
    setCurrentToolResults([]);
    setCurrentProcessSteps([]);
    setError(null);
  }, []);

  return {
    messages,
    status,
    statusMessage,
    streamingContent,
    currentToolResults,
    currentProcessSteps,
    approvalRequest,
    error,
    conversationId,
    usage,
    queueLength: queue.length,
    sendMessage,
    cancel,
    retry,
    reset,
    loadConversation,
  };
}
