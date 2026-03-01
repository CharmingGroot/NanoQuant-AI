import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

const API = "/agent";

interface DecisionItem {
  session_id?: string;
  skill_name?: string;
  result_summary?: string;
  timestamp?: number;
  error?: string;
}

@customElement("monitor-tab")
export class MonitorTab extends LitElement {
  static styles = css`
    .section-title {
      font-size: 1.125rem;
      font-weight: 600;
      color: var(--nq-title);
      margin: 0 0 16px 0;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 8px;
    }
    .card-block {
      background: var(--nq-surface);
      border: 1px solid var(--nq-border);
      border-radius: var(--nq-radius);
      padding: 20px;
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
    .btn-refresh {
      padding: 6px 12px;
      font-size: 0.8125rem;
      background: var(--nq-accent);
      color: #fff;
      border: none;
      border-radius: var(--nq-radius-sm);
      cursor: pointer;
    }
    .btn-refresh:hover { opacity: 0.9; }
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
    .pill.err { background: rgba(248, 81, 73, 0.2); color: var(--nq-danger); }
    .pill.meta { background: rgba(163, 113, 247, 0.2); color: var(--nq-purple); }
    .meta { font-size: 0.8125rem; color: var(--nq-text-muted); }
  `;

  @state() private items: DecisionItem[] = [];
  @state() private loading = false;

  connectedCallback() {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this.loading = true;
    try {
      const res = await fetch(`${API}/kg/recent?limit=20`);
      const data = (await res.json()) as { decisions?: DecisionItem[] };
      this.items = data.decisions ?? [];
    } catch {
      this.items = [];
    } finally {
      this.loading = false;
    }
  }

  private _formatTime(ts?: number) {
    if (ts == null) return "—";
    const d = new Date(ts * 1000);
    return d.toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }

  render() {
    return html`
      <h2 class="section-title">모니터</h2>
      <div class="card-block">
        <h2>↻ 실시간 활동 (최근 스킬 실행)</h2>
        <div style="display:flex;justify-content:flex-end;margin-bottom:8px;">
          <button type="button" class="btn-refresh" @click=${() => this._load()} ?disabled=${this.loading}>새로고침</button>
        </div>
        ${this.items.length === 0 && !this.loading
          ? html`<p class="meta">최근 활동이 없습니다.</p>`
          : html`
              <table>
                <thead>
                  <tr>
                    <th>스킬</th>
                    <th>세션</th>
                    <th>상태</th>
                    <th>결과 요약</th>
                    <th>시각</th>
                  </tr>
                </thead>
                <tbody>
                  ${this.items.map(
                    (d) => html`
                      <tr>
                        <td><span class="pill meta">${d.skill_name ?? "—"}</span></td>
                        <td>${(d.session_id ?? "").slice(0, 8)}</td>
                        <td>${d.error ? html`<span class="pill err">오류</span>` : html`<span class="pill ok">완료</span>`}</td>
                        <td>${d.error ? String(d.error).slice(0, 50) : String(d.result_summary ?? "").slice(0, 60) || "—"}</td>
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
