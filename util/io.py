"""
util/io.py - 파일 입출력 유틸리티
"""

import json
from typing import Any, Optional


def load_json_file(path: str, default: Any = None) -> Any:
    """
    JSON 파일 로드. 실패 시 default 반환.

    Args:
        path: 파일 경로
        default: 로드 실패 시 반환값 (기본 None)
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        return default
