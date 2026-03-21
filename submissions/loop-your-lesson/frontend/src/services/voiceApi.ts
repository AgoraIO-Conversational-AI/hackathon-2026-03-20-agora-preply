/**
 * API client for voice practice session endpoints.
 */
import { apiFetch } from "@/api/client";

export interface VoiceSessionStartRequest {
  student_id: string;
  lesson_id: string;
  classtime_session_code?: string;
}

export interface VoiceSessionResponse {
  session_id: string;
  channel_name: string;
  rtc_token: string;
  uid: number;
  agent_id: string;
  agora_app_id: string;
  student_name: string;
  student_level: string;
}

export interface VoiceSessionStatus {
  session_id: string;
  agent_id: string;
  agent_status: string;
  channel: string;
}

export interface VoiceSessionStopResult {
  session_id: string;
  stopped: boolean;
  mastery_summary: Record<string, unknown>;
  quiz_events_count: number;
}

export const voiceApi = {
  async startSession(
    params: VoiceSessionStartRequest,
  ): Promise<VoiceSessionResponse> {
    return apiFetch<VoiceSessionResponse>("/voice-sessions/", {
      method: "POST",
      body: JSON.stringify(params),
    });
  },

  async getStatus(sessionId: string): Promise<VoiceSessionStatus> {
    return apiFetch<VoiceSessionStatus>(`/voice-sessions/${sessionId}/`);
  },

  async stopSession(sessionId: string): Promise<VoiceSessionStopResult> {
    return apiFetch<VoiceSessionStopResult>(
      `/voice-sessions/${sessionId}/stop/`,
      { method: "POST" },
    );
  },
};
