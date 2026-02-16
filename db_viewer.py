"""
db_viewer.py - Real-time SQLite viewer for NanoQuant decisions, reflections & portfolio

Run separately from the bot:
  python db_viewer.py

Open http://127.0.0.1:5050 in browser. Page auto-refreshes every 10 seconds.
"""

import os
import json
from flask import Flask, render_template_string, request
from database import TradingDatabase

app = Flask(__name__)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('NANOQUANT_DB', os.path.join(_BASE_DIR, 'nanoquant_v1.db'))
TRADE_HISTORY_PATH = os.environ.get('TRADE_HISTORY_PATH', os.path.join(_BASE_DIR, 'trade_history.json'))
db = TradingDatabase(DB_PATH)

REFRESH_SECONDS = 10
DECISIONS_LIMIT = 50
REFLECTIONS_LIMIT = 20

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="{{ refresh_seconds }}; url=?tab={{ active_tab }}">
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
  <p class="meta">DB: {{ db_path }} | 자동 새로고침: {{ refresh_seconds }}초 | 마지막 로드: {{ last_load }}</p>

  <nav class="tabs">
    <a href="?tab=decisions" class="{{ 'active' if active_tab == 'decisions' else '' }}">최근 결정</a>
    <a href="?tab=missed_profit" class="{{ 'active' if active_tab == 'missed_profit' else '' }}">판단 사후 추적</a>
    <a href="?tab=portfolio" class="{{ 'active' if active_tab == 'portfolio' else '' }}">포트폴리오</a>
  </nav>

  <section id="tab-decisions" class="tab-pane {{ 'active' if active_tab == 'decisions' else '' }}">
    <h2>최근 결정 (최신 {{ decisions|length }}건)</h2>
    <table>
      <thead>
        <tr>
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
      <tbody>
        {% for d in decisions %}
        <tr>
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
              <summary>뉴스 {{ d.meta.get('news_count', 0) }}건 · 트리거 {{ (d.meta.get('trigger_reasons') or [])|length }}개</summary>
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
        <tr><td colspan="15">아직 결정 내역이 없습니다.</td></tr>
        {% endfor %}
      </tbody>
    </table>
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
</body>
</html>
"""


def _parse_decision_meta(decisions):
    """Parse metadata JSON, attach as 'meta', and extract quant columns for display.
    Supports both flat quant_indicators (legacy) and multi-timeframe {15m, 1h, 1d} format."""
    for d in decisions:
        try:
            d['meta'] = json.loads(d['metadata']) if d.get('metadata') else {}
        except (json.JSONDecodeError, TypeError):
            d['meta'] = {}
        # 금액 표시: BUY=$5.00, SELL=50%, 대기(HOLD)=-
        act, amt = d.get('action', ''), d.get('amount')
        d['_amount_display'] = f'${float(amt):.2f}' if act == 'BUY' and amt is not None else (f'{float(amt):.0f}%' if act == 'SELL' and amt is not None else '-')
        qi = d.get('meta', {}).get('quant_indicators') or {}
        # Multi-timeframe: { '15m': {...}, '1h': {...}, '1d': {...} }
        if isinstance(qi.get('15m'), dict) or isinstance(qi.get('1h'), dict) or isinstance(qi.get('1d'), dict):
            q15 = qi.get('15m') or {}
            q1h = qi.get('1h') or {}
            q1d = qi.get('1d') or {}
            d['_rsi'] = _fmt_mtf(q15.get('rsi'), q1h.get('rsi'), q1d.get('rsi'), '.1f')
            d['_sma'] = _fmt_mtf(q15.get('sma_20'), q1h.get('sma_20'), q1d.get('sma_20'), '.2f')
            d['_macd'] = _fmt_mtf(
                (q15.get('macd') or {}).get('histogram'),
                (q1h.get('macd') or {}).get('histogram'),
                (q1d.get('macd') or {}).get('histogram'),
                '.3f',
            )
            d['_bb_pct'] = _fmt_mtf(
                (q15.get('bollinger') or {}).get('pct_b'),
                (q1h.get('bollinger') or {}).get('pct_b'),
                (q1d.get('bollinger') or {}).get('pct_b'),
                '.2f',
            )
            d['_vol_ratio'] = q15.get('volume_ratio') or q1h.get('volume_ratio')
        else:
            d['_rsi'] = _fmt_num(qi.get('rsi'), '.1f')
            d['_sma'] = _fmt_num(qi.get('sma_20'), '.2f')
            d['_macd'] = _fmt_num((qi.get('macd') or {}).get('histogram'), '.3f')
            d['_bb_pct'] = _fmt_num((qi.get('bollinger') or {}).get('pct_b'), '.2f')
            d['_vol_ratio'] = qi.get('volume_ratio')
    return decisions


def _fmt_mtf(v15, v1h, v1d, fmt='.1f'):
    """Format multi-timeframe values for display: 15m / 1h / 1d (유의미한 소수 자리)"""
    parts = []
    for v in (v15, v1h, v1d):
        if v is not None and isinstance(v, (int, float)):
            parts.append(f'{float(v):{fmt}}')
        else:
            parts.append('-')
    return ' / '.join(parts) if any(p != '-' for p in parts) else None


def _fmt_num(v, fmt='.2f'):
    """단일 수치를 표시용 소수 자리로 포맷 (레거시/혼합 데이터용)"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return f'{float(v):{fmt}}'
    return v


def _load_portfolio(initial_cash: float = 75.0):
    """
    trade_history.json에서 포트폴리오 상태 복원 후 현재가 반영.

    Returns:
        dict with cash, total_value, pnl, pnl_pct, initial_cash, positions
        or None if no history
    """
    if not os.path.exists(TRADE_HISTORY_PATH):
        return None
    try:
        with open(TRADE_HISTORY_PATH, 'r', encoding='utf-8') as f:
            history = json.load(f)
    except (json.JSONDecodeError, TypeError):
        return None
    if not history or not isinstance(history, list):
        return None

    cash = initial_cash
    positions = {}

    for record in history:
        action = record.get('action')
        ticker = record.get('ticker')
        shares = record.get('shares', 0)
        price = record.get('price', 0)
        amount = record.get('amount', 0)
        if not action or not ticker:
            continue
        if action == 'BUY' and price > 0:
            if ticker in positions:
                cv = positions[ticker]['qty'] * positions[ticker]['avg_price']
                total_qty = positions[ticker]['qty'] + shares
                positions[ticker] = {'qty': total_qty, 'avg_price': (cv + amount) / total_qty}
            else:
                positions[ticker] = {'qty': shares, 'avg_price': price}
            cash -= amount
        elif action == 'SELL':
            if ticker not in positions:
                continue
            positions[ticker]['qty'] -= shares
            if positions[ticker]['qty'] < 0.001:
                del positions[ticker]
            cash += amount

    total_value = cash
    pos_list = []

    try:
        from data_fetcher import DataFetcher
        fetcher = DataFetcher()
        for ticker, pos in positions.items():
            current_price = fetcher.get_current_price(ticker)
            qty = pos['qty']
            avg_price = pos['avg_price']
            cost = qty * avg_price
            value = (qty * current_price) if current_price else None
            pnl_pct = ((current_price - avg_price) / avg_price * 100) if current_price and avg_price else None
            if value is not None:
                total_value += value
            pos_list.append({
                'ticker': ticker,
                'qty': qty,
                'avg_price': avg_price,
                'current_price': current_price,
                'value': value,
                'pnl_pct': pnl_pct,
            })
    except Exception:
        for ticker, pos in positions.items():
            total_value += pos['qty'] * pos['avg_price']
            pos_list.append({
                'ticker': ticker,
                'qty': pos['qty'],
                'avg_price': pos['avg_price'],
                'current_price': None,
                'value': pos['qty'] * pos['avg_price'],
                'pnl_pct': None,
            })

    pnl = total_value - initial_cash
    pnl_pct = (pnl / initial_cash * 100) if initial_cash else 0

    # 거래 내역: 최신순 (역순)
    trade_log = list(reversed(history)) if history else []

    return {
        'cash': cash,
        'total_value': total_value,
        'pnl': pnl,
        'pnl_pct': pnl_pct,
        'initial_cash': initial_cash,
        'positions': pos_list,
        'trade_history': trade_log,
    }


def _parse_hold_followup_meta(followups):
    """Parse metadata JSON and compute 옳고 그름 for decision followups"""
    for h in followups:
        try:
            h['meta'] = json.loads(h['metadata']) if h.get('metadata') else {}
        except (json.JSONDecodeError, TypeError):
            h['meta'] = {}
        # 옳고 그름: DB is_success 사용, 없으면 pnl+action으로 계산
        action = h.get('action', 'HOLD')
        pnl = h.get('pnl_pct') or 0
        if h.get('is_success') is not None:
            h['_is_correct'] = bool(h['is_success'])
        else:
            if action == 'BUY':
                h['_is_correct'] = pnl > 0
            else:
                h['_is_correct'] = pnl < 0
        h['_correctness_label'] = '올바름' if h['_is_correct'] else '틀림'
    return followups


@app.route('/')
def index():
    from datetime import datetime
    active_tab = request.args.get('tab', 'decisions')
    if active_tab not in ('decisions', 'missed_profit', 'portfolio'):
        active_tab = 'decisions'

    decisions = db.get_decisions(limit=DECISIONS_LIMIT)
    decisions = _parse_decision_meta(decisions)
    hold_followups = _parse_hold_followup_meta(db.get_decision_followups(limit=100))

    initial_cash = float(os.environ.get('TRADING_CAPITAL', 75))
    portfolio = _load_portfolio(initial_cash=initial_cash)

    return render_template_string(
        HTML_TEMPLATE,
        db_path=DB_PATH,
        refresh_seconds=REFRESH_SECONDS,
        last_load=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        decisions=decisions,
        hold_followups=hold_followups,
        portfolio=portfolio,
        active_tab=active_tab,
        trade_history_path=TRADE_HISTORY_PATH,
    )


def main():
    port = int(os.environ.get('DB_VIEWER_PORT', 5050))
    print(f"DB Viewer: http://127.0.0.1:{port}")
    print(f"DB: {DB_PATH} | Refresh: {REFRESH_SECONDS}s")
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
