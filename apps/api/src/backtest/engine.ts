/**
 * 백테스트 엔진 1단계 — RSI 임계값 전략 (docs/menu/backtest/05)
 */
import * as history from "../data/history.js";

export interface BacktestParams {
  start_date: string;
  end_date: string;
  symbols: string[];
  strategy: { type: string; params?: Record<string, number> };
  initial_capital?: number;
  commission_pct?: number;
}

export interface Trade {
  date: string;
  symbol: string;
  side: "buy" | "sell";
  price: number;
  quantity: number;
  pnl?: number;
  pnl_pct?: number;
}

export interface BacktestResult {
  total_return_pct: number;
  annualized_return_pct: number;
  max_drawdown_pct: number;
  trade_count: number;
  win_rate: number;
  equity_curve: number[];
  trades: Trade[];
  start_date: string;
  end_date: string;
}

const DEFAULT_CAPITAL = 1_000_000;
const DEFAULT_COMMISSION = 0;

export async function runBacktest(params: BacktestParams): Promise<BacktestResult> {
  const { start_date, end_date, symbols, strategy } = params;
  const symbol = symbols?.[0] ?? "AAPL";
  const initialCapital = params.initial_capital ?? DEFAULT_CAPITAL;
  const commissionPct = params.commission_pct ?? DEFAULT_COMMISSION;

  const rows = await history.getHistory(symbol, start_date, end_date);
  if (rows.length === 0) {
    return {
      total_return_pct: 0,
      annualized_return_pct: 0,
      max_drawdown_pct: 0,
      trade_count: 0,
      win_rate: 0,
      equity_curve: [],
      trades: [],
      start_date,
      end_date,
    };
  }

  const type = (strategy?.type as string) || "rsi_threshold";
  const p = strategy?.params ?? {};
  const period = Math.max(2, Number(p.period) || 14);
  const buyBelow = Number(p.buy_below) ?? 30;
  const sellAbove = Number(p.sell_above) ?? 70;

  const closes = rows.map((r) => r.close);
  const rsiValues = history.computeRSI(closes, period);

  const trades: Trade[] = [];
  let position = 0;
  let entryPrice = 0;
  let cash = initialCapital;
  let equity = initialCapital;
  const equityCurve: number[] = [];

  for (let i = 0; i < rows.length; i++) {
    const row = rows[i]!;
    const rsi = rsiValues[i];
    const price = row.close;

    if (rsi == null) {
      equityCurve.push(equity / initialCapital);
      continue;
    }

    if (position === 0 && rsi < buyBelow) {
      const cost = price * (1 + commissionPct / 100);
      const qty = Math.floor(cash / cost);
      if (qty > 0) {
        position = qty;
        entryPrice = price;
        cash -= cost * qty;
        trades.push({ date: row.date, symbol, side: "buy", price, quantity: qty });
      }
    } else if (position > 0 && rsi > sellAbove) {
      const proceeds = price * (1 - commissionPct / 100) * position;
      const pnl = (price - entryPrice) * position;
      const pnlPct = (price / entryPrice - 1) * 100;
      cash += proceeds;
      trades.push({
        date: row.date,
        symbol,
        side: "sell",
        price,
        quantity: position,
        pnl: Math.round(pnl * 100) / 100,
        pnl_pct: Math.round(pnlPct * 100) / 100,
      });
      position = 0;
    }

    equity = cash + position * price;
    equityCurve.push(equity / initialCapital);
  }

  const finalEquity = cash + position * (rows[rows.length - 1]!.close);
  const totalReturnPct = (finalEquity / initialCapital - 1) * 100;

  let peak = 1;
  let maxDrawdownPct = 0;
  for (const e of equityCurve) {
    if (e > peak) peak = e;
    const dd = (1 - e / peak) * 100;
    if (dd > maxDrawdownPct) maxDrawdownPct = dd;
  }

  const days = rows.length;
  const years = Math.max(0.001, days / 365);
  const annualizedReturnPct = (Math.pow(finalEquity / initialCapital, 1 / years) - 1) * 100;

  const sellTrades = trades.filter((t) => t.side === "sell" && t.pnl != null);
  const wins = sellTrades.filter((t) => (t.pnl ?? 0) > 0).length;
  const winRate = sellTrades.length > 0 ? wins / sellTrades.length : 0;

  return {
    total_return_pct: Math.round(totalReturnPct * 100) / 100,
    annualized_return_pct: Math.round(annualizedReturnPct * 100) / 100,
    max_drawdown_pct: Math.round(maxDrawdownPct * 100) / 100,
    trade_count: trades.length,
    win_rate: Math.round(winRate * 100) / 100,
    equity_curve: equityCurve.map((x) => Math.round(x * 1e6) / 1e6),
    trades,
    start_date,
    end_date,
  };
}
