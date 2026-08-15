"""integrity_check.py - 运行时完整性校验 (防内存转储/篡改)

启动时调用 verify_integrity() 检查关键 .pyc / .so 模块的 SHA-256。
EXPECTED_HASHES 由打包脚本生成;运行时任何不一致都会触发熔断。
"""
import hashlib
import sys
from pathlib import Path


CRITICAL_FILES = [
    "main.py",
    "app/__init__.py",
    "core/ai_manager.py",
]


def calc_checksum(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# 由 build_obfuscated.py 注入 {relpath: sha256}
EXPECTED_HASHES = {}


def verify_integrity(strict=True):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    for rel, expected in EXPECTED_HASHES.items():
        p = base / rel
        if not p.exists():
            if strict:
                return False
            continue
        if calc_checksum(p) != expected:
            return False
    return True


def runtime_self_test():
    """每 N 分钟自检,防调试器热修补"""
    return verify_integrity(strict=False)


if __name__ == "__main__":
    if verify_integrity():
        print("integrity OK")
    else:
        print("integrity FAILED - possible tampering")
        sys.exit(1)