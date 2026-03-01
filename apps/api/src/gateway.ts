/**
 * Gateway — Interface Layer
 * 채팅/메시지 수신 → Standard Message 포맷으로 정규화, Session 관리
 */
import { v4 as uuidv4 } from "uuid";
import * as sessionStore from "./sessionStore.js";
import type { StandardMessage, Turn } from "./types.js";

export function getOrCreateSession(sessionId?: string | null): string {
  if (sessionId && sessionStore.exists(sessionId)) return sessionId;
  return sessionStore.createSession();
}

export function toStandardMessage(
  content: string,
  sessionId: string | null,
  userId = "default",
  channel = "web"
): StandardMessage {
  const sid = getOrCreateSession(sessionId);
  return {
    session_id: sid,
    user_id: userId,
    content: content.trim(),
    timestamp: new Date().toISOString(),
    channel,
    message_id: uuidv4().slice(0, 12),
  };
}

export function appendUserTurn(sessionId: string, content: string): void {
  sessionStore.append(sessionId, {
    role: "user",
    content,
    timestamp: new Date().toISOString(),
  });
}

export function appendAssistantTurn(
  sessionId: string,
  content: string,
  tool_calls?: Turn["tool_calls"]
): void {
  sessionStore.append(sessionId, {
    role: "assistant",
    content,
    timestamp: new Date().toISOString(),
    tool_calls,
  });
}

export function getHistoryForControl(sessionId: string): Turn[] {
  return sessionStore.getHistory(sessionId);
}
