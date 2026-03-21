import { useCallback, useEffect } from "react";
import { X, BookOpen } from "lucide-react";
import { AnamAvatar } from "@/views/VoicePractice/AnamAvatar";
import { useAgoraRTC } from "@/views/VoicePractice/useAgoraRTC";
import { useVoiceSession } from "@/views/VoicePractice/useVoiceSession";
import Button from "@/components/ui/Button";

interface PracticeModalProps {
  sessionCode: string;
  focusTopic: string;
  questionCount: number;
  studentName?: string;
  studentId?: string;
  lessonId?: string;
  onClose: () => void;
}

function classtimeUrl(code: string) {
  return `https://www.classtime.com/code/${code}`;
}

export function PracticeModal({
  sessionCode,
  focusTopic,
  questionCount,
  studentName,
  studentId,
  lessonId,
  onClose,
}: PracticeModalProps) {
  const src = classtimeUrl(sessionCode);
  const voiceSession = useVoiceSession();
  const agora = useAgoraRTC();

  // Start voice agent when modal opens
  useEffect(() => {
    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout>;
    async function startVoice() {
      const data = await voiceSession.start(
        studentId ?? "student",
        lessonId ?? "lesson",
        sessionCode,
      );
      if (data && !cancelled) {
        timeoutId = setTimeout(async () => {
          if (!cancelled) {
            await agora.join({
              appId: data.agora_app_id,
              channel: data.channel_name,
              token: data.rtc_token,
              uid: data.uid,
            });
          }
        }, 1500);
      }
    }
    startVoice();
    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleClose = useCallback(async () => {
    await agora.leave();
    await voiceSession.stop();
    onClose();
  }, [agora, voiceSession, onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 animate-[fadeIn_0.15s_ease-out]">
      <div className="flex h-[92vh] w-[95vw] max-w-7xl flex-col overflow-hidden rounded-[var(--radius-xl)] bg-[var(--color-surface)] shadow-2xl animate-[expandDown_0.2s_ease-out]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--color-border)] px-5 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full [background:var(--color-highlight-gradient)]">
              <BookOpen className="h-4 w-4 text-[color:var(--color-text-primary)]" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[color:var(--color-text-primary)]">
                {focusTopic}
              </h3>
              <p className="text-xs text-[color:var(--color-text-muted)]">
                {questionCount} questions
                {studentName && ` · ${studentName}`}
                {voiceSession.session && " · Voice practice active"}
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="rounded-[var(--radius-md)] p-2 text-[color:var(--color-text-muted)] transition-preply hover:bg-[var(--color-surface-secondary)] hover:text-[color:var(--color-text-primary)]"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Main content: quiz + avatar side by side */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left: Classtime quiz */}
          <div className="flex-1 bg-white">
            <iframe
              src={src}
              className="h-full w-full border-none"
              allow="clipboard-write"
              title="Classtime practice session"
            />
          </div>

          {/* Right: Voice practice avatar */}
          <div className="w-72 flex flex-col items-center justify-center gap-4 border-l border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <AnamAvatar
              isConnected={agora.isConnected}
              remoteAudioReady={agora.remoteAudioReady}
              videoTrack={agora.remoteVideoTrack}
              studentName={voiceSession.session?.student_name ?? studentName ?? "Student"}
              isMuted={agora.isMuted}
              onToggleMute={agora.toggleMute}
            />

            {voiceSession.error && (
              <p className="text-xs text-center text-red-600 dark:text-red-400">
                {voiceSession.error}
              </p>
            )}
            {agora.error && (
              <p className="text-xs text-center text-red-600 dark:text-red-400">
                {agora.error}
              </p>
            )}

            <p className="text-[10px] text-center text-[color:var(--color-text-muted)]">
              Answer questions while chatting — the avatar adapts based on your quiz answers
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-[var(--color-border)] px-5 py-3">
          <p className="text-xs text-[color:var(--color-text-muted)]">
            Powered by Classtime + Agora ConvoAI · Session {sessionCode}
          </p>
          <Button variant="tertiary" size="sm" onClick={handleClose}>
            Close and return to chat
          </Button>
        </div>
      </div>
    </div>
  );
}
