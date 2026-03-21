import type { StreamEvent } from "@/lib/types";
import type { PreplyMode } from "@/lib/modes";
import { API_BASE, getCsrfToken } from "./client";

async function* parseSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
): AsyncGenerator<StreamEvent> {
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    let eventType = "";
    let dataLines: string[] = [];

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        eventType = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        dataLines.push(line.slice(6));
      } else if (line === "") {
        if (eventType && dataLines.length > 0) {
          try {
            const data = JSON.parse(dataLines.join("\n"));
            yield { type: eventType, ...data } as StreamEvent;
          } catch {
            // skip malformed events
          }
        }
        eventType = "";
        dataLines = [];
      }
    }
  }
}

export interface StreamOptions {
  mode: PreplyMode;
  teacherId?: string;
  studentId?: string;
  lessonId?: string;
}

export async function* streamChat(
  conversationId: string,
  message: string,
  options: StreamOptions,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const body: Record<string, string> = { message, mode: options.mode };
  if (options.teacherId) body.teacher_id = options.teacherId;
  if (options.studentId) body.student_id = options.studentId;
  if (options.lessonId) body.lesson_id = options.lessonId;

  const response = await fetch(
    `${API_BASE}/conversations/${conversationId}/stream/`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      credentials: "include",
      body: JSON.stringify(body),
      signal,
    },
  );

  if (!response.ok) {
    throw new Error(`Stream error: ${response.status}`);
  }

  if (!response.body) {
    throw new Error("No response body");
  }

  yield* parseSSEStream(response.body.getReader());
}
