"""
util/format.py - 포맷팅·표시용 유틸리티
"""

# 루프별 시각적 구분용 색상 팔레트 (같은 cycle_id = 같은 색)
CYCLE_COLORS = [
    '#38bdf8', '#fbbf24', '#a78bfa', '#34d399', '#f87171',
    '#60a5fa', '#facc15', '#c084fc', '#2dd4bf', '#fb923c',
]


def cycle_color(cycle_id: str) -> str:
    """cycle_id에서 일관된 색상 반환 (시각적 구분용)"""
    if not cycle_id:
        return '#475569'
    h = hash(cycle_id) % len(CYCLE_COLORS)
    return CYCLE_COLORS[abs(h)]


def fmt_num(v, fmt: str = '.2f'):
    """단일 수치를 표시용 소수 자리로 포맷 (레거시/혼합 데이터용)"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return f'{float(v):{fmt}}'
    return v


def fmt_mtf(v15, v1h, v1d, fmt: str = '.1f'):
    """다중 타임프레임 값 포맷: 15m / 1h / 1d"""
    parts = []
    for v in (v15, v1h, v1d):
        if v is not None and isinstance(v, (int, float)):
            parts.append(f'{float(v):{fmt}}')
        else:
            parts.append('-')
    return ' / '.join(parts) if any(p != '-' for p in parts) else None
