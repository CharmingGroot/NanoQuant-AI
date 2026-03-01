/**
 * API routes — 채팅, 승인, 스킬 목록, KG
 */
import express, { type Request, type Response } from "express";
import { z } from "zod";
import * as gateway from "./gateway.js";
import * as sessionStore from "./sessionStore.js";
import * as hitlStore from "./hitlStore.js";
import * as kg from "./kg.js";
import { complete, type ModelKind } from "./llm.js";
import { runReact } from "./react.js";
import "./skills/index.js";
import { registry, HITL_SKILLS } from "./skills/index.js";
import * as history from "./data/history.js";
import { runBacktest } from "./backtest/engine.js";
import * as db from "./db.js";
import { v4 as uuidv4 } from "uuid";

const router: express.Router = express.Router();

const BACKTEST_SERVICE_URL = process.env.BACKTEST_SERVICE_URL ?? "";

async function proxyBacktest(body: { start_date: string; end_date: string; symbols: string[]; strategy: { type: string; params: Record<string, number> } }): Promise<Record<string, unknown> | null> {
  if (!BACKTEST_SERVICE_URL) return null;
  try {
    const base = BACKTEST_SERVICE_URL.replace(/\/$/, "");
    const res = await fetch(`${base}/backtest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) return null;
    return (await res.json()) as Record<string, unknown>;
  } catch {
    return null;
  }
}

async function proxyHistory(symbol: string, start: string, end: string, interval: string): Promise<{ symbol: string; interval: string; rows: unknown[] } | null> {
  if (!BACKTEST_SERVICE_URL) return null;
  try {
    const base = BACKTEST_SERVICE_URL.replace(/\/$/, "");
    const params = new URLSearchParams({ symbol, start, end, interval: interval === "d" ? "1d" : interval });
    const res = await fetch(`${base}/history?${params}`);
    if (!res.ok) return null;
    return (await res.json()) as { symbol: string; interval: string; rows: unknown[] };
  } catch {
    return null;
  }
}

router.get("/health", (_req: Request, res: Response) => {
  res.json({ status: "ok", service: "nanoquant-api" });
});

const chatBody = z.object({
  content: z.string().min(1),
  session_id: z.string().optional().nullable(),
  api_key: z.string().optional(),
  model: z.enum(["claude", "gpt"]).optional(),
  force_skill: z.string().optional(),
});

router.post("/chat", async (req: Request, res: Response) => {
  try {
    const parsed = chatBody.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: "content is required" });
    }
    const { content, session_id, api_key, model, force_skill } = parsed.data;

    const sessionId = gateway.getOrCreateSession(session_id);
    gateway.appendUserTurn(sessionId, content);

    const history = gateway.getHistoryForControl(sessionId);

    const llm = (prompt: string) =>
      complete(prompt, (model as ModelKind) ?? "claude", api_key);

    const { content: responseText, tool_calls } = await runReact(
      content,
      history,
      { llm, forceSkill: force_skill ?? undefined }
    );

    gateway.appendAssistantTurn(sessionId, responseText, tool_calls);

    for (const tc of tool_calls) {
      if (tc.hitl_required && tc.hitl_id) {
        hitlStore.add(tc.hitl_id, sessionId, tc.skill, tc.args ?? {});
      }
    }

    for (const tc of tool_calls) {
      if (tc.hitl_required) continue;
      kg.addSkillUse(
        sessionId,
        tc.skill,
        tc.args ?? {},
        tc.result_preview ?? "",
        tc.error
      );
    }

    return res.json({
      content: responseText,
      session_id: sessionId,
      tool_calls,
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return res.status(500).json({ error: msg });
  }
});

const approveBody = z.object({
  session_id: z.string().optional(),
  hitl_id: z.string().min(1),
  approved: z.boolean(),
});

router.post("/approve", async (req: Request, res: Response) => {
  try {
    const parsed = approveBody.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: "hitl_id is required" });
    }
    const { hitl_id, session_id, approved } = parsed.data;

    const pending = hitlStore.pop(hitl_id);
    if (!pending) {
      return res
        .status(404)
        .json({
          error: "Unknown or expired hitl_id",
          content: "해당 승인 요청을 찾을 수 없거나 만료되었습니다.",
        });
    }

    if (session_id && pending.session_id !== session_id) {
      return res.status(400).json({ error: "session_id mismatch" });
    }

    if (!approved) {
      return res.json({
        content: "취소되었습니다.",
        approved: false,
        skill: pending.skill_name,
      });
    }

    try {
      const result = await registry.run(pending.skill_name, pending.args);
      const resultStr =
        typeof result === "object" ? JSON.stringify(result) : String(result);
      kg.addSkillUse(
        pending.session_id,
        pending.skill_name,
        pending.args,
        resultStr.slice(0, 500),
        undefined
      );
      return res.json({
        content: `실행 완료: ${pending.skill_name} → ${resultStr.slice(0, 200)}`,
        approved: true,
        skill: pending.skill_name,
        result_preview: resultStr.slice(0, 500),
      });
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : String(e);
      return res.json({
        content: `실행 실패: ${errMsg}`,
        approved: true,
        skill: pending.skill_name,
        error: errMsg,
      });
    }
  } catch (e) {
    return res.status(500).json({
      error: e instanceof Error ? e.message : String(e),
    });
  }
});

router.get("/skills", (_req: Request, res: Response) => {
  const skills = registry.listSkills();
  return res.json({ skills, hitl_skills: Array.from(HITL_SKILLS) });
});

router.get("/kg/recent", (req: Request, res: Response) => {
  const limit = Math.min(100, Math.max(1, Number(req.query.limit) || 20));
  const decisions = kg.getRecentDecisions(limit);
  return res.json({ decisions });
});

router.get("/sessions", (_req: Request, res: Response) => {
  const sessions = sessionStore.listSessions();
  return res.json({ sessions });
});

const newSessionBody = z.object({
  title: z.string().max(120).optional(),
});

router.post("/sessions", (req: Request, res: Response) => {
  const parsed = newSessionBody.safeParse(req.body ?? {});
  const title = parsed.success ? parsed.data.title : undefined;
  const sessionId = sessionStore.createSession(title);
  return res.status(201).json({ session_id: sessionId });
});

router.get("/sessions/:id", (req: Request, res: Response) => {
  const id = String(req.params.id ?? "").trim();
  if (!id) return res.status(400).json({ error: "session id required" });
  if (!sessionStore.exists(id))
    return res.status(404).json({ error: "session not found" });
  const meta = sessionStore.getSessionMeta(id);
  const history = sessionStore.getHistory(id);
  return res.json({
    session_id: id,
    title: meta?.title ?? "새 대화",
    updated_at: meta?.updated_at ?? 0,
    history,
  });
});

router.delete("/sessions/:id", (req: Request, res: Response) => {
  const id = String(req.params.id ?? "").trim();
  if (!id) return res.status(400).json({ error: "session id required" });
  const deleted = sessionStore.deleteSession(id);
  if (!deleted) return res.status(404).json({ error: "session not found" });
  return res.json({ ok: true });
});

const patchSessionBody = z.object({
  title: z.string().max(120).optional(),
});

router.patch("/sessions/:id", (req: Request, res: Response) => {
  const id = String(req.params.id ?? "").trim();
  if (!id) return res.status(400).json({ error: "session id required" });
  if (!sessionStore.exists(id))
    return res.status(404).json({ error: "session not found" });
  const parsed = patchSessionBody.safeParse(req.body ?? {});
  const title = parsed.success ? parsed.data.title : undefined;
  if (title === undefined) return res.status(400).json({ error: "title required" });
  sessionStore.updateSessionTitle(id, title);
  return res.json({ ok: true });
});

router.get("/portfolio", (_req: Request, res: Response) => {
  // 스텁: 연동 시 get_portfolio 스킬 또는 DB 조회
  return res.json({
    total_asset: 0,
    cash: 0,
    positions: [],
    pnl_today: 0,
    updated_at: Date.now() / 1000,
  });
});

router.get("/kg/graph", (_req: Request, res: Response) => {
  const graph = kg.getGraph();
  return res.json(graph);
});

router.get("/kg/decisions/:id", (req: Request, res: Response) => {
  const id = String(req.params.id ?? "").trim();
  if (!id) return res.status(400).json({ error: "decision id required" });
  const decision = kg.getDecisionById(id);
  if (!decision) return res.status(404).json({ error: "decision not found" });
  return res.json(decision);
});

router.get("/kg/skills", (_req: Request, res: Response) => {
  const skills = kg.getSkills();
  return res.json({ skills });
});

router.get("/kg/nodes", (req: Request, res: Response) => {
  const type = req.query.type as string | undefined;
  const from = req.query.from as string | undefined;
  const to = req.query.to as string | undefined;
  const limit = Number(req.query.limit) || 50;
  const fromTs = from ? Math.floor(new Date(from).getTime() / 1000) : undefined;
  const toTs = to ? Math.floor(new Date(to).getTime() / 1000) : undefined;
  const nodes = kg.getNodes({ type, fromTs, toTs, limit });
  return res.json({ nodes });
});

router.get("/data/history", async (req: Request, res: Response) => {
  const symbol = (req.query.symbol as string) || "AAPL";
  const start = (req.query.start as string) || new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const end = (req.query.end as string) || new Date().toISOString().slice(0, 10);
  const interval = (req.query.interval as string) || "d";
  try {
    const proxied = await proxyHistory(symbol, start, end, interval);
    if (proxied) return res.json(proxied);
    const rows = await history.getHistory(symbol, start, end, interval);
    return res.json({ symbol, interval, rows });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return res.status(500).json({ error: msg });
  }
});

const backtestBody = z.object({
  start_date: z.string().optional(),
  end_date: z.string().optional(),
  symbols: z.array(z.string()).optional(),
  strategy: z.object({
    type: z.string().optional(),
    params: z.record(z.unknown()).optional(),
  }).optional(),
});

router.post("/backtest", async (req: Request, res: Response) => {
  const parsed = backtestBody.safeParse(req.body ?? {});
  const body = parsed.success ? parsed.data : {};
  const start = body.start_date ?? new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const end = body.end_date ?? new Date().toISOString().slice(0, 10);
  const symbols = body.symbols?.length ? body.symbols : ["AAPL"];
  const strat = body.strategy ?? {};
  const rsiTypes = ["rsi_30_70", "rsi_25_75", "rsi_20_80"];
  const type = (strat.type && rsiTypes.includes(strat.type as string)) ? "rsi_threshold" : (strat.type ?? "rsi_threshold");
  const params: Record<string, number> = { period: 14, buy_below: 30, sell_above: 70 };
  if (strat.params && typeof strat.params === "object") {
    if (typeof (strat.params as Record<string, unknown>).period === "number") params.period = (strat.params as Record<string, number>).period;
    if (typeof (strat.params as Record<string, unknown>).buy_below === "number") params.buy_below = (strat.params as Record<string, number>).buy_below;
    if (typeof (strat.params as Record<string, unknown>).sell_above === "number") params.sell_above = (strat.params as Record<string, number>).sell_above;
  }
  try {
    const payload = { start_date: start, end_date: end, symbols, strategy: { type, params } };
    const proxied = await proxyBacktest(payload);
    const result = proxied ?? await runBacktest({
      start_date: start,
      end_date: end,
      symbols,
      strategy: { type, params },
    });
    const runId = uuidv4();
    if (db.isDbEnabled()) {
      db.insertBacktestRun(
        runId,
        {
          start_date: start,
          end_date: end,
          symbols,
          strategy_type: body.strategy?.type ?? "rsi_threshold",
          strategy_params: params,
        },
        result
      );
    }
    return res.json({ ...result, run_id: runId });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return res.status(500).json({ error: msg, total_return_pct: 0, trade_count: 0, trades: [] });
  }
});

router.get("/backtest/runs", (_req: Request, res: Response) => {
  const limit = Math.min(50, Math.max(1, Number(_req.query.limit) || 20));
  const runs = db.getBacktestRuns(limit);
  return res.json({ runs });
});

router.get("/backtest/runs/:id", (req: Request, res: Response) => {
  const id = String(req.params.id ?? "").trim();
  if (!id) return res.status(400).json({ error: "run id required" });
  const run = db.getBacktestRunById(id);
  if (!run) return res.status(404).json({ error: "run not found" });
  let result_json: { equity_curve?: number[]; trades?: unknown[] } = {};
  try {
    if (run.result_json) result_json = JSON.parse(run.result_json) as { equity_curve?: number[]; trades?: unknown[] };
  } catch {}
  return res.json({
    id: run.id,
    start_date: run.start_date,
    end_date: run.end_date,
    symbols: JSON.parse(run.symbols) as string[],
    strategy_type: run.strategy_type,
    strategy_params: run.strategy_params ? (JSON.parse(run.strategy_params) as Record<string, unknown>) : null,
    total_return_pct: run.total_return_pct,
    annualized_return_pct: run.annualized_return_pct,
    max_drawdown_pct: run.max_drawdown_pct,
    trade_count: run.trade_count,
    win_rate: run.win_rate,
    equity_curve: result_json.equity_curve,
    trades: result_json.trades,
    created_at: run.created_at,
  });
});

export default router;
