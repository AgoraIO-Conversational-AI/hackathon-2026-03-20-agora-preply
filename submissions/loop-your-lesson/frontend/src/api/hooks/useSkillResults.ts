import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../client";

export interface SkillResultError {
  type: string;
  subtype: string;
  severity: string;
  communicative_impact: string;
  original: string;
  corrected: string;
  explanation: string;
  reasoning: string;
  l1_transfer: boolean;
  l1_transfer_explanation: string;
  correction_strategy: string;
  utterance_index: number | null;
  timestamp: string;
  exercise_priority: number | null;
}

export interface SkillResultTheme {
  topic: string;
  communicative_function: string;
  initiated_by: string;
  vocabulary_active: Array<string | { term: string; level?: string; context?: string }>;
  vocabulary_passive: Array<string | { term: string; level?: string; context?: string }>;
  chunks: Array<string | { term: string }>;
  range: { start: string; end: string };
}

export interface SkillResultLevel {
  overall: string;
  dimensions: {
    range: string;
    accuracy: string;
    fluency: string;
    interaction: string;
    coherence: string;
  };
  strengths: string[];
  gaps: string[];
  suggestions: string[];
  zpd: { lower: string; upper: string };
}

export interface SkillResultErrorPattern {
  label: string;
  error_type: string;
  error_subtype: string;
  status: "new" | "recurring" | "improving" | "mastered";
  occurrence_count: number;
  lesson_count: number;
  times_tested: number;
  times_correct: number;
  mastery_score: number | null;
}

export interface SkillResultPracticeQuestion {
  question_index: number;
  question_type: string;
  difficulty: string;
  stem: string;
  source_error: string | null;
}

export interface SkillResultPracticeResult {
  question_index: number;
  is_correct: boolean;
  student_answer: string;
}

export interface SkillResultClasstimeSession {
  session_code: string;
  student_url: string;
  status: string;
  questions: SkillResultPracticeQuestion[];
  results: SkillResultPracticeResult[];
  completed: boolean;
}

export interface SkillResults {
  lesson_id: string;
  lesson_date: string;
  errors: SkillResultError[];
  themes: SkillResultTheme[];
  level: SkillResultLevel | null;
  error_patterns: SkillResultErrorPattern[];
  classtime_session: SkillResultClasstimeSession | null;
  skill_status: Record<string, string>;
}

export function useSkillResults(lessonId: string | undefined) {
  return useQuery({
    queryKey: ["skillResults", lessonId],
    queryFn: () => apiFetch<SkillResults>(`/lessons/${lessonId}/skill-results/`),
    enabled: !!lessonId,
    staleTime: 30_000,
  });
}
