export const WidgetType = {
  ERROR_ANALYSIS: "error_analysis",
  THEME_MAP: "theme_map",
  PRACTICE_CARD: "practice_card",
} as const;

export const ErrorType = {
  GRAMMAR: "grammar",
  VOCABULARY: "vocabulary",
  PRONUNCIATION: "pronunciation",
  FLUENCY: "fluency",
} as const;

export const Severity = {
  MINOR: "minor",
  MODERATE: "moderate",
  MAJOR: "major",
} as const;

export const StreamEventType = {
  STATUS: "status",
  THINKING: "thinking",
  TOOL_START: "tool_start",
  TOOL_RESULT: "tool_result",
  STREAM: "stream",
  COMPLETE: "complete",
  ERROR: "error",
  CONVERSATION: "conversation",
  APPROVAL: "approval",
} as const;

export const CEFRLevel = {
  A1: "A1",
  A2: "A2",
  B1: "B1",
  B2: "B2",
  C1: "C1",
  C2: "C2",
} as const;
