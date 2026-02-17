"""
db_viewer.py - Real-time SQLite viewer for NanoQuant decisions, reflections & portfolio

Run separately from the bot:
  python db_viewer.py

Open http://127.0.0.1:5050 in browser. Page auto-refreshes every 10 seconds.
"""

import os
import json
from flask import Flask, render_template_string, request, jsonify
from core import TradingDatabase
from util import path_for
from ui import parse_decision_meta, get_followup_data, load_portfolio, get_watchlist

app = Flask(__name__)
DB_PATH = os.environ.get('NANOQUANT_DB', path_for('nanoquant_v1.db'))
TRADE_HISTORY_PATH = os.environ.get('TRADE_HISTORY_PATH', path_for('trade_history.json'))
db = TradingDatabase(DB_PATH)

REFRESH_SECONDS = int(os.environ.get('DB_VIEWER_REFRESH_SECONDS', 0))  # 0 = 자동 리프레시 비활성화
DECISIONS_LIMIT = int(os.environ.get('DB_VIEWER_DECISIONS_LIMIT', 50))
DECISIONS_PER_PAGE = int(os.environ.get('DB_VIEWER_DECISIONS_PER_PAGE', 20))  # 최근 결정 탭 페이징
REFLECTIONS_LIMIT = int(os.environ.get('DB_VIEWER_REFLECTIONS_LIMIT', 20))

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {% if refresh_seconds > 0 %}
  <meta http-equiv="refresh" content="{{ refresh_seconds }}; url=?tab={{ active_tab }}">
  {% endif %}
  <title>나노퀀트 DB 뷰어</title>
  <style>
    .tabs { display: flex; gap: 0; margin-bottom: 16px; border-bottom: 1px solid #334155; }
    .tabs a {
      padding: 10px 20px;
      color: #94a3b8;
      text-decoration: none;
      border-bottom: 2px solid transparent;
      margin-bottom: -1px;
    }
    .tabs a:hover { color: #e2e4e8; }
    .tabs a.active { color: #7dd3fc; border-bottom-color: #7dd3fc; }
    .tab-pane { display: none; }
    .tab-pane.active { display: block; }
    * { box-sizing: border-box; }
    body {
      font-family: 'Consolas', 'Monaco', monospace;
      background: #1a1d23;
      color: #e2e4e8;
      margin: 0;
      padding: 16px;
      font-size: 13px;
    }
    h1 { font-size: 1.25rem; margin: 0 0 8px 0; color: #7dd3fc; }
    .meta {
      color: #94a3b8;
      margin-bottom: 20px;
      font-size: 12px;
    }
    section {
      margin-bottom: 28px;
    }
    section h2 {
      font-size: 1rem;
      color: #a5b4fc;
      margin: 0 0 10px 0;
      padding-bottom: 6px;
      border-bottom: 1px solid #334155;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      background: #0f1116;
      border-radius: 8px;
      overflow: hidden;
    }
    th, td {
      padding: 8px 12px;
      text-align: left;
      border-bottom: 1px solid #1e293b;
    }
    th {
      background: #1e293b;
      color: #94a3b8;
      font-weight: 600;
    }
    tr:hover { background: #1e293b; }
    .action-BUY  { color: #86efac; }
    .action-SELL { color: #fca5a5; }
    .action-HOLD { color: #fcd34d; }
    .success { color: #86efac; }
    .fail { color: #fca5a5; }
    .reasoning { max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .note { max-width: 360px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .source-data { font-size: 11px; color: #94a3b8; padding: 8px; background: #1e293b; border-radius: 4px; margin-top: 6px; max-width: 480px; }
    .source-data ul { margin: 4px 0 0 0; padding-left: 18px; }
    .source-data li { margin: 2px 0; }
    .source-data strong { color: #a5b4fc; }
    details summary { cursor: pointer; color: #7dd3fc; }
  </style>
</head>
<body>
  <h1>나노퀀트 DB 뷰어</h1>
  <p class="meta">DB: {{ db_path }} | 자동 새로고침: {% if refresh_seconds > 0 %}{{ refresh_seconds }}초{% else %}꺼짐{% endif %} | 마지막 로드: {{ last_load }}
    <a href="{{ request.url }}" style="margin-left:12px;display:inline-block;padding:4px 12px;background:linear-gradient(135deg,#38bdf8,#0ea5e9);color:#0f172a;text-decoration:none;border-radius:6px;font-weight:600;">새로고침</a>
  </p>

  <nav class="tabs">
    <a href="?tab=decisions" class="{{ 'active' if active_tab == 'decisions' else '' }}">최근 결정</a>
    <a href="?tab=missed_profit" class="{{ 'active' if active_tab == 'missed_profit' else '' }}">판단 사후 추적</a>
    <a href="?tab=portfolio" class="{{ 'active' if active_tab == 'portfolio' else '' }}">포트폴리오</a>
    <a href="?tab=forecast" class="{{ 'active' if active_tab == 'forecast' else '' }}">예측</a>
  </nav>

  <section id="tab-decisions" class="tab-pane {{ 'active' if active_tab == 'decisions' else '' }}">
    <h2 id="decisions-header">최근 결정 (전체 {{ decisions_total }}건, {{ decisions|length }}건 표시)</h2>
    <table>
      <thead>
        <tr>
          <th>루프</th>
          <th>시간</th>
          <th>종목</th>
          <th>행동</th>
          <th>가격</th>
          <th>금액</th>
          <th>확신도</th>
          <th>리스크</th>
          <th>트리거</th>
          <th>RSI (15m/1h/1d)</th>
          <th>SMA (15m/1h/1d)</th>
          <th>MACD (15m/1h/1d)</th>
          <th>BB%B (15m/1h/1d)</th>
          <th>Vol비율</th>
          <th>사유</th>
          <th>수집 데이터</th>
        </tr>
      </thead>
      <tbody id="decisions-tbody">
        {% for d in decisions %}
        <tr>
          <td title="{{ d.cycle_id or '' }}"><span class="cycle-dot" style="display:inline-block;width:10px;height:10px;border-radius:3px;background:{{ d._cycle_color or '#475569' }};"></span></td>
          <td>{{ d.timestamp[:19] if d.timestamp else '-' }}</td>
          <td>{{ d.ticker }}</td>
          <td class="action-{{ d.action }}">{% if d.action == 'BUY' %}매수{% elif d.action == 'SELL' %}매도{% else %}대기{% endif %}</td>
          <td>{{ "%.2f"|format(d.price) if d.price is not none else '-' }}</td>
          <td>{{ d.get('_amount_display', '-') }}</td>
          <td>{{ "%.0f"|format(d.confidence) if d.confidence is not none else '-' }}%</td>
          <td>{{ d.risk_level or '-' }}</td>
          <td>{{ d.trigger_score or '-' }}</td>
          <td>{{ d._rsi if d._rsi is not none else '-' }}</td>
          <td>{{ d._sma if d._sma is not none else '-' }}</td>
          <td>{{ d._macd if d._macd is not none else '-' }}</td>
          <td>{{ d._bb_pct if d._bb_pct is not none else '-' }}</td>
          <td>{{ ("%.2f"|format(d._vol_ratio) + "x") if d._vol_ratio is not none else '-' }}</td>
          <td class="reasoning" title="{{ d.reasoning or '' }}">{{ (d.reasoning or '-')[:60] }}{% if (d.reasoning or '')|length > 60 %}...{% endif %}</td>
          <td>
            {% if d.meta %}
            <details>
              <summary>뉴스 {{ d.meta.get('news_count', 0) }}건 · 트리거 {{ (d.meta.get('trigger_reasons') or [])|length }}개{% if d.meta.get('hold_duration_minutes') is not none %} · 보유 {{ d.meta.hold_duration_minutes }}분{% endif %}</summary>
              <div class="source-data">
                {% if d.meta.get('news_headlines') %}
                <strong>뉴스 헤드라인:</strong>
                <ul>
                  {% for n in d.meta.news_headlines %}
                  <li>{% if n.get('link') %}<a href="{{ n.link }}" target="_blank" rel="noopener" style="color:#7dd3fc;">{% endif %}{{ (n.get('title') or '-')[:80] }}{% if (n.get('title') or '')|length > 80 %}...{% endif %}{% if n.get('link') %}</a>{% endif %} <span style="color:#64748b;">({{ n.get('time', '') }})</span></li>
                  {% endfor %}
                </ul>
                {% elif d.meta.get('news_count', 0) > 0 %}
                <em>뉴스 {{ d.meta.news_count }}건 수집됨 (헤드라인 상세 미저장 · 이전 형식 기록)</em>
                {% else %}
                <em>수집된 뉴스 없음</em>
                {% endif %}
                {% if d.meta.get('trigger_reasons') %}
                <strong>트리거 사유:</strong>
                <ul>
                  {% for r in d.meta.trigger_reasons %}
                  <li>{{ r }}</li>
                  {% endfor %}
                </ul>
                {% endif %}
                {% if d.meta.get('matched_keywords') %}
                <strong>매칭 키워드:</strong> {{ d.meta.matched_keywords|join(', ') }}
                {% endif %}
              </div>
            </details>
            {% else %}
            -
            {% endif %}
          </td>
        </tr>
        {% else %}
        <tr><td colspan="16">아직 결정 내역이 없습니다.</td></tr>
        {% endfor %}
      </tbody>
    </table>
    <div id="decisions-pagination" class="pagination" style="margin-top:16px;display:{{ 'flex' if decisions_total > decisions_per_page else 'none' }};align-items:center;gap:8px;flex-wrap:wrap;">
      <button type="button" id="decisions-prev" data-page="{{ page - 1 }}" style="color:#7dd3fc;padding:6px 12px;background:#1e293b;border:1px solid #334155;border-radius:6px;cursor:pointer;font-size:13px;" {{ 'disabled' if page <= 1 else '' }}>← 이전</button>
      <span id="decisions-page-info" style="color:#94a3b8;margin:0 8px;">{{ page }} / {{ total_pages }}</span>
      <button type="button" id="decisions-next" data-page="{{ page + 1 }}" style="color:#7dd3fc;padding:6px 12px;background:#1e293b;border:1px solid #334155;border-radius:6px;cursor:pointer;font-size:13px;" {{ 'disabled' if page >= total_pages else '' }}>다음 →</button>
    </div>
  </section>

  <section id="tab-missed_profit" class="tab-pane {{ 'active' if active_tab == 'missed_profit' else '' }}">
    <h2>판단 사후 추적 (옳고 그름 + 학습 메모)</h2>
    <p class="meta" style="margin-bottom: 12px;">모든 판단 후 24h 경과 시점. BUY: 상승=올바름. SELL: 하락=올바름. HOLD: 하락=올바름. LLM 학습 메모 포함.</p>
    <table>
      <thead>
        <tr>
          <th>결정 시각</th>
          <th>행동</th>
          <th>종목</th>
          <th>결정가</th>
          <th>후속가</th>
          <th>변동 %</th>
          <th>옳고 그름</th>
          <th>사유</th>
          <th>학습 메모</th>
          <th>판단 맥락</th>
        </tr>
      </thead>
      <tbody>
        {% for h in hold_followups %}
        <tr>
          <td>{{ (h.timestamp or '')[:19] }}</td>
          <td class="action-{{ h.action }}">{% if h.action == 'BUY' %}매수{% elif h.action == 'SELL' %}매도{% else %}대기{% endif %}</td>
          <td>{{ h.ticker }}</td>
          <td>${{ "%.2f"|format(h.decision_price) if h.decision_price is not none else '-' }}</td>
          <td>${{ "%.2f"|format(h.followup_price) if h.followup_price is not none else '-' }}</td>
          <td class="{{ 'success' if (h.pnl_pct or 0) > 0 else ('fail' if (h.pnl_pct or 0) < 0 else '') }}">{{ "%+.2f"|format(h.pnl_pct) if h.pnl_pct is not none else '-' }}%</td>
          <td class="{{ 'success' if h._is_correct else 'fail' }}">{{ h._correctness_label or '-' }}</td>
          <td class="reasoning" title="{{ h.reasoning or '' }}">{{ (h.reasoning or '-')[:60] }}{% if (h.reasoning or '')|length > 60 %}...{% endif %}</td>
          <td class="note" title="{{ h.reflection_note or '' }}">{{ (h.reflection_note or '-')[:80] }}{% if (h.reflection_note or '')|length > 80 %}...{% endif %}</td>
          <td>
            {% if h.meta %}
            <details>
              <summary>트리거 {{ (h.meta.get('trigger_reasons') or [])|length }}개 · 뉴스 {{ h.meta.get('news_count', 0) }}건</summary>
              <div class="source-data">
                {% if h.meta.get('trigger_reasons') %}
                <strong>트리거:</strong>
                <ul>{% for r in h.meta.trigger_reasons %}<li>{{ r }}</li>{% endfor %}</ul>
                {% endif %}
                {% if h.meta.get('quant_indicators') %}
                <strong>지표:</strong> (15m/1h/1d RSI, SMA 등 저장됨)
                {% endif %}
              </div>
            </details>
            {% else %}
            -
            {% endif %}
          </td>
        </tr>
        {% else %}
        <tr><td colspan="10">판단 사후 추적 내역 없음. 24h 경과 후 07:00에 자동 수집됩니다.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </section>

  <section id="tab-portfolio" class="tab-pane {{ 'active' if active_tab == 'portfolio' else '' }}">
    <h2>포트폴리오 (시뮬레이션)</h2>
    {% if portfolio %}
    <div class="source-data" style="margin-bottom: 12px;">
      <strong>현금</strong>: ${{ "%.2f"|format(portfolio.cash) }} &nbsp;|&nbsp;
      <strong>평가총액</strong>: ${{ "%.2f"|format(portfolio.total_value) }} &nbsp;|&nbsp;
      <strong>손익</strong>: <span class="{{ 'success' if portfolio.pnl >= 0 else 'fail' }}">{{ "%+.2f"|format(portfolio.pnl) }} ({{ "%+.1f"|format(portfolio.pnl_pct) }}%)</span>
    </div>
    <table>
      <thead>
        <tr>
          <th>종목</th>
          <th>수량</th>
          <th>평균단가</th>
          <th>현재가</th>
          <th>평가금액</th>
          <th>손익 %</th>
        </tr>
      </thead>
      <tbody>
        {% for p in portfolio.positions %}
        <tr>
          <td>{{ p.ticker }}</td>
          <td>{{ "%.4f"|format(p.qty) }}</td>
          <td>${{ "%.2f"|format(p.avg_price) }}</td>
          <td>${{ "%.2f"|format(p.current_price) if p.current_price is not none else '-' }}</td>
          <td>${{ "%.2f"|format(p.value) if p.value is not none else '-' }}</td>
          <td class="{{ 'success' if (p.pnl_pct or 0) >= 0 else 'fail' }}">{{ ("%+.2f"|format(p.pnl_pct) + "%") if p.pnl_pct is not none else '-' }}</td>
        </tr>
        {% else %}
        <tr><td colspan="6">보유 종목 없음</td></tr>
        {% endfor %}
      </tbody>
    </table>
    <h3 style="font-size: 0.95rem; margin: 20px 0 8px 0; color: #a5b4fc;">거래 내역 (실제 매수/매도)</h3>
    <table>
      <thead>
        <tr>
          <th>시간</th>
          <th>종목</th>
          <th>행동</th>
          <th>수량</th>
          <th>가격</th>
          <th>금액</th>
        </tr>
      </thead>
      <tbody>
        {% for t in portfolio.trade_history %}
        <tr>
          <td>{{ t.timestamp[:19] if t.timestamp else '-' }}</td>
          <td>{{ t.ticker }}</td>
          <td class="action-{{ t.action }}">{% if t.action == 'BUY' %}매수{% else %}매도{% endif %}</td>
          <td>{{ "%.4f"|format(t.shares) if t.shares is not none else '-' }}</td>
          <td>${{ "%.2f"|format(t.price) if t.price is not none else '-' }}</td>
          <td>${{ "%.2f"|format(t.amount) if t.amount is not none else '-' }}</td>
        </tr>
        {% else %}
        <tr><td colspan="6">거래 내역 없음</td></tr>
        {% endfor %}
      </tbody>
    </table>
    <p class="meta" style="margin-top: 8px;">초기자본: ${{ "%.2f"|format(portfolio.initial_cash) }} | 파일: {{ trade_history_path }}</p>
    {% else %}
    <p class="meta">trade_history.json이 없거나 비어 있습니다. main.py 실행 후 거래가 발생하면 표시됩니다.</p>
    {% endif %}
  </section>

  <section id="tab-forecast" class="tab-pane {{ 'active' if active_tab == 'forecast' else '' }}">
    <h2>가격 예측 (참고용)</h2>
    <p class="meta">등록 티커의 과거 주가로 미래 구간을 예측합니다. 실제 투자 결정과 무관합니다.</p>
    <div class="forecast-controls" style="margin-bottom: 20px; display: flex; flex-wrap: wrap; align-items: center; gap: 14px; padding: 14px 18px; background: rgba(15,23,42,0.6); border-radius: 8px; border: 1px solid rgba(51,65,85,0.5);">
      <label style="display:flex;align-items:center;gap:8px;">종목
        <select id="forecast-ticker" style="background:#1e293b;color:#e2e4e8;border:1px solid #475569;padding:8px 12px;border-radius:6px;min-width:100px;font-size:13px;">
          {% for t in watchlist %}
          <option value="{{ t }}">{{ t }}</option>
          {% else %}
          <option value="">watchlist 없음</option>
          {% endfor %}
        </select>
      </label>
      <label style="display:flex;align-items:center;gap:8px;">모델
        <select id="forecast-model" style="background:#1e293b;color:#e2e4e8;border:1px solid #475569;padding:8px 12px;border-radius:6px;min-width:140px;font-size:13px;">
          <option value="arima" selected>ARIMA</option>
          <option value="prophet">Prophet</option>
          <option value="linear">가중치 선형</option>
          <option value="ma">지수이동평균</option>
        </select>
      </label>
      <button type="button" id="forecast-load" style="background:linear-gradient(135deg,#38bdf8,#0ea5e9);color:#0f172a;border:none;padding:8px 18px;border-radius:6px;cursor:pointer;font-weight:600;font-size:13px;box-shadow:0 2px 8px rgba(56,189,248,0.3);">적용</button>
    </div>
    <div id="forecast-error" class="meta" style="color:#fca5a5;display:none;"></div>
    <div class="forecast-chart-wrap" style="position:relative;height:420px;background:linear-gradient(135deg,#0f172a 0%,#1e293b 50%,#0f172a 100%);border-radius:12px;padding:20px;border:1px solid rgba(148,163,184,0.15);box-shadow:0 4px 24px rgba(0,0,0,0.3);">
      <canvas id="forecast-chart"></canvas>
    </div>
  </section>
</body>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
(function() {
  function esc(s) { if (s == null || s === '') return ''; return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
  function buildMetaCell(meta) {
    if (!meta || typeof meta !== 'object') return '-';
    var nc = meta.news_count || 0;
    var tr = (meta.trigger_reasons || []).length;
    var hold = meta.hold_duration_minutes;
    var sum = '뉴스 ' + nc + '건 · 트리거 ' + tr + '개' + (hold != null ? ' · 보유 ' + hold + '분' : '');
    var inner = '';
    if (meta.news_headlines && meta.news_headlines.length) {
      inner += '<strong>뉴스 헤드라인:</strong><ul>';
      meta.news_headlines.forEach(function(n) {
        var t = (n.title || '-').substring(0, 80);
        if ((n.title || '').length > 80) t += '...';
        var lnk = n.link ? '<a href="' + esc(n.link) + '" target="_blank" rel="noopener" style="color:#7dd3fc;">' : '';
        inner += '<li>' + lnk + esc(t) + (n.link ? '</a>' : '') + ' <span style="color:#64748b;">(' + esc(n.time || '') + ')</span></li>';
      });
      inner += '</ul>';
    } else if (nc > 0) {
      inner += '<em>뉴스 ' + nc + '건 수집됨 (헤드라인 상세 미저장 · 이전 형식 기록)</em>';
    } else {
      inner += '<em>수집된 뉴스 없음</em>';
    }
    if (meta.trigger_reasons && meta.trigger_reasons.length) {
      inner += '<strong>트리거 사유:</strong><ul>';
      meta.trigger_reasons.forEach(function(r) { inner += '<li>' + esc(r) + '</li>'; });
      inner += '</ul>';
    }
    if (meta.matched_keywords && meta.matched_keywords.length) {
      inner += '<strong>매칭 키워드:</strong> ' + esc(meta.matched_keywords.join(', '));
    }
    return '<details><summary>' + esc(sum) + '</summary><div class="source-data">' + inner + '</div></details>';
  }
  function buildRow(d) {
    var ts = (d.timestamp || '-').substring(0, 19);
    var actLabel = d.action === 'BUY' ? '매수' : (d.action === 'SELL' ? '매도' : '대기');
    var priceStr = d.price != null ? (Number(d.price).toFixed(2)) : '-';
    var amtStr = d._amount_display || '-';
    var confStr = d.confidence != null ? (Number(d.confidence).toFixed(0) + '%') : '-';
    var volStr = d._vol_ratio != null ? (Number(d._vol_ratio).toFixed(2) + 'x') : '-';
    var reason = (d.reasoning || '-').substring(0, 60);
    if ((d.reasoning || '').length > 60) reason += '...';
    return '<tr>' +
      '<td title="' + esc(d.cycle_id || '') + '"><span class="cycle-dot" style="display:inline-block;width:10px;height:10px;border-radius:3px;background:' + esc(d._cycle_color || '#475569') + ';"></span></td>' +
      '<td>' + esc(ts) + '</td>' +
      '<td>' + esc(d.ticker || '-') + '</td>' +
      '<td class="action-' + esc(d.action || '') + '">' + esc(actLabel) + '</td>' +
      '<td>' + esc(priceStr) + '</td>' +
      '<td>' + esc(amtStr) + '</td>' +
      '<td>' + esc(confStr) + '</td>' +
      '<td>' + esc(d.risk_level || '-') + '</td>' +
      '<td>' + esc(d.trigger_score != null ? String(d.trigger_score) : '-') + '</td>' +
      '<td>' + esc(d._rsi != null ? String(d._rsi) : '-') + '</td>' +
      '<td>' + esc(d._sma != null ? String(d._sma) : '-') + '</td>' +
      '<td>' + esc(d._macd != null ? String(d._macd) : '-') + '</td>' +
      '<td>' + esc(d._bb_pct != null ? String(d._bb_pct) : '-') + '</td>' +
      '<td>' + esc(volStr) + '</td>' +
      '<td class="reasoning" title="' + esc(d.reasoning || '') + '">' + esc(reason) + '</td>' +
      '<td>' + buildMetaCell(d.meta) + '</td>' +
      '</tr>';
  }
  function loadDecisionsPage(page) {
    var tbody = document.getElementById('decisions-tbody');
    var header = document.getElementById('decisions-header');
    var pag = document.getElementById('decisions-pagination');
    var prevBtn = document.getElementById('decisions-prev');
    var nextBtn = document.getElementById('decisions-next');
    var info = document.getElementById('decisions-page-info');
    if (!tbody || !header) return;
    tbody.innerHTML = '<tr><td colspan="16" style="color:#94a3b8;">로딩 중...</td></tr>';
    fetch('/api/decisions?page=' + encodeURIComponent(page))
      .then(function(r) { return r.json(); })
      .then(function(data) {
        var html = '';
        if (!data.decisions || data.decisions.length === 0) {
          html = '<tr><td colspan="16">아직 결정 내역이 없습니다.</td></tr>';
        } else {
          data.decisions.forEach(function(d) { html += buildRow(d); });
        }
        tbody.innerHTML = html;
        header.textContent = '최근 결정 (전체 ' + (data.decisions_total || 0) + '건, ' + (data.decisions ? data.decisions.length : 0) + '건 표시)';
        if (info) info.textContent = (data.page || 1) + ' / ' + (data.total_pages || 1);
        if (prevBtn) { prevBtn.disabled = (data.page || 1) <= 1; prevBtn.dataset.page = (data.page || 1) - 1; }
        if (nextBtn) { nextBtn.disabled = (data.page || 1) >= (data.total_pages || 1); nextBtn.dataset.page = (data.page || 1) + 1; }
        if (pag && (data.decisions_total || 0) > (data.decisions_per_page || 20)) pag.style.display = 'flex';
      })
      .catch(function(e) {
        tbody.innerHTML = '<tr><td colspan="16" style="color:#fca5a5;">로드 실패: ' + esc(e.message) + '</td></tr>';
      });
  }
  var prevBtn = document.getElementById('decisions-prev');
  var nextBtn = document.getElementById('decisions-next');
  if (prevBtn) prevBtn.addEventListener('click', function() { var p = parseInt(prevBtn.dataset.page, 10); if (p >= 1) loadDecisionsPage(p); });
  if (nextBtn) nextBtn.addEventListener('click', function() { var p = parseInt(nextBtn.dataset.page, 10); if (p >= 1) loadDecisionsPage(p); });
})();
</script>
<script>
(function() {
  var chart = null;
  function getSelected() {
    var ticker = document.getElementById('forecast-ticker').value;
    var model = document.getElementById('forecast-model').value;
    return { ticker: ticker, model: model };
  }
  function draw(data) {
    var ctx = document.getElementById('forecast-chart').getContext('2d');
    if (chart) chart.destroy();
    if (data.error) return;

    var actual = data.actual_full || [];
    var predicted = data.predicted_full || data.forecast_full || [];
    var labels = data.labels_full || [];

    var gradActual = ctx.createLinearGradient(0, 0, 0, 400);
    gradActual.addColorStop(0, 'rgba(125, 211, 252, 0.25)');
    gradActual.addColorStop(1, 'rgba(125, 211, 252, 0)');

    var gradPred = ctx.createLinearGradient(0, 0, 0, 400);
    gradPred.addColorStop(0, 'rgba(251, 191, 36, 0.12)');
    gradPred.addColorStop(1, 'rgba(251, 191, 36, 0)');

    chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          { label: '실제', data: actual,
            borderColor: '#38bdf8', borderWidth: 2.5,
            backgroundColor: gradActual, fill: true,
            tension: 0.4, pointRadius: 0, pointHoverRadius: 6,
            pointBackgroundColor: '#38bdf8', pointBorderColor: '#0f172a', pointBorderWidth: 2
          },
          { label: '예측(퀀트)', data: predicted,
            borderColor: '#fbbf24', borderWidth: 2.5, borderDash: [8, 4],
            backgroundColor: gradPred, fill: true,
            tension: 0.4, pointRadius: 0, pointHoverRadius: 6,
            pointBackgroundColor: '#fbbf24', pointBorderColor: '#0f172a', pointBorderWidth: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { intersect: false, mode: 'index' },
        plugins: {
          legend: {
            position: 'top',
            labels: { color: '#e2e4e8', font: { family: 'system-ui', size: 13 }, usePointStyle: true }
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(148,163,184,0.1)' },
            ticks: { color: '#94a3b8', maxTicksLimit: 12, font: { size: 11 } }
          },
          y: {
            grid: { color: 'rgba(148,163,184,0.1)' },
            ticks: { color: '#94a3b8', font: { size: 11 } }
          }
        }
      }
    });
  }
  function load() {
    var sel = getSelected();
    if (!sel.ticker) return;
    var errEl = document.getElementById('forecast-error');
    errEl.style.display = 'none';
    fetch('/api/forecast/' + encodeURIComponent(sel.ticker) + '?model=' + encodeURIComponent(sel.model))
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.error) { errEl.textContent = data.error; errEl.style.display = 'block'; return; }
        draw(data);
      })
      .catch(function(e) { errEl.textContent = '로드 실패: ' + e.message; errEl.style.display = 'block'; });
  }
  document.getElementById('forecast-load').addEventListener('click', load);
  if (document.getElementById('tab-forecast').classList.contains('active')) {
    load();
  }
})();
</script>
</html>
"""


@app.route('/api/decisions')
def api_decisions():
    """페이징용: decisions JSON (테이블만 갱신, 전체 새로고침 없음)"""
    page = max(1, int(request.args.get('page', 1)))
    decisions_total = db.count_decisions()
    total_pages = max(1, (decisions_total + DECISIONS_PER_PAGE - 1) // DECISIONS_PER_PAGE)
    page = min(page, total_pages)
    offset = (page - 1) * DECISIONS_PER_PAGE

    decisions = db.get_decisions(limit=DECISIONS_PER_PAGE, offset=offset)
    decisions = parse_decision_meta(decisions)

    rows = [dict(d) for d in decisions]
    return jsonify({
        'decisions': rows,
        'decisions_total': decisions_total,
        'page': page,
        'total_pages': total_pages,
        'decisions_per_page': DECISIONS_PER_PAGE,
    })


@app.route('/api/forecast/<ticker>')
def api_forecast(ticker):
    """예측 차트용 JSON. model=ma|linear|arima|prophet (일봉만)"""
    if not (ticker and ticker.strip()):
        return jsonify({'error': '티커를 선택하세요'}), 400
    model = request.args.get('model', 'linear')
    try:
        from forecast import get_forecast_chart_payload
        data = get_forecast_chart_payload(ticker, model=model)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/')
def index():
    from datetime import datetime
    active_tab = request.args.get('tab', 'decisions')
    if active_tab not in ('decisions', 'missed_profit', 'portfolio', 'forecast'):
        active_tab = 'decisions'

    page = max(1, int(request.args.get('page', 1)))
    decisions_total = db.count_decisions()
    total_pages = max(1, (decisions_total + DECISIONS_PER_PAGE - 1) // DECISIONS_PER_PAGE)
    page = min(page, total_pages)
    offset = (page - 1) * DECISIONS_PER_PAGE

    decisions = db.get_decisions(limit=DECISIONS_PER_PAGE, offset=offset)
    decisions = parse_decision_meta(decisions)
    hold_followups = get_followup_data(db, limit=100)

    initial_cash = float(os.environ.get('TRADING_CAPITAL', 75))
    portfolio = load_portfolio(TRADE_HISTORY_PATH, initial_cash=initial_cash)

    watchlist = get_watchlist()

    return render_template_string(
        HTML_TEMPLATE,
        db_path=DB_PATH,
        refresh_seconds=REFRESH_SECONDS,
        last_load=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        decisions=decisions,
        decisions_total=decisions_total,
        decisions_per_page=DECISIONS_PER_PAGE,
        page=page,
        total_pages=total_pages,
        hold_followups=hold_followups,
        portfolio=portfolio,
        active_tab=active_tab,
        trade_history_path=TRADE_HISTORY_PATH,
        watchlist=watchlist,
    )


def main():
    port = int(os.environ.get('DB_VIEWER_PORT', 5050))
    print(f"DB Viewer: http://127.0.0.1:{port}")
    print(f"DB: {DB_PATH} | Refresh: {REFRESH_SECONDS}s")
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
