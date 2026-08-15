from app.services.llm_config import LLMConfig


class FakeLLM:
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
        self.calls.append(
            {
                "prompt": user_message,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "timeout": timeout,
            }
        )
        if "评审" in user_message or "审计" in user_message:
            return "OK"
        if "制定生成计划" in user_message:
            return "LLM_PLAN_MARKER\n- 目标用户：初学者\n- 交付边界：只基于源笔记"
        return (
            "# LLM_MARKER 真实大模型生成内容\n\n"
            "## 目标用户\nPython 初学者。\n\n"
            "## 可交付内容\n基于源笔记生成的操作步骤、代码示例、避坑清单和验收标准。\n\n"
            "## 验收标准\n读者能够解释列表推导式并完成练习。"
        )


def test_generate_products_uses_llm_workflow(client, sample_note, monkeypatch):
    import app.routers.ai as ai_router

    fake_llm = FakeLLM()
    monkeypatch.setattr(ai_router, "reload_llm_service", lambda: fake_llm)
    monkeypatch.setattr(ai_router, "get_llm_service", lambda: fake_llm)

    response = client.post(
        "/api/ai/generate",
        json={
            "note_id": sample_note.id,
            "product_types": ["article"],
            "save_to_db": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    product = data["products"][0]
    assert product["used_llm"] is True
    assert "LLM_MARKER" in product["content"]
    assert any(call["max_tokens"] for call in fake_llm.calls)
    assert len(fake_llm.calls) >= 2
    assert [step["stage"] for step in product["workflow_trace"]][-1] == "result_delivery"
