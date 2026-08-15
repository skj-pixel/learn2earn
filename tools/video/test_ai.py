# -*- coding: utf-8 -*-
"""测试 07 的 analyze(离线) 与 fast-generate(需LLM) 是否可用（带短超时）。"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:9010"
CHROME = r"C:\Users\aimin\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, executable_path=CHROME)
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(BASE, wait_until="domcontentloaded")
    page.fill("input[type=email]", "demo@example.com")
    page.fill("input[type=password]", "123456")
    page.click("button[type=submit]")
    page.wait_for_timeout(2000)

    out = page.evaluate("""async () => {
        const t = localStorage.getItem('learn2earn_access_token');
        const h = { 'Authorization': 'Bearer ' + t, 'Content-Type': 'application/json' };
        const res = {};
        const withTimeout = (p, ms) => Promise.race([p, new Promise((_,rej)=>setTimeout(()=>rej(new Error('TIMEOUT'+ms)), ms))]);
        // 1) analyze (离线规则)
        try {
            const r = await fetch('/api/ai/analyze', {method:'POST', headers:h,
                body: JSON.stringify({content:'本文讲解动态规划的解题四步骤：定义状态、写状态转移、初始化、遍历顺序。', subject_name:'算法'})});
            const j = await r.json();
            res.analyze = {status:r.status, hasAnalysis: !!j.analysis, nSugg:(j.suggestions||[]).length};
        } catch(e){ res.analyze = {error:String(e)}; }
        // 2) product-types
        try {
            const r = await fetch('/api/ai/product-types', {headers:h});
            res.ptypes = {status:r.status, n:(await r.json()).length};
        } catch(e){ res.ptypes={error:String(e)}; }
        // 3) fast-generate (需 LLM) —— 8s 超时快速判定
        try {
            const ctrl = new AbortController();
            const to = setTimeout(()=>ctrl.abort(), 8000);
            const r = await fetch('/api/ai/fast-generate', {method:'POST', headers:h, signal:ctrl.signal,
                body: JSON.stringify({note_id:9, product_types:['article'], save_to_db:false})});
            clearTimeout(to);
            const j = await r.json();
            res.fast = {status:r.status, ok: j.get ? j.get('success') : j.success, detail: j.detail||''};
        } catch(e){ res.fast = {error:String(e)}; }
        return res;
    }""")
    print(json.dumps(out, ensure_ascii=False)[:2500])
    ctx.close(); b.close()
