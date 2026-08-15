import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[2] / "reports" / "gui_v2" / "mobile_390x844.png"
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 390, "height": 844})
    auth = page.request.post("http://127.0.0.1:8123/api/auth/login", data={
        "email": "codex-editor-v2@example.com", "password": "codex-editor-v2-password"
    })
    token = auth.json()["access_token"]
    page.add_init_script(f"localStorage.setItem('learn2earn_access_token', {json.dumps(token)})")
    page.goto("http://127.0.0.1:9020/subjects", wait_until="networkidle")
    page.screenshot(path=str(OUT), full_page=True)
    metrics = page.evaluate("({width: innerWidth, scroll: document.documentElement.scrollWidth})")
    assert metrics["scroll"] <= metrics["width"], metrics
    assert page.get_by_placeholder("按名称搜索科目").is_visible()
    print(metrics)
    page.context.close()
