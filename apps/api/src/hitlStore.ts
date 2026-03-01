/**
 * HITL pending store — 승인 대기 항목
 */
const pending = new Map<
  string,
  { session_id: string; skill_name: string; args: Record<string, unknown> }
>();
const MAX = 100;

export function add(
  hitlId: string,
  sessionId: string,
  skillName: string,
  args: Record<string, unknown>
): void {
  if (pending.size >= MAX) {
    const first = pending.keys().next().value;
    if (first) pending.delete(first);
  }
  pending.set(hitlId, {
    session_id: sessionId,
    skill_name: skillName,
    args: args ?? {},
  });
}

export function pop(
  hitlId: string
): { session_id: string; skill_name: string; args: Record<string, unknown> } | undefined {
  const v = pending.get(hitlId);
  if (v) pending.delete(hitlId);
  return v;
}
