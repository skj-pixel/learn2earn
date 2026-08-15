"""启动脚本回归测试。

🔍 [作用] 锁住两类曾经真实发生、且都表现为"双击启动没反应/白屏"的高危故障：
          1) 前端 dist 半同步损坏（只剩 index.html，assets 目录被云盘删掉），
             而启动脚本只检查 index.html 存在 → 误判已就绪 → 跳过重建 → 白屏；
          2) Windows 中文环境下 .ps1 编码陷阱：无 BOM 的 UTF-8 文件里出现中文，
             PowerShell 5.1 会按 GBK 解码，在**解析期**就崩溃（报错还是乱码）。
🔍 [陷阱] 这两类问题都不会被后端 pytest 的业务用例覆盖，只能靠对脚本文本本身做静态断言。
"""
from __future__ import annotations

# 🔍 [语法] pathlib.Path 提供跨平台路径对象；这里只用它做定位与读字节
from pathlib import Path

import pytest

# 🔍 [作用] 定位仓库根目录。本文件位于 <root>/backend/tests/，故向上两级即根。
# 🔍 [陷阱] 必须用 resolve()，否则 parents 在相对路径调用（如 pytest 从子目录启动）下会算错。
REPO_ROOT = Path(__file__).resolve().parents[2]

# 🔍 [作用] 启动链路涉及的脚本目录
SCRIPTS_DIR = REPO_ROOT / "scripts"

# 🔍 [语法] UTF-8 BOM 的字节序列（EF BB BF），用于判断文件是否显式带 BOM
UTF8_BOM = b"\xef\xbb\xbf"


def _iter_ps1_files() -> list[Path]:
    # 🔍 [作用] 收集 scripts/ 下全部 PowerShell 脚本，保证新增脚本自动纳入编码检查
    # 🔍 [陷阱] 用 sorted 固定顺序，避免不同文件系统下用例顺序漂移导致排查困难
    return sorted(SCRIPTS_DIR.glob("*.ps1"))


class TestPowerShellEncodingSafety:
    """PowerShell 脚本编码安全（对应用户的"编码铁律"）。"""

    def test_scripts_dir_exists(self):
        # 🔍 [作用] 前置断言：目录不存在时后面的 glob 会静默返回空列表，导致用例假绿
        assert SCRIPTS_DIR.is_dir(), f"scripts 目录不存在：{SCRIPTS_DIR}"
        assert _iter_ps1_files(), "scripts 目录下没有找到任何 .ps1 文件"

    @pytest.mark.parametrize("ps1_path", _iter_ps1_files(), ids=lambda p: p.name)
    def test_no_bom_script_must_be_pure_ascii(self, ps1_path: Path):
        # 🔍 [作用] 核心铁律：不带 BOM 的 .ps1 里绝不允许出现非 ASCII 字节
        # 🔍 [陷阱] 中文 Windows 的 PowerShell 5.1 对无 BOM 文件按 GBK 解码，
        #          UTF-8 中文字节会被解析成非法符号，属于**解析期**语法崩溃，
        #          错误信息本身也是乱码，排查成本极高。
        raw = ps1_path.read_bytes()
        if raw.startswith(UTF8_BOM):
            # 🔍 [作用] 带 BOM 的文件编码明确，可以安全使用中文注释，直接放行
            return
        # 🔍 [语法] 生成器表达式 + enumerate(raw, 1) 找出首个越界字节的位置，便于定位
        offenders = [(i, b) for i, b in enumerate(raw, 1) if b > 0x7F]
        assert not offenders, (
            f"{ps1_path.name} 无 UTF-8 BOM 却包含 {len(offenders)} 个非 ASCII 字节"
            f"（首个位于第 {offenders[0][0]} 字节，值 0x{offenders[0][1]:02X}）。"
            "请改用纯英文提示，或将文件另存为 UTF-8 with BOM。"
        )

    def test_fast_launcher_has_bom_for_chinese_comments(self):
        # 🔍 [作用] start_local_demo_fast.ps1 内含中文 🔍 注释，必须带 BOM 才安全
        path = SCRIPTS_DIR / "start_local_demo_fast.ps1"
        raw = path.read_bytes()
        assert raw.startswith(UTF8_BOM), (
            "start_local_demo_fast.ps1 含中文注释，必须保存为 UTF-8 with BOM，"
            "否则 PowerShell 5.1 在中文 Windows 上会解析崩溃。"
        )

    @pytest.mark.parametrize("ps1_path", _iter_ps1_files(), ids=lambda p: p.name)
    def test_no_c_style_line_comment(self, ps1_path: Path):
        # 🔍 [作用] PowerShell 的行注释是 '#'，'//' 不是注释而是非法 token。
        # 🔍 [陷阱] 编辑中断/误粘贴很容易留下 '// placeholder' 这类残留，
        #          它不会被任何业务测试发现，只在用户双击时炸成解析错误。
        text = ps1_path.read_text(encoding="utf-8-sig")
        bad_lines = [
            (idx, line.strip())
            for idx, line in enumerate(text.splitlines(), 1)
            # 🔍 [陷阱] 只匹配"整行以 // 开头"，避免误伤字符串里的 http:// 之类
            if line.strip().startswith("//")
        ]
        assert not bad_lines, (
            f"{ps1_path.name} 存在 C 风格注释（PowerShell 非法）：{bad_lines}"
        )


class TestDistIntegrityGuard:
    """前端 dist 完整性校验必须存在（防止半同步损坏被误判为就绪）。"""

    def test_fast_launcher_validates_asset_references(self):
        # 🔍 [作用] 校验快速启动脚本真的会逐个核对 index.html 引用的 /assets 资源
        text = (SCRIPTS_DIR / "start_local_demo_fast.ps1").read_text(encoding="utf-8-sig")
        assert "function Test-FrontendBuild" in text, "缺少 Test-FrontendBuild 完整性校验函数"
        # 🔍 [作用] 必须解析 index.html 中的 /assets/ 引用，而不是只判断文件存在
        assert "/assets/" in text, "未见对 /assets/ 引用的解析逻辑"
        assert "dist\\assets" in text, "未见对 dist\\assets 目录的存在性检查"
        # 🔍 [陷阱] 旧实现只有 index.html 一个判据；这里确保 Test-PreparedEnvironment 已改调完整性函数
        assert "if (-not (Test-FrontendBuild))" in text, (
            "Test-PreparedEnvironment 未接入 Test-FrontendBuild，残缺 dist 仍会被误判为就绪"
        )

    def test_prepare_script_verifies_build_output(self):
        # 🔍 [作用] 一次性准备脚本在构建完成后也必须自检产物，构建失败要显式 throw
        text = (SCRIPTS_DIR / "prepare_local_demo_once.ps1").read_text(encoding="utf-8-sig")
        assert "dist\\assets" in text, "prepare 脚本未校验 dist\\assets 是否生成"
        assert "Frontend build is incomplete" in text, "prepare 脚本缺少构建不完整时的报错分支"

    def test_prepare_script_falls_back_when_npm_ci_fails(self):
        # 🔍 [作用] npm ci 会先整体删除 node_modules，可能被杀软/云同步客户端占用而失败；
        #          此时必须回退到非破坏性的 npm install，而不是直接放弃。
        text = (SCRIPTS_DIR / "prepare_local_demo_once.ps1").read_text(encoding="utf-8-sig")
        assert "npm ci" in text and "npm install" in text, "缺少 npm ci → npm install 的回退链"
        assert "installOk" in text, "未见 npm ci 失败后的回退控制标志"
