// Chat state machine
export type ChatStatus =
  | "idle"
  | "connecting"
  | "thinking"
  | "streaming"
  | "executing_tool"
  | "awaiting_approval"
  | "complete"
  | "error";

// SSE event types
export type StreamEventTypeName =
  | "conversation"
  | "message"
  | "stream"
  | "thinking"
  | "status"
  | "tool_start"
  | "tool_result"
  | "approval"
  | "complete"
  | "error";

export interface StreamEvent {
  type: StreamEventTypeName;
  [key: string]: unknown;
}

// Process steps — trust UX timeline
export interface ProcessThinkingStep {
  type: "thinking";
  content: string;
}

export interface ProcessToolCallStep {
  type: "tool_call";
  toolName: string;
  toolId: string;
  toolInput: Record<string, unknown>;
  status: "running" | "completed" | "failed";
  result?: {
    message: string;
    data: Record<string, unknown>;
    executionTimeMs: number;
  };
}

export interface ProcessStatusStep {
  type: "status";
  message: string;
}

export type ProcessStep =
  | ProcessThinkingStep
  | ProcessToolCallStep
  | ProcessStatusStep;

// Tool results
export interface ToolResult {
  toolName: string;
  toolId: string;
  message: string;
  data: Record<string, unknown>;
  executionTimeMs: number;
}

// Messages
export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  toolResults?: ToolResult[];
  processSteps?: ProcessStep[];
}

// Approval requests
export interface ApprovalRequest {
  approvalId: string;
  toolName: string;
  toolInput: Record<string, unknown>;
  description: string;
}

// Subject config (language pair, etc.)
export interface SubjectConfig {
  l1?: string;
  l2?: string;
  language_pair?: string;
}

// Conversation list
export interface ConversationSummary {
  id: string;
  title: string;
  mode: string;
  status: string;
  created_at: string;
  updated_at: string;
  teacher_id?: string;
  teacher_name?: string;
  student_id?: string;
  student_name?: string;
  student_level?: string;
  student_goal?: string;
  total_lessons?: number;
  subject_config?: SubjectConfig;
  lesson_id?: string;
  lesson_date?: string;
  lesson_summary?: string;
  lesson_duration?: number;
}

// Conversation detail (returned by GET /conversations/:id/)
export interface ConversationDetail {
  id: string;
  title: string;
  mode: string;
  status: string;
  messages: Array<{
    id: string;
    role: string;
    content: string;
    timestamp: string;
    toolResults?: ToolResult[];
    processSteps?: ProcessStep[];
  }>;
  teacher_id?: string;
  teacher_name?: string;
  student_id?: string;
  student_name?: string;
  student_level?: string;
  student_goal?: string;
  total_lessons?: number;
  subject_config?: SubjectConfig;
  lesson_id?: string;
  lesson_date?: string;
  lesson_summary?: string;
  lesson_duration?: number;
}

// Context options for new conversations
export interface ContextLesson {
  id: string;
  date: string;
  summary: string;
}

export interface ContextStudent {
  id: string;
  name: string;
  level: string;
  goal?: string;
  total_lessons?: number;
  subject_config?: SubjectConfig;
  lessons: ContextLesson[];
}

export interface ContextOptions {
  teachers: Array<{ id: string; name: string }>;
  students: ContextStudent[];
}

// Widget data types

export interface ErrorItem {
  type: string;
  severity: string;
  original: string;
  corrected: string;
  explanation: string;
  position?: { utterance: number; timestamp: string };
  transcript_position?: { utterance: number; timestamp: string };
  reasoning: string;
}

export interface ErrorAnalysisData {
  widget_type: "error_analysis";
  errors: ErrorItem[];
  summary: {
    total: number;
    by_type: Record<string, number>;
    by_severity: Record<string, number>;
  };
}

export interface ThemeItem {
  topic: string;
  communicative_function?: string;
  initiated_by?: string;
  vocabulary_active?: string[];
  vocabulary_passive?: string[];
  chunks?: string[];
  transcript_range: { start: string; end: string };
}

export interface ThemeMapData {
  widget_type: "theme_map";
  themes: ThemeItem[];
}

export interface PracticeCardData {
  widget_type: "practice_card";
  question_count: number;
  question_types: Record<string, number>;
  focus_topic: string;
  goal?: string;
  themes?: string[];
  source_errors: Array<{ timestamp: string; original: string; corrected?: string }>;
  session_url?: string;
  session_code?: string;
  student_id?: string;
  lesson_id?: string;
  student_name?: string;
}

// Usage tracking
export interface UsageInfo {
  totalInputTokens: number;
  totalOutputTokens: number;
  costUsd: number;
}
