import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useChat } from "@/api/hooks/useChat";
import { useContextOptions } from "@/api/hooks/useContextOptions";
import { ChatArea } from "@/components/chat/ChatArea";
import { ChatInput } from "@/components/chat/ChatInput";
import { ContextHeader } from "@/components/chat/ContextHeader";
import type { ContextInfo } from "@/components/chat/ContextHeader";
import { apiFetch } from "@/api/client";
import type { PreplyMode } from "@/lib/modes";
import { MODES } from "@/lib/modes";
import type { ConversationDetail, Message, SubjectConfig } from "@/lib/types";

interface ConversationContext {
  teacherName?: string;
  studentName?: string;
  studentLevel?: string;
  studentGoal?: string;
  totalLessons?: number;
  subjectConfig?: SubjectConfig;
  lessonDate?: string;
  lessonSummary?: string;
  lessonDuration?: number;
  teacherId?: string;
  studentId?: string;
  lessonId?: string;
}

export default function ChatPage() {
  const chat = useChat();
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: contextOptions } = useContextOptions();

  // Initialize mode from URL param, default to student_practice
  const [mode, setModeState] = useState<PreplyMode>(() => {
    const param = searchParams.get("mode");
    if (param === MODES.DAILY_BRIEFING) return MODES.DAILY_BRIEFING;
    return MODES.STUDENT_PRACTICE;
  });

  // Sync mode to URL search param
  const setMode = useCallback(
    (newMode: PreplyMode) => {
      setModeState(newMode);
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("mode", newMode);
        return next;
      }, { replace: true });
    },
    [setSearchParams],
  );
  const [isLoadingConversation, setIsLoadingConversation] = useState(false);
  const [convContext, setConvContext] = useState<ConversationContext>({});

  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(
    () => searchParams.get("studentId"),
  );
  const [selectedLessonId, setSelectedLessonId] = useState<string | null>(
    () => searchParams.get("lessonId"),
  );

  const isNewConversation = !conversationId && !chat.conversationId;

  // Reset state when navigating to /chat (new conversation)
  useEffect(() => {
    if (!conversationId && chat.conversationId) {
      chat.reset();
      setConvContext({});
      setSelectedStudentId(null);
      setSelectedLessonId(null);
    }
  }, [conversationId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Load conversation when URL param changes
  useEffect(() => {
    if (!conversationId) return;
    if (conversationId === chat.conversationId) return;

    let cancelled = false;
    setIsLoadingConversation(true);

    apiFetch<ConversationDetail>(`/conversations/${conversationId}/`)
      .then((data) => {
        if (cancelled) return;
        const messages: Message[] = data.messages.map((m) => ({
          id: m.id,
          role: m.role as "user" | "assistant",
          content: m.content,
          timestamp: new Date(m.timestamp),
          toolResults: m.toolResults,
          processSteps: m.processSteps,
        }));
        setMode(data.mode as PreplyMode);
        setConvContext({
          teacherName: data.teacher_name,
          studentName: data.student_name,
          studentLevel: data.student_level,
          studentGoal: data.student_goal,
          totalLessons: data.total_lessons,
          subjectConfig: data.subject_config,
          lessonDate: data.lesson_date,
          lessonSummary: data.lesson_summary,
          lessonDuration: data.lesson_duration,
          teacherId: data.teacher_id,
          studentId: data.student_id,
          lessonId: data.lesson_id,
        });
        chat.loadConversation(conversationId, messages);
      })
      .catch(() => {
        if (!cancelled) chat.loadConversation(conversationId);
      })
      .finally(() => {
        if (!cancelled) setIsLoadingConversation(false);
      });

    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  // Sync URL when a new conversation is created during streaming
  useEffect(() => {
    if (chat.conversationId && chat.conversationId !== conversationId) {
      navigate(`/chat/${chat.conversationId}`, { replace: true });
    }
  }, [chat.conversationId]);

  // Auto-send ref (used after handleSend is defined)
  const autoSentRef = useRef(false);

  // Build ContextInfo: for loaded conversations use convContext,
  // for new conversations derive from selected student
  const selectedStudent = useMemo(
    () => contextOptions?.students.find((s) => s.id === selectedStudentId),
    [contextOptions, selectedStudentId],
  );

  const selectedLesson = useMemo(
    () => selectedStudent?.lessons.find((l) => l.id === selectedLessonId),
    [selectedStudent, selectedLessonId],
  );

  const contextInfo: ContextInfo = useMemo(() => {
    if (!isNewConversation) {
      return {
        teacherName: convContext.teacherName,
        studentName: convContext.studentName,
        studentLevel: convContext.studentLevel,
        studentGoal: convContext.studentGoal,
        totalLessons: convContext.totalLessons,
        subjectConfig: convContext.subjectConfig,
        lessonDate: convContext.lessonDate,
        lessonSummary: convContext.lessonSummary,
        lessonDuration: convContext.lessonDuration,
      };
    }
    // Derive from selected student/lesson for new conversations
    if (selectedStudent) {
      return {
        studentName: selectedStudent.name,
        studentLevel: selectedStudent.level,
        studentGoal: selectedStudent.goal,
        totalLessons: selectedStudent.total_lessons,
        subjectConfig: selectedStudent.subject_config,
        lessonDate: selectedLesson?.date,
        lessonSummary: selectedLesson?.summary,
      };
    }
    return {};
  }, [isNewConversation, convContext, selectedStudent, selectedLesson]);

  const handleSend = useCallback(
    (message: string) => {
      // Snapshot selected context into convContext on first message
      // so it persists when isNewConversation flips to false
      if (isNewConversation && selectedStudent) {
        setConvContext({
          studentName: selectedStudent.name,
          studentLevel: selectedStudent.level,
          studentGoal: selectedStudent.goal,
          totalLessons: selectedStudent.total_lessons,
          subjectConfig: selectedStudent.subject_config,
          lessonDate: selectedLesson?.date,
          lessonSummary: selectedLesson?.summary,
          studentId: selectedStudent.id,
          lessonId: selectedLesson?.id,
        });
      }

      chat.sendMessage(message, {
        mode,
        teacherId: convContext.teacherId,
        studentId: convContext.studentId ?? selectedStudentId ?? undefined,
        lessonId: convContext.lessonId ?? selectedLessonId ?? undefined,
      });
    },
    [chat, mode, convContext, selectedStudentId, selectedLessonId, isNewConversation, selectedStudent, selectedLesson],
  );

  // Auto-send first message when arriving from lesson detail page with context
  useEffect(() => {
    const urlStudentId = searchParams.get("studentId");
    const urlLessonId = searchParams.get("lessonId");
    if (
      !autoSentRef.current &&
      isNewConversation &&
      urlStudentId &&
      urlLessonId &&
      selectedStudentId === urlStudentId &&
      selectedLessonId === urlLessonId &&
      contextOptions
    ) {
      autoSentRef.current = true;
      handleSend("Show me my errors and set up practice");
    }
  }, [isNewConversation, selectedStudentId, selectedLessonId, contextOptions, handleSend]); // eslint-disable-line react-hooks/exhaustive-deps

  const isProcessing =
    chat.status === "connecting" ||
    chat.status === "thinking" ||
    chat.status === "streaming" ||
    chat.status === "executing_tool" ||
    chat.status === "awaiting_approval";

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-[var(--color-surface)]">
      {/* Sticky header: mode + student/lesson selector */}
      <ContextHeader
        mode={mode}
        context={contextInfo}
        isNewConversation={isNewConversation}
        students={contextOptions?.students ?? []}
        selectedStudentId={selectedStudentId}
        selectedLessonId={selectedLessonId}
        onStudentChange={setSelectedStudentId}
        onLessonChange={setSelectedLessonId}
      />
      <ChatArea
        messages={chat.messages}
        status={isLoadingConversation ? "connecting" : chat.status}
        statusMessage={
          isLoadingConversation ? "Loading..." : chat.statusMessage
        }
        streamingContent={chat.streamingContent}
        currentProcessSteps={chat.currentProcessSteps}
        approvalRequest={chat.approvalRequest}
        error={chat.error}
        onRetry={chat.retry}
        onSuggest={handleSend}
        mode={mode}
        contextInfo={contextInfo}
      />
      <ChatInput
        key={conversationId ?? "new"}
        onSend={handleSend}
        onCancel={chat.cancel}
        disabled={isProcessing || isLoadingConversation || (isNewConversation && (!selectedStudentId || !selectedLessonId))}
        placeholder={isNewConversation && (!selectedStudentId || !selectedLessonId) ? "Select a student and lesson to start..." : undefined}
        queueLength={chat.queueLength}
        mode={mode}
        onModeChange={setMode}
      />
    </div>
  );
}
