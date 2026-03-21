import type { LucideIcon } from "lucide-react";
import {
  Sun,
  GraduationCap,
  LayoutDashboard,
  UserRound,
  AlertTriangle,
  ClipboardList,
} from "lucide-react";

export const MODES = {
  DAILY_BRIEFING: "daily_briefing",
  STUDENT_PRACTICE: "student_practice",
} as const;

export type PreplyMode = (typeof MODES)[keyof typeof MODES];

export interface ModeTool {
  name: string;
  icon: LucideIcon;
}

export interface ModeDefinition {
  name: string;
  icon: LucideIcon;
  description: string;
  tools: ModeTool[];
  suggestionChips: string[];
  headline: string;
}

export const MODE_DEFINITIONS: Record<PreplyMode, ModeDefinition> = {
  student_practice: {
    name: "Practice assistant",
    icon: GraduationCap,
    description: "Explore your lesson analysis and get guidance.",
    tools: [
      { name: "Practice", icon: ClipboardList },
      { name: "Errors", icon: AlertTriangle },
    ],
    suggestionChips: [
      "What errors should I focus on?",
      "Explain this topic",
      "How is my level?",
    ],
    headline: "Let's explore your lesson together.",
  },
  daily_briefing: {
    name: "Daily briefing (TBD)",
    icon: Sun,
    description: "Review student progress and prep for today's lessons.",
    tools: [
      { name: "Overview", icon: LayoutDashboard },
      { name: "Student reports", icon: UserRound },
    ],
    suggestionChips: [
      "Show today's overview",
      "How did Maria do?",
      "Who needs attention?",
    ],
    headline: "Good morning! Ready to prep for today's lessons.",
  },
};

// Student practice chips localized to native language
const STUDENT_CHIPS_BY_L1: Record<string, { chips: string[]; headline: string }> = {
  Spanish: {
    chips: [
      "En que errores debo enfocarme?",
      "Explicame este tema",
      "Como esta mi nivel?",
    ],
    headline: "Exploremos tu leccion juntos.",
  },
  French: {
    chips: [
      "Sur quelles erreurs dois-je me concentrer?",
      "Explique-moi ce sujet",
      "Quel est mon niveau?",
    ],
    headline: "Explorons votre lecon ensemble.",
  },
  "Mandarin Chinese": {
    chips: [
      "我应该关注哪些错误?",
      "解释这个主题",
      "我的水平怎么样?",
    ],
    headline: "让我们一起探索你的课程。",
  },
  Portuguese: {
    chips: [
      "Em quais erros devo me concentrar?",
      "Explique este topico",
      "Como esta meu nivel?",
    ],
    headline: "Vamos explorar sua licao juntos.",
  },
  German: {
    chips: [
      "Auf welche Fehler sollte ich mich konzentrieren?",
      "Erklare dieses Thema",
      "Wie ist mein Niveau?",
    ],
    headline: "Lass uns deine Lektion gemeinsam erkunden.",
  },
  Polish: {
    chips: [
      "Na jakich bledach powinienem sie skupic?",
      "Wytlumacz mi ten temat",
      "Jaki jest moj poziom?",
    ],
    headline: "Przyjrzyjmy sie Twojej lekcji razem.",
  },
  Ukrainian: {
    chips: [
      "На яких помилках варто зосередитись?",
      "Поясни цю тему",
      "Який мій рівень?",
    ],
    headline: "Давай разом розберемо твій урок.",
  },
};

/** Get suggestion chips for student practice, localized to L1 if available. */
export function getStudentChips(l1?: string): { chips: string[]; headline: string } {
  if (l1 && STUDENT_CHIPS_BY_L1[l1]) {
    return STUDENT_CHIPS_BY_L1[l1];
  }
  return {
    chips: MODE_DEFINITIONS.student_practice.suggestionChips,
    headline: MODE_DEFINITIONS.student_practice.headline,
  };
}
