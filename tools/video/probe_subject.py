# -*- coding: utf-8 -*-
import os, time, sys
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:9010"
CHROME = r"C:\Users\aimin\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
SHOT = os.path.join(HERE, "_probe_subject.png")

def main():
    out = []
    ts = str(int(time.time()))[-6:]
    name = "探针科目-" + ts
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, executable_path=CHROME, args=["--no-sandbox"])
        ctx = b.new_context(viewport={"width":1440,"height":900}, locale="zh-CN")
        ctx.on("dialog", lambda d: d.accept())
        pg = ctx.new_page()
        pg.goto(BASE_URL + "/", wait_until="domcontentloaded")
        pg.wait_for_selector("input[type=email]", timeout=15000)
        pg.fill("input[type=email]", "demo@example.com")
        pg.fill("input[type=password]", "123456")
        pg.click("button[type=submit]")
        pg.wait_for_selector("text=工作台", timeout=15000)
        pg.goto(BASE_URL + "/subjects", wait_until="domcontentloaded")
        pg.wait_for_timeout(1000)
        # 新建
        pg.get_by_role("button", name="新建科目").first.click()
        pg.wait_for_selector("input[placeholder*='例如']", timeout=8000)
        pg.fill("input[placeholder*='例如']", name)
        pg.fill("textarea[placeholder*='简单描述']", "探针描述")
        pg.get_by_role("button", name="创建科目").first.click()
        pg.wait_for_timeout(1200)
        out.append("after create, card text count: " + str(pg.get_by_text(name, exact=True).count()))
        # 编辑：点 ✏️
        card = pg.locator("div").filter(has_text=name).filter(has=pg.locator("button:has-text('✏️')")).last
        card.locator("button:has-text('✏️')").first.click()
        pg.wait_for_timeout(1000)
        cnt = pg.locator("input[placeholder*='例如']").count()
        out.append("inputs matching 例如 after edit click: " + str(cnt))
        html = pg.evaluate("""() => {
            const f = document.querySelector('input[placeholder*=\\"例如\\"]');
            if(!f) return 'NO_INPUT';
            const r = f.getBoundingClientRect();
            return JSON.stringify({value:f.value, ph:f.placeholder, rect:{x:r.x,y:r.y,w:r.width,h:r.height}, disabled:f.disabled, visible:r.width>0});
        }""")
        out.append("input info: " + str(html))
        try:
            pg.locator("input[placeholder*='例如']").first.fill(name + "-改", timeout=5000)
            out.append("FILL OK")
        except Exception as e:
            out.append("FILL ERR: " + str(e)[:200])
        pg.screenshot(path=SHOT)
        out.append("screenshot: " + SHOT)
        b.close()
    with open(os.path.join(HERE, "_probe_subject_out.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        with open(os.path.join(HERE, "_probe_subject_out.txt"), "w", encoding="utf-8") as f:
            f.write("FATAL: " + str(e)[:500])
