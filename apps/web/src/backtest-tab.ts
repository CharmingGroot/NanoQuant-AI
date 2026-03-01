/**
 * 백테스트 탭 — docs/menu/backtest
 * 기간·종목·전략 입력 폼, 실행, 결과 요약·거래 내역·수익 곡선(스텁)
 */
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

const API = "/agent";

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
  `;

  @state() private startDate = "";
  @state() private endDate = "";
  @state() private symbol = "AAPL";
  @state() private strategy = "rsi_30_70";
  @state() private loading = false;
  @state() private result: {
    total_return_pct?: number;
    annualized_return_pct?: number;
    max_drawdown_pct?: number;
    trade_count?: number;
    win_rate?: number;
    message?: string;
    trades?: unknown[];
    equity_curve?: number[];
  } | null = null;
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
      this.result = {
        total_return_pct: data.total_return_pct as number,
        annualized_return_pct: data.annualized_return_pct as number,
        max_drawdown_pct: data.max_drawdown_pct as number,
        trade_count: data.trade_count as number,
        win_rate: data.win_rate as number,
        trades: (data.trades as unknown[]) ?? [],
        equity_curve: (data.equity_curve as number[]) ?? [],
      };
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

  private async _run() {
    this.loading = true;
    this.result = null;
    try {
      const res = await fetch(`${API}/backtest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          start_date: this.startDate,
          end_date: this.endDate,
          symbols: [this.symbol],
          strategy: { type: this.strategy, params: {} },
        }),
      });
      const data = (await res.json()) as Record<string, unknown>;
      this.result = {
        total_return_pct: data.total_return_pct as number,
        annualized_return_pct: data.annualized_return_pct as number,
        max_drawdown_pct: data.max_drawdown_pct as number,
        trade_count: data.trade_count as number,
        win_rate: data.win_rate as number,
        message: (data.error as string) || (data.message as string),
        trades: (data.trades as unknown[]) ?? [],
        equity_curve: (data.equity_curve as number[]) ?? [],
      };
      this._loadRuns();
    } catch (e) {
      this.result = { message: e instanceof Error ? e.message : String(e) };
    } finally {
      this.loading = false;
    }
  }

  render() {
    return html`
      <h2 class="section-title">백테스트</h2>
      <div class="form-card">
        <div class="form-row">
          <label>
            시작일
            <input type="date" .value=${this.startDate} @input=${(e: Event) => { this.startDate = (e.target as HTMLInputElement).value; }} />
          </label>
          <label>
            종료일
            <input type="date" .value=${this.endDate} @input=${(e: Event) => { this.endDate = (e.target as HTMLInputElement).value; }} />
          </label>
          <label>
            종목
            <input type="text" .value=${this.symbol} @input=${(e: Event) => { this.symbol = (e.target as HTMLInputElement).value; }} placeholder="예: AAPL" />
          </label>
          <label>
            전략
            <select .value=${this.strategy} @change=${(e: Event) => { this.strategy = (e.target as HTMLSelectElement).value; }}>
              <option value="rsi_30_70">RSI 30/70</option>
            </select>
          </label>
          <button type="button" class="btn-run" ?disabled=${this.loading} @click=${this._run}>
            ${this.loading ? "실행 중…" : "실행"}
          </button>
        </div>
      </div>

      ${this.result
        ? html`
            <div class="result-card">
              <h3 class="section-title">결과 요약</h3>
              ${this.result.message
                ? html`<p class="meta">${this.result.message}</p>`
                : html`
                    <div class="result-cards">
                      <div><div class="val">${this.result.total_return_pct ?? 0}%</div><div class="label">총 수익률</div></div>
                      <div><div class="val">${this.result.annualized_return_pct ?? 0}%</div><div class="label">연환산</div></div>
                      <div><div class="val">${this.result.max_drawdown_pct ?? 0}%</div><div class="label">최대 낙폭</div></div>
                      <div><div class="val">${this.result.trade_count ?? 0}</div><div class="label">거래 횟수</div></div>
                      <div><div class="val">${((this.result.win_rate ?? 0) * 100).toFixed(1)}%</div><div class="label">승률</div></div>
                    </div>
                    ${this.result.equity_curve && this.result.equity_curve.length > 0
                      ? html`
                          <p class="equity-chart-title">수익 곡선 (자산 비율)</p>
                          <div class="equity-chart">
                            <svg width="100%" height="200" viewBox="0 0 400 200" preserveAspectRatio="none">
                              ${this._equityCurvePath(this.result.equity_curve)}
                            </svg>
                          </div>
                        `
                      : ""}
                  `}
              ${this.result.trades && this.result.trades.length > 0
                ? html`
                    <h4 style="margin:16px 0 8px 0;font-size:0.9375rem;">거래 내역</h4>
                    <table>
                      <thead><tr><th>일자</th><th>종목</th><th>매수/매도</th><th>가격</th><th>수량</th><th>손익</th></tr></thead>
                      <tbody>
                        ${(this.result.trades as { date?: string; symbol?: string; side?: string; price?: number; quantity?: number; pnl?: number; pnl_pct?: number }[]).slice(0, 30).map(
                          (t) => html`<tr><td>${t.date ?? "—"}</td><td>${t.symbol ?? "—"}</td><td>${t.side ?? "—"}</td><td>${t.price ?? "—"}</td><td>${t.quantity ?? "—"}</td><td>${t.side === "sell" && t.pnl != null ? `${t.pnl >= 0 ? "+" : ""}${t.pnl} (${t.pnl_pct != null ? (t.pnl_pct >= 0 ? "+" : "") + t.pnl_pct + "%" : "—"})` : "—"}</td></tr>`
                        )}
                      </tbody>
                    </table>
                  `
                : this.result.message ? "" : html`<p class="meta">거래 내역이 없습니다.</p>`}
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
