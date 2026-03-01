/**
 * 백테스트 탭 — docs/menu/backtest
 * 기간·종목·전략 입력 폼, 실행, 결과 요약·거래 내역·수익 곡선(스텁)
 */
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

const API = "/agent";

/** 종목 빠른 선택용 프리셋 */
const PRESET_SYMBOLS = ["AAPL", "MSFT", "SOFI", "SPY", "QQQ", "NVDA", "GOOGL"];

/** 종목 선택 시 자동으로 돌릴 전략들 (사용자는 전략을 고르지 않음) */
const STRATEGY_PRESETS = [
  { id: "rsi_30_70", label: "RSI 30/70", params: { period: 14, buy_below: 30, sell_above: 70 } },
  { id: "rsi_25_75", label: "RSI 25/75", params: { period: 14, buy_below: 25, sell_above: 75 } },
  { id: "rsi_20_80", label: "RSI 20/80", params: { period: 14, buy_below: 20, sell_above: 80 } },
];

interface SingleResult {
  symbol: string;
  strategyId: string;
  strategyLabel: string;
  total_return_pct?: number;
  annualized_return_pct?: number;
  max_drawdown_pct?: number;
  trade_count?: number;
  win_rate?: number;
  message?: string;
  trades?: unknown[];
  equity_curve?: number[];
}

@customElement("backtest-tab")
export class BacktestTab extends LitElement {
  static styles = css`
    .section-title {
      font-size: 1.125rem;
      font-weight: 600;
      color: var(--nq-title);
      margin: 0 0 16px 0;
    }
    .form-card {
      background: var(--nq-surface);
      border: 1px solid var(--nq-border);
      border-radius: var(--nq-radius);
      padding: 20px;
      margin-bottom: 24px;
    }
    .form-row {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      align-items: flex-end;
      margin-bottom: 12px;
    }
    .form-row:last-child { margin-bottom: 0; }
    label {
      display: flex;
      flex-direction: column;
      gap: 4px;
      font-size: 0.8125rem;
      color: var(--nq-text-muted);
    }
    input, select {
      padding: 8px 12px;
      background: var(--nq-bg);
      border: 1px solid var(--nq-border);
      border-radius: var(--nq-radius-sm);
      color: var(--nq-text);
      font-size: 0.875rem;
      min-width: 140px;
    }
    .btn-run {
      padding: 10px 20px;
      background: var(--nq-accent);
      color: #fff;
      border: none;
      border-radius: var(--nq-radius-sm);
      font-weight: 600;
      font-size: 0.9375rem;
      cursor: pointer;
    }
    .btn-run:hover:not(:disabled) { opacity: 0.9; }
    .btn-run:disabled { opacity: 0.6; cursor: not-allowed; }
    .result-card {
      background: var(--nq-surface);
      border: 1px solid var(--nq-border);
      border-radius: var(--nq-radius);
      padding: 20px;
      margin-bottom: 20px;
    }
    .result-cards {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }
    .result-cards .val { font-size: 1.25rem; font-weight: 700; color: var(--nq-text); }
    .result-cards .label { font-size: 0.75rem; color: var(--nq-text-muted); }
    .meta { font-size: 0.8125rem; color: var(--nq-text-muted); margin: 8px 0 0 0; }
    .equity-chart {
      width: 100%;
      height: 200px;
      margin: 16px 0;
      background: var(--nq-bg);
      border: 1px solid var(--nq-border);
      border-radius: var(--nq-radius-sm);
    }
    .equity-chart-title { font-size: 0.8125rem; color: var(--nq-text-muted); margin-bottom: 8px; }
    table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
    th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--nq-border); }
    th { color: var(--nq-text-muted); font-weight: 500; }
    .runs-card { margin-top: 24px; }
    .run-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 12px;
      margin-bottom: 6px;
      background: var(--nq-bg);
      border: 1px solid var(--nq-border);
      border-radius: var(--nq-radius-sm);
      cursor: pointer;
      font-size: 0.8125rem;
      transition: background 0.15s, border-color 0.15s;
    }
    .run-item:hover { background: var(--nq-surface-hover); border-color: var(--nq-accent); }
    .run-item .range { color: var(--nq-text-muted); }
    .run-item .pct { font-weight: 600; color: var(--nq-text); }
    .symbol-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
    }
    .symbol-chip {
      padding: 6px 12px;
      border-radius: var(--nq-radius-sm);
      font-size: 0.8125rem;
      font-weight: 500;
      cursor: pointer;
      border: 1px solid var(--nq-border);
      background: var(--nq-bg);
      color: var(--nq-text-muted);
      transition: background 0.15s, border-color 0.15s, color 0.15s;
    }
    .symbol-chip:hover { background: var(--nq-surface-hover); color: var(--nq-text); }
    .symbol-chip.selected { border-color: var(--nq-accent); background: rgba(56, 139, 253, 0.12); color: var(--nq-accent); }
    .custom-symbol-wrap { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
    .custom-symbol-wrap input { min-width: 100px; }
    .result-mini {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 12px;
      margin-bottom: 6px;
      background: var(--nq-bg);
      border: 1px solid var(--nq-border);
      border-radius: var(--nq-radius-sm);
      cursor: pointer;
      font-size: 0.8125rem;
      transition: background 0.15s, border-color 0.15s;
    }
    .result-mini:hover { background: var(--nq-surface-hover); }
    .result-mini.active { border-color: var(--nq-accent); background: rgba(56, 139, 253, 0.08); }
    .result-mini .title { font-weight: 600; color: var(--nq-text); }
    .result-mini .pct { font-weight: 600; color: var(--nq-success); }
    .result-mini .pct.negative { color: var(--nq-danger); }
  `;

  @state() private startDate = "";
  @state() private endDate = "";
  /** 선택된 종목 (칩 클릭으로 토글, 기본 1개) */
  @state() private selectedSymbols: string[] = ["AAPL"];
  /** 직접 입력으로 추가할 종목 (엔터 시 selectedSymbols에 추가) */
  @state() private customSymbolInput = "";
  @state() private loading = false;
  /** 종목×전략별 실행 결과 목록 */
  @state() private results: SingleResult[] = [];
  /** 상세 보기할 결과 인덱스 (거래 내역·수익 곡선 표시) */
  @state() private selectedResultIndex = 0;
  @state() private runs: { id: string; start_date: string; end_date: string; symbols: string; strategy_type: string; total_return_pct: number | null; created_at: number }[] = [];
  @state() private runsLoading = false;

  connectedCallback() {
    super.connectedCallback();
    const end = new Date();
    const start = new Date(end);
    start.setFullYear(start.getFullYear() - 1);
    this.endDate = end.toISOString().slice(0, 10);
    this.startDate = start.toISOString().slice(0, 10);
    this._loadRuns();
    this.addEventListener("app-refresh", () => this._loadRuns());
  }

  private async _loadRuns() {
    this.runsLoading = true;
    try {
      const res = await fetch(`${API}/backtest/runs?limit=20`);
      const data = (await res.json()) as { runs?: { id: string; start_date: string; end_date: string; symbols: string; strategy_type: string; total_return_pct: number | null; created_at: number }[] };
      this.runs = data.runs ?? [];
    } catch {
      this.runs = [];
    } finally {
      this.runsLoading = false;
    }
  }

  private async _loadRun(id: string) {
    try {
      const res = await fetch(`${API}/backtest/runs/${id}`);
      if (!res.ok) return;
      const data = (await res.json()) as Record<string, unknown>;
      const symbols = (data.symbols as string[]) ?? [];
      const symbol = Array.isArray(symbols) && symbols.length ? symbols[0] : "—";
      const strategyType = (data.strategy_type as string) ?? "—";
      const strategyLabel = STRATEGY_PRESETS.find((p) => p.id === strategyType)?.label ?? strategyType;
      this.results = [
        {
          symbol,
          strategyId: strategyType,
          strategyLabel,
          total_return_pct: data.total_return_pct as number,
          annualized_return_pct: data.annualized_return_pct as number,
          max_drawdown_pct: data.max_drawdown_pct as number,
          trade_count: data.trade_count as number,
          win_rate: data.win_rate as number,
          trades: (data.trades as unknown[]) ?? [],
          equity_curve: (data.equity_curve as number[]) ?? [],
        },
      ];
      this.selectedResultIndex = 0;
    } catch {}
  }

  private _formatSymbols(symbols: string): string {
    if (!symbols) return "—";
    try {
      if (symbols.startsWith("[")) return (JSON.parse(symbols) as string[]).join(", ");
      return symbols;
    } catch {
      return symbols;
    }
  }

  private _equityCurvePath(curve: number[]) {
    if (!curve.length) return html``;
    const min = Math.min(...curve);
    const max = Math.max(...curve);
    const range = max - min || 1;
    const pad = 4;
    const w = 400;
    const h = 200;
    const points = curve
      .map((v, i) => {
        const x = curve.length === 1 ? w / 2 : (i / (curve.length - 1)) * w;
        const y = h - pad - ((v - min) / range) * (h - pad * 2);
        return `${x},${y}`;
      })
      .join(" ");
    return html`<polyline fill="none" stroke="var(--nq-accent)" stroke-width="1.5" points="${points}" />`;
  }

  private _toggleSymbol(sym: string) {
    const s = sym.trim().toUpperCase();
    if (!s) return;
    const idx = this.selectedSymbols.indexOf(s);
    if (idx >= 0) {
      const next = this.selectedSymbols.filter((_, i) => i !== idx);
      this.selectedSymbols = next.length ? next : [s];
    } else {
      this.selectedSymbols = [...this.selectedSymbols, s];
    }
  }

  private _addCustomSymbol() {
    const s = this.customSymbolInput.trim().toUpperCase();
    if (!s || this.selectedSymbols.includes(s)) return;
    this.selectedSymbols = [...this.selectedSymbols, s];
    this.customSymbolInput = "";
  }

  private async _run() {
    const symbols = this.selectedSymbols.length ? this.selectedSymbols : ["AAPL"];
    this.loading = true;
    this.results = [];
    this.selectedResultIndex = 0;
    const list: SingleResult[] = [];
    try {
      for (const symbol of symbols) {
        for (const preset of STRATEGY_PRESETS) {
          const res = await fetch(`${API}/backtest`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              start_date: this.startDate,
              end_date: this.endDate,
              symbols: [symbol],
              strategy: { type: preset.id, params: preset.params },
            }),
          });
          const data = (await res.json()) as Record<string, unknown>;
          list.push({
            symbol,
            strategyId: preset.id,
            strategyLabel: preset.label,
            total_return_pct: data.total_return_pct as number,
            annualized_return_pct: data.annualized_return_pct as number,
            max_drawdown_pct: data.max_drawdown_pct as number,
            trade_count: data.trade_count as number,
            win_rate: data.win_rate as number,
            message: (data.error as string) || (data.message as string),
            trades: (data.trades as unknown[]) ?? [],
            equity_curve: (data.equity_curve as number[]) ?? [],
          });
        }
      }
      this.results = list;
      this._loadRuns();
    } catch (e) {
      this.results = [{ symbol: symbols[0] ?? "", strategyId: "", strategyLabel: "", message: e instanceof Error ? e.message : String(e) }];
    } finally {
      this.loading = false;
    }
  }

  render() {
    const selectedResult = this.results[this.selectedResultIndex] ?? null;
    return html`
      <h2 class="section-title">백테스트</h2>
      <div class="form-card">
        <p class="meta" style="margin-bottom: 10px;">종목을 선택하고 실행하면 등록된 전략(RSI 30/70, 25/75, 20/80)이 모두 자동 실행됩니다.</p>
        <div class="form-row">
          <label>
            시작일
            <input type="date" .value=${this.startDate} @input=${(e: Event) => { this.startDate = (e.target as HTMLInputElement).value; }} />
          </label>
          <label>
            종료일
            <input type="date" .value=${this.endDate} @input=${(e: Event) => { this.endDate = (e.target as HTMLInputElement).value; }} />
          </label>
          <button type="button" class="btn-run" ?disabled=${this.loading} @click=${this._run}>
            ${this.loading ? "실행 중…" : "실행"}
          </button>
        </div>
        <div class="form-row" style="align-items: center;">
          <label style="flex: 1; min-width: 200px;">
            종목 선택
            <div class="symbol-chips">
              ${PRESET_SYMBOLS.map(
                (sym) => html`
                  <button type="button" class="symbol-chip ${this.selectedSymbols.includes(sym) ? "selected" : ""}" @click=${() => this._toggleSymbol(sym)}>${sym}</button>
                `
              )}
              <div class="custom-symbol-wrap">
                <input
                  type="text"
                  .value=${this.customSymbolInput}
                  placeholder="직접 입력 후 엔터"
                  @input=${(e: Event) => { this.customSymbolInput = (e.target as HTMLInputElement).value; }}
                  @keydown=${(e: KeyboardEvent) => { if (e.key === "Enter") { e.preventDefault(); this._addCustomSymbol(); } }}
                />
                <button type="button" class="btn-run" style="padding: 6px 12px; font-size: 0.8125rem;" ?disabled=${!this.customSymbolInput.trim()} @click=${this._addCustomSymbol}>추가</button>
              </div>
            </div>
          </label>
        </div>
      </div>

      ${this.results.length > 0
        ? html`
            <div class="result-card">
              <h3 class="section-title">결과 (종목 × 전략)</h3>
              <div style="margin-bottom: 14px;">
                ${this.results.map(
                  (r, i) => html`
                    <div class="result-mini ${i === this.selectedResultIndex ? "active" : ""}" @click=${() => { this.selectedResultIndex = i; }}>
                      <span class="title">${r.symbol} · ${r.strategyLabel}</span>
                      ${r.message ? html`<span class="meta">${r.message}</span>` : html`<span class="pct ${(r.total_return_pct ?? 0) < 0 ? "negative" : ""}">${r.total_return_pct != null ? `${r.total_return_pct}%` : "—"}</span>`}
                    </div>
                  `
                )}
              </div>
              ${selectedResult
                ? selectedResult.message
                  ? html`<p class="meta">${selectedResult.message}</p>`
                  : html`
                      <div class="result-cards">
                        <div><div class="val">${selectedResult.total_return_pct ?? 0}%</div><div class="label">총 수익률</div></div>
                        <div><div class="val">${selectedResult.annualized_return_pct ?? 0}%</div><div class="label">연환산</div></div>
                        <div><div class="val">${selectedResult.max_drawdown_pct ?? 0}%</div><div class="label">최대 낙폭</div></div>
                        <div><div class="val">${selectedResult.trade_count ?? 0}</div><div class="label">거래 횟수</div></div>
                        <div><div class="val">${((selectedResult.win_rate ?? 0) * 100).toFixed(1)}%</div><div class="label">승률</div></div>
                      </div>
                      ${selectedResult.equity_curve && selectedResult.equity_curve.length > 0
                        ? html`
                            <p class="equity-chart-title">수익 곡선 (자산 비율)</p>
                            <div class="equity-chart">
                              <svg width="100%" height="200" viewBox="0 0 400 200" preserveAspectRatio="none">
                                ${this._equityCurvePath(selectedResult.equity_curve)}
                              </svg>
                            </div>
                          `
                        : ""}
                      ${selectedResult.trades && selectedResult.trades.length > 0
                        ? html`
                            <h4 style="margin:16px 0 8px 0;font-size:0.9375rem;">거래 내역</h4>
                            <table>
                              <thead><tr><th>일자</th><th>종목</th><th>매수/매도</th><th>가격</th><th>수량</th><th>손익</th></tr></thead>
                              <tbody>
                                ${(selectedResult.trades as { date?: string; symbol?: string; side?: string; price?: number; quantity?: number; pnl?: number; pnl_pct?: number }[]).slice(0, 30).map(
                                  (t) => html`<tr><td>${t.date ?? "—"}</td><td>${t.symbol ?? "—"}</td><td>${t.side ?? "—"}</td><td>${t.price ?? "—"}</td><td>${t.quantity ?? "—"}</td><td>${t.side === "sell" && t.pnl != null ? `${t.pnl >= 0 ? "+" : ""}${t.pnl} (${t.pnl_pct != null ? (t.pnl_pct >= 0 ? "+" : "") + t.pnl_pct + "%" : "—"})` : "—"}</td></tr>`
                                )}
                              </tbody>
                            </table>
                          `
                        : html`<p class="meta">거래 내역이 없습니다.</p>`}
                    `
                : ""}
            </div>
          `
        : ""}

      <div class="result-card runs-card">
        <h3 class="section-title">최근 실행</h3>
        ${this.runsLoading ? html`<p class="meta">불러오는 중…</p>` : null}
        ${!this.runsLoading && this.runs.length === 0 ? html`<p class="meta">실행 이력이 없습니다. 위에서 백테스트를 실행하면 여기에 쌓입니다.</p>` : null}
        ${!this.runsLoading && this.runs.length > 0
          ? html`
              ${this.runs.map(
                (r) => html`
                  <div class="run-item" @click=${() => this._loadRun(r.id)}>
                    <span class="range">${r.start_date} ~ ${r.end_date}</span>
                    <span>${this._formatSymbols(r.symbols)}</span>
                    <span class="pct">${r.total_return_pct != null ? `${r.total_return_pct}%` : "—"}</span>
                  </div>
                `
              )}
            `
          : ""}
      </div>
    `;
  }
}
