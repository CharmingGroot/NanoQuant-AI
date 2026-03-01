import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

const STORAGE_KEY = "nanoquant_agent_api";
const API = "/agent";

interface SkillMeta {
  name: string;
  description: string;
  params_schema: Record<string, string>;
}

@customElement("settings-tab")
export class SettingsTab extends LitElement {
  static styles = css`
    .section-title { font-size: 1.125rem; font-weight: 600; color: var(--nq-title); margin: 0 0 8px 0; }
    .meta { font-size: 0.8125rem; color: var(--nq-text-muted); margin-bottom: 24px; }
    .card {
      background: var(--nq-surface);
      border: 1px solid var(--nq-border);
      border-radius: var(--nq-radius);
      padding: 24px;
      margin-bottom: 24px;
      box-shadow: var(--nq-shadow);
    }
    .card h3 {
      font-size: 0.9375rem;
      font-weight: 600;
      color: var(--nq-title);
      margin: 0 0 8px 0;
    }
    .card .meta { margin-bottom: 16px; }
    .form-row {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      align-items: center;
      margin-bottom: 16px;
    }
    .form-row label {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--nq-text-muted);
      min-width: 80px;
    }
    .form-row input,
    .form-row select {
      padding: 10px 14px;
      background: var(--nq-bg);
      border: 1px solid var(--nq-border);
      border-radius: var(--nq-radius-sm);
      color: var(--nq-text);
      font-size: 0.9375rem;
      min-width: 200px;
      outline: none;
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    .form-row input:focus,
    .form-row select:focus {
      border-color: var(--nq-accent);
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
    }
    .btn-save {
      padding: 10px 20px;
      background: var(--nq-accent);
      color: white;
      border: none;
      border-radius: var(--nq-radius-sm);
      font-weight: 600;
      font-size: 0.875rem;
      cursor: pointer;
      transition: background 0.15s;
    }
    .btn-save:hover { background: var(--nq-accent-hover); }
    .save-status { font-size: 0.8125rem; color: var(--nq-success); margin-top: 8px; }
    .table-wrap {
      overflow-x: auto;
      border: 1px solid var(--nq-border);
      border-radius: var(--nq-radius);
      background: var(--nq-surface);
    }
    table { width: 100%; border-collapse: collapse; }
    th {
      padding: 12px 16px;
      text-align: left;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--nq-text-muted);
      background: rgba(0,0,0,0.2);
      border-bottom: 1px solid var(--nq-border);
    }
    td {
      padding: 14px 16px;
      font-size: 0.875rem;
      color: var(--nq-text);
      border-bottom: 1px solid var(--nq-border);
    }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: rgba(255,255,255,0.02); }
    .empty { color: var(--nq-text-muted); text-align: center; padding: 24px; }
  `;

  @state() private provider = "claude";
  @state() private model = "";
  @state() private apiKey = "";
  @state() private saveStatus = "";
  @state() private skills: SkillMeta[] = [];
  @state() private hitlSkills: string[] = [];

  connectedCallback() {
    super.connectedCallback();
    this._loadStored();
    this._loadSkills();
  }

  private _loadStored() {
    try {
      const s = localStorage.getItem(STORAGE_KEY);
      if (s) {
        const o = JSON.parse(s) as { provider?: string; model?: string; api_key?: string };
        if (o.provider) this.provider = o.provider;
        if (o.model) this.model = o.model;
        if (o.api_key) this.apiKey = o.api_key;
      }
    } catch {}
  }

  private _save() {
    const o = {
      provider: this.provider,
      model: this.model.trim() || undefined,
      api_key: this.apiKey.trim(),
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(o));
    this.saveStatus = "저장되었습니다 (브라우저에만 보관)";
  }

  private async _loadSkills() {
    try {
      const res = await fetch(`${API}/skills`);
      const data = (await res.json()) as { skills?: SkillMeta[]; hitl_skills?: string[] };
      this.skills = data.skills ?? [];
      this.hitlSkills = data.hitl_skills ?? [];
    } catch (e) {
      this.skills = [];
      this.hitlSkills = [];
    }
  }

  render() {
    return html`
      <h2 class="section-title">설정</h2>
      <p class="meta">에이전트 채팅에 필요한 API 키와 가용 스킬 목록입니다.</p>

      <div class="card">
        <h3>LLM API 키</h3>
        <p class="meta">채팅 시 사용됩니다. 키는 브라우저에만 저장됩니다.</p>
        <div class="form-row">
          <label>제공자</label>
          <select .value=${this.provider} @change=${(e: Event) => { this.provider = (e.target as HTMLSelectElement).value; }}>
            <option value="claude">Claude (Anthropic)</option>
            <option value="gpt">OpenAI (GPT)</option>
          </select>
        </div>
        <div class="form-row">
          <label>모델</label>
          <input type="text" placeholder="claude-3-5-sonnet 또는 gpt-4o" .value=${this.model} @input=${(e: Event) => { this.model = (e.target as HTMLInputElement).value; }} />
        </div>
        <div class="form-row">
          <label>API Key</label>
          <input type="password" placeholder="sk-..." .value=${this.apiKey} @input=${(e: Event) => { this.apiKey = (e.target as HTMLInputElement).value; }} />
        </div>
        <div class="form-row">
          <span></span>
          <button class="btn-save" @click=${() => this._save()}>저장</button>
        </div>
        ${this.saveStatus ? html`<p class="save-status">${this.saveStatus}</p>` : ""}
      </div>

      <div class="card">
        <h3>스킬·도구 목록</h3>
        <p class="meta">에이전트가 호출할 수 있는 스킬입니다. HITL은 실행 전 사용자 승인이 필요한 스킬입니다.</p>
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>스킬명</th><th>설명</th><th>파라미터</th><th>HITL</th></tr>
            </thead>
            <tbody>
              ${this.skills.length === 0
                ? html`<tr><td colspan="4" class="empty">불러오는 중...</td></tr>`
                : this.skills.map(
                    (s) => html`
                      <tr>
                        <td><strong>${s.name}</strong></td>
                        <td>${(s.description || "").slice(0, 120)}</td>
                        <td style="font-size:0.75rem;color:var(--nq-text-muted)">${JSON.stringify(s.params_schema ?? {})}</td>
                        <td>${this.hitlSkills.includes(s.name) ? "Y" : "—"}</td>
                      </tr>
                    `
                  )}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }
}
