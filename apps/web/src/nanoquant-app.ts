import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";

type TabId = "dashboard" | "chat" | "backtest" | "monitor" | "kg" | "settings";

@customElement("nanoquant-app")
export class NanoQuantApp extends LitElement {
  static styles = css`
    :host {
      display: block;
      min-height: 100vh;
      background: var(--nq-bg);
      color: var(--nq-text);
      font-family: "Plus Jakarta Sans", system-ui, sans-serif;
    }
    .header-wrap {
      background: var(--nq-surface);
      border-bottom: 1px solid var(--nq-border);
      padding: 20px 24px 16px;
    }
    .header-top {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
    }
    .header-title {
      font-size: 1.5rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--nq-title);
      margin: 0 0 4px 0;
    }
    .header-sub {
      font-size: 0.875rem;
      color: var(--nq-text-muted);
      margin: 0;
    }
    .header-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .btn-refresh {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 14px;
      background: var(--nq-accent);
      color: #fff;
      border: none;
      border-radius: var(--nq-radius-sm);
      font-size: 0.875rem;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }
    .btn-refresh:hover { background: var(--nq-accent-hover); }
    .last-update {
      font-size: 0.8125rem;
      color: var(--nq-text-muted);
    }
    .tabs {
      display: flex;
      gap: 4px;
      margin-top: 16px;
      padding-top: 12px;
      border-top: 1px solid var(--nq-border);
    }
    .tabs a {
      padding: 8px 16px;
      color: var(--nq-text-muted);
      text-decoration: none;
      font-size: 0.875rem;
      font-weight: 500;
      border-radius: var(--nq-radius-sm);
      transition: color 0.15s, background 0.15s;
    }
    .tabs a:hover { color: var(--nq-text); background: var(--nq-surface-hover); }
    .tabs a.active { color: var(--nq-text); background: var(--nq-accent); color: #fff; }
    .pane { padding: 24px; max-width: 1000px; margin: 0 auto; }
    .card {
      background: var(--nq-surface);
      border: 1px solid var(--nq-border);
      border-radius: var(--nq-radius);
      padding: 20px;
    }
    .section-title { font-size: 1.125rem; font-weight: 600; color: var(--nq-title); margin: 0 0 8px 0; }
    .meta { font-size: 0.8125rem; color: var(--nq-text-muted); }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 12px 16px; text-align: left; }
  `;

  @state() activeTab: TabId = "chat";
  @state() sessionId: string | null = null;
  @state() lastUpdate = "";

  connectedCallback() {
    super.connectedCallback();
    this.addEventListener("set-tab", ((e: CustomEvent<TabId>) => {
      this.activeTab = e.detail;
    }) as EventListener);
    this._setLastUpdate();
  }

  private _setLastUpdate() {
    const now = new Date();
    this.lastUpdate = now.toLocaleTimeString("ko-KR", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }

  private _refresh() {
    this._setLastUpdate();
    this.dispatchEvent(new CustomEvent("app-refresh", { bubbles: true, composed: true }));
  }

  render() {
    return html`
      <header class="header-wrap">
        <div class="header-top">
          <div>
            <h1 class="header-title">NanoQuant AI</h1>
            <p class="header-sub">실시간 퀀트 에이전트 모니터링 및 통합 관리</p>
          </div>
          <div class="header-actions">
            <button type="button" class="btn-refresh" @click=${this._refresh}>↻ 새로고침</button>
            <span class="last-update">Last Update: ${this.lastUpdate}</span>
          </div>
        </div>
        <nav class="tabs">
          <a href="#" class="${this.activeTab === "dashboard" ? "active" : ""}" @click=${() => this._setTab("dashboard")}>대시보드</a>
          <a href="#" class="${this.activeTab === "chat" ? "active" : ""}" @click=${() => this._setTab("chat")}>AI 채팅</a>
          <a href="#" class="${this.activeTab === "backtest" ? "active" : ""}" @click=${() => this._setTab("backtest")}>백테스트</a>
          <a href="#" class="${this.activeTab === "monitor" ? "active" : ""}" @click=${() => this._setTab("monitor")}>모니터</a>
          <a href="#" class="${this.activeTab === "kg" ? "active" : ""}" @click=${() => this._setTab("kg")}>지식그래프</a>
          <a href="#" class="${this.activeTab === "settings" ? "active" : ""}" @click=${() => this._setTab("settings")}>설정</a>
        </nav>
      </header>
      <main class="pane">
        ${this.activeTab === "dashboard" ? html`<dashboard-tab></dashboard-tab>` : ""}
        ${this.activeTab === "chat" ? html`<chat-tab .sessionId=${this.sessionId} @session-changed=${(e: CustomEvent) => { this.sessionId = e.detail; }}></chat-tab>` : ""}
        ${this.activeTab === "backtest" ? html`<backtest-tab></backtest-tab>` : ""}
        ${this.activeTab === "monitor" ? html`<monitor-tab></monitor-tab>` : ""}
        ${this.activeTab === "kg" ? html`<kg-tab @navigate-to=${(e: CustomEvent<{ tab: TabId; sessionId?: string }>) => { const d = e.detail; if (d) { this.activeTab = d.tab; if (d.sessionId != null) this.sessionId = d.sessionId; } }}></kg-tab>` : ""}
        ${this.activeTab === "settings" ? html`<settings-tab></settings-tab>` : ""}
      </main>
    `;
  }

  private _setTab(tab: TabId) {
    this.activeTab = tab;
  }
}
