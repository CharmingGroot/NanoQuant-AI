/**
 * Control Layer — ReAct 루프 (DAG 없음)
 * Reason(LLM: 가용 Skills 메타정보만 보고 스킬명+인자 JSON 도출) → Act → Observe → 반복
 * 부록 A: 동일 (skill, args) 3회 실패 시 스킵.
 */
import type { Turn, ToolCallResult } from "./types.js";
import * as registry from "./skills/registry.js";
import { HITL_SKILLS } from "./skills/index.js";
import * as kg from "./kg.js";
import type { ModelKind } from "./llm.js";

const MAX_STEPS = 10;

function extractJson(text: string): Record<string, unknown> | null {
  const m = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
  const raw = m ? m[1].trim() : text;
  const obj = raw.match(/\{[\s\S]*\}/);
  if (!obj) return null;
  try {
    return JSON.parse(obj[0]) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function buildPrompt(
  userMessage: string,
  history: Turn[],
  skillsDesc: string,
  observations: string[],
  forceSkill?: string
): string {
  const lines = [
    "You are a quant trading assistant. You have access to skills (tools).",
    "Respond ONLY with a single JSON object, no other text.",
    "",
  ];
  if (forceSkill) {
    lines.push(
      `The user requested to use the skill "${forceSkill}" for this query. Prefer calling this skill (with appropriate args) when answering.`,
      ""
    );
  }
  lines.push(
    "Format 1 - Call a skill:",
    '{"thought": "brief reasoning", "action": "call", "skill": "<skill_name>", "args": {<key-value pairs>}}',
    "",
    "Format 2 - Give final answer:",
    '{"thought": "brief reasoning", "action": "answer", "content": "<your response in Korean or English>"}',
    "",
    "Available skills (metadata only; you decide, then the system will execute):",
    skillsDesc,
    "",
  );
  const recentDecisions = kg.getRecentDecisions(5);
  if (recentDecisions.length > 0) {
    lines.push("Recent agent decisions (for context):");
    recentDecisions.forEach((d, i) => {
      const skill = String((d as Record<string, unknown>).skill_name ?? "—");
      const summary = String((d as Record<string, unknown>).result_summary ?? "").slice(0, 120);
      lines.push(`${i + 1}. ${skill}: ${summary}`);
    });
    lines.push("");
  }
  lines.push("User message:", userMessage, "");
  if (history.length) {
    lines.push("Recent conversation:");
    history.slice(-10).forEach((t) => {
      lines.push(`- ${t.role}: ${(t.content || "").slice(0, 500)}`);
    });
    lines.push("");
  }
  if (observations.length) {
    lines.push("Observations (results from your last skill calls):");
    observations.slice(-3).forEach((o, i) => {
      lines.push(`${i + 1}. ${String(o).slice(0, 1500)}`);
    });
    lines.push("");
  }
  lines.push("Respond with exactly one JSON object:");
  return lines.join("\n");
}

export interface ReactOptions {
  llm: (prompt: string) => Promise<string>;
  maxSteps?: number;
  apiKey?: string;
  model?: ModelKind;
  forceSkill?: string;
}

export async function runReact(
  userMessage: string,
  history: Turn[],
  options: ReactOptions
): Promise<{ content: string; tool_calls: ToolCallResult[] }> {
  const { llm, maxSteps = MAX_STEPS, forceSkill } = options;
  const skillsList = registry.listSkills();
  const skillsDesc = skillsList
    .map(
      (s) =>
        `- ${s.name}: ${s.description} | params: ${JSON.stringify(s.params_schema)}`
    )
    .join("\n");

  const observations: string[] = [];
  const toolCalls: ToolCallResult[] = [];
  const retryFailures = new Map<string, number>();

  for (let step = 0; step < maxSteps; step++) {
    const prompt = buildPrompt(userMessage, history, skillsDesc, observations, forceSkill);
    const response = await llm(prompt);
    const parsed = extractJson(response);

    if (!parsed) {
      return {
        content: response.trim() || "응답을 생성하지 못했습니다.",
        tool_calls: toolCalls,
      };
    }

    const action = (parsed.action ?? parsed.Action) as string | undefined;
    if (action === "answer") {
      const content = (parsed.content ?? parsed.Content ?? "") as string;
      return { content: content.trim(), tool_calls: toolCalls };
    }

    if (action === "call") {
      const skillName = (parsed.skill ?? parsed.Skill ?? "") as string;
      const args = (parsed.args ?? parsed.Args ?? {}) as Record<string, unknown>;
      if (!skillName) {
        observations.push("Error: skill name missing in JSON.");
        continue;
      }

      const argsKey = `${skillName}:${JSON.stringify(args)}`;
      if ((retryFailures.get(argsKey) ?? 0) >= 3) {
        observations.push(
          `[Reflection] ${skillName} has failed 3 times for this task. Manual check recommended.`
        );
        continue;
      }

      if (HITL_SKILLS.has(skillName)) {
        const hitlId = crypto.randomUUID().slice(0, 12);
        observations.push(
          `[HITL] ${skillName} requires user approval (hitl_id=${hitlId}). Not executed.`
        );
        toolCalls.push({
          skill: skillName,
          args,
          hitl_required: true,
          hitl_id: hitlId,
        });
        continue;
      }

      try {
        const result = await registry.run(skillName, args);
        retryFailures.set(argsKey, 0);
        const obsStr =
          typeof result === "object"
            ? JSON.stringify(result)
            : String(result);
        observations.push(
          obsStr.length > 2000 ? obsStr.slice(0, 2000) + "...(truncated)" : obsStr
        );
        toolCalls.push({
          skill: skillName,
          args,
          result_preview: obsStr.slice(0, 200),
        });
      } catch (e) {
        const errMsg = e instanceof Error ? e.message : String(e);
        retryFailures.set(argsKey, (retryFailures.get(argsKey) ?? 0) + 1);
        observations.push(`Error: ${errMsg}`);
        toolCalls.push({ skill: skillName, args, error: errMsg });
      }
      continue;
    }

    observations.push(`Unknown action: ${action}. Use "call" or "answer".`);
  }

  return {
    content: "최대 단계에 도달했습니다. 요약할 수 있는 결과를 바탕으로 답변해 주세요.",
    tool_calls: toolCalls,
  };
}
