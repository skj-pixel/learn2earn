"""License Manager - 一机一码授权校验

生成机器码:
    python license_manager.py fingerprint

校验授权:
    python license_manager.py verify LICENSE.json

生产环境应该从 license server 拉取许可,本地文件仅作离线缓存。
"""
import hashlib
import json
import os
import platform
import re
import socket
import subprocess
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path


CACHE_PATH = Path.home() / ".license_cache.json"
SECRET_SALT = "CHANGE_ME_IN_PRODUCTION"


def get_machine_fingerprint() -> str:
    """基于硬件生成机器指纹"""
    parts = []
    parts.append(platform.processor())
    parts.append(platform.machine())
    mac = ':'.join(re.findall('..', '%012x' % uuid.getnode()))
    parts.append(mac)
    parts.append(platform.node())
    parts.append(platform.version())
    try:
        if sys.platform == "win32":
            out = subprocess.check_output(["wmic", "csproduct", "get", "uuid"], stderr=subprocess.DEVNULL).decode()
            sn = out.splitlines()[-1].strip()
        elif sys.platform == "darwin":
            out = subprocess.check_output(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], stderr=subprocess.DEVNULL).decode()
            sn = ""
            for line in out.splitlines():
                if "IOPlatformUUID" in line:
                    sn = line.split('"')[1]
                    break
        else:
            sn = ""
            for p in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
                if Path(p).exists():
                    sn = Path(p).read_text().strip()
                    break
        parts.append(sn)
    except Exception:
        pass
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32].upper()


def generate_license(machine_fp: str, days: int = 365) -> dict:
    """生成授权文件 (生产环境应由 license server 私钥签名)"""
    exp = (datetime.now() + timedelta(days=days)).isoformat()
    sig_input = "{}|{}|{}".format(machine_fp, exp, SECRET_SALT)
    payload = {
        "machine_fp": machine_fp,
        "issued_at": datetime.now().isoformat(),
        "expires_at": exp,
        "modules": ["core", "ai_inference"],
        "version_max": "1.0.0",
        "signature": hashlib.sha256(sig_input.encode()).hexdigest(),
    }
    return payload


def verify_license(license_data) -> bool:
    """校验授权 (校验机器码、签名、有效期)"""
    if not license_data:
        return False
    if license_data.get("machine_fp") != get_machine_fingerprint():
        return False
    try:
        exp = datetime.fromisoformat(license_data["expires_at"])
        if exp < datetime.now():
            return False
    except Exception:
        return False
    sig_input = "{}|{}|{}".format(
        license_data["machine_fp"], license_data["expires_at"], SECRET_SALT
    )
    expected = hashlib.sha256(sig_input.encode()).hexdigest()
    if license_data.get("signature") != expected:
        return False
    return True


def require_license(license_path: str = None) -> bool:
    """入口校验 - 程序启动时调用"""
    fp = get_machine_fingerprint()
    candidates = [license_path] if license_path else []
    candidates += ["LICENSE.json", os.path.expanduser("~/.license.json"),
                   os.environ.get("LICENSE_FILE", "")]
    for c in candidates:
        if c and Path(c).exists():
            try:
                data = json.loads(Path(c).read_text())
                if verify_license(data):
                    return True
            except Exception:
                pass
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "fingerprint":
        print("Machine Fingerprint: {}".format(get_machine_fingerprint()))
    elif cmd == "generate":
        fp = get_machine_fingerprint()
        lic = generate_license(fp)
        Path("LICENSE.json").write_text(json.dumps(lic, indent=2))
        print("License generated for {}, expires {}".format(fp, lic["expires_at"]))
    elif cmd == "verify":
        if len(sys.argv) < 3:
            print("Usage: license_manager.py verify <license.json>")
            sys.exit(1)
        data = json.loads(Path(sys.argv[2]).read_text())
        if verify_license(data):
            print("OK: license valid")
        else:
            print("FAIL: license invalid or expired")
            sys.exit(1)
    elif cmd == "check":
        if require_license():
            print("OK: license present and valid")
        else:
            print("FAIL: no valid license found")
            sys.exit(1)