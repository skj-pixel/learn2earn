# -*- coding: utf-8 -*-
"""深层页面探针：笔记列表 / 笔记编辑器 / 产品生成器 / 产品详情。"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:9010"
CHROME = r"C:\Users\aimin\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe"


def dump(page, tag):
    print(f"\n########## {tag} ##########")
    print("URL:", page.url)
    btns = [b.strip().replace("\n", " ")[:36] for b in page.locator("button").all_inner_texts() if b.strip()]
    print("BUTTONS(%d):" % len(btns), btns[:45])
    ph = page.eval_on_selector_all("input,textarea", "els=>els.map(e=>e.placeholder||e.type)")
    print("INPUTS:", ph[:20])
    print("TEXT:", page.inner_text("body")[:500].replace("\n", " | "))


def login(page):
    page.goto(BASE, wait_until="networkidle")
    page.fill("input[type=email]", "demo@example.com")
    page.fill("input[type=password]", "123456")
    page.click("button[type=submit]")
    page.wait_for_timeout(2200)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True, executable_path=CHROME)
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    login(page)

    data = page.evaluate("""async () => {
        const t = localStorage.getItem('learn2earn_access_token');
        const h = { 'Authorization': 'Bearer ' + t };
        const s = await (await fetch('/api/subjects', {headers:h})).json();
        const n = await (await fetch('/api/notes', {headers:h})).json();
        const pr = await (await fetch('/api/products', {headers:h})).json();
        return {sub:(s.subjects||s).slice(0,6).map(x=>({id:x.id,name:x.name})),
                notes:(n.notes||n).slice(0,8).map(x=>({id:x.id,t:x.title,sid:x.subject_id})),
                prodN:(pr.products||pr).length, prod0:(pr.products||pr)[0]};
    }""")
    print("########## API 数据 ##########")
    print(json.dumps(data, ensure_ascii=False)[:1200])

    sid = data["sub"][0]["id"]
    nid = data["notes"][0]["id"]
    pid = data["prod0"]["id"]

    page.goto(f"{BASE}/subjects/{sid}/notes", wait_until="networkidle"); page.wait_for_timeout(1200)
    dump(page, f"笔记列表 subject={sid}")

    page.goto(f"{BASE}/subjects/{sid}/notes/new", wait_until="networkidle"); page.wait_for_timeout(1200)
    dump(page, "新建笔记编辑器")

    page.goto(f"{BASE}/subjects/{sid}/notes/{nid}", wait_until="networkidle"); page.wait_for_timeout(1500)
    dump(page, f"编辑笔记 note={nid}")

    page.goto(f"{BASE}/notes/{nid}/generate", wait_until="networkidle"); page.wait_for_timeout(2500)
    dump(page, f"产品生成器 note={nid}")

    page.goto(f"{BASE}/products/{pid}", wait_until="networkidle"); page.wait_for_timeout(1500)
    dump(page, f"产品详情 product={pid}")

    print("\nPAGE_ERRORS:", errs[:5])
    ctx.close(); b.close()
