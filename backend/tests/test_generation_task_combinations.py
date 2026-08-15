# 🔍 [作用] 后台生成任务模块测试：不选 MemoryBear 时也必须正常执行。
import app.services.generation_task_service as service


class FakeTable:
    # 🔍 [作用] 用内存字典模拟 cloud_db 表接口，隔离数据库与线程。
    def __init__(self, rows):
        self.rows = rows

    # 🔍 [作用] 按主键读取任务、笔记和科目。
    def get(self, row_id):
        return self.rows.get(row_id)

    # 🔍 [作用] 返回历史数据，供可选记忆服务读取。
    def list(self):
        return list(self.rows.values())

    # 🔍 [作用] 记录新建产品并返回标准字典。
    def create(self, data):
        row = {"id": max(self.rows.keys(), default=0) + 1, **data}
        self.rows[row["id"]] = row
        return row

    # 🔍 [作用] 更新任务进度或产品内容。
    def update(self, row_id, data):
        self.rows[row_id].update(data)
        return self.rows[row_id]


def test_task_runs_without_memorybear(monkeypatch):
    # 🔍 [作用] 构造仅使用源笔记约束的合法自由组合。
    tables = {
        "generation_tasks": FakeTable({1: {"id": 1, "note_id": 1, "product_types": ["article"], "skill_ids": [], "algorithms": ["hierarchical_planning"], "techniques": ["source_grounding"], "status": "queued"}}),
        "notes": FakeTable({1: {"id": 1, "title": "测试笔记", "raw_content": "可靠正文", "subject_id": 1, "tags": []}}),
        "subjects": FakeTable({1: {"id": 1, "name": "测试科目"}}),
        "products": FakeTable({}),
    }
    # 🔍 [作用] 将数据库入口替换为确定性内存表。
    monkeypatch.setattr(service, "table", lambda name, user: tables[name])
    # 🔍 [作用] 本测试不选择 Skill，避免访问真实 Session。
    monkeypatch.setattr(service, "_load_selected_skills", lambda user, ids: [])
    # 🔍 [作用] 模拟已配置的 LLM 服务。
    fake_llm = type("ReadyLLM", (), {"is_ready": lambda self: True})()
    monkeypatch.setattr(service, "reload_llm_service", lambda: None)
    monkeypatch.setattr(service, "get_llm_service", lambda: fake_llm)

    class FakeGenerator:
        # 🔍 [作用] 接受生产代码相同构造参数。
        def __init__(self, llm):
            self.llm = llm

        # 🔍 [作用] 返回可保存的确定性产品，避免真实网络调用。
        async def generate(self, **kwargs):
            return {"content": "# 已生成", "quality_report": {}, "workflow_trace": []}

    monkeypatch.setattr(service, "AgenticProductGenerator", FakeGenerator)
    # 🔍 [作用] 直接执行工作线程主体，验证先前未定义变量错误已消失。
    service._run_task(1, {"id": "local:test"})
    # 🔍 [作用] 任务应完成且产品必须记录来源任务编号。
    assert tables["generation_tasks"].rows[1]["status"] == "completed"
    product = next(iter(tables["products"].rows.values()))
    assert product["generation_meta"]["task_id"] == 1
    assert product["generation_meta"]["techniques"] == ["source_grounding"]


# =============================================================================
# 2026-08 feat/29：每产品类型独立生成策略
# =============================================================================
def test_per_product_strategy_overrides_task_level(monkeypatch):
    """product_strategies 中指定的产品类型，应使用自己的 strategy 覆盖 task 级默认。"""
    tables = {
        "generation_tasks": FakeTable({1: {
            "id": 1, "note_id": 1,
            "product_types": ["article", "ppt"],
            "skill_ids": [10, 20],  # task 级：两个 skill
            "algorithms": ["hierarchical_planning"],  # task 级默认算法
            "techniques": ["source_grounding", "quality_scoring"],
            "product_strategies": {
                "article": {"skill_ids": [99], "algorithms": ["chunked_generation"], "techniques": ["source_grounding"]},
                # "ppt" 故意不写 → 沿用 task 级
            },
            "status": "queued",
        }}),
        "notes": FakeTable({1: {"id": 1, "title": "测试笔记", "raw_content": "x", "subject_id": 1, "tags": []}}),
        "subjects": FakeTable({1: {"id": 1, "name": "测试科目"}}),
        "products": FakeTable({}),
    }
    monkeypatch.setattr(service, "table", lambda name, user: tables[name])

    # 🔍 [作用] 真实记录每个 product_type 调用的参数
    captured = {}

    def fake_load_skills(user, ids):
        return [{"id": int(i), "name": f"skill-{i}", "instructions": "", "description": ""} for i in ids]

    monkeypatch.setattr(service, "_load_selected_skills", fake_load_skills)
    fake_llm = type("ReadyLLM", (), {"is_ready": lambda self: True})()
    monkeypatch.setattr(service, "reload_llm_service", lambda: None)
    monkeypatch.setattr(service, "get_llm_service", lambda: fake_llm)

    class FakeGenerator:
        def __init__(self, llm):
            self.llm = llm

        async def generate(self, **kwargs):
            captured[kwargs["product_type"]] = {
                "skill_prompt": kwargs["skill_prompt"],
                "algorithms": list(kwargs["algorithms"]),
                "techniques": list(kwargs["techniques"]),
            }
            return {"content": f"# {kwargs['product_type']}", "quality_report": {}, "workflow_trace": []}

    monkeypatch.setattr(service, "AgenticProductGenerator", FakeGenerator)
    service._run_task(1, {"id": "local:test"})
    # 🔍 [作用] 任务必须完成
    assert tables["generation_tasks"].rows[1]["status"] == "completed"
    # 🔍 [作用] article 用了 override 的 algorithms/chunked_generation
    assert captured["article"]["algorithms"] == ["chunked_generation"]
    # 🔍 [作用] article 用了 override 的 techniques
    assert captured["article"]["techniques"] == ["source_grounding"]
    # 🔍 [作用] article 的 skill_prompt 只包含 override 的 skill (id=99)
    assert "skill-99" in captured["article"]["skill_prompt"]
    assert "skill-10" not in captured["article"]["skill_prompt"]
    assert "skill-20" not in captured["article"]["skill_prompt"]
    # 🔍 [作用] ppt 沿用 task 级：algorithms=task 级, techniques=task 级
    assert captured["ppt"]["algorithms"] == ["hierarchical_planning"]
    assert captured["ppt"]["techniques"] == ["source_grounding", "quality_scoring"]
    # 🔍 [作用] ppt 的 skill_prompt 包含 task 级合并的 skill-10 / skill-20
    assert "skill-10" in captured["ppt"]["skill_prompt"]
    assert "skill-20" in captured["ppt"]["skill_prompt"]
    # 🔍 [作用] 产品 generation_meta 里记录 effective 覆盖（便于回溯）
    products = list(tables["products"].rows.values())
    by_type = {p["product_type"]: p for p in products}
    assert by_type["article"]["generation_meta"]["effective"]["algorithms"] == ["chunked_generation"]
    assert by_type["article"]["generation_meta"]["effective"]["skill_ids"] == [99]
    # 🔍 [作用] ppt 的 effective 沿用 task 级
    assert by_type["ppt"]["generation_meta"]["effective"]["skill_ids"] == [10, 20]
    assert by_type["ppt"]["generation_meta"]["effective"]["algorithms"] == ["hierarchical_planning"]


def test_per_product_strategy_resolve_helper():
    """_resolve_per_product_strategy：override 中缺字段时回退到 task 级。"""
    task = {
        "skill_ids": [1, 2],
        "algorithms": ["a1"],
        "techniques": ["t1", "t2"],
        "product_strategies": {
            "article": {"algorithms": ["a2"]},  # 只覆盖 algorithms
        },
    }
    res = service._resolve_per_product_strategy(task, "article")
    assert res["skill_ids"] == [1, 2]  # 回退
    assert res["algorithms"] == ["a2"]  # override
    assert res["techniques"] == ["t1", "t2"]  # 回退
    # 未指定的 product_type → 全部回退到 task 级
    res2 = service._resolve_per_product_strategy(task, "ppt")
    assert res2 == {"skill_ids": [1, 2], "algorithms": ["a1"], "techniques": ["t1", "t2"]}
    # 空 product_strategies → 不报错
    res3 = service._resolve_per_product_strategy({"skill_ids": [], "algorithms": [], "techniques": []}, "x")
    assert res3 == {"skill_ids": [], "algorithms": [], "techniques": []}
