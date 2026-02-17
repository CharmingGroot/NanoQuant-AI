"""
util/serialize.py - JSON/DB 직렬화 유틸리티
"""


def serialize_quant_multi(quant_multi: dict) -> dict:
    """다중 타임프레임 quant_indicators를 JSON/DB 저장 가능한 형태로 직렬화"""
    out = {}
    for tf, indicators in (quant_multi or {}).items():
        if not indicators:
            continue
        ser = {}
        for k, v in indicators.items():
            if v is None:
                continue
            ser[k] = list(v) if isinstance(v, tuple) else v
        out[tf] = ser
    return out
