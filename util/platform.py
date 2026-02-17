"""
util/platform.py - 플랫폼별 설정 유틸리티
"""

import os
import sys


def fix_windows_ssl():
    """
    Windows: 프로젝트 경로에 비ASCII 문자가 있으면 certifi cacert 경로가
    curl/OpenSSL에서 깨질 수 있음. ASCII 전용 경로로 복사 후 사용.
    """
    if sys.platform != "win32":
        return
    try:
        import certifi
        import shutil
        path = certifi.where()
        if not path or (isinstance(path, str) and path.isascii()):
            return
        dest_dir = os.environ.get("TEMP") or os.environ.get("TMP") or os.path.expandvars("%TEMP%")
        if not dest_dir or not dest_dir.isascii():
            dest_dir = os.path.join(os.environ.get("SYSTEMROOT", "C:\\Windows"), "Temp")
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, "nanoquant_cacert.pem")
        shutil.copy2(path, dest)
        os.environ["SSL_CERT_FILE"] = dest
        os.environ["REQUESTS_CA_BUNDLE"] = dest
    except Exception:
        pass
