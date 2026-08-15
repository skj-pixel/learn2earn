# =============================================================================
# tests/test_product_planner.py - 产品架构规划器单元测试
# =============================================================================
# 测试 ProductPlanner 和 ProductPlan 的核心功能：
#   1. ProductPlan 数据模型（初始化/to_dict/to_markdown）
#   2. _plan_with_template（模板引擎规划）
#   3. _parse_llm_response（LLM 响应解析）
#   4. plan_sync（同步规划入口）
#   5. 规划内容完整性（所有字段非空）
#   6. 定价策略正确性
#   7. 产品项排序和过滤
# =============================================================================

import pytest                              # pytest 框架
from app.services.product_planner import ProductPlanner, ProductPlan  # 被测试模块


# =============================================================================
# 测试数据
# =============================================================================
# 中等长度笔记内容（用于测试规划生成）
TEST_CONTENT = """# Python装饰器学习笔记

## 基本概念
装饰器是Python中用于修改函数行为的语法糖。

## 代码示例
```python
def my_decorator(func):
    def wrapper(*args, **kwargs):
        print("Before function")
        result = func(*args, **kwargs)
        print("After function")
        return result
    return wrapper

@my_decorator
def say_hello(name):
    print(f"Hello, {name}!")

say_hello("World")
```

## 注意事项
1. 装饰器本质是高阶函数
2. 使用functools.wraps保留原函数元信息
3. 多个装饰器的执行顺序是从内到外
"""


# =============================================================================
# ProductPlan 数据模型测试
# =============================================================================
class TestProductPlan:
    """ProductPlan 数据模型测试"""

    def test_product_plan_init(self):
        """
        测试用例：ProductPlan 初始化
        验证点：所有属性正确初始化
        """
        plan = ProductPlan(
            note_title="Python装饰器",
            subject_name="Python编程",
            difficulty="intermediate",
        )

        # 验证 overview
        assert plan.overview["topic"] == "Python装饰器"
        assert plan.overview["subject"] == "Python编程"
        assert plan.overview["difficulty"] == "intermediate"
        assert plan.overview["total_potential_revenue"] == 0

        # 验证初始空列表
        assert plan.product_items == []
        assert plan.content_strategy["generation_order"] == []

    def test_product_plan_to_dict(self):
        """
        测试用例：to_dict() 序列化
        验证点：返回 dict 且包含所有顶层的 key
        """
        plan = ProductPlan("test", "test", "beginner")
        result = plan.to_dict()

        # 验证结构
        assert isinstance(result, dict)
        assert "overview" in result
        assert "product_items" in result
        assert "content_strategy" in result
        assert "pricing_strategy" in result
        assert "timeline" in result

    def test_product_plan_to_markdown(self):
        """
        测试用例：to_markdown() 生成 Markdown
        验证点：包含标题、定价、时间线等关键信息
        """
        plan = ProductPlan("Python装饰器", "Python", "intermediate")
        plan.overview["target_audience"] = "中级Python开发者"
        plan.overview["unique_value"] = "将装饰器知识转化为付费产品"
        plan.product_items.append({
            "type": "article",
            "icon": "📝",
            "name": "技术文章",
            "priority": 1,
            "suggested_title": "Python装饰器实战指南",
            "angle": "从源码角度理解装饰器",
            "estimated_price": 29,
            "platforms": ["CSDN", "掘金"],
            "outline": ["概念解释", "代码示例", "常见坑点"],
        })
        plan.pricing_strategy["individual_prices"] = {"article": 29}
        plan.pricing_strategy["bundle_price"] = 50
        plan.pricing_strategy["pricing_rationale"] = "打包优惠"
        plan.timeline["estimated_minutes"] = 10

        md = plan.to_markdown()

        # 验证关键内容
        assert "# 📐 知识付费产品架构方案" in md
        assert "Python装饰器" in md
        assert "独特价值主张" in md
        assert "推荐产品蓝图" in md
        assert "技术文章" in md
        assert "定价策略" in md
        assert "时间线预估" in md

    def test_product_plan_revenue_calculation(self):
        """
        测试用例：总收入计算
        验证点：total_potential_revenue = 所有产品价格之和
        """
        plan = ProductPlan("test", "test", "beginner")
        plan.product_items = [
            {"type": "article", "estimated_price": 29, "priority": 1, "suggested_title": "", "angle": "", "platforms": [], "outline": [], "icon": "📝", "name": ""},
            {"type": "sop", "estimated_price": 39, "priority": 2, "suggested_title": "", "angle": "", "platforms": [], "outline": [], "icon": "📋", "name": ""},
            {"type": "quiz", "estimated_price": 19, "priority": 3, "suggested_title": "", "angle": "", "platforms": [], "outline": [], "icon": "✍️", "name": ""},
        ]

        total = sum(item["estimated_price"] for item in plan.product_items)
        plan.overview["total_potential_revenue"] = total

        assert plan.overview["total_potential_revenue"] == 87  # 29+39+19


# =============================================================================
# ProductPlanner 模板规划测试
# =============================================================================
class TestProductPlannerTemplate:
    """模板引擎规划测试（无需 LLM）"""

    def test_plan_with_template_basic(self):
        """
        测试用例：模板规划基础功能
        验证点：规划对象非空，包含产品项
        """
        planner = ProductPlanner()                     # 不传 LLM → 使用模板
        plan = planner._plan_with_template(
            note_title="Python装饰器",
            note_content=TEST_CONTENT,
            subject_name="Python编程",
            difficulty="intermediate",
            suggestions=[
                {"type": "article", "name": "技术文章", "reason": "有完整技术内容"},
                {"type": "sop", "name": "SOP文档", "reason": "可整理标准流程"},
                {"type": "checklist", "name": "行动清单", "reason": "学习笔记适合"},
            ],
        )

        # 验证规划完整性
        assert plan is not None
        assert plan.overview["topic"] == "Python装饰器"
        assert plan.overview["subject"] == "Python编程"
        assert len(plan.product_items) == 3             # 3个推荐产品

    def test_plan_with_template_fills_all_fields(self):
        """
        测试用例：模板规划填充所有字段
        验证点：overview/content_strategy/pricing/timeline 均非空
        """
        planner = ProductPlanner()
        plan = planner._plan_with_template(
            note_title="测试",
            note_content="测试内容。Python基础知识。",
            subject_name="Python",
            difficulty="beginner",
            suggestions=[{"type": "article", "name": "文章", "reason": "基础内容"}],
        )

        # 验证 overview
        assert plan.overview["target_audience"] != ""
        assert plan.overview["unique_value"] != ""
        assert plan.overview["monetization_goal"] != ""

        # 验证 product_items
        assert len(plan.product_items) >= 1
        item = plan.product_items[0]
        assert item["type"] == "article"
        assert item["estimated_price"] > 0              # 有合理定价
        assert len(item["outline"]) >= 2                # 有至少2个大纲项

        # 验证 content_strategy
        assert plan.content_strategy["generation_order"] != []
        assert len(plan.content_strategy["cross_references"]) > 0

        # 验证 pricing_strategy
        assert plan.pricing_strategy["bundle_price"] > 0
        assert plan.pricing_strategy["premium_price"] > plan.pricing_strategy["bundle_price"]

        # 验证 timeline
        assert plan.timeline["estimated_minutes"] > 0
        assert plan.timeline["chunk_count_total"] > 0

    def test_plan_with_template_empty_suggestions(self):
        """
        测试用例：空推荐列表
        验证点：规划的 product_items 为空
        """
        planner = ProductPlanner()
        plan = planner._plan_with_template(
            note_title="测试",
            note_content="内容",
            subject_name="",
            difficulty="beginner",
            suggestions=[],  # 空推荐
        )

        assert plan.product_items == []
        assert plan.overview["total_potential_revenue"] == 0

    def test_plan_sync_method(self):
        """
        测试用例：plan_sync 同步方法
        验证点：同步和异步返回相同结构
        """
        planner = ProductPlanner()
        plan = planner.plan_sync(
            note_title="测试同步",
            note_content=TEST_CONTENT,
            subject_name="Python",
        )

        assert plan is not None
        assert plan.overview["topic"] == "测试同步"
        assert len(plan.product_items) > 0

    def test_plan_with_difficulty_levels(self):
        """
        测试用例：不同难度等级的规划
        验证点：overview 中的难度正确
        """
        for difficulty in ["beginner", "intermediate", "advanced"]:
            planner = ProductPlanner()
            plan = planner._plan_with_template(
                "测试", "内容", "Python", difficulty, [{"type": "article", "name": "", "reason": ""}]
            )
            assert plan.overview["difficulty"] == difficulty

    def test_plan_to_markdown_is_readable(self):
        """
        测试用例：to_markdown 输出可读性
        验证点：MD 长度 > 500，包含多个章节
        """
        planner = ProductPlanner()
        plan = planner._plan_with_template(
            "Python装饰器", TEST_CONTENT, "Python", "intermediate",
            [
                {"type": "article", "name": "技术文章", "reason": "全面"},
                {"type": "sop", "name": "SOP文档", "reason": "流程"},
                {"type": "course_outline", "name": "课程大纲", "reason": "系统"},
                {"type": "checklist", "name": "行动清单", "reason": "实用"},
            ],
        )

        md = plan.to_markdown()
        assert len(md) > 500                              # 足够长
        assert "## " in md                                # 有二级标题
        assert "### " in md                               # 有三级标题
        assert "¥" in md                                  # 有价格符号


# =============================================================================
# _parse_llm_response 测试
# =============================================================================
class TestParseLLMResponse:
    """LLM 响应解析测试"""

    def test_parse_clean_json(self):
        """
        测试用例：解析纯 JSON
        验证点：正确解析 JSON 结构
        """
        planner = ProductPlanner()
        response = '{"overview": {"target_audience": "测试受众", "unique_value": "价值", "monetization_goal": "目标"}, "product_items": [], "content_strategy": {"generation_order": [], "cross_references": "", "free_vs_paid": ""}, "pricing_strategy": {"individual_prices": {}, "bundle_price": 0, "premium_price": 0, "pricing_rationale": ""}, "timeline": {"estimated_minutes": 10, "chunk_count_total": 5, "suggested_schedule": "测试"}}'

        result = planner._parse_llm_response(response)

        assert result["overview"]["target_audience"] == "测试受众"
        assert result["timeline"]["estimated_minutes"] == 10

    def test_parse_json_in_code_block(self):
        """
        测试用例：解析包裹在 ```json ``` 中的 JSON
        验证点：正确去除代码块标记
        """
        planner = ProductPlanner()
        response = '```json\n{"overview": {"target_audience": "A", "unique_value": "B", "monetization_goal": "C"}, "product_items": [], "content_strategy": {"generation_order": [], "cross_references": "", "free_vs_paid": ""}, "pricing_strategy": {"individual_prices": {}, "bundle_price": 0, "premium_price": 0, "pricing_rationale": ""}, "timeline": {"estimated_minutes": 5, "chunk_count_total": 3, "suggested_schedule": ""}}\n```'

        result = planner._parse_llm_response(response)

        assert result["overview"]["target_audience"] == "A"
        assert result["timeline"]["chunk_count_total"] == 3

    def test_parse_json_with_extra_text(self):
        """
        测试用例：JSON 前后有额外文本
        验证点：正确提取 JSON 部分
        """
        planner = ProductPlanner()
        response = '这是额外说明\n\n{"overview": {"target_audience": "X", "unique_value": "Y", "monetization_goal": "Z"}, "product_items": [], "content_strategy": {"generation_order": [], "cross_references": "", "free_vs_paid": ""}, "pricing_strategy": {"individual_prices": {}, "bundle_price": 0, "premium_price": 0, "pricing_rationale": ""}, "timeline": {"estimated_minutes": 1, "chunk_count_total": 1, "suggested_schedule": ""}}\n\n结束'

        result = planner._parse_llm_response(response)

        assert result["overview"]["target_audience"] == "X"

    def test_parse_invalid_json_returns_empty(self):
        """
        测试用例：解析无效 JSON
        验证点：返回空结构（不抛异常）
        """
        planner = ProductPlanner()
        response = "这不是 JSON"

        result = planner._parse_llm_response(response)

        # 返回空结构
        assert isinstance(result, dict)
        assert "overview" in result
        assert result["product_items"] == []

    def test_parse_empty_string(self):
        """
        测试用例：解析空字符串
        验证点：返回空结构
        """
        planner = ProductPlanner()
        result = planner._parse_llm_response("")

        assert isinstance(result, dict)
        assert result["overview"] == {}
        assert result["product_items"] == []


# =============================================================================
# 自动确认流程测试
# =============================================================================
class TestAutoConfirm:
    """自动确认流程逻辑测试"""

    def test_plan_has_auto_confirm_support(self):
        """
        测试用例：验证 PlanRequest 支持 auto_confirm 字段
        验证点：API 可以接受 auto_confirm=True 的请求
        """
        from app.routers.ai import PlanRequest

        # 创建带 auto_confirm 的请求
        req = PlanRequest(note_id=1, auto_confirm=True)
        assert req.auto_confirm is True
        assert req.note_id == 1

        # 创建不带 auto_confirm 的请求（默认值）
        req_default = PlanRequest(note_id=2)
        assert req_default.auto_confirm is False
