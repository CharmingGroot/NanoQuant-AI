"""
ui/decisions.py - 최근 결정 탭 데이터/파싱
"""

import json
from util import cycle_color, fmt_num, fmt_mtf


def parse_decision_meta(decisions):
    """Parse metadata JSON, attach 'meta', extract quant columns for display."""
    for d in decisions:
        try:
            d['meta'] = json.loads(d['metadata']) if d.get('metadata') else {}
        except (json.JSONDecodeError, TypeError):
            d['meta'] = {}
        d['_cycle_color'] = cycle_color(d.get('cycle_id'))
        act, amt = d.get('action', ''), d.get('amount')
        d['_amount_display'] = f'${float(amt):.2f}' if act == 'BUY' and amt is not None else (f'{float(amt):.0f}%' if act == 'SELL' and amt is not None else '-')
        qi = d.get('meta', {}).get('quant_indicators') or {}
        if isinstance(qi.get('15m'), dict) or isinstance(qi.get('1h'), dict) or isinstance(qi.get('1d'), dict):
            q15 = qi.get('15m') or {}
            q1h = qi.get('1h') or {}
            q1d = qi.get('1d') or {}
            d['_rsi'] = fmt_mtf(q15.get('rsi'), q1h.get('rsi'), q1d.get('rsi'), '.1f')
            d['_sma'] = fmt_mtf(q15.get('sma_20'), q1h.get('sma_20'), q1d.get('sma_20'), '.2f')
            d['_macd'] = fmt_mtf(
                (q15.get('macd') or {}).get('histogram'),
                (q1h.get('macd') or {}).get('histogram'),
                (q1d.get('macd') or {}).get('histogram'),
                '.3f',
            )
            d['_bb_pct'] = fmt_mtf(
                (q15.get('bollinger') or {}).get('pct_b'),
                (q1h.get('bollinger') or {}).get('pct_b'),
                (q1d.get('bollinger') or {}).get('pct_b'),
                '.2f',
            )
            d['_vol_ratio'] = q15.get('volume_ratio') or q1h.get('volume_ratio')
        else:
            d['_rsi'] = fmt_num(qi.get('rsi'), '.1f')
            d['_sma'] = fmt_num(qi.get('sma_20'), '.2f')
            d['_macd'] = fmt_num((qi.get('macd') or {}).get('histogram'), '.3f')
            d['_bb_pct'] = fmt_num((qi.get('bollinger') or {}).get('pct_b'), '.2f')
            d['_vol_ratio'] = qi.get('volume_ratio')
    return decisions


def get_decisions_data(db, limit: int, offset: int):
    """(decisions, total_count)"""
    total = db.count_decisions()
    decisions = db.get_decisions(limit=limit, offset=offset)
    return parse_decision_meta(decisions), total
