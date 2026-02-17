"""
util/paths.py - 프로젝트 경로 유틸리티
"""

import os

_REF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def project_root() -> str:
    """프로젝트 루트 디렉터리 경로"""
    return _REF


def path_for(*parts: str) -> str:
    """프로젝트 루트 기준 파일 경로"""
    return os.path.join(project_root(), *parts)
