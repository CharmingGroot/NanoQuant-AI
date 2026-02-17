"""
ui/followup.py - 판단 사후 추적 탭 데이터/파싱
"""

import json


def parse_followup_meta(followups):
    """Parse metadata JSON, compute 옳고 그름 for decision followups"""
    for h in followups:
        try:
            h['meta'] = json.loads(h['metadata']) if h.get('metadata') else {}
        except (json.JSONDecodeError, TypeError):
            h['meta'] = {}
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


def get_followup_data(db, limit: int = 100):
    """판단 사후 추적 데이터"""
    rows = db.get_decision_followups(limit=limit)
    return parse_followup_meta(rows)
