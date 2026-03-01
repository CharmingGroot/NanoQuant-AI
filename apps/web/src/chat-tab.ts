import { LitElement, html, css } from "lit";
import { customElement, state, property } from "lit/decorators.js";

const API = "/agent";

interface ToolCall {
  skill: string;
  args?: Record<string, unknown>;
  result_preview?: string;
  error?: string;
  hitl_required?: boolean;
  hitl_id?: string;
}

interface SessionItem {
  id: string;
  title: string;
  updated_at: number;
}

interface HistoryTurn {
  role: "user" | "assistant";
  content: string;
  tool_calls?: ToolCall[];
}

interface SkillItem {
  name: string;
  description: string;
  params_schema: Record<string, string>;
}

@customElement("chat-tab")
export class ChatTab extends LitElement {
  static styles = css`
    :host { display: flex; flex-direction: column; flex: 1; min-height: 0; }
    .layout { display: flex; gap: 0; align-items: stretch; flex: 1; min-height: 0; }
    .sidebar-left {
      width: 220px;
      flex-shrink: 0;
      display: flex;
      flex-direction: column;
      gap: 0;
      background: var(--nq-surface);
      border-right: 1px solid var(--nq-border-subtle);
      padding: 8px 8px;
    }
    .sidebar-title {
      font-size: 0.65rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--nq-text-muted);
      margin: 0 0 6px 0;
      padding: 0 2px;
    }
    .btn-new {
      padding: 6px 10px;
      background: var(--nq-accent);
      color: #fff;
      border: none;
      border-radius: var(--nq-radius-sm);
      font-size: 0.875rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s, transform 0.05s;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }
    .btn-new:hover { background: var(--nq-accent-hover); }
    .btn-new:active { transform: scale(0.98); }
    .session-list {
      display: flex;
      flex-direction: column;
      gap: 3px;
      overflow-y: auto;
      flex: 1;
      min-height: 0;
      margin-top: 6px;
    }
    .session-list::-webkit-scrollbar { width: 6px; }
    .session-list::-webkit-scrollbar-thumb { background: var(--nq-border); border-radius: 3px; }
    .session-item {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 8px;
      background: var(--nq-bg);
      border: 1px solid transparent;
      border-radius: var(--nq-radius-sm);
      cursor: pointer;
      transition: background 0.15s, border-color 0.15s;
      text-align: left;
    }
    .session-item:hover { background: var(--nq-surface-hover); }
    .session-item.active {
      border-color: var(--nq-accent);
      background: rgba(56, 139, 253, 0.1);
    }
    .session-item .item-label {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .session-item .item-title {
      font-size: 0.8125rem;
      color: var(--nq-text);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .session-item .item-time {
      font-size: 0.6875rem;
      color: var(--nq-text-muted);
    }
    .session-item .del, .session-item .edit {
      flex-shrink: 0;
      padding: 4px;
      background: none;
      border: none;
      color: var(--nq-text-muted);
      cursor: pointer;
      font-size: 0.875rem;
      line-height: 1;
      opacity: 0.7;
    }
    .session-item:hover .del, .session-item:hover .edit { opacity: 1; }
    .session-item .del:hover { color: var(--nq-danger); }
    .session-item .edit:hover { color: var(--nq-accent); }
    .session-item input.edit-inp {
      flex: 1;
      min-width: 0;
      padding: 4px 8px;
      font-size: 0.8125rem;
      background: var(--nq-surface);
      border: 1px solid var(--nq-accent);
      border-radius: 4px;
      color: var(--nq-text);
    }
    .main { flex: 1; min-width: 0; display: flex; flex-direction: column; padding: 0 8px; min-height: 0; }
    .sidebar-right {
      width: 200px;
      flex-shrink: 0;
      display: flex;
      flex-direction: column;
      background: var(--nq-surface);
      border-left: 1px solid var(--nq-border-subtle);
      padding: 8px 8px;
      overflow-y: auto;
      max-height: 100%;
    }
    .sidebar-right::-webkit-scrollbar { width: 6px; }
    .sidebar-right::-webkit-scrollbar-thumb { background: var(--nq-border); border-radius: 3px; }
    .skill-item {
      padding: 6px 8px;
      border-radius: var(--nq-radius-sm);
      font-size: 0.75rem;
      color: var(--nq-text);
      cursor: pointer;
      transition: background 0.15s, border-color 0.15s;
      text-align: left;
      border: 1px solid transparent;
      margin-bottom: 2px;
    }
    .skill-item:hover { background: var(--nq-surface-hover); }
    .skill-item.selected {
      border-color: var(--nq-accent);
      background: rgba(56, 139, 253, 0.12);
      color: var(--nq-accent);
    }
    .skill-item .skill-name { font-weight: 600; }
    .skill-item .skill-desc { font-size: 0.6875rem; color: var(--nq-text-muted); margin-top: 2px; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
    .forced-skill-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 4px 8px;
      margin-bottom: 4px;
      background: rgba(56, 139, 253, 0.12);
      border: 1px solid var(--nq-accent);
      border-radius: var(--nq-radius-sm);
      font-size: 0.8125rem;
      color: var(--nq-accent);
    }
    .forced-skill-badge .clear { margin-left: auto; padding: 2px 8px; background: transparent; border: none; color: var(--nq-text-muted); cursor: pointer; border-radius: 4px; }
    .forced-skill-badge .clear:hover { color: var(--nq-text); background: var(--nq-surface-hover); }
    .section-title {
      font-size: 0.9375rem;
      font-weight: 700;
      color: var(--nq-title);
      margin: 0 0 2px 0;
      letter-spacing: -0.02em;
    }
    .hint {
      font-size: 0.6875rem;
      color: var(--nq-text-muted);
      margin-bottom: 6px;
      line-height: 1.4;
    }
    .hint a {
      color: var(--nq-accent);
      text-decoration: none;
      font-weight: 500;
    }
    .hint a:hover { text-decoration: underline; }
    .log {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      padding: 10px 12px;
      background: var(--nq-surface-elevated);
      border: 1px solid var(--nq-border-subtle);
      border-radius: var(--nq-radius);
      margin-bottom: 6px;
      box-shadow: var(--nq-shadow-sm);
    }
    .log::-webkit-scrollbar { width: 8px; }
    .log::-webkit-scrollbar-thumb { background: var(--nq-border); border-radius: 4px; }
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 0;
      text-align: center;
      padding: 8px 12px;
    }
    .empty-state-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
    }
    .empty-state-icon {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: rgba(56, 139, 253, 0.15);
      color: var(--nq-accent);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.875rem;
      flex-shrink: 0;
    }
    .empty-state-title {
      font-size: 0.8125rem;
      font-weight: 600;
      color: var(--nq-text);
      margin: 0;
    }
    .empty-state-sub {
      font-size: 0.75rem;
      color: var(--nq-text-muted);
      margin: 0 0 8px 0;
      max-width: 320px;
    }
    .suggestion-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      justify-content: center;
    }
    .suggestion-chip {
      padding: 5px 10px;
      background: var(--nq-surface);
      border: 1px solid var(--nq-border);
      border-radius: var(--nq-pill-radius);
      font-size: 0.6875rem;
      color: var(--nq-text-muted);
      cursor: pointer;
      transition: background 0.15s, border-color 0.15s, color 0.15s;
    }
    .suggestion-chip:hover {
      background: var(--nq-surface-hover);
      border-color: var(--nq-accent);
      color: var(--nq-accent);
    }
    .msg {
      margin-bottom: 6px;
      padding: 6px 10px;
      border-radius: var(--nq-radius-sm);
      font-size: 0.875rem;
      line-height: 1.5;
    }
    .msg:last-child { margin-bottom: 0; }
    .msg.user {
      background: var(--nq-chat-user-bg);
      border: 1px solid rgba(59, 130, 246, 0.2);
      margin-right: 16px;
    }
    .msg.assistant {
      background: var(--nq-chat-bot-bg);
      border: 1px solid var(--nq-border);
      margin-left: 16px;
    }
    .msg-role {
      font-size: 0.6875rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--nq-text-muted);
      margin-bottom: 4px;
    }
    .msg-content { color: var(--nq-text); }
    .msg-tools {
      margin-top: 6px;
      padding-top: 6px;
      border-top: 1px solid var(--nq-border);
      font-size: 0.8125rem;
      color: var(--nq-text-muted);
    }
    .hitl { margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
    .hitl button {
      font-size: 0.8125rem;
      padding: 6px 14px;
      border-radius: 6px;
      font-weight: 500;
      cursor: pointer;
      border: none;
    }
    .hitl button:first-of-type { background: var(--nq-accent); color: white; }
    .hitl button:last-of-type {
      background: transparent;
      color: var(--nq-text-muted);
      border: 1px solid var(--nq-border);
    }
    .input-bar {
      display: flex;
      gap: 8px;
      align-items: center;
      padding: 6px 10px;
      background: var(--nq-surface);
      border: 1px solid var(--nq-border-subtle);
      border-radius: var(--nq-radius);
      box-shadow: var(--nq-shadow-sm);
    }
    input[type="text"] {
      flex: 1;
      padding: 6px 10px;
      background: var(--nq-bg);
      border: 1px solid var(--nq-border);
      border-radius: var(--nq-radius-sm);
      color: var(--nq-text);
      font-size: 0.875rem;
      outline: none;
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    input[type="text"]::placeholder { color: var(--nq-text-muted); }
    input[type="text"]:focus {
      border-color: var(--nq-accent);
      box-shadow: 0 0 0 2px rgba(56, 139, 253, 0.2);
    }
    .btn-send {
      padding: 6px 12px;
      background: var(--nq-accent);
      color: #fff;
      border: none;
      border-radius: var(--nq-radius-sm);
      font-weight: 600;
      font-size: 0.8125rem;
      cursor: pointer;
      transition: background 0.2s, transform 0.05s;
    }
    .btn-send:hover:not(:disabled) { background: var(--nq-accent-hover); }
    .btn-send:active:not(:disabled) { transform: scale(0.98); }
    .btn-send:disabled { opacity: 0.5; cursor: not-allowed; }
    .status { margin-top: 4px; font-size: 0.6875rem; color: var(--nq-text-muted); padding: 0 2px; }
    .status.loading { color: var(--nq-accent); }
  `;

  @property({ type: String }) sessionId: string | null = null;
  @state() private sessions: SessionItem[] = [];
  @state() private currentSessionId: string | null = null;
  @state() private messages: { role: "user" | "assistant"; content: string; tool_calls?: ToolCall[] }[] = [];
  @state() private input = "";
  @state() private status = "";
  @state() private loading = false;
  @state() private editingSessionId: string | null = null;
  @state() private editingTitle = "";
  @state() private skills: SkillItem[] = [];
  @state() private forcedSkill: string | null = null;

  connectedCallback() {
    super.connectedCallback();
    this._loadSessions();
    this._loadSkills();
    if (this.sessionId) {
      this.currentSessionId = this.sessionId;
      this._loadHistory(this.sessionId);
    }
  }

  updated(changed: Map<string, unknown>) {
    if (changed.has("sessionId") && this.sessionId && this.sessionId !== this.currentSessionId) {
      this.currentSessionId = this.sessionId;
      this._loadHistory(this.sessionId);
    }
  }

  private async _loadSessions() {
    try {
      const res = await fetch(`${API}/sessions`);
      const data = (await res.json()) as { sessions?: SessionItem[] };
      this.sessions = data.sessions ?? [];
    } catch {
      this.sessions = [];
    }
  }

  private async _loadSkills() {
    try {
      const res = await fetch(`${API}/skills`);
      const data = (await res.json()) as { skills?: SkillItem[] };
      this.skills = data.skills ?? [];
    } catch {
      this.skills = [];
    }
  }

  private _skillTooltip(s: SkillItem): string {
    const params = Object.keys(s.params_schema ?? {}).length
      ? `\n파라미터: ${JSON.stringify(s.params_schema)}`
      : "";
    return `${s.description}${params}`;
  }

  private async _loadHistory(sid: string) {
    try {
      const res = await fetch(`${API}/sessions/${sid}`);
      if (!res.ok) {
        this.messages = [];
        return;
      }
      const data = (await res.json()) as { history?: HistoryTurn[] };
      const history = data.history ?? [];
      this.messages = history.map((t) => ({
        role: t.role,
        content: t.content,
        tool_calls: t.tool_calls,
      }));
    } catch {
      this.messages = [];
    }
  }

  private _relativeTime(ts: number): string {
    const sec = Math.floor((Date.now() / 1000) - ts);
    if (sec < 60) return "방금 전";
    if (sec < 3600) return `${Math.floor(sec / 60)}분 전`;
    if (sec < 86400) return `${Math.floor(sec / 3600)}시간 전`;
    return `${Math.floor(sec / 86400)}일 전`;
  }

  private _getStoredApi(): { api_key?: string; model?: string; provider?: string } {
    try {
      const s = localStorage.getItem("nanoquant_agent_api");
      if (s) return JSON.parse(s) as { api_key?: string; model?: string; provider?: string };
    } catch {}
    return {};
  }

  private async _newSession() {
    try {
      const res = await fetch(`${API}/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = (await res.json()) as { session_id?: string };
      if (data.session_id) {
        this.currentSessionId = data.session_id;
        this.messages = [];
        this.dispatchEvent(new CustomEvent("session-changed", { detail: data.session_id }));
        await this._loadSessions();
      }
    } catch {
      this.status = "세션 생성 실패";
    }
  }

  private async _selectSession(sid: string) {
    this.currentSessionId = sid;
    this.dispatchEvent(new CustomEvent("session-changed", { detail: sid }));
    await this._loadHistory(sid);
  }

  private _startEditTitle(s: SessionItem) {
    this.editingSessionId = s.id;
    this.editingTitle = s.title || "";
  }

  private _cancelEditTitle() {
    this.editingSessionId = null;
    this.editingTitle = "";
  }

  private async _saveTitle(sid: string) {
    const title = this.editingTitle.trim().slice(0, 120) || "새 대화";
    try {
      const res = await fetch(`${API}/sessions/${sid}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      });
      if (res.ok) {
        await this._loadSessions();
        this.editingSessionId = null;
        this.editingTitle = "";
      } else {
        this.status = "제목 수정에 실패했습니다.";
      }
    } catch {
      this.status = "제목 수정에 실패했습니다.";
    }
  }

  private async _deleteSession(sid: string, e: Event) {
    e.stopPropagation();
    if (!confirm("이 대화를 삭제할까요? 삭제된 대화는 복구할 수 없습니다.")) return;
    try {
      const res = await fetch(`${API}/sessions/${sid}`, { method: "DELETE" });
      if (!res.ok) return;
      if (this.currentSessionId === sid) {
        this.currentSessionId = this.sessions.find((s) => s.id !== sid)?.id ?? null;
        this.dispatchEvent(new CustomEvent("session-changed", { detail: this.currentSessionId }));
        if (this.currentSessionId) this._loadHistory(this.currentSessionId);
        else this.messages = [];
      }
      await this._loadSessions();
    } catch {}
  }

  private async _send() {
    const content = this.input.trim();
    if (!content || this.loading) return;
    this.loading = true;
    this.messages = [...this.messages, { role: "user", content }];
    this.input = "";
    this.status = "응답 대기 중...";

    const body: Record<string, unknown> = { content };
    if (this.currentSessionId) body.session_id = this.currentSessionId;
    if (this.forcedSkill) {
      body.force_skill = this.forcedSkill;
      this.forcedSkill = null;
    }
    const stored = this._getStoredApi();
    if (stored.api_key) body.api_key = stored.api_key;
    body.model = stored.model || stored.provider || "claude";

    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = (await res.json()) as {
        content?: string;
        session_id?: string;
        tool_calls?: ToolCall[];
        error?: string;
      };
      if (data.session_id) {
        this.currentSessionId = data.session_id;
        this.dispatchEvent(new CustomEvent("session-changed", { detail: data.session_id }));
        await this._loadSessions();
      }
      if (data.error) {
        this.messages = [...this.messages, { role: "assistant", content: `오류: ${data.error}` }];
      } else {
        this.messages = [
          ...this.messages,
          {
            role: "assistant",
            content: data.content ?? "",
            tool_calls: data.tool_calls ?? [],
          },
        ];
      }
      this.status = "";
    } catch (e) {
      this.messages = [
        ...this.messages,
        { role: "assistant", content: `요청 실패: ${e instanceof Error ? e.message : String(e)}` },
      ];
      this.status = "";
    } finally {
      this.loading = false;
    }
  }

  private async _approve(hitlId: string, approved: boolean) {
    const body = { hitl_id: hitlId, approved, session_id: this.currentSessionId };
    try {
      const res = await fetch(`${API}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = (await res.json()) as { content?: string };
      if (data.content) {
        this.messages = [...this.messages, { role: "assistant", content: data.content }];
      }
    } catch (e) {
      this.messages = [...this.messages, { role: "assistant", content: `승인 요청 실패: ${e}` }];
    }
  }

  private _suggestions = [
    "SOFI RSI 알려줘",
    "최근 결정 요약해줘",
    "등록된 스킬 목록 알려줘",
  ];

  render() {
    return html`
      <div class="layout">
        <aside class="sidebar-left">
          <button type="button" class="btn-new" @click=${() => this._newSession()}>+ 새 채팅</button>
          <p class="sidebar-title" style="margin-top:8px;">채팅</p>
          ${this.sessions.length === 0
            ? html`<p style="font-size:0.8125rem;color:var(--nq-text-muted);margin:8px 4px 0;text-align:center;">아직 대화가 없습니다.</p>`
            : ""}
          <div class="session-list">
            ${this.sessions.map(
              (s) => html`
                <div
                  class="session-item ${this.currentSessionId === s.id ? "active" : ""}"
                  @click=${(e: Event) => { if (this.editingSessionId !== s.id) this._selectSession(s.id); }}
                >
                  ${this.editingSessionId === s.id
                    ? html`
                        <input
                          class="edit-inp"
                          .value=${this.editingTitle}
                          @input=${(e: Event) => { this.editingTitle = (e.target as HTMLInputElement).value; }}
                          @keydown=${(e: KeyboardEvent) => {
                            e.stopPropagation();
                            if (e.key === "Enter") this._saveTitle(s.id);
                            if (e.key === "Escape") this._cancelEditTitle();
                          }}
                          @blur=${() => this._saveTitle(s.id)}
                          @click=${(e: Event) => e.stopPropagation()}
                        />
                      `
                    : html`
                        <div class="item-label">
                          <span class="item-title" title="${s.title}">${s.title || "새 대화"}</span>
                          <span class="item-time">${this._relativeTime(s.updated_at)}</span>
                        </div>
                      `}
                  ${this.editingSessionId !== s.id
                    ? html`
                        <button type="button" class="edit" title="제목 수정" @click=${(e: Event) => { e.stopPropagation(); this._startEditTitle(s); }} aria-label="제목 수정">✎</button>
                        <button type="button" class="del" title="삭제" @click=${(e: Event) => this._deleteSession(s.id, e)} aria-label="삭제">×</button>
                      `
                    : ""}
                </div>
              `
            )}
          </div>
        </aside>
        <div class="main">
          <h2 class="section-title">AI 채팅</h2>
          <p class="hint">
            지시를 입력하면 에이전트가 스킬을 호출해 답변합니다.
            API 키가 없으면 <a href="#" @click=${(e: Event) => { e.preventDefault(); this.dispatchEvent(new CustomEvent("set-tab", { detail: "settings", bubbles: true, composed: true })); }}>설정에서 입력하세요</a>.
          </p>
          <div class="log">
            ${this.messages.length === 0
              ? html`
                  <div class="empty-state">
                    <div class="empty-state-row">
                      <div class="empty-state-icon">💬</div>
                      <p class="empty-state-title">대화를 시작하세요</p>
                    </div>
                    <p class="empty-state-sub">아래 예시를 눌러 보내거나 메시지를 입력하세요.</p>
                    <div class="suggestion-chips">
                      ${this._suggestions.map(
                        (text) => html`
                          <button type="button" class="suggestion-chip" @click=${() => { this.input = text; }}>${text}</button>
                        `
                      )}
                    </div>
                  </div>
                `
              : this.messages.map(
                  (m) => html`
                    <div class="msg ${m.role}">
                      <div class="msg-role">${m.role === "user" ? "나" : "에이전트"}</div>
                      <div class="msg-content">${m.content}</div>
                      ${m.tool_calls?.length
                        ? html`
                            <div class="msg-tools">
                              스킬: ${m.tool_calls.map((t) => t.skill + (t.hitl_required ? " (승인 대기)" : "")).join(", ")}
                            </div>
                            ${m.tool_calls.some((t) => t.hitl_required && t.hitl_id)
                              ? html`
                                  <div class="hitl">
                                    ${m.tool_calls
                                      .filter((t) => t.hitl_required && t.hitl_id)
                                      .map(
                                        (t) => html`
                                          <button @click=${() => this._approve(t.hitl_id!, true)}>실행 허용</button>
                                          <button @click=${() => this._approve(t.hitl_id!, false)}>취소</button>
                                        `
                                      )}
                                  </div>
                                `
                              : ""}
                          `
                        : ""}
                    </div>
                  `
                )}
          </div>
          ${this.forcedSkill
            ? html`
                <div class="forced-skill-badge">
                  <span>이번 질의에 사용: <strong>${this.forcedSkill}</strong></span>
                  <button type="button" class="clear" @click=${() => { this.forcedSkill = null; }} aria-label="선택 해제">✕</button>
                </div>
              `
            : ""}
          <div class="input-bar">
            <input
              type="text"
              placeholder="지시를 입력하세요 (예: SOFI RSI 알려줘)"
              .value=${this.input}
              @input=${(e: Event) => { this.input = (e.target as HTMLInputElement).value; }}
              @keydown=${(e: KeyboardEvent) => { if (e.key === "Enter") this._send(); }}
            />
            <button class="btn-send" @click=${() => this._send()} ?disabled=${this.loading}>전송</button>
          </div>
          <p class="status ${this.loading ? "loading" : ""}">${this.status}</p>
        </div>

        <aside class="sidebar-right">
          <p class="sidebar-title">스킬 & 도구</p>
          <p style="font-size:0.6875rem;color:var(--nq-text-muted);margin:0 0 6px 2px;">클릭하면 이번 질의에 사용됩니다.</p>
          ${this.skills.length === 0
            ? html`<p style="font-size:0.8125rem;color:var(--nq-text-muted);">불러오는 중…</p>`
            : this.skills.map(
                (s) => html`
                  <div
                    class="skill-item ${this.forcedSkill === s.name ? "selected" : ""}"
                    title="${this._skillTooltip(s)}"
                    @click=${() => { this.forcedSkill = this.forcedSkill === s.name ? null : s.name; }}
                  >
                    <div class="skill-name">${s.name}</div>
                    <div class="skill-desc">${s.description}</div>
                  </div>
                `
              )}
        </aside>
      </div>
    `;
  }
}
