/**
 * Standard Message (Interface Layer)
 * 기획서: session_id, user_id, content, timestamp, channel, message_id
 */
export interface StandardMessage {
  session_id: string;
  user_id: string;
  content: string;
  timestamp: string;
  channel: string;
  message_id: string;
}

export interface Turn {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  tool_calls?: ToolCallResult[];
}

export interface ToolCallResult {
  skill: string;
  args: Record<string, unknown>;
  result_preview?: string;
  error?: string;
  hitl_required?: boolean;
  hitl_id?: string;
}

export interface SkillMeta {
  name: string;
  description: string;
  params_schema: Record<string, string>;
}
