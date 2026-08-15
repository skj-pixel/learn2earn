# =============================================================================
# tests/test_reasoning_leak_integration.py - F02 端到端思维链泄漏修复验证
# =============================================================================
# 目标：用返回"脏内容"（带 <thinking> 泄漏 + 正文合法"硬性要求："）的假 LLM 跑通
#       AgenticProductGenerator 生成全流程，断言最终交付产品：
#         1. 不含任何 <think / <thinking 思维链标签；
#         2. 不含大模型第一人称思考自述（"用户让我…"）；
#         3. 正文里合法的"硬性要求："保留（B4 回归，绝不能误删）；
#         4. 正文里第一人称题干保留。
#
# 复用了 test_llm_first_generation.py 的 FakeLLM + API client 模式。
# =============================================================================

from app.services.llm_config import LLMConfig


DIRTY_PRODUCT = (
    "<thinking>\n"
    "用户让我为「Redis 持久化」出一套面试题库。"
    "我需要先梳理 RDB 和 AOF 的区别，再分层出题，最后加评分点。\n"
    "</think>\n"
    "# Redis 持久化面试题库\n\n"
    "## 基础题\n1. 请解释 RDB 和 AOF 的区别。\n\n"
    "## 评分说明\n硬性要求：候选人必须答出两种机制各自的优缺点及适用场景。\n\n"
    "## 场景题\n1. 假如我需要把缓存命中率提升 10 倍，我应该怎么做？\n"
)


class DirtyFakeLLM:
    """始终返回带思维链泄漏的脏内容，专门用来验证清洗管线。"""

    def __init__(self):
        self.config = LLMConfig(
            provider="fake",
            api_key="fake-key",
            base_url="http://fake.local/v1",
            model="fake-model",
            max_tokens=4096,
            temperature=0.5,
            is_enabled=True,
        )
        self.calls = []

    def is_ready(self):
        return True

    async def chat(self, user_message: str, max_tokens=None, temperature=None, timeout=120):
        self.calls.append({"prompt": user_message[:40]})
        # 计划阶段给一个能通过的标记
        if "制定生成计划" in user_message:
            return "LLM_PLAN_MARKER\n- 目标用户：初学者\n- 交付边界：只基于源笔记"
        # 产品生成与润色阶段：返回脏内容（带思考过程泄漏）
        return DIRTY_PRODUCT


def test_agentic_pipeline_strips_reasoning_leakage(client, sample_note, monkeypatch):
    """端到端：脏 LLM 输出经管线后，交付产品必须零思考过程残留。"""
    import app.routers.ai as ai_router

    fake = DirtyFakeLLM()
    monkeypatch.setattr(ai_router, "reload_llm_service", lambda: fake)
    monkeypatch.setattr(ai_router, "get_llm_service", lambda: fake)

    response = client.post(
        "/api/ai/generate",
        json={
            "note_id": sample_note.id,
            "product_types": ["interview_qa"],
            "save_to_db": False,
        },
    )

    assert response.status_code == 200, response.text
    product = response.json()["products"][0]
    content = product["content"]

    # 1) 思维链标签彻底清除
    assert "<think" not in content, f"思维链标签残留: {content[:120]}"
    # 2) 第一人称思考自述清除
    assert "用户让我" not in content, "大模型思考自述残留"
    # 3) 正文合法"硬性要求："必须保留（B4 回归，不能误删）
    assert "硬性要求：候选人必须答出两种机制各自的优缺点及适用场景" in content
    # 4) 正文标题与第一人称题干保留
    assert "# Redis 持久化面试题库" in content
    assert "假如我需要把缓存命中率提升 10 倍" in content
    # 管线确实被调用（证明测试真实跑通了生成流程）
    assert len(fake.calls) >= 2
    assert product["workflow_trace"][-1]["stage"] == "result_delivery"
