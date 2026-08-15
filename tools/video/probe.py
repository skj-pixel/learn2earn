# -*- coding: utf-8 -*-
"""Learn2Earn UI 探针：登录后遍历各路由，打印可交互元素，便于编写录屏断言。"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:9010"
CHROME = r"C:\Users\aimin\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe"


def dump(page, tag):
    print(f"\n########## {tag} ##########")
    print("URL:", page.url)
    btns = page.locator("button").all_inner_texts()
    print("BUTTONS:", [b.strip().replace("\n", " ")[:30] for b in btns if b.strip()][:40])
    links = page.locator("a").all_inner_texts()
    print("LINKS:", [b.strip().replace("\n", " ")[:30] for b in links if b.strip()][:30])
    inputs = page.locator("input, textarea, select").count()
    print("INPUT_COUNT:", inputs)
    ph = page.eval_on_selector_all("input,textarea", "els=>els.map(e=>e.placeholder||e.type)")
    print("PLACEHOLDERS:", ph[:20])
    body = page.inner_text("body")
    print("TEXT_HEAD:", body[:600].replace("\n", " | "))


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, executable_path=CHROME)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(800)
        dump(page, "登录页")

        # 登录
        page.fill("input[type=email]", "demo@example.com")
        page.fill("input[type=password]", "123456")
        page.click("button[type=submit]")
        page.wait_for_timeout(2500)
        dump(page, "工作台 /")

        for path, tag in [("/subjects", "科目管理"), ("/products", "产品库"), ("/settings", "LLM设置")]:
            page.goto(BASE + "/#" + path) if False else None
            page.evaluate(f"window.history.pushState({{}},'','{path}')")
            page.goto(BASE + path, wait_until="networkidle")
            page.wait_for_timeout(1500)
            dump(page, tag)

        # 现有数据
        data = page.evaluate("""async () => {
            const t = localStorage.getItem('learn2earn_access_token');
            const h = { 'Authorization': 'Bearer ' + t };
            const s = await (await fetch('/api/subjects', {headers:h})).json();
            const n = await (await fetch('/api/notes', {headers:h})).json();
            const pr = await (await fetch('/api/products', {headers:h})).json();
            return {subjects: s, notes: n, products: pr};
        }""")
        print("\n########## 现有数据 ##########")
        print(json.dumps(data, ensure_ascii=False)[:2000])
        print("\nPAGE_ERRORS:", errs)
        ctx.close(); b.close()


main()
