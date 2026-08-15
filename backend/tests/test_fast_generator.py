# =============================================================================
# tests/test_fast_generator.py - 快速生成器单元测试
# =============================================================================

import pytest
from app.services.fast_generator import FastGenerator, fast_generator
from app.services.llm_service import LLMService
from app.services.llm_config import LLMConfig


# =============================================================================
# 测试数据
# =============================================================================
# 模拟 LLM 返回的多产品内容（含规划+3个产品）
MOCK_RESPONSE = """---PLAN---
{"target_audience":"中级Python开发者","unique_value":"将装饰器知识系统化","selected_products":["article","sop","checklist"],"total_revenue":77}
---PRODUCTS---
---PRODUCT article---
# Python装饰器实战指南
## 引言
装饰器是Python中最优雅的特性之一。
## 核心概念
装饰器本质是高阶函数。
## 总结
掌握装饰器让你写出更优雅的代码。
---
---PRODUCT sop---
# Python装饰器SOP
## 文档信息
| 项目 | 内容 |
## 操作流程
### 第一步
---
---PRODUCT checklist---
# 装饰器学习清单
- [ ] 理解高阶函数
- [ ] 手写装饰器
- [ ] 掌握functools.wraps
---
---END---"""

MOCK_RESPONSE_NO_END = """---PLAN---
{"selected_products":["article"],"total_revenue":29}
---PRODUCTS---
---PRODUCT article---
# 测试文章
正文内容
---END---"""


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def mock_llm():
    """模拟LLM服务"""
    config = LLMConfig(
        provider="test", api_key="test-key-12345678",
        base_url="http://test/v1", model="test-model", is_enabled=True,
    )
    return LLMService(config)


# =============================================================================
# FastGenerator 初始化测试
# =============================================================================
class TestFastGeneratorInit:
    """初始化测试"""

    def test_init_with_llm(self, mock_llm):
        """传入LLM创建实例"""
        gen = FastGenerator(mock_llm)
        assert gen.llm is mock_llm
        assert gen.PLAN_START == "---PLAN---"
        assert gen.ALL_END == "---END---"

    def test_module_singleton(self):
        """模块级单例存在"""
        assert fast_generator is not None
        assert isinstance(fast_generator, FastGenerator)


# =============================================================================
# _parse_response 测试
# =============================================================================
class TestParseResponse:
    """响应解析测试"""

    def test_parse_complete_response(self, mock_llm):
        """解析完整的多产品响应"""
        gen = FastGenerator(mock_llm)
        plan, products = gen._parse_response(MOCK_RESPONSE, "Python装饰器")

        # 验证规划
        assert plan["target_audience"] == "中级Python开发者"
        assert plan["unique_value"] == "将装饰器知识系统化"
        assert plan["total_revenue"] == 77

        # 验证产品数量
        assert len(products) == 3

        # 验证产品类型
        types = [p["type"] for p in products]
        assert "article" in types
        assert "sop" in types
        assert "checklist" in types

    def test_parse_article_content(self, mock_llm):
        """解析的文章内容应包含标题"""
        gen = FastGenerator(mock_llm)
        plan, products = gen._parse_response(MOCK_RESPONSE, "Python装饰器")

        article = next(p for p in products if p["type"] == "article")
        assert "装饰器" in article["content"]
        assert "## 引言" in article["content"]

    def test_parse_product_has_metadata(self, mock_llm):
        """每个产品应有type/name/icon/title/price_suggestion"""
        gen = FastGenerator(mock_llm)
        plan, products = gen._parse_response(MOCK_RESPONSE, "Python装饰器")

        for p in products:
            assert "type" in p
            assert "name" in p
            assert "icon" in p
            assert "title" in p
            assert "price_suggestion" in p
            assert p["price_suggestion"] >= 0

    def test_parse_empty_response(self, mock_llm):
        """空响应→空产品列表"""
        gen = FastGenerator(mock_llm)
        plan, products = gen._parse_response("", "test")
        assert products == []

    def test_parse_response_without_plan(self, mock_llm):
        """无规划标记→plan返回空，产品按标记解析"""
        gen = FastGenerator(mock_llm)
        response = "---PRODUCTS---\n---PRODUCT article---\n正文内容需要超过五十个字符才能被识别为有效的知识付费产品内容。本文详细介绍了Python装饰器的核心概念和实战技巧。\n---END---"
        plan, products = gen._parse_response(response, "test")
        # 无PLAN标记时plan应为默认空值
        assert plan["target_audience"] == ""
        # 内容>50字符且正确标记→应有1个产品
        assert len(products) >= 1, f"Expected 1+ products, got {len(products)}. Content length check."

    def test_parse_fallback_for_plain_text(self, mock_llm):
        """超长纯文本(>500字符)→回退为一篇文章"""
        gen = FastGenerator(mock_llm)
        long_text = "Python装饰器学习笔记" * 100  # 约800字符
        plan, products = gen._parse_response(long_text, "test")
        # 回退逻辑：无标记且文本>500字符→作为单篇文章
        assert len(products) >= 1
        assert products[0]["type"] == "article"


# =============================================================================
# _estimate_token_saving 测试
# =============================================================================
class TestEstimateTokenSaving:
    """Token节省估算测试"""

    def test_saving_with_3_products(self, mock_llm):
        """3个产品→应节省约60-85%"""
        gen = FastGenerator(mock_llm)
        products = [{"type": "article"}, {"type": "sop"}, {"type": "checklist"}]
        pct = gen._estimate_token_saving(products)
        assert 40 <= pct <= 90

    def test_saving_with_6_products(self, mock_llm):
        """6个产品→节省约50%"""
        gen = FastGenerator(mock_llm)
        products = [{"type": t} for t in ["article","sop","quiz","mindmap","checklist","workflow"]]
        pct = gen._estimate_token_saving(products)
        assert pct >= 50  # 产品越多，节省越多

    def test_saving_with_zero_products(self, mock_llm):
        """0个产品→0%节省"""
        gen = FastGenerator(mock_llm)
        pct = gen._estimate_token_saving([])
        assert pct == 0


# =============================================================================
# _build_combined_prompt 测试
# =============================================================================
class TestBuildCombinedPrompt:
    """合并prompt构建测试"""

    def test_prompt_contains_note_content(self, mock_llm):
        """prompt应包含笔记内容"""
        gen = FastGenerator(mock_llm)
        prompt = gen._build_combined_prompt("测试", "Python装饰器笔记", "Python")
        assert "Python装饰器笔记" in prompt
        assert "---PLAN---" in prompt
        assert "---PRODUCTS---" in prompt
        assert "---END---" in prompt

    def test_prompt_has_output_format_instructions(self, mock_llm):
        """prompt应包含输出格式说明"""
        gen = FastGenerator(mock_llm)
        prompt = gen._build_combined_prompt("标题", "内容", "科目")
        assert "输出格式" in prompt
        assert "---PRODUCT " in prompt

    def test_prompt_truncates_long_content(self, mock_llm):
        """超长笔记应截断（保护prompt长度）"""
        gen = FastGenerator(mock_llm)
        long_content = "A" * 10000
        prompt = gen._build_combined_prompt("标题", long_content, "科目")
        # 不应包含全部10000字符
        assert len(prompt) < 8000


# =============================================================================
# 集成：generate_all 无LLM时的行为
# =============================================================================
class TestGenerateAllNoLLM:
    """无LLM时的generate_all行为"""

    def test_generate_all_without_llm(self, mock_llm):
        """LLM不可用→返回error"""
        # 创建一个不可用的LLM（api_key为空）
        config = LLMConfig(is_enabled=False)
        llm = LLMService(config)
        gen = FastGenerator(llm)

        import asyncio
        result = asyncio.run(gen.generate_all("test", "content", "Python"))

        assert result["success"] is False
        assert "LLM" in result["error"] or "配置" in result["error"]
