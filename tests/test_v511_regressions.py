from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_stats_count_the_same_visible_rows_as_resource_lists():
    source = (ROOT / "backend/app/main.py").read_text(encoding="utf-8")
    assert 'visible_notes = table("notes", user).list()' in source
    assert 'visible_products = table("products", user).list()' in source
    assert "note_count = len(visible_notes)" in source
    assert "product_count = len(visible_products)" in source


def test_task_contract_and_retry_preserve_user_prompts():
    router = (ROOT / "backend/app/routers/tasks.py").read_text(encoding="utf-8")
    assert "common_prompt: str" in router
    assert "product_prompts: dict[str, str]" in router
    assert '"__user_prompts__": {' in router
    retry_payload = router.split("def retry_task", 1)[1]
    assert '"product_strategies": previous.get("product_strategies") or {}' in retry_payload
    assert '"common_prompt":' not in retry_payload
    assert '"product_prompts":' not in retry_payload


def test_generation_combines_common_and_current_product_prompt():
    service = (ROOT / "backend/app/services/generation_task_service.py").read_text(encoding="utf-8")
    assert "task.get(\"common_prompt\")" in service
    assert "task.get(\"product_prompts\")" in service
    assert "## 用户公共生成要求" in service
    assert "## 当前产品专属生成要求" in service
