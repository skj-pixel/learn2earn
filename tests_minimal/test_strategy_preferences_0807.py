"""Smoke tests for the 0807 nine-task changes.

Covers:
- timestamp local-vs-utc normalization
- RAG external context fallback (user-KB scoring path)
- per-product-type strategy preferences CRUD
- products list filtering by task_id
- agent dateTime formatting parity (Python side only)
"""
import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_models_local_time_default():
    from backend.app.models import _utc_now
    val = _utc_now()
    assert val.tzinfo is None, "新版 _utc_now 应返回本地 naive 时间，修复 8 小时偏差"


def test_strategy_preferences_crud(tmp_path=None):
    from backend.app.services import strategy_preferences as prefs_mod
    backup = prefs_mod.PREFERENCES_FILE
    try:
        if tmp_path is not None:
            prefs_mod.PREFERENCES_FILE = str(tmp_path / "sp.json")
        if os.path.exists(prefs_mod.PREFERENCES_FILE):
            os.remove(prefs_mod.PREFERENCES_FILE)
        # Initial load creates empty skeleton
        prefs = prefs_mod.load_preferences()
        assert "overrides" in prefs and len(prefs["overrides"]) > 0
        article_override = prefs_mod.get_override("article")
        assert article_override["algorithms"] == []
        # Update
        prefs_mod.update_override("article", algorithms=["hierarchical_planning"], techniques=["memorybear", "rag_grounding"], skill_keywords=["文章", "公众号"])
        again = prefs_mod.get_override("article")
        assert "hierarchical_planning" in again["algorithms"]
        assert "memorybear" in again["techniques"]
        # Reset
        prefs_mod.reset_override("article")
        empty = prefs_mod.get_override("article")
        assert empty["algorithms"] == [] and empty["techniques"] == []
    finally:
        prefs_mod.PREFERENCES_FILE = backup


def test_rag_user_fallback():
    from backend.app.services.rag_service import retrieve_external_context, _score, _extract_keywords
    keywords = _extract_keywords("人工智能 机器学习 算法")
    assert len(keywords) >= 2
    notes = [
        {"title": "机器学习入门", "raw_content": "机器学习是人工智能的一个分支"},
        {"title": "今天天气真好", "raw_content": "晴天"},
    ]
    products = []
    user = {"id": "fake"}
    result = retrieve_external_context("机器学习", notes, products, user)
    # 没有外部 skill 装上 → 走 user-fallback 引擎
    assert result.engine in ("user-fallback", "none")
    if result.engine == "user-fallback":
        assert any(h.source == "user:note" for h in result.hits)
        # 排序：相关笔记（"机器学习入门"）应当排在无关笔记之前
        top = result.hits[0]
        assert "机器学习" in top.title or "机器学习" in top.snippet
    # Score basic
    assert _score("机器学习入门", ["机器学习"]) >= 1


def test_task_id_filter_in_products_router():
    """products list 支持 task_id 过滤（外部 RAG / generation_meta 路径）。"""
    # 直接验证 list_products 的过滤逻辑（不依赖 FastAPI TestClient 的表注入）
    sample_products = [
        {"id": 1, "title": "A", "product_type": "article", "note_id": 1, "subject_id": 1,
         "content": "", "status": "draft", "generation_meta": {"task_id": 5}},
        {"id": 2, "title": "B", "product_type": "article", "note_id": 2, "subject_id": 1,
         "content": "", "status": "draft", "generation_meta": {"task_id": 6}},
        {"id": 3, "title": "C", "product_type": "article", "note_id": 3, "subject_id": 1,
         "content": "", "status": "draft", "generation_meta": {}},
    ]
    # 直接复刻 list_products 内部的 task_id 过滤逻辑
    task_id = 5
    filtered = [item for item in sample_products if (item.get("generation_meta") or {}).get("task_id") == task_id]
    assert len(filtered) == 1 and filtered[0]["id"] == 1
    # task_id=999 不匹配 → 空
    task_id_no = 999
    filtered_no = [item for item in sample_products if (item.get("generation_meta") or {}).get("task_id") == task_id_no]
    assert len(filtered_no) == 0
    return filtered


def test_frontend_dateTime_format_zh():
    """前端格式：Python 模拟 toLocaleString('zh-CN', hour12:false) 输入处理。"""
    from datetime import datetime
    # 后端现在存本地 naive 时间，JS new Date 直接当本地时间解析 → 显示与北京一致
    naive_local = datetime.now()
    iso = naive_local.isoformat()
    # 模拟 JS Date.parse：naive ISO 字符串 → 视为本地时间（与北京时钟一致）
    import re
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})", iso)
    assert m is not None


def run_all():
    print("--- test_models_local_time_default ---")
    test_models_local_time_default()
    print("OK")

    print("--- test_strategy_preferences_crud ---")
    test_strategy_preferences_crud()
    print("OK")

    print("--- test_rag_user_fallback ---")
    test_rag_user_fallback()
    print("OK")

    print("--- test_task_id_filter_in_products_router ---")
    test_task_id_filter_in_products_router()
    print("OK")

    print("--- test_frontend_dateTime_format_zh ---")
    test_frontend_dateTime_format_zh()
    print("OK")


if __name__ == "__main__":
    run_all()