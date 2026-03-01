/**
 * 지식그래프 뷰어 탭 — docs/menu/kg
 * 노드·엣지 목록, Decision 클릭 시 해당 세션으로 이동
 */
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

const API = "/agent";

interface KgNode {
  id: string;
  type: string;
  data: Record<string, unknown>;
}

interface KgEdge {
  from_id: string;
  to_id: string;
  type: string;
}

@customElement("kg-tab")
export class KgTab extends LitElement {
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
    .card-block {
      background: var(--nq-surface);
      border: 1px solid var(--nq-border);
      border-radius: var(--nq-radius);
      padding: 20px;
      margin-bottom: 20px;
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
    th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--nq-border); }
    th { color: var(--nq-text-muted); font-weight: 500; }
    .link-session {
      color: var(--nq-accent);
      cursor: pointer;
      text-decoration: none;
      font-weight: 500;
    }
    .link-session:hover { text-decoration: underline; }
    .pill {
      display: inline-block;
      padding: 2px 10px;
      border-radius: var(--nq-pill-radius);
      font-size: 0.75rem;
      font-weight: 500;
    }
    .pill.skill { background: rgba(163, 113, 247, 0.2); color: var(--nq-purple); }
    .pill.decision { background: rgba(88, 166, 255, 0.2); color: var(--nq-accent); }
    .meta { font-size: 0.8125rem; color: var(--nq-text-muted); }
    .detail-panel {
      margin-top: 12px;
      padding: 12px;
      background: var(--nq-bg);
      border-radius: var(--nq-radius-sm);
      font-size: 0.8125rem;
      word-break: break-all;
    }
    .filter-bar {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
      margin-bottom: 12px;
    }
    .filter-bar label {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.8125rem;
      color: var(--nq-text-muted);
    }
    .filter-bar select,
    .filter-bar input[type="date"] {
      padding: 6px 10px;
      background: var(--nq-bg);
      border: 1px solid var(--nq-border);
      border-radius: var(--nq-radius-sm);
      color: var(--nq-text);
      font-size: 0.8125rem;
    }
  `;

  @state() private nodes: KgNode[] = [];
  @state() private edges: KgEdge[] = [];
  @state() private selectedNode: KgNode | null = null;
  @state() private loading = false;
  @state() private filterType = "";
  @state() private filterFrom = "";
  @state() private filterTo = "";

  connectedCallback() {
    super.connectedCallback();
    this._load();
    this.addEventListener("app-refresh", () => this._load());
  }

  private async _load() {
    this.loading = true;
    try {
      const hasFilter = this.filterType || this.filterFrom || this.filterTo;
      if (hasFilter) {
        const params = new URLSearchParams();
        if (this.filterType) params.set("type", this.filterType);
        if (this.filterFrom) params.set("from", this.filterFrom);
        if (this.filterTo) params.set("to", this.filterTo);
        params.set("limit", "100");
        const res = await fetch(`${API}/kg/nodes?${params}`);
        const data = (await res.json()) as { nodes?: KgNode[] };
        this.nodes = data.nodes ?? [];
        this.edges = [];
      } else {
        const res = await fetch(`${API}/kg/graph`);
        const data = (await res.json()) as { nodes?: KgNode[]; edges?: KgEdge[] };
        this.nodes = data.nodes ?? [];
        this.edges = data.edges ?? [];
      }
      this.selectedNode = null;
    } catch {
      this.nodes = [];
      this.edges = [];
    } finally {
      this.loading = false;
    }
  }

  private _formatTime(ts?: number) {
    if (ts == null) return "—";
    return new Date(ts * 1000).toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  }

  private _goToSession(sessionId: string) {
    this.dispatchEvent(new CustomEvent("navigate-to", { bubbles: true, composed: true, detail: { tab: "chat" as const, sessionId } }));
  }

  private _selectNode(node: KgNode) {
    this.selectedNode = this.selectedNode?.id === node.id ? null : node;
  }

  render() {
    const decisions = this.nodes.filter((n) => n.type === "decision");
    const skills = this.nodes.filter((n) => n.type === "skill");

    return html`
      <h2 class="section-title">지식그래프</h2>
      <div class="card-block">
        <h3 class="section-title">
          노드·엣지
          <button type="button" class="btn-section" ?disabled=${this.loading} @click=${this._load}>새로고침</button>
        </h3>
        <div class="filter-bar">
          <label>
            타입
            <select .value=${this.filterType} @change=${(e: Event) => { this.filterType = (e.target as HTMLSelectElement).value; this._load(); }}>
              <option value="">전체</option>
              <option value="decision">Decision</option>
              <option value="skill">Skill</option>
            </select>
          </label>
          <label>
            기간 시작
            <input type="date" .value=${this.filterFrom} @change=${(e: Event) => { this.filterFrom = (e.target as HTMLInputElement).value; this._load(); }} />
          </label>
          <label>
            기간 종료
            <input type="date" .value=${this.filterTo} @change=${(e: Event) => { this.filterTo = (e.target as HTMLInputElement).value; this._load(); }} />
          </label>
        </div>
        ${this.loading ? html`<p class="meta">불러오는 중…</p>` : null}
        ${!this.loading && this.nodes.length === 0 ? html`<p class="meta">노드가 없습니다. 채팅에서 스킬을 실행하면 여기에 기록됩니다.</p>` : null}
        ${!this.loading && this.nodes.length > 0
          ? html`
              <p class="meta">노드 ${this.nodes.length}개${this.edges.length > 0 ? `, 엣지 ${this.edges.length}개` : ""}</p>
              ${this.selectedNode
                ? html`
                    <div class="detail-panel">
                      <strong>${this.selectedNode.id}</strong> (${this.selectedNode.type})
                      <pre style="margin:8px 0 0 0;font-size:0.75rem;white-space:pre-wrap;">${JSON.stringify(this.selectedNode.data, null, 2)}</pre>
                      ${this.selectedNode.type === "decision" && this.selectedNode.data.session_id
                        ? html`<a class="link-session" @click=${() => this._goToSession(String(this.selectedNode!.data.session_id))}>해당 세션 보기</a>`
                        : ""}
                    </div>
                  `
                : ""}
            `
          : ""}
      </div>

      <div class="card-block">
        <h3 class="section-title">최근 결정 (Decision)</h3>
        ${decisions.length === 0
          ? html`<p class="meta">최근 결정이 없습니다.</p>`
          : html`
              <table>
                <thead>
                  <tr>
                    <th>id</th>
                    <th>스킬</th>
                    <th>세션</th>
                    <th>결과 요약</th>
                    <th>시각</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  ${decisions.slice(0, 30).map(
                    (n) => html`
                      <tr>
                        <td><span class="pill decision">${n.id.slice(0, 14)}…</span></td>
                        <td>${String(n.data.skill_name ?? "—")}</td>
                        <td>${String(n.data.session_id ?? "").slice(0, 8)}</td>
                        <td>${String(n.data.result_summary ?? "").slice(0, 50) || "—"}</td>
                        <td>${this._formatTime(n.data.timestamp as number)}</td>
                        <td>
                          <a class="link-session" @click=${() => this._goToSession(String(n.data.session_id))}>세션 보기</a>
                          <button type="button" class="link-session" style="margin-left:8px;background:none;border:none;" @click=${() => this._selectNode(n)}>상세</button>
                        </td>
                      </tr>
                    `
                  )}
                </tbody>
              </table>
            `}
      </div>

      <div class="card-block">
        <h3 class="section-title">스킬 (Skill)</h3>
        ${skills.length === 0
          ? html`<p class="meta">등록된 스킬 노드가 없습니다.</p>`
          : html`
              <table>
                <thead>
                  <tr><th>id</th><th>이름</th><th>설명</th><th></th></tr>
                </thead>
                <tbody>
                  ${skills.map(
                    (n) => html`
                      <tr>
                        <td><span class="pill skill">${n.id}</span></td>
                        <td>${String(n.data.name ?? "—")}</td>
                        <td>${String(n.data.description ?? "").slice(0, 60)}</td>
                        <td><button type="button" class="link-session" style="background:none;border:none;" @click=${() => this._selectNode(n)}>상세</button></td>
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
