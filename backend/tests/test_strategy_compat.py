# 🔍 [语法] 模块级 docstring
# 🔍 [作用] F04 单元测试：strategy_compat 自由组合兼容层
"""
验证 strategy_compat.validate_combination 的咨询式语义：
    - 结构性错误（algorithms 空 / 类型非法）才进 errors；
    - 未知策略 / 未实装 / 缺 LLM / skill 不存在 只进 warnings，绝不阻断；
    - 任意组合都允许（自由组合的核心保证）。
"""

import pytest

# 🔍 [语法] 相对导入
from app.services.strategy_compat import (
    validate_combination,
    list_strategies,
    GENERATION_ALGORITHMS,
)


def test_two_hidden_compatibility_groups_are_sparse_conflict_registries():
    from app.services.strategy_compat import compatibility_matrices
    matrix = compatibility_matrices([{"id": 1, "name": "PPT Skill"}])
    assert set(matrix) == {"generation", "quality"}
    assert matrix["generation"]
    assert all(row["status"] == "conflict" for row in matrix["generation"] + matrix["quality"])
    assert not any(row["left"] == "skill:1" or row["right"] == "skill:1" for row in matrix["generation"])
    assert all(not value.startswith("skill:") for row in matrix["quality"] for value in (row["left"], row["right"]))


def test_sparse_rules_do_not_grow_quadratically_with_skill_count():
    from app.services.strategy_compat import compatibility_matrices
    small = compatibility_matrices([{"id": 1, "name": "One"}])
    large = compatibility_matrices([{"id": value, "name": str(value)} for value in range(1000)])
    assert len(large["generation"]) == len(small["generation"])


def test_declared_algorithm_conflict_blocks_combination():
    result = validate_combination(algorithms=["single_pass", "iterative_refinement"])
    assert result.errors
    assert any("single_pass + iterative_refinement" in error for error in result.errors)


def test_valid_combination_has_no_errors():
    # 🔍 [作用] 已知实装算法 + 已知实装技术 应通过，无 errors
    r = validate_combination(
        skill_ids=[1, 2],
        algorithms=["hierarchical_planning", "iterative_refinement"],
        techniques=["hallucination_check", "quality_scoring"],
        llm_ready=True,
    )
    assert r.errors == []
    assert r.to_dict()["ok"] is True
    assert r.normalized["algorithms"] == ["hierarchical_planning", "iterative_refinement"]


def test_empty_algorithms_is_error():
    # 🔍 [作用] 没有算法无法生成，属结构性错误
    r = validate_combination(algorithms=[], techniques=["quality_scoring"])
    assert any("生成算法" in e for e in r.errors)
    assert r.to_dict()["ok"] is False


def test_unknown_algorithm_is_warning_not_error():
    # 🔍 [作用] 自由组合：未知算法仅警告，不阻断
    r = validate_combination(algorithms=["some_future_algo"], techniques=[])
    assert r.errors == []
    assert any("some_future_algo" in w for w in r.warnings)


def test_unimplemented_technique_is_warning():
    # 🔍 [作用] 未实装技术（如 audience_role_injection）应给出咨询警告
    r = validate_combination(
        algorithms=["hierarchical_planning"],
        techniques=["audience_role_injection"],
    )
    assert r.errors == []
    assert any("audience_role_injection" in w for w in r.warnings)


def test_needs_llm_but_not_ready_warns():
    # 🔍 [作用] 算法需 LLM 但当前未配置时给警告
    r = validate_combination(
        algorithms=["hierarchical_planning"],
        techniques=[],
        llm_ready=False,
    )
    assert r.errors == []
    assert any("LLM" in w for w in r.warnings)


def test_unknown_skill_id_warns_when_available_given():
    # 🔍 [作用] 传入已安装集合后，越界 skill id 应警告
    r = validate_combination(
        skill_ids=[999],
        algorithms=["hierarchical_planning"],
        techniques=[],
        available_skill_ids={1, 2, 3},
    )
    assert r.errors == []
    assert any("999" in w for w in r.warnings)


def test_type_errors_blocked():
    # 🔍 [作用] 非法类型属结构性错误
    r = validate_combination(algorithms="not-a-list", techniques=[])
    assert any("algorithms" in e for e in r.errors)


def test_list_strategies_shape():
    # 🔍 [作用] 对外登记应包含算法与技术两个列表
    s = list_strategies()
    assert isinstance(s["algorithms"], list) and len(s["algorithms"]) > 0
    assert isinstance(s["techniques"], list) and len(s["techniques"]) > 0
    # 🔍 [作用] 登记的算法 id 与实际常量一致
    assert all(a["id"] in GENERATION_ALGORITHMS for a in s["algorithms"])


def test_memorybear_and_rag_have_truthful_compatibility_status():
    # 🔍 [作用] MemoryBear 已实现且不应误报；RAG 未接真实向量库时必须明确降级。
    techniques = {item["id"]: item for item in list_strategies()["techniques"]}
    assert techniques["memorybear"]["implemented"] is True
    assert techniques["rag_grounding"]["implemented"] is False
    result = validate_combination(
        algorithms=["hierarchical_planning"],
        techniques=["memorybear", "rag_grounding"],
    )
    assert not any("memorybear" in warning.lower() for warning in result.warnings)
    assert any("rag_grounding" in warning for warning in result.warnings)
