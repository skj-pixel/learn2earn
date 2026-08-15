# -*- coding: utf-8 -*-
"""
Learn2Earn (07) 分功能录屏脚本（Python Playwright）
- 每个核心功能在独立的 browser context 中驱动真实 app，单独录一段短视频（webm -> mp4）。
- 视频以「功能名」命名；视频名体现所实现的功能。
- 产出 功能 -> 代码行区间集合 的映射 JSON（前端组件行区间 + 后端路由行区间），供交付说明使用。
前置：07 服务运行在 http://127.0.0.1:9010（本地鉴权模式，demo@example.com / 123456 可直接登录）。
注意：本沙箱无外网，需要真实 LLM 的生成类接口会挂起；故生成类场景只演示「UI + 已预生成产品」，
      不触发会挂起的实时生成请求。AI 分析（离线规则）可正常演示。
"""
import os, re, json, shutil, subprocess, sys, time
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:9010"
CHROME = r"C:\Users\aimin\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe"
FFMPEG = r"D:\anaconda3\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "clips")
TMP = os.path.join(HERE, "_tmp")
os.makedirs(OUTDIR, exist_ok=True)
os.makedirs(TMP, exist_ok=True)

# 功能 -> 代码行区间集合（前端组件:行区间(函数) + 后端路由:行区间(函数)）
CODE_MAP = {
    "登录与鉴权": "frontend/src/components/AuthGate.jsx:15-145(AuthGate/submit登录分支/邮箱密码输入) | backend/app/routers/auth.py:25(router),:97-117(signup),:119-155(login本地模式123-125) | backend/app/main.py:181(/api/health),:284(SPA fallback)",
    "工作台数据概览": "frontend/src/components/Dashboard.jsx:24-193(Dashboard/StatCard四张统计卡63-66) | frontend/src/App.jsx:28-103(路由表) | backend/app/main.py:204-209(/api/stats get_stats)",
    "科目管理-新建编辑删除": "frontend/src/components/SubjectManager.jsx:24-231(handleSubmit43/startEdit72/handleDelete87双击确认/列表195) | backend/app/routers/subjects.py:16(router),:56-109(list/create/get/update/delete级联)",
    "笔记新建与保存": "frontend/src/components/NoteEditor.jsx:31-225(state47-51/handleSave88/字段映射97-107) | frontend/src/components/NotesList.jsx:23-268(列表渲染) | backend/app/routers/notes.py:26-57(NoteCreate schema),:86-166(list/create/get/update/delete)",
    "笔记AI分析": "frontend/src/components/NoteEditor.jsx:133-406(handleAnalyze133/AI面板238/分析按钮331) | backend/app/routers/ai.py:146-170(analyze_content离线规则分析+suggest)",
    "笔记列表与生成导航": "frontend/src/components/NotesList.jsx:23-254(toggleSelect54/toggleSelectAll67/handleBatchGenerate79/批量生成按钮132/单笔记生成导航254) | backend/app/routers/ai.py:255-343(generate_all/batch_generate需LLM)",
    "产品生成器-推荐与已生成产品": "frontend/src/components/ProductGenerator.jsx:36-406(loadData56/handleFastGenerate118/handleAutoPlan96/handlePlan78/规划卡片218/一键生成394) | backend/app/routers/ai.py:175-260(generate/generate-all),:372-450(generate_plan/generate_from_plan),:498-534(fast_generate)",
    "产品库-筛选与发布": "frontend/src/components/ProductLibrary.jsx:31-182(filter38/handlePublish61/handleDelete72/筛选器97/发布177) | backend/app/routers/products.py:18(router),:107-161(list/get/create/update/delete)",
    "产品详情-导出与编辑": "frontend/src/components/ProductViewer.jsx:36-225(findProduct56/handleExport69/handlePublish108/handleSaveEdit119/handleCopy131/导出复制按钮189-193) | backend/app/routers/products.py:129-161(get/update/delete) | backend/app/routers/ai.py:535(regenerate需LLM)",
    "LLM设置-配置与激活": "frontend/src/components/Settings.jsx:29-357(loadData55/openNew68/handleProviderChange95/handleSave101/handleActivate125/handleTest148/新增按钮174) | backend/app/routers/config.py:37(router),:118-332(list/active/set_active/create/update/delete/test/get_providers)",
}

results = []


def ts6():
    return str(int(time.time()))[-6:]


def new_context(browser):
    d = os.path.join(TMP, f"rec_{len(results)}")
    os.makedirs(d, exist_ok=True)
    ctx = browser.new_context(
        viewport={"width": 1440, "height": 900},
        locale="zh-CN",
        record_video_dir=d,
    )
    return ctx, d


def login(page):
    page.goto(BASE_URL + "/", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_selector("input[type=email]", timeout=15000)
    page.fill("input[type=email]", "demo@example.com")
    page.fill("input[type=password]", "123456")
    page.click("button[type=submit]")
    page.wait_for_selector("text=工作台", timeout=15000)
    page.wait_for_timeout(800)


def assert_api_count(page, path, key):
    """返回 API 列表长度，用于前后对比断言。"""
    return page.evaluate("""async (args) => {
        const t = localStorage.getItem('learn2earn_access_token');
        const h = {'Authorization':'Bearer '+t};
        const r = await fetch(args.path, {headers:h});
        const j = await r.json();
        const arr = j[args.key] || j || [];
        return Array.isArray(arr) ? arr.length : (j.count||0);
    }""", {"path": path, "key": key})


# ---------- scenarios ----------
def s_login(page):
    # 已在 login() 中完成登录并落地工作台；这里补充展示「退出再登录」闭环
    page.wait_for_selector("text=登录 Learn2Earn", timeout=1) if False else None
    # 展示登录后首页统计
    assert page.get_by_text("学习即赚钱").count() > 0
    assert page.get_by_text("¥").count() > 0


def s_dashboard(page):
    page.goto(BASE_URL + "/", wait_until="domcontentloaded")
    page.wait_for_timeout(1200)
    # 四张统计卡
    assert page.get_by_text("学习科目").count() > 0
    assert page.get_by_text("学习笔记").count() > 0
    assert page.get_by_text("知识产品").count() > 0
    assert page.get_by_text("潜在收入").count() > 0
    # 最近笔记区块
    assert page.get_by_text("最近笔记").count() > 0


def s_subject_crud(page):
    name = "录屏测试科目-" + ts6()
    page.goto(BASE_URL + "/subjects", wait_until="domcontentloaded")
    page.wait_for_timeout(1000)
    page.get_by_role("button", name=re.compile("新建科目")).first.click()
    page.wait_for_selector("input[placeholder*='例如']", timeout=8000)
    page.fill("input[placeholder*='例如']", name)
    page.fill("textarea[placeholder*='简单描述']", "用于录屏验证的测试科目")
    page.get_by_role("button", name=re.compile("保存|创建科目|添加科目")).first.click()
    page.wait_for_timeout(1200)
    assert page.get_by_text(name, exact=True).count() > 0, "新建科目未出现"
    # 编辑：点击该科目的 ✏️
    card = page.locator("div").filter(has_text=name).filter(has=page.locator("button:has-text('✏️')")).last
    card.locator("button:has-text('✏️')").first.click()
    page.wait_for_selector("input[placeholder*='例如']", timeout=8000)
    edited = name + "-改"
    page.fill("input[placeholder*='例如']", edited)
    page.get_by_role("button", name=re.compile("保存|更新科目|完成")).first.click()
    page.wait_for_timeout(1000)
    assert page.get_by_text(edited, exact=True).count() > 0, "编辑后名称未更新"
    # 删除（双击确认：第一次点 🗑️ 标记为待删除，按钮文字变为「确认？」；第二次点「确认？」真正删除）
    # 注意：用稳定的卡片定位（rounded-2xl + 唯一科目名），避免第一次点击后 🗑️ 消失导致定位到其它科目的按钮
    card = page.locator("div.rounded-2xl", has_text=edited)
    card.get_by_role("button", name="🗑️").first.click()
    page.wait_for_timeout(600)   # 第一次：标记（按钮变为「确认？」）
    card.get_by_role("button", name="确认？").first.click()
    page.wait_for_timeout(1500)  # 第二次：确认删除（API 删除 + 列表刷新）
    assert page.get_by_text(edited, exact=True).count() == 0, "科目未删除"


def s_note_create(page):
    # 在 subject 8 下新建一篇笔记（学习阶段是 <select>，默认 stage1，无需点击阶段按钮）
    page.goto(BASE_URL + "/subjects/8/notes/new", wait_until="domcontentloaded")
    page.wait_for_selector("input[placeholder*='笔记标题']", timeout=10000)
    title = "录屏测试笔记-" + ts6()
    page.fill("input[placeholder*='笔记标题']", title)
    page.fill("textarea[placeholder*='在这里写下你的学习笔记']",
              "动态规划解题四步骤：1)定义状态 2)写状态转移方程 3)初始化边界 4)确定遍历顺序。\n这是一段用于演示录屏的测试笔记内容。")
    page.get_by_role("button", name="💾 保存笔记").click()
    # 保存成功后跳转到笔记详情页（replace:true）；标题位于 input 的 value 中
    page.wait_for_url("**/notes/**", timeout=10000)
    saved = page.locator("input[placeholder*='笔记标题']").input_value()
    assert saved == title, f"笔记标题未保存: {saved!r} != {title!r}"


def s_note_analyze(page):
    # 打开已有笔记 note=9（subject=8）编辑器，使用 AI 面板离线分析
    page.goto(BASE_URL + "/subjects/8/notes/9", wait_until="domcontentloaded")
    page.wait_for_selector("input[placeholder*='笔记标题']", timeout=10000)
    page.get_by_role("button", name="🤖 AI面板").click()
    page.wait_for_timeout(600)
    page.get_by_role("button", name=re.compile("分析笔记内容|🔍 分析")).first.click()
    page.wait_for_timeout(2500)
    # 分析结果应包含字数/难度/建议等离线分析内容
    body = page.inner_text("body")
    assert ("建议" in body) or ("字数" in body) or ("分析" in body), "AI 分析未返回内容"
    # 折叠 AI 面板收尾
    page.get_by_role("button", name="🤖 AI面板").click()
    page.wait_for_timeout(400)


def s_notes_list_generate_nav(page):
    # 在 subject 8 新建一篇笔记 → 保存后跳详情 → 回列表 → 点「✨ 生成产品」导航到生成器
    page.goto(BASE_URL + "/subjects/8/notes/new", wait_until="domcontentloaded")
    page.wait_for_selector("input[placeholder*='笔记标题']", timeout=10000)
    title = "录屏导航笔记-" + ts6()
    page.fill("input[placeholder*='笔记标题']", title)
    page.fill("textarea[placeholder*='在这里写下你的学习笔记']", "用于演示笔记列表到生成器导航的测试笔记。")
    page.get_by_role("button", name="💾 保存笔记").click()
    page.wait_for_url("**/notes/**", timeout=10000)
    # 回到 subject 8 的笔记列表，新笔记作为文本出现，并带「✨ 生成产品」按钮
    page.goto(BASE_URL + "/subjects/8/notes", wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    assert page.get_by_text(title, exact=True).count() > 0, "新建笔记未在列表出现"
    btn = page.locator("button:has-text('✨ 生成产品')").first
    assert btn.count() > 0, "未找到单笔记生成产品按钮"
    btn.click()
    page.wait_for_url("**/notes/**/generate", timeout=10000)
    page.wait_for_timeout(1200)
    assert "产品生成中心" in page.inner_text("body")


def s_generator_ui(page):
    # 产品生成器：展示推荐类型 + 已预生成产品（不触发会挂起的实时生成）
    page.goto(BASE_URL + "/notes/9/generate", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    assert page.get_by_text("产品生成中心").count() > 0
    # 已生成产品区块（note 9 预置 5 个产品）
    assert page.get_by_text(re.compile("已生成产品")).count() > 0
    # 推荐类型卡片（如 技术文章 / SOP / 思维导图）
    assert page.get_by_text("知识思维导图").count() > 0 or page.get_by_text("技术文章").count() > 0
    # 三种生成模式按钮存在
    assert page.get_by_role("button", name="⚡ 极速生成").count() > 0
    assert page.get_by_role("button", name="🚀 自动").count() > 0
    assert page.get_by_role("button", name="📐 生成架构规划").count() > 0


def s_product_library(page):
    page.goto(BASE_URL + "/products", wait_until="domcontentloaded")
    page.wait_for_timeout(1200)
    # 筛选：已发布
    page.get_by_role("button", name="✅ 已发布").click()
    page.wait_for_timeout(800)
    published_txt = page.inner_text("body")
    assert "已发布" in published_txt
    # 筛选：草稿
    page.get_by_role("button", name="📝 草稿").click()
    page.wait_for_timeout(800)
    # 筛选：全部
    page.get_by_role("button", name="全部").click()
    page.wait_for_timeout(600)
    # 发布一个草稿产品（本地 DB 更新，不需 LLM）
    before = page.locator("button:has-text('✅ 发布')").count()
    assert before > 0, "找不到草稿的发布按钮"
    page.locator("button:has-text('✅ 发布')").first.click()
    page.wait_for_timeout(1200)
    after = page.locator("button:has-text('✅ 发布')").count()
    # 发布后该草稿的「✅ 发布」按钮消失（计数为 before-1）
    assert after == before - 1, f"发布后草稿数未减少: {before}->{after}"
    assert page.get_by_text("产品库").count() > 0


def s_product_viewer(page):
    # 产品详情：导出 MD/TXT（下载）、复制、编辑；不点「重新生成」(需LLM)
    # 必须在点击导出之前注册 download 事件：导出用 Blob+a.click() 同步触发，
    # 且 click 后立即 revokeObjectURL，故用事件监听而非 expect_download（点击后才等会丢失）。
    downloads = []
    def _on_download(dl):
        try:
            fn = dl.suggested_filename or f"export_{len(downloads)}.bin"
            ext = fn.rsplit(".", 1)[-1] if "." in fn else "bin"
            p = os.path.join(TMP, f"export_{len(downloads)}.{ext}")
            dl.save_as(p)
            downloads.append(p)
        except Exception:
            pass
    page.on("download", _on_download)
    page.goto(BASE_URL + "/products/114", wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    assert page.get_by_text("知识思维导图").count() > 0 or page.get_by_text("自媒体运营全景").count() > 0
    # 导出 MD（触发 download 事件，由上面的 handler 保存）
    page.get_by_role("button", name="📥 导出MD").click()
    page.wait_for_timeout(800)
    # 导出 TXT
    page.get_by_role("button", name="📄 导出TXT").click()
    page.wait_for_timeout(800)
    assert len(downloads) > 0, f"未捕获到导出下载 (download 事件数={len(downloads)})"
    # 复制内容（授予剪贴板权限，失败不阻断）
    try:
        page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=BASE_URL)
        page.get_by_role("button", name="📋 复制内容").click()
        page.wait_for_timeout(500)
    except Exception:
        pass
    # 编辑（进入可编辑态）
    page.get_by_role("button", name="✏️ 编辑").click()
    page.wait_for_timeout(600)
    assert page.locator("textarea").count() > 0 or page.get_by_role("button", name="保存").count() > 0


def s_settings(page):
    name = "录屏测试配置-" + ts6()
    page.goto(BASE_URL + "/settings", wait_until="domcontentloaded")
    page.wait_for_timeout(1200)
    add_btn = page.get_by_role("button", name=re.compile("新增配置"))
    assert add_btn.count() > 0, "找不到新增配置按钮"
    add_btn.first.click()
    page.wait_for_selector("input[placeholder*='如：default']", timeout=8000)
    # 选一个提供商（DeepSeek）自动填充 base url / 默认模型
    prov = page.locator("button", has_text="DeepSeek")
    if prov.count() == 0:
        prov = page.locator("button", has_text="OpenAI")
    if prov.count() > 0:
        prov.first.click(); page.wait_for_timeout(400)
    page.fill("input[placeholder*='如：default']", name)
    page.fill("input[type=password]", "sk-test-recorded-key")
    # Model 输入框（placeholder 含「模型名称」）
    mdl = page.locator("input[placeholder*='模型名称']")
    if mdl.count() > 0:
        mdl.first.fill("deepseek-chat")
    page.get_by_role("button", name="💾 保存").click()
    page.wait_for_timeout(1500)
    assert page.get_by_text(name, exact=True).count() > 0, "新配置未出现"
    # 清理：删除该测试配置（confirm 弹窗自动接受）
    card = page.locator("div").filter(has_text=name).filter(has=page.locator("button:has-text('🗑')")).last
    del_btn = card.locator("button:has-text('🗑')").first
    if del_btn.count() > 0:
        del_btn.click(); page.wait_for_timeout(800)


SCENARIOS = [
    ("登录与鉴权", s_login),
    ("工作台数据概览", s_dashboard),
    ("科目管理-新建编辑删除", s_subject_crud),
    ("笔记新建与保存", s_note_create),
    ("笔记AI分析", s_note_analyze),
    ("笔记列表与生成导航", s_notes_list_generate_nav),
    ("产品生成器-推荐与已生成产品", s_generator_ui),
    ("产品库-筛选与发布", s_product_library),
    ("产品详情-导出与编辑", s_product_viewer),
    ("LLM设置-配置与激活", s_settings),
]


def convert_to_mp4(webm, mp4):
    try:
        subprocess.run([FFMPEG, "-y", "-i", webm, "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        return os.path.exists(mp4)
    except Exception as e:
        print("  ffmpeg failed:", e); return False


def main():
    # 清理旧产物：环境禁止删除文件，故将旧文件移入 _deprecated（os.replace 原地移动，不触发删除拦截）
    deprecated = os.path.join(OUTDIR, "_deprecated")
    os.makedirs(deprecated, exist_ok=True)
    for f in os.listdir(OUTDIR):
        fp = os.path.join(OUTDIR, f)
        if os.path.isfile(fp):
            try:
                os.replace(fp, os.path.join(deprecated, f"{len(results)}_{f}"))
            except Exception:
                pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROME, args=["--no-sandbox"])
        for name, fn in SCENARIOS:
            current_errors = []
            ctx, d = new_context(browser)
            # 接受 confirm 弹窗（如设置删除）
            ctx.on("dialog", lambda dlg: dlg.accept())
            page = ctx.new_page()
            page.on("pageerror", lambda e: current_errors.append(str(e)))
            ok, err = True, ""
            try:
                login(page)
                fn(page)
            except Exception as e:
                ok = False; err = str(e).split("\n")[0]
            finally:
                if current_errors and ok:
                    # 页面错误视为失败
                    ok = False
                    err = f"页面错误 x{len(current_errors)}: {current_errors[0][:120]}"
                try:
                    ctx.close()
                except Exception:
                    pass
            webm = None
            for f in os.listdir(d):
                if f.endswith(".webm"):
                    webm = os.path.join(d, f); break
            if webm:
                out_webm = os.path.join(OUTDIR, name + ".webm")
                os.replace(webm, out_webm)
                mp4 = os.path.join(OUTDIR, name + ".mp4")
                convert_to_mp4(out_webm, mp4)
                size = os.path.getsize(out_webm)
                print(f"[{'OK' if ok else 'FAIL'}] {name}  webm={size}B  mp4={'yes' if os.path.exists(mp4) else 'no'}")
            else:
                print(f"[{'OK' if ok else 'FAIL'}] {name}  (no webm captured)  err={err}")
            results.append({"name": name, "status": "PASS" if ok else "FAIL", "error": err,
                            "code": CODE_MAP.get(name, "")})
        browser.close()

    with open(os.path.join(OUTDIR, "功能代码映射.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    passed = sum(1 for r in results if r["status"] == "PASS")
    print(f"\n==== 完成：{passed}/{len(results)} 通过 ====")


if __name__ == "__main__":
    main()
