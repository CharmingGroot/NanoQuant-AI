"""
ui/forecast.py - 예측 탭 데이터
"""


def get_watchlist():
    """등록 티커 목록 (forecast 모듈 위임)"""
    try:
        from forecast import load_watchlist
        return load_watchlist()
    except Exception:
        return []
