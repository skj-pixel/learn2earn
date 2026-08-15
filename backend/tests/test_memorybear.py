"""MemoryBear 升级版单元测试（5 层 + 艾宾浩斯 + 3D 反熵增 + 场景路由）。"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.memorybear import (
    ebbinghaus_recency,
    importance_score,
    derive_implicit_memory,
    fact_merge,
    conflict_detect,
    pattern_abstract,
    run_entropy_engine,
    compute_activation,
    route_memory,
    route_scene,
    build_memory_context,
    memorybear_stats,
    MemoryItem,
    MemoryRouterConfig,
)


def test_ebbinghaus_recency_boundaries():
    # 0-1d 强记
    assert ebbinghaus_recency(0) == 1.0
    assert ebbinghaus_recency(0.5) == 1.0
    # 1-7d
    assert ebbinghaus_recency(5) == 0.7
    # 7-30d
    assert ebbinghaus_recency(15) == 0.4
    # 30-90d
    assert ebbinghaus_recency(60) == 0.2
    # >90d 衰减到底
    assert ebbinghaus_recency(120) == 0.1
    # 负天数被夹到 0
    assert ebbinghaus_recency(-5) == 1.0


def test_importance_score_weights():
    # 无信号 → 低分
    low = importance_score({"tags": []})
    # 编辑 + 标签 + 产品引用全满 → 高分（tanh 饱和趋近 1）
    high = importance_score({"tags": ["a", "b", "c"], "edit_count": 5, "product_ref_count": 3})
    assert low < high
    assert high > 0.6
    assert low < 0.1


def test_derive_implicit_memory_counts():
    notes = [
        {"tags": ["Python", "基础"]},
        {"tags": ["Python", "进阶"]},
    ]
    products = [
        {"product_type": "course_outline", "keywords": ["Python"], "subject_id": 1},
        {"product_type": "course_outline", "keywords": ["Python"], "subject_id": 1},
    ]
    implicit = derive_implicit_memory(notes, products)
    assert "course_outline" in implicit["top_product_types"]
    assert "Python" in implicit["top_tags"]
    assert "1" in implicit["top_subjects"]


def test_fact_merge_groups_overlapping():
    items = [
        MemoryItem(layer="episodic", title="Python 列表推导式", content="列表推导式是 Python 创建列表的简洁方式"),
        MemoryItem(layer="episodic", title="Python 列表推导式进阶", content="嵌套列表推导式也是 Python 特性"),
        MemoryItem(layer="episodic", title="SQL 索引优化", content="数据库索引加速查询"),
    ]
    merged = fact_merge(items)
    # 前两条高度重叠 → 合并为 1 组；第三条独立 → 共 2 组
    assert len(merged) == 2


def test_conflict_detect_same_topic_diff_content():
    items = [
        MemoryItem(layer="episodic", title="装饰器 - A", content="装饰器用于包装函数并保留元数据"),
        MemoryItem(layer="episodic", title="装饰器 - B", content="装饰器会降低代码可读性且难以调试"),
    ]
    conflicts = conflict_detect(items)
    assert len(conflicts) == 1


def test_pattern_abstract_extracts_common():
    items = [
        MemoryItem(layer="episodic", title="Python 装饰器入门", content="x"),
        MemoryItem(layer="episodic", title="Python 装饰器进阶", content="y"),
    ]
    patterns = pattern_abstract(items)
    assert "python" in patterns


def test_run_entropy_engine_returns_report():
    items = [
        MemoryItem(layer="episodic", title="Python 装饰器入门", content="装饰器是 Python 的高级特性"),
        MemoryItem(layer="episodic", title="Python 装饰器进阶", content="装饰器用于包装函数"),
    ]
    report = run_entropy_engine(items)
    assert report.merged_groups >= 1
    assert report.patterns_abstracted >= 1


def test_compute_activation_weighted():
    act = compute_activation(1.0, 1.0, 1.0)
    assert act == 1.0
    act2 = compute_activation(0.0, 0.0, 0.0)
    assert act2 == 0.0


def test_route_memory_per_layer_limit_and_char_cap():
    items = [
        MemoryItem(layer="episodic", title=f"n{i}", content="x" * 200, activation=0.9 - i * 0.01)
        for i in range(20)
    ]
    items.append(MemoryItem(layer="working", title="cur", content="y" * 100, activation=1.0))
    routed = route_memory(items)
    # working 限额 1，episodic 限额 6
    assert sum(1 for i in routed if i.layer == "working") == 1
    assert sum(1 for i in routed if i.layer == "episodic") <= 6
    # 总字符上限 1 万
    assert sum(len(i.content) for i in routed) <= 10000


def test_route_scene_memorybear_dominant_when_history_rich():
    note = {"title": "t", "raw_content": "c"}
    notes = [{"id": 1}, {"id": 2}]
    products = []
    decision = route_scene(note, notes, products)
    assert decision.memorybear_weight != 0.8
    assert decision.memorybear_weight + decision.rag_weight == 1.0


def test_route_scene_rag_dominant_for_knowledge_query():
    note = {"title": "什么是", "raw_content": "Transformer 的原理是什么？教程"}
    notes = []
    products = []
    decision = route_scene(note, notes, products)
    assert decision.rag_weight > decision.memorybear_weight


def test_build_memory_context_5_layers():
    note = {
        "id": 1,
        "title": "Python 列表推导式",
        "raw_content": "列表推导式是 Python 创建列表的简洁方式",
        "created_at": "2026-08-01T00:00:00+00:00",
    }
    notes = [
        {"id": 2, "title": "Python 装饰器", "raw_content": "装饰器是 Python 高级特性",
         "created_at": "2026-07-15T00:00:00+00:00", "tags": ["Python", "装饰器"]},
    ]
    products = [
        {"id": 1, "title": "[教程] Python 列表推导式 - 课程大纲", "content": "大纲...",
         "product_type": "course_outline", "subject_id": 1, "created_at": "2026-07-20T00:00:00+00:00",
         "keywords": ["Python", "列表推导式"]},
    ]
    subject = {"name": "Python编程"}
    ctx, meta = build_memory_context(note, subject, notes, products)
    # 五层结构关键词
    assert "工作记忆" in ctx
    assert "episodic记忆" in ctx or "情景记忆" in ctx
    assert "explicit记忆" in ctx or "显性记忆" in ctx
    assert "implicit记忆" in ctx or "用户偏好" in ctx
    assert "3D 反熵增引擎" in ctx
    assert "场景路由" in ctx
    # meta 统计
    assert meta["layers"]["working"] >= 1
    assert meta["layers"]["episodic"] >= 1
    assert meta["layers"]["explicit"] >= 1
    assert meta["layers"]["implicit"] >= 1
    assert meta["scene_router"]["memorybear_weight"] + meta["scene_router"]["rag_weight"] == 1.0


def test_scene_weights_change_with_history_volume():
    note = {"id": 1, "title": "个人复盘", "raw_content": "记录自己的执行经验"}
    sparse = route_scene(note, [note], [])
    rich = route_scene(note, [note] + [{"id": i} for i in range(2, 8)], [{"id": 1}])
    assert sparse.memorybear_weight < rich.memorybear_weight


def test_memory_router_does_not_fill_every_layer_to_static_quota():
    episodic = [MemoryItem(layer="episodic", title=f"n{i}", content="x", activation=0.9) for i in range(6)]
    routed = route_memory(episodic)
    assert len(routed) == 3


def test_build_memory_context_with_naive_timestamps():
    # cloud_db 存的是 naive 本地 ISO（无时区），now 也是 naive，相减不能报错。
    note = {"id": 1, "title": "测试主题", "raw_content": "测试内容", "created_at": "2026-08-01T10:00:00"}
    notes = [{"id": 2, "title": "相关笔记", "raw_content": "测试主题相关内容",
              "created_at": "2026-07-01T10:00:00", "tags": ["测试"]}]
    products = []
    ctx, meta = build_memory_context(note, {"name": "科目"}, notes, products)
    assert "工作记忆" in ctx
    assert meta["layers"]["episodic"] >= 1


def test_memorybear_stats_structure():
    notes = [
        {"id": 1, "title": "A", "raw_content": "a", "created_at": "2026-07-01T00:00:00+00:00", "tags": ["x"]},
        {"id": 2, "title": "B", "raw_content": "b", "created_at": "2026-07-02T00:00:00+00:00", "tags": ["y"]},
    ]
    products = [{"id": 1, "title": "P", "content": "p", "product_type": "sop",
                 "created_at": "2026-07-03T00:00:00+00:00", "keywords": ["z"]}]
    stats = memorybear_stats(notes, products)
    assert stats["layers"]["episodic"] == 2
    assert stats["layers"]["explicit"] == 1
    assert stats["total_items"] >= 3
    assert "importance_distribution" in stats
    assert "entropy" in stats
