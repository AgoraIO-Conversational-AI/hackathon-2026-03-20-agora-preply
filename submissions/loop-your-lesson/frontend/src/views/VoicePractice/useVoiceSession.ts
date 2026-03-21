/**
 * Voice session lifecycle hook.
 *
 * Manages: start session → connect RTC → active → stop session.
 * Orchestrates API calls and Agora RTC connection.
 */
import { useCallback, useState } from "react";

import {
  voiceApi,
  type VoiceSessionResponse,
  type VoiceSessionStopResult,
} from "@/services/voiceApi";

export type SessionStatus =
  | "idle"
  | "starting"
  | "connecting"
  | "active"
  | "stopping"
  | "ended"
  | "error";

interface UseVoiceSessionReturn {
  session: VoiceSessionResponse | null;
  status: SessionStatus;
  error: string | null;
  result: VoiceSessionStopResult | null;
  start: (
    studentId: string,
    lessonId: string,
    classtimeCode?: string,
  ) => Promise<VoiceSessionResponse | null>;
  stop: () => Promise<void>;
}

export function useVoiceSession(): UseVoiceSessionReturn {
  const [session, setSession] = useState<VoiceSessionResponse | null>(null);
  const [status, setStatus] = useState<SessionStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VoiceSessionStopResult | null>(null);

  const start = useCallback(
    async (
      studentId: string,
      lessonId: string,
      classtimeCode?: string,
    ): Promise<VoiceSessionResponse | null> => {
      try {
        setError(null);
        setResult(null);
        setStatus("starting");

        const data = await voiceApi.startSession({
          student_id: studentId,
          lesson_id: lessonId,
          classtime_session_code: classtimeCode,
        });

        setSession(data);
        setStatus("connecting");
        return data;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to start session";
        setError(message);
        setStatus("error");
        return null;
      }
    },
    [],
  );

  const stop = useCallback(async () => {
    if (!session) return;

    try {
      setStatus("stopping");
      const stopResult = await voiceApi.stopSession(session.session_id);
      setResult(stopResult);
      setStatus("ended");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to stop session";
      setError(message);
      setStatus("error");
    }
  }, [session]);

  return { session, status, error, result, start, stop };
}
