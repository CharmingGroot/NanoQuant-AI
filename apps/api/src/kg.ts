/**
 * Knowledge Graph 1단계 — 부록 C
 * 노드: Indicator, Skill, Decision. 엣지: used_in, composes.
 * C-2: SQLite 영속성 — initFromDb() 로드, add 시 write-through.
 */
import * as db from "./db.js";

interface Node {
  id: string;
  type: "indicator" | "skill" | "decision";
  data: Record<string, unknown>;
}

const nodes = new Map<string, Node>();
const edges: { from_id: string; to_id: string; type: string }[] = [];

/** 서버 기동 시 DB에서 노드·엣지 로드 (db.initDb() 이후 호출) */
export function initFromDb(): void {
  if (!db.isDbEnabled()) return;
  nodes.clear();
  edges.length = 0;
  try {
    for (const row of db.loadKgNodes()) {
      let data: Record<string, unknown> = {};
      try {
        data = (JSON.parse(row.data) as Record<string, unknown>) ?? {};
      } catch {}
      nodes.set(row.id, { id: row.id, type: row.type as Node["type"], data });
    }
    for (const row of db.loadKgEdges()) {
      edges.push({ from_id: row.from_id, to_id: row.to_id, type: row.type });
    }
  } catch (e) {
    console.warn("KG load from DB failed:", e);
  }
}

export function addNode(
  id: string,
  type: Node["type"],
  data: Record<string, unknown>
): void {
  const payload = data ?? {};
  nodes.set(id, { id, type, data: payload });
  if (db.isDbEnabled()) db.insertKgNode(id, type, payload);
}

export function addEdge(fromId: string, toId: string, edgeType: string): void {
  if (nodes.has(fromId) && nodes.has(toId)) {
    edges.push({ from_id: fromId, to_id: toId, type: edgeType });
    if (db.isDbEnabled()) db.insertKgEdge(fromId, toId, edgeType);
  }
}

export function ensureSkill(name: string, description = ""): string {
  const id = `skill:${name}`;
  if (!nodes.has(id)) addNode(id, "skill", { name, description });
  return id;
}

export function addSkillUse(
  sessionId: string,
  skillName: string,
  args: Record<string, unknown>,
  resultSummary = "",
  error?: string
): string {
  const id = `decision:${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
  addNode(id, "decision", {
    session_id: sessionId,
    skill_name: skillName,
    args,
    result_summary: String(resultSummary).slice(0, 500),
    error,
    timestamp: Date.now() / 1000,
  });
  const skillId = ensureSkill(skillName);
  addEdge(id, skillId, "used_in");
  return id;
}

export function getRecentDecisions(limit = 50): Record<string, unknown>[] {
  const list = Array.from(nodes.values())
    .filter((n) => n.type === "decision")
    .sort(
      (a, b) =>
        (b.data.timestamp as number) - (a.data.timestamp as number)
    )
    .slice(0, limit);
  return list.map((n) => ({ id: n.id, ...n.data }));
}

/** 뷰어용: 노드·엣지 일괄 (docs/menu/kg/03-api) */
export function getGraph(): {
  nodes: { id: string; type: string; data: Record<string, unknown> }[];
  edges: { from_id: string; to_id: string; type: string }[];
} {
  const nodeList = Array.from(nodes.values()).map((n) => ({
    id: n.id,
    type: n.type,
    data: n.data,
  }));
  return { nodes: nodeList, edges: [...edges] };
}

/** 단일 Decision 상세 (docs/menu/kg/06) */
export function getDecisionById(id: string): Record<string, unknown> | null {
  const node = nodes.get(id);
  if (!node || node.type !== "decision") return null;
  return { id: node.id, ...node.data };
}

/** Skill 노드 목록 (뷰어·통계) */
export function getSkills(): { id: string; name: string; description?: string }[] {
  return Array.from(nodes.values())
    .filter((n) => n.type === "skill")
    .map((n) => ({
      id: n.id,
      name: String(n.data.name ?? ""),
      description: n.data.description != null ? String(n.data.description) : undefined,
    }));
}

/** 타입·기간 필터 노드 목록 (뷰어 필터·페이지네이션) */
export function getNodes(options: {
  type?: string;
  fromTs?: number;
  toTs?: number;
  limit?: number;
}): { id: string; type: string; data: Record<string, unknown> }[] {
  let list = Array.from(nodes.values());
  if (options.type) {
    list = list.filter((n) => n.type === options.type);
  }
  if (options.fromTs != null || options.toTs != null) {
    list = list.filter((n) => {
      const ts = n.data.timestamp as number | undefined;
      if (ts == null) return n.type !== "decision";
      if (options.fromTs != null && ts < options.fromTs) return false;
      if (options.toTs != null && ts > options.toTs) return false;
      return true;
    });
  }
  list.sort((a, b) => {
    const ta = (a.data.timestamp as number) ?? 0;
    const tb = (b.data.timestamp as number) ?? 0;
    return tb - ta;
  });
  const limit = Math.min(200, Math.max(1, options.limit ?? 50));
  return list.slice(0, limit).map((n) => ({ id: n.id, type: n.type, data: n.data }));
}
