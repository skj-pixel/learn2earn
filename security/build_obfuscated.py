"""build_obfuscated.py - 一键混淆打包流水线

使用:
    python build_obfuscated.py src_dir/ build_dir/

步骤:
    1. 扫描 src_dir/ 中所有 .py 文件
    2. 对每个文件运行 obfuscate.obfuscate_file()
    3. 生成 EXPECTED_HASHES 字典 (供 integrity_check.py 校验)
    4. 输出到 build_dir/

生产环境应再叠加:
    - Cython/Numba 编译为 .so/.pyd
    - PyInstaller --key=xxx 加密打包
    - UPX 压缩 + 签名
"""
import hashlib
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from obfuscate import obfuscate_file


def build(src_dir, build_dir):
    src = Path(src_dir)
    dst = Path(build_dir)
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)

    hashes = {}
    for f in src.rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        rel = f.relative_to(src)
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            obf = obfuscate_file(f)
            out.write_text(obf, encoding="utf-8")
            h = hashlib.sha256(out.read_bytes()).hexdigest()
            hashes[str(rel)] = h
            print("  obfuscated: {} -> {}".format(f, out))
        except Exception as e:
            print("  skipped ({}): {}".format(f, e))
            shutil.copy(f, out)

    # 生成 integrity 校验表
    integrity_path = dst / "integrity_hashes.json"
    import json
    integrity_path.write_text(json.dumps(hashes, indent=2))
    print("\nGenerated integrity_hashes.json with {} entries".format(len(hashes)))
    print("\nBuild complete. Next steps:")
    print("  1. Replace EXPECTED_HASHES in security/integrity_check.py with this dict")
    print("  2. Run pyinstaller --key=xxx --onefile build/main.py")
    print("  3. Sign the resulting binary with gpg/codesign")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    build(sys.argv[1], sys.argv[2])