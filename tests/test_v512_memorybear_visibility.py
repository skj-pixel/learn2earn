from backend.app.services.memorybear import build_memory_context


def test_memory_preview_reports_all_five_layers_and_current_perception():
    note = {
        "id": 7,
        "title": "AI Agent 产品化实战",
        "raw_content": "从用户需求识别产品机会，并用迭代验证交付质量。",
        "tags": ["AI Agent", "产品化"],
        "learning_stage": "stage2",
    }
    context, meta = build_memory_context(note, {"name": "产品课"}, [note], [])

    assert set(meta["layers"]) == {
        "perception", "working", "episodic", "explicit", "implicit"
    }
    assert meta["layers"]["perception"] == 1
    assert meta["layers"]["working"] == 1
    assert "感知记忆（当前输入信号）" in context
    assert "AI Agent 产品化实战" in context


def test_memory_preview_marks_router_values_as_advice_not_retrieval_results():
    note = {"id": 8, "title": "API 教程", "raw_content": "查询 API 定义"}
    _, meta = build_memory_context(note, None, [note], [])

    assert meta["scene_router"]["mode"] == "routing_advice"
    assert meta["capabilities"]["memorybear"] == "active"
    assert meta["capabilities"]["rag"] == "on_demand"
