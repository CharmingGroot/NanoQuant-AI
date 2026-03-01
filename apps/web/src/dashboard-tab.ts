import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

const API = "/agent";

interface SkillItem {
  name: string;
  description: string;
  params_schema: Record<string, string>;
}

interface DecisionItem {
  session_id?: string;
  skill_name?: string;
  result_summary?: string;
  timestamp?: number;
  args?: Record<string, unknown>;
}

interface PositionItem {
  symbol?: string;
  name?: string;
  qty?: number;
  avg_price?: number;
  current_price?: number;
  value?: number;
  pnl?: number;
  pnl_pct?: number;
  weight_pct?: number;
}

interface PortfolioData {
  total_asset?: number;
  cash?: number;
  positions?: PositionItem[];
  pnl_today?: number;
  updated_at?: number;
}

@customElement("dashboard-tab")
export class DashboardTab extends LitElement {
  static styles = css`
    .section-title {
      font-size: 1.125rem;
      font-weight: 600;
      color: var(--nq-title);
      margin: 0 0 8px 0;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 8px;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 24px;
    }
    @media (max-width: 900px) { .cards { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 480px) { .cards { grid-template-columns: 1fr; } }
    .sum-card {
      background: var(--nq-surface);
      border: 1px solid var(--nq-border);
      border-radius: var(--nq-radius);
      padding: 20px;
      display: flex;
      align-items: flex-start;
      gap: 14px;
    }
    .sum-card .icon {
      width: 40px;
      height: 40px;
      border-radius: var(--nq-radius-sm);
      background: rgba(88, 166, 255, 0.2);
      color: var(--nq-accent);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.25rem;
      flex-shrink: 0;
    }
    .sum-card .icon.purple { background: rgba(163, 113, 247, 0.2); color: var(--nq-purple); }
    .sum-card .icon.green { background: rgba(63, 185, 80, 0.2); color: var(--nq-success); }
    .sum-card .icon.gold { background: rgba(210, 153, 34, 0.2); color: var(--nq-warning); }
    .sum-card .val { font-size: 1.5rem; font-weight: 700; color: var(--nq-text); margin: 0 0 4px 0; }
    .sum-card .val.negative { color: var(--nq-danger); }
    .sum-card .label { font-size: 0.8125rem; color: var(--nq-text-muted); margin: 0; }
    .card-block {
      background: var(--nq-surface);
      border: 1px solid var(--nq-border);
      border-radius: var(--nq-radius);
      padding: 20px;
      margin-bottom: 20px;
    }
    .card-block h2 {
      font-size: 1rem;
      font-weight: 600;
      color: var(--nq-title);
      margin: 0 0 12px 0;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .btn-section {
      padding: 6px 12px;
      font-size: 0.8125rem;
      background: var(--nq-accent);
      color: #fff;
      border: none;
      border-radius: var(--nq-radius-sm);
      cursor: pointer;
    }
    .btn-section:hover { opacity: 0.9; }
    table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
    th { text-align: left; padding: 10px 12px; color: var(--nq-text-muted); font-weight: 500; border-bottom: 1px solid var(--nq-border); }
    td { padding: 10px 12px; border-bottom: 1px solid var(--nq-border); }
    tr:last-child td { border-bottom: none; }
    .pill {
      display: inline-block;
      padding: 2px 10px;
      border-radius: var(--nq-pill-radius);
      font-size: 0.75rem;
      font-weight: 500;
    }
    .pill.ok { background: rgba(63, 185, 80, 0.2); color: var(--nq-success); }
    .pill.meta { background: rgba(163, 113, 247, 0.2); color: var(--nq-purple); }
    .meta { font-size: 0.8125rem; color: var(--nq-text-muted); }
  `;

  @state() private apiConnected = 0;
  @state() private skillsCount = 0;
  @state() private sessionsCount = 0;
  @state() private decisionsCount = 0;
  @state() private skills: SkillItem[] = [];
  @state() private recentDecisions: DecisionItem[] = [];
  @state() private portfolio: PortfolioData | null = null;
  @state() private portfolioError = "";

  connectedCallback() {
    super.connectedCallback();
    this._load();
    this.addEventListener("app-refresh", () => this._load());
  }

  private async _load() {
    try {
      const [healthRes, skillsRes, sessionsRes, kgRes, portfolioRes] = await Promise.all([
        fetch(`${API}/health`).catch(() => null),
        fetch(`${API}/skills`),
        fetch(`${API}/sessions`),
        fetch(`${API}/kg/recent?limit=10`),
        fetch(`${API}/portfolio`).catch(() => null),
      ]);
      this.apiConnected = healthRes?.ok === true ? 1 : 0;
      const skillsData = (await skillsRes.json()) as { skills?: SkillItem[] };
      const sessionsData = (await sessionsRes.json()) as { sessions?: unknown[] };
      const kgData = (await kgRes.json()) as { decisions?: DecisionItem[] };
      this.skills = skillsData.skills ?? [];
      this.skillsCount = this.skills.length;
      this.sessionsCount = sessionsData.sessions?.length ?? 0;
      this.recentDecisions = kgData.decisions ?? [];
      this.decisionsCount = this.recentDecisions.length;
      this.portfolioError = "";
      if (portfolioRes?.ok) {
        this.portfolio = (await portfolioRes.json()) as PortfolioData;
      } else {
        this.portfolio = null;
        if (portfolioRes && !portfolioRes.ok) this.portfolioError = "포트폴리오를 불러올 수 없습니다. 새로고침하거나 설정에서 연동을 확인하세요.";
      }
    } catch {
      this.apiConnected = 0;
      this.skills = [];
      this.skillsCount = 0;
      this.sessionsCount = 0;
      this.recentDecisions = [];
      this.decisionsCount = 0;
      this.portfolio = null;
      this.portfolioError = "포트폴리오를 불러올 수 없습니다.";
    }
  }

  private _formatTime(ts?: number) {
    if (ts == null) return "—";
    const d = new Date(ts * 1000);
    return d.toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  }

  private _formatMoney(n: number | undefined) {
    if (n == null) return "—";
    return n.toLocaleString("ko-KR", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  }

  render() {
    return html`
      <h2 class="section-title">대시보드</h2>
      <div class="cards">
        <div class="sum-card">
          <div class="icon">◇</div>
          <div>
            <p class="val">${this.apiConnected}</p>
            <p class="label">연결된 API</p>
          </div>
        </div>
        <div class="sum-card">
          <div class="icon purple">◈</div>
          <div>
            <p class="val">${this.sessionsCount}</p>
            <p class="label">활성 세션</p>
          </div>
        </div>
        <div class="sum-card">
          <div class="icon green">▣</div>
          <div>
            <p class="val">${this.skillsCount}</p>
            <p class="label">등록 스킬</p>
          </div>
        </div>
        <div class="sum-card">
          <div class="icon gold">◉</div>
          <div>
            <p class="val">${this.decisionsCount}</p>
            <p class="label">최근 결정</p>
          </div>
        </div>
      </div>

      <div class="card-block">
        <h2>현재 포트폴리오</h2>
        ${this.portfolioError ? html`<p class="meta" style="color:var(--nq-danger);">${this.portfolioError}</p><button type="button" class="btn-section" style="margin-top:8px;" @click=${() => this._load()}>새로고침</button>` : null}
        ${!this.portfolioError && this.portfolio
          ? html`
              <p class="meta">총자산 ${this._formatMoney(this.portfolio.total_asset)} · 현금 ${this._formatMoney(this.portfolio.cash)} · 일손익 ${this._formatMoney(this.portfolio.pnl_today)} · Last Update ${this.portfolio.updated_at ? this._formatTime(this.portfolio.updated_at) : "—"}</p>
              ${!this.portfolio.positions?.length
                ? html`<p class="meta" style="margin-top:12px;">보유 포지션이 없습니다. 연동된 계좌/시뮬레이션에 포지션이 없습니다.</p>`
                : html`
                    <table style="margin-top:12px;">
                      <thead>
                        <tr>
                          <th>종목</th>
                          <th>수량</th>
                          <th>평균 단가</th>
                          <th>현재가</th>
                          <th>평가금액</th>
                          <th>손익</th>
                          <th>손익률</th>
                        </tr>
                      </thead>
                      <tbody>
                        ${(this.portfolio.positions ?? []).map(
                          (p) => html`
                            <tr>
                              <td>${p.symbol ?? "—"} ${p.name ? `(${p.name})` : ""}</td>
                              <td>${p.qty ?? "—"}</td>
                              <td>${this._formatMoney(p.avg_price)}</td>
                              <td>${this._formatMoney(p.current_price)}</td>
                              <td>${this._formatMoney(p.value)}</td>
                              <td class="${(p.pnl ?? 0) < 0 ? "val negative" : ""}">${this._formatMoney(p.pnl)}</td>
                              <td class="${(p.pnl_pct ?? 0) < 0 ? "val negative" : ""}">${p.pnl_pct != null ? `${p.pnl_pct.toFixed(2)}%` : "—"}</td>
                            </tr>
                          `
                        )}
                      </tbody>
                    </table>
                  `}
            `
          : !this.portfolioError ? html`<p class="meta">포트폴리오 데이터를 불러오는 중이거나 연동되지 않았습니다.</p>` : ""}
      </div>

      <div class="card-block">
        <h2>↻ 스킬 연결</h2>
        <div style="display:flex;justify-content:flex-end;margin-bottom:8px;">
          <button type="button" class="btn-section" @click=${() => this._load()}>새로고침</button>
        </div>
        ${this.skills.length === 0
          ? html`<p class="meta">등록된 스킬이 없습니다.</p>`
          : html`
              <table>
                <thead>
                  <tr>
                    <th>스킬</th>
                    <th>상태</th>
                    <th>설명</th>
                    <th>파라미터</th>
                  </tr>
                </thead>
                <tbody>
                  ${this.skills.map(
                    (s) => html`
                      <tr>
                        <td><strong>${s.name}</strong></td>
                        <td><span class="pill ok">사용 가능</span></td>
                        <td>${(s.description ?? "").slice(0, 60)}</td>
                        <td style="font-size:0.75rem;color:var(--nq-text-muted)">${Object.keys(s.params_schema ?? {}).join(", ") || "—"}</td>
                      </tr>
                    `
                  )}
                </tbody>
              </table>
            `}
      </div>

      <div class="card-block">
        <h2>↻ 최근 결정</h2>
        <div style="display:flex;justify-content:flex-end;margin-bottom:8px;">
          <button type="button" class="btn-section" @click=${() => this._load()}>새로고침</button>
        </div>
        ${this.recentDecisions.length === 0
          ? html`<p class="meta">최근 스킬 실행 이력이 없습니다.</p>`
          : html`
              <table>
                <thead>
                  <tr>
                    <th>스킬</th>
                    <th>세션</th>
                    <th>결과 요약</th>
                    <th>시각</th>
                  </tr>
                </thead>
                <tbody>
                  ${this.recentDecisions.map(
                    (d) => html`
                      <tr>
                        <td><span class="pill meta">${d.skill_name ?? "—"}</span></td>
                        <td>${(d.session_id ?? "").slice(0, 8)}</td>
                        <td>${String(d.result_summary ?? "").slice(0, 80) || "—"}</td>
                        <td>${this._formatTime(d.timestamp)}</td>
                      </tr>
                    `
                  )}
                </tbody>
              </table>
            `}
      </div>
    `;
  }
}
