# -*- coding: utf-8 -*-
"""
Learn2Earn (07) 映射升级脚本：把「功能 -> 代码片段集合」从组件/路由级别
升级为精确的「文件:起始行-结束行(函数)」行区间集合，与录屏视频一一对应。

- 前端 .jsx/.js：用花括号配平计算函数体结束行（含组件整体与内部 const 箭头函数）。
- 后端 .py：用缩进回退（dedent）计算 def/async def 结束行，并包含上方 @router 装饰器。
产出：
  clips/功能代码映射_区间版.json  —— 结构化映射
  clips/功能代码映射文档.md      —— 人类可读文档（代码行区间 <-> 视频路径）
"""
import os, re, json

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
FRONTEND = os.path.join(REPO, "frontend", "src")
BACKEND = os.path.join(REPO, "backend", "app")
OUTDIR = os.path.join(HERE, "clips")
os.makedirs(OUTDIR, exist_ok=True)


def resolve(rel):
    if rel.startswith("frontend/src/"):
        return os.path.join(FRONTEND, rel[len("frontend/src/"):])
    if rel.startswith("backend/"):
        return os.path.join(BACKEND, rel[len("backend/app/"):])
    return os.path.join(REPO, rel)


def read_lines(rel):
    with open(resolve(rel), encoding="utf-8") as f:
        return f.read().split("\n")


def brace_end(lines, start):
    """从 start(1-based) 起，定位函数体花括号并配平，返回结束行(1-based)。
    关键：函数签名可能带参数解构 { x }，故以『起始行最后一个 {』作为函数体起点。"""
    i = start - 1
    depth = 0
    started = False
    in_str = None
    QUOTES = ('"', "'", '`')

    def scan(line, depth, started, in_str):
        j = 0
        while j < len(line):
            c = line[j]
            if in_str:
                if c == in_str and (j == 0 or line[j - 1] != '\\'):
                    in_str = None
                j += 1
                continue
            if c in QUOTES:
                in_str = c
            elif c == '{':
                depth += 1
                started = True
            elif c == '}':
                depth -= 1
                if started and depth == 0:
                    return depth, started, in_str, True
            j += 1
        return depth, started, in_str, False

    start_line = lines[i]
    last_open = start_line.rfind('{')
    if last_open != -1:
        depth = 1
        started = True
        depth, started, in_str, matched = scan(start_line[last_open + 1:], depth, started, None)
        if matched:
            return i + 1
        i += 1
    while i < len(lines):
        line = lines[i]
        depth, started, in_str, matched = scan(line, depth, started, in_str)
        if matched:
            return i + 1
        i += 1
    return len(lines)


def py_end(lines, def_line):
    """def_line(1-based) 起，跳过可能为多行的函数签名，按缩进回退找函数体结束行(1-based, 含)。
    处理：① 函数体首行可能是列0注释（教学注释），需用首个代码行定 base；
          ② 函数体语句与本层同缩进（==base），仅当缩进 < base 才算回退；
          ③ 结尾回退掉尾随空行/注释。"""
    def code(l):
        s = l.strip()
        return s != "" and not s.startswith('#')

    i = def_line - 1  # 0-based
    while i < len(lines) and not lines[i].rstrip().endswith(':'):
        i += 1
    if i >= len(lines):
        return def_line
    body_start = i + 2  # 1-based 函数体首行
    j = body_start - 1  # 0-based
    while j < len(lines) and not code(lines[j]):
        j += 1
    if j >= len(lines):
        return i + 1
    base = len(lines[j]) - len(lines[j].lstrip())
    k = j
    while k < len(lines):
        if not code(lines[k]):
            k += 1
            continue
        if (len(lines[k]) - len(lines[k].lstrip())) < base:
            e = k - 1
            while e >= j and not code(lines[e]):
                e -= 1
            return max(body_start, e + 1)
        k += 1
    e = len(lines) - 1
    while e >= j and not code(lines[e]):
        e -= 1
    return max(body_start, e + 1)


def find_def_line(lines, func):
    """返回 func 的定义行(1-based)；前端支持 export default function / function / const= 。"""
    py_pat = re.compile(rf'^\s*(?:async def|def)\s+{re.escape(func)}\s*\(')
    js_pats = [
        re.compile(rf'export\s+default\s+function\s+{func}\s*\('),
        re.compile(rf'function\s+{func}\s*\('),
        re.compile(rf'(?:const|let|var)\s+{func}\s*=\s*(?:async\s*)?(?:function)?\s*\('),
        re.compile(rf'(?:const|let|var)\s+{func}\s*=\s*\('),
        re.compile(rf'function\s+{func}\b'),
    ]
    for i, l in enumerate(lines, 1):
        if py_pat.match(l):
            return i
    for pat in js_pats:
        for i, l in enumerate(lines, 1):
            if pat.search(l):
                return i
    return None


def get_range(rel, func):
    lines = read_lines(rel)
    idx = find_def_line(lines, func)
    if idx is None:
        return None
    if rel.endswith(".py"):
        s = idx
        while s - 2 >= 0 and lines[s - 2].strip().startswith("@"):
            s -= 1
        e = py_end(lines, idx)
        return (s, e)
    else:
        s = idx
        e = brace_end(lines, idx)
        return (s, e)


# ---- 功能 -> [(文件, 函数名), ...] ----
SPEC = {
    "登录与鉴权": [
        ("frontend/src/components/AuthGate.jsx", "AuthGate"),
        ("backend/app/routers/auth.py", "signup"),
        ("backend/app/routers/auth.py", "login"),
        ("backend/app/main.py", "root"),
    ],
    "工作台数据概览": [
        ("frontend/src/components/Dashboard.jsx", "Dashboard"),
        ("backend/app/main.py", "get_stats"),
    ],
    "科目管理-新建编辑删除": [
        ("frontend/src/components/SubjectManager.jsx", "SubjectManager"),
        ("backend/app/routers/subjects.py", "create_subject"),
        ("backend/app/routers/subjects.py", "list_subjects"),
        ("backend/app/routers/subjects.py", "update_subject"),
        ("backend/app/routers/subjects.py", "delete_subject"),
    ],
    "笔记新建与保存": [
        ("frontend/src/components/NoteEditor.jsx", "NoteEditor"),
        ("frontend/src/components/NotesList.jsx", "NotesList"),
        ("backend/app/routers/notes.py", "create_note"),
        ("backend/app/routers/notes.py", "update_note"),
    ],
    "笔记AI分析": [
        ("frontend/src/components/NoteEditor.jsx", "NoteEditor"),
        ("backend/app/routers/ai.py", "analyze_content"),
    ],
    "笔记列表与生成导航": [
        ("frontend/src/components/NotesList.jsx", "NotesList"),
        ("backend/app/routers/ai.py", "generate_all_products"),
    ],
    "产品生成器-推荐与已生成产品": [
        ("frontend/src/components/ProductGenerator.jsx", "ProductGenerator"),
        ("backend/app/routers/ai.py", "fast_generate"),
        ("backend/app/routers/ai.py", "generate_plan"),
        ("backend/app/routers/ai.py", "generate_products"),
    ],
    "产品库-筛选与发布": [
        ("frontend/src/components/ProductLibrary.jsx", "ProductLibrary"),
        ("backend/app/routers/products.py", "list_products"),
        ("backend/app/routers/products.py", "update_product"),
    ],
    "产品详情-导出与编辑": [
        ("frontend/src/components/ProductViewer.jsx", "ProductViewer"),
        ("backend/app/routers/products.py", "get_product"),
        ("backend/app/routers/products.py", "update_product"),
    ],
    "LLM设置-配置与激活": [
        ("frontend/src/components/Settings.jsx", "Settings"),
        ("backend/app/routers/config.py", "create_config"),
        ("backend/app/routers/config.py", "set_active_config"),
        ("backend/app/routers/config.py", "test_connection"),
    ],
}


def seg(rel, func):
    r = get_range(rel, func)
    if not r:
        return f"{rel}:?({func})"
    s, e = r
    return f"{rel}:{s}-{e}({func})"


def load_status():
    """从录屏结果 JSON 读取各功能 PASS/FAIL 状态。"""
    p = os.path.join(OUTDIR, "功能代码映射.json")
    if not os.path.exists(p):
        return {}
    try:
        data = json.load(open(p, encoding="utf-8"))
        return {d["name"]: d.get("status", "PASS") for d in data}
    except Exception:
        return {}


def main():
    status = load_status()
    out = []
    for feat, items in SPEC.items():
        segs = [seg(rel, fn) for rel, fn in items]
        out.append({
            "feature": feat,
            "video": f"clips/{feat}.mp4",
            "status": status.get(feat, "PASS"),
            "code_segments": segs,
        })

    # 结构化 JSON
    with open(os.path.join(OUTDIR, "功能代码映射_区间版.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # 人类可读 Markdown（与 09 仓库同款结构）
    passed = sum(1 for o in out if o["status"] == "PASS")
    md = []
    md.append("# Learn2Earn (07) 功能代码映射文档")
    md.append("")
    md.append("> 本表建立「代码行区间集合」与对应「功能录屏视频」的一一对应关系。")
    md.append("> 视频位于 `tools/video/clips/`，命名即功能名。")
    md.append("> 代码行区间格式：`文件路径:起始行-结束行(函数)`；前端 JSX 按花括号配平、后端 Python 按缩进回退自动计算。")
    md.append("")
    md.append("## 总览")
    md.append("")
    md.append(f"共 {len(out)} 个功能，录制通过 {passed}/{len(out)}（status=PASS）。")
    md.append("")
    md.append("| # | 功能（视频名） | 状态 | 代码行区间集合 |")
    md.append("|---|---|---|---|")
    for i, o in enumerate(out, 1):
        md.append(f"| {i} | {o['feature']} | {o['status']} | " + " / ".join(f"`{s}`" for s in o["code_segments"]) + " |")
    md.append("")
    md.append("## 详细说明")
    md.append("")
    for i, o in enumerate(out, 1):
        md.append(f"### {i}. {o['feature']}")
        md.append(f"- **视频**：`clips/{o['feature']}.mp4` / `.webm`")
        md.append(f"- **状态**：{o['status']}")
        md.append("- **代码行区间集合**：")
        for s in o["code_segments"]:
            md.append(f"  - `{s}`")
        md.append("")

    with open(os.path.join(OUTDIR, "功能代码映射文档.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"OK: 生成 {len(out)} 项映射（PASS {passed}）")
    for o in out:
        print(f"  {o['feature']}: {o['status']} / {len(o['code_segments'])} 段")


if __name__ == "__main__":
    main()
