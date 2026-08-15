"""E2E frontend test using Playwright against backend :9000 (which serves SPA)."""
import sys, json, time, urllib.request, os, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright, expect

BASE = 'http://127.0.0.1:9000'
SCREENSHOT_DIR = 'C:/Users/aimin/.qclaw/workspace/_e2e_screens'
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def shot(page, name):
    path = os.path.join(SCREENSHOT_DIR, f'{name}.png')
    page.screenshot(path=path)
    print(f'  shot: {path}')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context()
    page = ctx.new_page()

    page.set_default_timeout(15000)

    # Track JS console errors
    errors = []
    page.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
    page.on('console', lambda msg: errors.append(f'console.{msg.type}: {msg.text}') if msg.type == 'error' else None)

    # === Test 1: Load root, should redirect to login or dashboard ===
    print('T1: Load root')
    page.goto(f'{BASE}/', wait_until='networkidle')
    shot(page, '01_root')
    body = page.inner_text('body')
    print(f'  body[:100]: {body[:100]!r}')
    assert 'Learn2Earn' in body or '登录' in body or 'Login' in body.lower(), f'no app content: {body[:200]}'

    # === Test 2: Login flow ===
    print('T2: Login')
    # Find inputs
    inputs = page.locator('input').all()
    print(f'  found {len(inputs)} inputs')
    # Try to find email and password fields
    email_input = page.locator('input[type="email"], input[placeholder*="mail" i], input[placeholder*="邮箱"]').first
    pwd_input = page.locator('input[type="password"]').first
    if email_input.count() > 0:
        email_input.fill('e2e@x.com')
    if pwd_input.count() > 0:
        pwd_input.fill('e2elongpw')
    shot(page, '02_login_filled')

    # Click submit button
    submit_btn = page.locator('button[type="submit"], button:has-text("登录"), button:has-text("Login")').first
    if submit_btn.count() > 0:
        submit_btn.click()
        # Wait for navigation away from login (loading + dashboard render)
        for _ in range(30):
            time.sleep(0.5)
            body_check = page.inner_text('body')
            if '登录' not in body_check and '欢迎回来' not in body_check:
                break
        try:
            page.wait_for_load_state('networkidle', timeout=15000)
        except Exception:
            pass
        time.sleep(2)
    shot(page, '03_after_login')

    body2 = page.inner_text('body')
    print(f'  body[:300]: {body2[:300]!r}')
    # Expect to see dashboard navigation
    assert any(kw in body2 for kw in ['科目', '笔记', '产品', 'Subjects', 'Notes', 'Products', 'Dashboard', '工作台']), \
        f'no dashboard: {body2[:300]}'

    # === Test 3: Navigate to Notes ===
    print('T3: Click Notes')
    notes_link = page.locator('a[href*="note" i], a:has-text("笔记"), a:has-text("Notes")').first
    if notes_link.count() > 0:
        notes_link.click()
        time.sleep(1)
    shot(page, '04_notes')

    # === Test 4: Navigate to Products ===
    print('T4: Click Products')
    products_link = page.locator('a[href*="product" i], a:has-text("产品"), a:has-text("Products")').first
    if products_link.count() > 0:
        products_link.click()
        time.sleep(1)
    shot(page, '05_products')

    # === Test 5: Navigate to Settings/Config ===
    print('T5: Click Settings')
    settings_link = page.locator('a[href*="setting" i], a:has-text("设置"), a:has-text("Settings"), a:has-text("配置")').first
    if settings_link.count() > 0:
        settings_link.click()
        time.sleep(1)
    shot(page, '06_settings')

    # === Final: report errors ===
    if errors:
        print(f'\n{len(errors)} JS errors:')
        for e in errors[:10]:
            print(f'  {e}')
    else:
        print('\nNo JS errors detected')

    browser.close()
    print('DONE — E2E passed')
