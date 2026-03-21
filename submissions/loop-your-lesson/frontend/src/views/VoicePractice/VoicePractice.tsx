/**
 * Voice Practice — main view.
 *
 * Layout: Classtime quiz (opens in popup) + avatar (Agora RTC audio).
 * Student answers quiz questions while talking to the avatar — both active at once.
 * ConvoAI handles full-duplex audio. Quiz results feed the avatar in real-time
 * via backend Pusher listener -> /speak + /update.
 */
import { useCallback, useRef } from "react";
import { Phone, PhoneOff, Loader2, AlertCircle, ExternalLink } from "lucide-react";

import { AnamAvatar } from "./AnamAvatar";
import { useAgoraRTC } from "./useAgoraRTC";
import { useVoiceSession, type SessionStatus } from "./useVoiceSession";

// Demo defaults — replace with dynamic selection from UI
const DEFAULT_STUDENT_ID = "demo-maria";
const DEFAULT_LESSON_ID = "demo-lesson-1";
const DEFAULT_CLASSTIME_CODE = "UC84IQ";
const DEFAULT_CLASSTIME_URL =
  "https://www.classtime.com/code/UC84IQ/BPzccG5omPUTAYLD0KhM8A:AQ";

export default function VoicePractice() {
  const { session, status, error, result, start, stop } = useVoiceSession();
  const quizWindowRef = useRef<Window | null>(null);

  // Agora RTC
  const agora = useAgoraRTC();

  const openQuizWindow = useCallback(() => {
    // Open Classtime in a popup window (iframe blocked by Google OAuth)
    quizWindowRef.current = window.open(
      DEFAULT_CLASSTIME_URL,
      "classtime-quiz",
      "width=800,height=700,left=100,top=100",
    );
  }, []);

  const handleStart = useCallback(async () => {
    const data = await start(
      DEFAULT_STUDENT_ID,
      DEFAULT_LESSON_ID,
      DEFAULT_CLASSTIME_CODE,
    );
    if (data) {
      // Open quiz in separate window
      openQuizWindow();

      // Join RTC channel with fresh params after agent starts
      setTimeout(async () => {
        await agora.join({
          appId: data.agora_app_id,
          channel: data.channel_name,
          token: data.rtc_token,
          uid: data.uid,
        });
      }, 1500);
    }
  }, [start, agora, openQuizWindow]);

  const handleStop = useCallback(async () => {
    await agora.leave();
    await stop();
    // Close quiz window
    quizWindowRef.current?.close();
    quizWindowRef.current = null;
  }, [agora, stop]);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-[color:var(--color-border)] px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold text-[color:var(--color-text)]">
            Voice Practice Session
          </h1>
          {session && (
            <p className="text-sm text-[color:var(--color-text-secondary)]">
              Student: {session.student_name} · Level: {session.student_level}
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          {status === "active" && (
            <button
              onClick={openQuizWindow}
              className="flex items-center gap-2 rounded-lg border border-[color:var(--color-border)] px-3 py-2 text-sm text-[color:var(--color-text-secondary)] hover:bg-[color:var(--color-surface-secondary)] transition-colors"
            >
              <ExternalLink size={14} />
              Open Quiz
            </button>
          )}
          <SessionControls
            status={status}
            onStart={handleStart}
            onStop={handleStop}
          />
        </div>
      </header>

      {/* Main content — full width for voice practice */}
      <div className="flex flex-1 items-center justify-center p-8">
        {status === "idle" ? (
          <IdleState />
        ) : (
          <div className="flex flex-col items-center gap-8 max-w-md">
            <AnamAvatar
              isConnected={agora.isConnected}
              remoteAudioReady={agora.remoteAudioReady}
              videoTrack={agora.remoteVideoTrack}
              studentName={session?.student_name ?? "Student"}
              isMuted={agora.isMuted}
              onToggleMute={agora.toggleMute}
            />

            {/* Connection status */}
            <StatusIndicator status={status} />

            {/* Error display */}
            {(error || agora.error) && (
              <div className="flex items-center gap-2 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
                <AlertCircle size={16} />
                {error || agora.error}
              </div>
            )}

            {/* Quiz reminder */}
            {status === "active" && (
              <p className="text-center text-xs text-[color:var(--color-text-muted)]">
                Quiz is open in a separate window. Answer questions while chatting — the avatar adapts based on your answers.
              </p>
            )}

            {/* Session result */}
            {result && (
              <div className="rounded-lg bg-[color:var(--color-surface-secondary)] p-4 text-sm">
                <p className="font-medium text-[color:var(--color-text)]">
                  Session Complete
                </p>
                <p className="text-[color:var(--color-text-secondary)]">
                  Quiz events processed: {result.quiz_events_count}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function SessionControls({
  status,
  onStart,
  onStop,
}: {
  status: SessionStatus;
  onStart: () => void;
  onStop: () => void;
}) {
  if (status === "idle" || status === "ended" || status === "error") {
    return (
      <button
        onClick={onStart}
        className="flex items-center gap-2 rounded-lg bg-[color:var(--color-accent)] px-4 py-2 text-sm font-medium text-white hover:bg-[color:var(--color-accent-hover)] transition-colors"
      >
        <Phone size={16} />
        Start Session
      </button>
    );
  }

  if (status === "starting" || status === "connecting") {
    return (
      <button
        disabled
        className="flex items-center gap-2 rounded-lg bg-[color:var(--color-surface-secondary)] px-4 py-2 text-sm font-medium text-[color:var(--color-text-muted)] cursor-not-allowed"
      >
        <Loader2 size={16} className="animate-spin" />
        {status === "starting" ? "Starting agent..." : "Connecting audio..."}
      </button>
    );
  }

  return (
    <button
      onClick={onStop}
      className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
    >
      <PhoneOff size={16} />
      End Session
    </button>
  );
}

function StatusIndicator({ status }: { status: SessionStatus }) {
  const labels: Record<SessionStatus, string> = {
    idle: "",
    starting: "Starting ConvoAI agent...",
    connecting: "Connecting to audio channel...",
    active: "Session active — speak naturally!",
    stopping: "Ending session...",
    ended: "Session ended",
    error: "Connection error",
  };

  const label = labels[status];
  if (!label) return null;

  return (
    <p className="text-sm text-[color:var(--color-text-secondary)]">{label}</p>
  );
}

function IdleState() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 text-center">
      <div className="rounded-full bg-[color:var(--color-surface-secondary)] p-6">
        <Phone size={32} className="text-[color:var(--color-text-muted)]" />
      </div>
      <div>
        <h2 className="text-lg font-medium text-[color:var(--color-text)]">
          Ready to Practice
        </h2>
        <p className="mt-1 max-w-sm text-sm text-[color:var(--color-text-secondary)]">
          Start a session to practice speaking with an AI avatar that knows your
          lesson errors. A quiz opens in a separate window — the avatar adapts
          based on your quiz performance.
        </p>
      </div>
    </div>
  );
}
