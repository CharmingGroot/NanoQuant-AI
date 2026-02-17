# -*- coding: utf-8 -*-
"""틀림 판단의 학습메모 공통점 분석"""
import sqlite3
import os

from util import project_root
os.chdir(project_root())
conn = sqlite3.connect('nanoquant_v1.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("""
    SELECT d.ticker, d.action, d.timestamp, d.reasoning, f.reflection_note, f.pnl_pct
    FROM decision_followups f
    JOIN decisions d ON f.decision_id = d.id
    WHERE f.is_success = 0
    ORDER BY f.followup_at DESC
""")
rows = [dict(r) for r in cur.fetchall()]
conn.close()

with open('wrong_decisions_output.txt', 'w', encoding='utf-8') as out:
    out.write(f"=== 틀림 판단 {len(rows)}건 ===\n\n")
    for i, r in enumerate(rows, 1):
        out.write(f"--- #{i} {r['ticker']} {r['action']} pnl={r['pnl_pct']:+.2f}% ---\n")
        out.write(f"학습메모:\n{r.get('reflection_note') or '-'}\n\n")
