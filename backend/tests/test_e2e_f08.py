# 🔍 [语法] 模块级 docstring
# 🔍 [作用] F08 端到端集成测试：串联 F03–F07 新特性与生成主链路
"""
F08 验收：一条贯穿"记笔记 → 选策略 → 选技能 → 生成产品 → LLM 环境导入"的真实
用户旅程，验证 F03–F07 的新能力在集成层面协同工作、全链路可跑通。

覆盖：
    - F03 产品类型下架后仅剩 14 种（GET /api/ai/product-types）
    - F04 策略自由组合注册表（GET /api/ai/strategies）+ 任意组合不阻断（validate_combination）
    - F05 LLM 配置从环境变量导入（is_local_demo_mode / MultiLLMConfig 反映 env key）
    - F07 产品类型→技能推荐（GET /api/skills/recommendations，并触发内置包预置）
    - 生成主链路：以确定性 Agent 跑通 POST /api/ai/generate（无需真实 LLM）
"""
import os

import pytest

from app.services.strategy_compat import validate_combination
from app.services.llm_config import LLMConfig, MultiLLMConfig, is_local_demo_mode
from app.services.product_generator import PRODUCT_TYPES


@pytest.fixture(autouse=True)
def deterministic_agent_runtime(monkeypatch):
    """保持集成测试封闭：用确定性 Agent 替换真实 LLM 调用。"""
    from app.routers import ai as ai_router

    class ReadyLLM:
        def is_ready(self):
            return True

    async def generate(self, note_title, note_content, product_type, subject_name=""):
        excerpt = (note_content or "")[:600]
        content = (
            f"# {note_title}\n\n"
            f"## 产品类型\n{product_type}\n\n"
            f"## 学习内容\n{excerpt}\n\n"
            "## 交付说明\n本产物由测试用确定性 Agent 完成理解、规划、生成、校验与交付。"
        )
        return {
            "content": content,
            "used_llm": False,
            "workflow_trace": ["理解", "规划", "生成", "校验", "交付"],
            "quality_report": {"score": 100, "mode": "deterministic-test"},
            "elapsed_ms": 1,
        }

    monkeypatch.setattr(ai_router, "reload_llm_service", lambda: ReadyLLM())
    monkeypatch.setattr(ai_router, "get_llm_service", lambda: ReadyLLM())
    monkeypatch.setattr(ai_router.AgenticProductGenerator, "generate", generate)


@pytest.fixture(autouse=True)
def _clean_llm_env():
    # 🔍 [作用] 隔离 LLM 环境变量，避免污染其他测试
    saved = os.environ.get("LEARN2EARN_LLM_API_KEY")
    os.environ.pop("LEARN2EARN_LLM_API_KEY", None)
    yield
    if saved is None:
        os.environ.pop("LEARN2EARN_LLM_API_KEY", None)
    else:
        os.environ["LEARN2EARN_LLM_API_KEY"] = saved


def _create_subject_and_note(client):
    sub = client.post("/api/subjects", json={"name": "F08 集成测试科目", "icon": "🧪"})
    assert sub.status_code in (200, 201)
    subject_id = sub.json()["id"]
    note = client.post("/api/notes", json={
        "title": "FastAPI 依赖注入入门",
        "raw_content": "# FastAPI 依赖注入\n\n## 基本用法\n用 Depends 声明依赖。\n\n## 示例\n```python\nfrom fastapi import Depends\ndef get_db():\n    ...\n```\n\n## 常见坑点\n- 依赖循环\n- 作用域混淆",
        "subject_id": subject_id,
        "tags": ["FastAPI", "后端"],
        "learning_stage": "stage1",
    })
    assert note.status_code in (200, 201)
    return subject_id, note.json()["id"]


def test_f03_product_types_count(client):
    # 🔍 [作用] F03 验收：下架 8 种历史类型后，对外仅剩 14 种
    resp = client.get("/api/ai/product-types")
    assert resp.status_code == 200
    types = resp.json()
    assert len(types) == 14
    type_keys = {t["type"] for t in types}
    assert type_keys == set(PRODUCT_TYPES.keys())
    # 已下架类型不应再出现
    removed = {"schedule_template", "speech_sop", "course_creation_sop", "xiaohongshu_sop",
               "ima_knowledge_base", "solo_company_sop", "software_tutorial", "code_doc"}
    assert removed.isdisjoint(type_keys)


def test_f04_strategies_registry_and_free_combination(client):
    # 🔍 [作用] F04 验收：策略注册表可枚举；任意组合不阻断（仅 warning）
    resp = client.get("/api/ai/strategies")
    assert resp.status_code == 200
    reg = resp.json()
    assert "algorithms" in reg and "techniques" in reg
    assert len(reg["algorithms"]) >= 1

    # 任意自由组合（含未实装算法 + 不相关 skill）都不应被错误阻断
    r = validate_combination(
        skill_ids=[999],  # 不存在的 skill
        algorithms=["reflexion"],  # 未实装
        techniques=["memorybear", "source_grounding", "rag_grounding"],
        llm_ready=True,
    )
    assert r.errors == [], "自由组合绝不应产生阻断性错误"
    assert any("reflexion" in w or "skill" in w.lower() for w in r.warnings), "未实装/未知项应给出非阻塞警告"


def test_f05_llm_env_import_resolves_key():
    # 🔍 [作用] F05 验收：本地演示模式下，LLM 配置能从环境变量导入 Key
    # 注意：is_local_demo_mode() 反映"是否已配置云数据库"，不随 env Key 翻转，
    #       仅断言其返回稳定布尔；env 导入能力由下方 get_active 验证。
    assert isinstance(is_local_demo_mode(), bool)

    # 无 Key：激活配置 api_key 为空（本地演示模式，未接入真实模型）
    mgr_empty = MultiLLMConfig()
    mgr_empty.add_config(LLMConfig(name="default"))
    assert mgr_empty.get_active().api_key == ""

    # 设全局 env Key：get_active 应能注入 Key（F05 核心能力）
    os.environ["LEARN2EARN_LLM_API_KEY"] = "sk-env-injected"
    mgr = MultiLLMConfig()
    mgr.add_config(LLMConfig(name="default"))
    active = mgr.get_active()
    assert active is not None
    assert active.api_key == "sk-env-injected"


def test_f07_skill_recommendations_seeds_and_filters(client):
    # 🔍 [作用] F07 验收：按产品类型推荐技能，并触发内置 Skills 包预置
    resp = client.get("/api/skills/recommendations", params={"product_type": "article"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["product_type"] == "article"
    assert data["recommended_total"] >= 1
    assert data["matched_total"] >= 1
    returned = {s["name"] for s in data["skills"]}
    assert "wechat-article-pro" in returned
    # 推荐技能全部来自打包 zip，故不应有覆盖缺口
    assert data["coverage_gap"] is False
    assert data["missing_skills"] == []


def test_f08_end_to_end_pipeline(client):
    # 🔍 [作用] 全链路：建科目/笔记 → 取策略 → 取推荐技能 → 生成产品
    subject_id, note_id = _create_subject_and_note(client)

    # 取策略注册表 + 推荐技能（仅做存在性校验，证明新特性可用）
    strategies = client.get("/api/ai/strategies").json()
    assert "algorithms" in strategies
    rec = client.get("/api/skills/recommendations", params={"product_type": "ppt"}).json()
    assert rec["matched_total"] >= 1

    # 生成产品（article + ppt + sop，均存在映射技能）
    gen = client.post("/api/ai/generate", json={
        "note_id": note_id,
        "product_types": ["article", "ppt", "sop"],
    })
    assert gen.status_code == 200
    payload = gen.json()
    assert payload["generated"] == 3
    products = payload["products"]
    assert len(products) == 3
    generated_types = {p["type"] for p in products}
    assert generated_types == {"article", "ppt", "sop"}

    # 产品可读取
    pid = products[0]["id"]
    get_resp = client.get(f"/api/products/{pid}")
    assert get_resp.status_code == 200
