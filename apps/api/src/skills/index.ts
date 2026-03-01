/**
 * Built-in skills (퀀트·조회). 기획서: get_rsi, scan_candidates, get_portfolio, summarize_scan 등
 * 1단계: 간단한 스텁/목 데이터. 퀀트 연산은 추후 Python 호출 또는 TS 이식.
 * 백테스트: run_backtest — 툴화되어 채팅에서 에이전트가 호출 가능.
 */
import * as registry from "./registry.js";
import { runBacktest } from "../backtest/engine.js";

// 스텁: RSI 조회 (실제로는 yfinance 등 연동)
registry.register(
  "get_rsi_for_ticker",
  "Get RSI for a ticker (default 14 period). Returns number or null.",
  { ticker: "string", period: "number" },
  async (args) => {
    const ticker = String(args?.ticker ?? "").toUpperCase();
    if (!ticker) return { error: "ticker required" };
    // Stub: 실제 구현 시 API 또는 Python 자식 프로세스 호출
    return { ticker, rsi: 45.2, period: Number(args?.period) || 14 };
  }
);

registry.register(
  "get_current_price",
  "Get current price for a ticker. Returns number or null.",
  { ticker: "string" },
  async (args) => {
    const ticker = String(args?.ticker ?? "").toUpperCase();
    if (!ticker) return null;
    return { ticker, price: 12.34 };
  }
);

registry.register(
  "list_skills_meta",
  "List available skills (name, description, params). For agent self-awareness.",
  {},
  async () => {
    return registry.listSkills();
  }
);

/** 백테스트 툴 — 기간·종목·전략으로 과거 수익률·MDD·거래 수 등 반환. 채팅에서 "백테스트 해줘" 요청 시 호출. */
registry.register(
  "run_backtest",
  "Run a backtest for the given period and symbol(s) with RSI threshold strategy. Returns total return %, max drawdown %, trade count, win rate, and a short summary. Use when the user asks to backtest or evaluate a strategy over historical data.",
  {
    start_date: "string",
    end_date: "string",
    symbols: "string",
    strategy_type: "string",
    period: "number",
    buy_below: "number",
    sell_above: "number",
  },
  async (args) => {
    const start = String(args?.start_date ?? "").trim() || new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    const end = String(args?.end_date ?? "").trim() || new Date().toISOString().slice(0, 10);
    const symbolsRaw = args?.symbols;
    const symbols = Array.isArray(symbolsRaw)
      ? (symbolsRaw as string[]).map((s) => String(s).trim().toUpperCase()).filter(Boolean)
      : String(symbolsRaw ?? "AAPL")
          .split(/[\s,]+/)
          .map((s) => s.trim().toUpperCase())
          .filter(Boolean);
    if (symbols.length === 0) symbols.push("AAPL");
    const strategyType = String(args?.strategy_type ?? "rsi_threshold").trim() || "rsi_threshold";
    const period = Math.max(2, Number(args?.period) || 14);
    const buyBelow = Number(args?.buy_below) ?? 30;
    const sellAbove = Number(args?.sell_above) ?? 70;

    const result = await runBacktest({
      start_date: start,
      end_date: end,
      symbols,
      strategy: {
        type: strategyType === "rsi_30_70" ? "rsi_threshold" : strategyType,
        params: { period, buy_below: buyBelow, sell_above: sellAbove },
      },
    });

    const summary =
      `백테스트 결과 (${start} ~ ${end}, ${symbols.join(", ")}): ` +
      `총 수익률 ${result.total_return_pct}%, 연환산 ${result.annualized_return_pct}%, ` +
      `최대 낙폭 ${result.max_drawdown_pct}%, 거래 ${result.trade_count}회, 승률 ${(result.win_rate * 100).toFixed(1)}%.`;

    return {
      ...result,
      summary,
      message: summary,
    };
  }
);

export const HITL_SKILLS = new Set<string>(); // 실제 매매 등록 시 추가
export { registry };
