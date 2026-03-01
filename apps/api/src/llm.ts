/**
 * LLM 호출 — Claude 또는 OpenAI. 기획서: API 직접 호출 유지.
 */
const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

export type ModelKind = "claude" | "gpt";

export async function complete(
  prompt: string,
  model: ModelKind = "claude",
  apiKey?: string
): Promise<string> {
  const key = apiKey ?? (model === "claude" ? ANTHROPIC_API_KEY : OPENAI_API_KEY);
  if (!key) {
    throw new Error(
      model === "claude"
        ? "ANTHROPIC_API_KEY not set. Set in .env or pass api_key in request."
        : "OPENAI_API_KEY not set."
    );
  }

  if (model === "claude") {
    return callClaude(prompt, key);
  }
  return callOpenAI(prompt, key);
}

async function callClaude(prompt: string, apiKey: string): Promise<string> {
  try {
    const { Anthropic } = await import("@anthropic-ai/sdk");
    const client = new Anthropic({ apiKey });
    const msg = await client.messages.create({
      model: "claude-sonnet-4-20250514",
      max_tokens: 2048,
      messages: [{ role: "user", content: prompt }],
    });
    const text = msg.content
      .filter((c): c is { type: "text"; text: string } => c.type === "text")
      .map((c) => c.text)
      .join("");
    return text || "";
  } catch (e) {
    throw new Error(`Claude API error: ${e instanceof Error ? e.message : String(e)}`);
  }
}

async function callOpenAI(prompt: string, apiKey: string): Promise<string> {
  const res = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      messages: [{ role: "user", content: prompt }],
      max_tokens: 2048,
    }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(`OpenAI API error: ${res.status} ${t}`);
  }
  const j = (await res.json()) as { choices?: { message?: { content?: string } }[] };
  return j.choices?.[0]?.message?.content ?? "";
}
