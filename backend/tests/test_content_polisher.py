# =============================================================================
# tests/test_content_polisher.py - 内容抛光器单元测试
# =============================================================================

import pytest
from app.services.content_polisher import ContentPolisher


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def polisher():
    """创建抛光器实例"""
    return ContentPolisher()


# =============================================================================
# 测试数据
# =============================================================================

# 模拟LLM输出 — 含AI解释前缀
CONTENT_WITH_AI_PREFIX = """以下是生成的技术文章，供您参考：

# Python装饰器实战指南
## 引言
装饰器是Python中最优雅的特性之一。

## 核心概念
### 什么是装饰器
装饰器本质是一个高阶函数。
```python
def my_decorator(func):
    return func
```

## 总结
掌握装饰器就可以写出更优雅的代码。

希望对你有所帮助！"""

# 模拟LLM输出 — 含AI解释后缀
CONTENT_WITH_AI_SUFFIX = """# 文章标题
正文内容

以上内容由AI生成，如有错误请指正。"""

# 模拟LLM输出 — 未闭合代码块
CONTENT_WITH_UNCLOSED_CODE = """# 测试
## 代码示例
```python
print("hello")
"""

# 模拟LLM输出 — 多余空行
CONTENT_WITH_BLANKS = "# 标题\n\n\n\n\n段落1\n\n\n\n\n段落2"

# 模拟LLM输出 — * 列表标记
CONTENT_WITH_STAR_LIST = "# 标题\n* 项目1\n* 项目2\n  * 子项目"

# LLM输出 — 英文AI前缀
EN_AI_PREFIX = "Here is the technical article you requested:\n\n# Python Guide\nContent"

# 多前缀叠加
MULTI_PREFIX = "好的，没问题。\n\n以下是为你生成的：\n\n# 标题\n正文"


# =============================================================================
# AI 解释去除测试
# =============================================================================
class TestStripAIPrefix:
    """AI 解释前缀去除"""

    def test_strip_chinese_prefix(self, polisher):
        """去除'以下是'前缀"""
        cleaned, stats = polisher.polish(CONTENT_WITH_AI_PREFIX, "article", "Python")
        assert "以下是" not in cleaned[:100]
        assert stats["ai_stripped"] >= 1

    def test_strip_english_prefix(self, polisher):
        """去除英文AI前缀"""
        cleaned, stats = polisher.polish(EN_AI_PREFIX)
        assert "Here is" not in cleaned[:100]

    def test_preserve_real_content(self, polisher):
        """去除前缀后核心内容应保留"""
        cleaned, stats = polisher.polish(CONTENT_WITH_AI_PREFIX, "article", "Python")
        assert "Python装饰器实战指南" in cleaned
        assert "高阶函数" in cleaned

    def test_strip_multi_prefix(self, polisher):
        """去除多层叠加的AI解释"""
        cleaned, stats = polisher.polish(MULTI_PREFIX)
        assert "好的" not in cleaned[:100]

    def test_strip_ai_suffix(self, polisher):
        """去除末尾的AI客套话"""
        cleaned, stats = polisher.polish(CONTENT_WITH_AI_SUFFIX)
        assert "如有错误" not in cleaned[-100:]


# =============================================================================
# 代码块修复测试
# =============================================================================
class TestFixCodeBlocks:
    """代码块修复"""

    def test_fix_unclosed_code_block(self, polisher):
        """未闭合的代码块→补闭合标记"""
        cleaned, stats = polisher.polish(CONTENT_WITH_UNCLOSED_CODE)
        assert stats["code_fixed"] >= 1
        assert cleaned.count("```") % 2 == 0  # 偶数个 ```

    def test_preserve_correct_code_blocks(self, polisher):
        """正确闭合的代码块不变"""
        correct = "# 标题\n```python\nprint(1)\n```\n正文"
        cleaned, stats = polisher.polish(correct)
        assert cleaned.count("```") == 2  # 不变


# =============================================================================
# 空行标准化测试
# =============================================================================
class TestNormalizeBlankLines:
    """空行标准化"""

    def test_reduce_many_blanks(self, polisher):
        """5连空行→最多2空行"""
        cleaned, stats = polisher.polish(CONTENT_WITH_BLANKS)
        # 不应有5连空行
        assert "\n\n\n\n\n" not in cleaned

    def test_preserve_code_blocks(self, polisher):
        """代码块内的空行不处理"""
        content = "# Title\n\n```python\n\nprint(1)\n\n```\n\nEnd"
        cleaned, stats = polisher.polish(content)
        assert "```python" in cleaned
        assert "print(1)" in cleaned


# =============================================================================
# 列表标准化测试
# =============================================================================
class TestNormalizeListMarkers:
    """列表标准化"""

    def test_convert_star_to_dash(self, polisher):
        """* → -"""
        cleaned, stats = polisher.polish(CONTENT_WITH_STAR_LIST)
        # 应该是-列表
        assert "- 项目1" in cleaned

    def test_preserve_existing_dash(self, polisher):
        """已有的-不应被修改"""
        content = "# 标题\n- 项目1\n- 项目2"
        cleaned, stats = polisher.polish(content)
        assert cleaned.count("- 项目") == 2

    def test_preserve_ordered_lists(self, polisher):
        """有序列表不应被修改"""
        content = "# 标题\n1. 第一步\n2. 第二步"
        cleaned, stats = polisher.polish(content)
        assert "1. 第一步" in cleaned


# =============================================================================
# 标题修复测试
# =============================================================================
class TestEnsureFirstHeading:
    """首行标题修复"""

    def test_add_heading_when_missing(self, polisher):
        """无标题→添加标题"""
        content = "这是正文第一行\n更多内容"
        cleaned, stats = polisher.polish(content, title="Python装饰器")
        assert cleaned.startswith("#")

    def test_preserve_existing_heading(self, polisher):
        """已有标题→不修改"""
        content = "# 已有标题\n正文内容"
        cleaned, stats = polisher.polish(content, title="新标题")
        assert cleaned.startswith("# 已有标题")

    def test_no_title_provided(self, polisher):
        """无标题参数→不添加"""
        content = "正文内容"
        cleaned, stats = polisher.polish(content)
        assert not cleaned.startswith("#")


# =============================================================================
# 完整抛光流程测试
# =============================================================================
class TestPolishPipeline:
    """完整抛光流程"""

    def test_polish_returns_tuple(self, polisher):
        """polish返回(content, stats)"""
        result = polisher.polish("测试内容")
        assert isinstance(result, tuple)
        assert isinstance(result[0], str)
        assert isinstance(result[1], dict)

    def test_polish_handles_empty(self, polisher):
        """空内容→空返回"""
        cleaned, stats = polisher.polish("")
        assert cleaned == ""

    def test_polish_handles_whitespace(self, polisher):
        """纯空白→空返回"""
        cleaned, stats = polisher.polish("  \n  \n  ")
        assert cleaned == ""

    def test_all_ai_patterns_tested(self, polisher):
        """逐一验证所有AI模式"""
        test_cases = [
            "Here is the article:\n# 标题",
            "I'll create the content:\n# 标题",
            "Let me generate:\n# 标题",
            "Sure, here is:\n# 标题",
            "Certainly! Here:\n# 标题",
            "以下是生成的文章：\n# 标题",
            "下面为您生成：\n# 标题",
            "我来生成下面的内容：\n# 标题",
        ]
        for case in test_cases:
            cleaned, stats = polisher.polish(case)
            assert cleaned.startswith("#"), f"Failed to clean: {case[:50]}"

    def test_validate_clean_content(self, polisher):
        """已清洁内容→validate返回空"""
        clean = "# 标题\n\n## 小节\n正文内容足够长。" * 15  # 约300字
        issues = polisher.validate(clean)
        assert issues == []

    def test_validate_dirty_content(self, polisher):
        """含AI残余→validate检测到"""
        dirty = "Here is the article:\n# 标题\n短内容"
        issues = polisher.validate(dirty)
        assert len(issues) >= 1


# =============================================================================
# 静态方法测试
# =============================================================================
class TestPolishProduct:
    """静态方法"""

    def test_polish_product_static(self):
        """静态方法可独立使用，前缀被去掉后正文保留"""
        cleaned, stats = ContentPolisher.polish_product(
            "以下是文章：\n# 标题\n\n正文内容第一段。\n\n正文内容第二段。" * 3,
            "article",
            "测试标题"
        )
        # AI前缀"以下是文章："应被去掉
        assert not cleaned.startswith("以下是")
        # 正文标题和内容应保留
        assert "# 标题" in cleaned
        assert "正文内容" in cleaned


# =============================================================================
# 回归：确保不误删真实内容
# =============================================================================
class TestRegression:
    """回归测试"""

    def test_code_not_removed(self, polisher):
        """代码内容不应被当作AI解释删除"""
        code_content = "```python\nprint('Here is the output')\n```"
        cleaned, stats = polisher.polish(code_content)
        assert "print(" in cleaned or "Here is" in cleaned

    def test_inline_here_not_removed(self, polisher):
        """行内的'here is'不应被删除"""
        content = "# 标题\n正文中提到'here is the key'"
        cleaned, stats = polisher.polish(content)
        assert "here is the key" in cleaned

    def test_table_content_not_damaged(self, polisher):
        """表格内容不应被破坏"""
        table = "# 标题\n\n| 项目 | 内容 |\n|------|------|\n| 测试 | 数据 |"
        cleaned, stats = polisher.polish(table)
        assert "| 项目 |" in cleaned
        assert "| 测试 |" in cleaned


# =============================================================================
# 回归测试：去除大模型思维链 <think> 块（修复"产品正文泄漏思维链"Bug）
# =============================================================================
class TestStripReasoningBlocks:
    """针对 content_polisher._strip_reasoning_blocks 的回归测试。

    背景：推理模型（DeepSeek-R1 / MiniMax 等）会输出 <think>...</think> 思维链，
    历史上未被清洗，导致 38/49 个产品正文泄漏 "The user wants..."/"用户要求..."。
    """

    def test_strip_closed_think_block(self, polisher):
        """闭合的 <think>...</think> 应被整体删除，正文保留。"""
        raw = "<think>The user wants me to extract core concepts</think>\n\n# SPI 概念\n正文。"
        cleaned, stats = polisher.polish(raw)
        assert "<think" not in cleaned.lower()          # 标签清除
        assert "user wants" not in cleaned.lower()      # 思维链文字清除
        assert "# SPI 概念" in cleaned                    # 正文保留

    def test_strip_malformed_unclosed_think(self, polisher):
        """畸形未闭合 <think（缺 > 且紧跟中文）应删除到首个 Markdown 标题。"""
        raw = "<think用户要求我从一个关于SPI的笔记中提炼核心概念\n# SPI 知识导图\n- 概念A"
        cleaned, stats = polisher.polish(raw)
        assert "用户要求" not in cleaned                  # 中文思维链清除
        assert "<think" not in cleaned.lower()
        assert "# SPI 知识导图" in cleaned                 # 正文标题保留

    def test_strip_multiline_think(self, polisher):
        """跨多行的思维链块应被删除。"""
        raw = "<think>\nThe user wants to act as a senior engineer.\n多行思考。\n</think>\n正常文章开头。"
        cleaned, stats = polisher.polish(raw)
        assert "senior engineer" not in cleaned.lower()
        assert "正常文章开头。" in cleaned

    def test_normal_words_not_removed(self, polisher):
        """普通词 rethink/thinking 不应被误删（避免过度清洗）。"""
        raw = "# 标题\n正文里偶然提到 rethink 或 thinking 这些词。"
        cleaned, stats = polisher.polish(raw)
        assert "rethink" in cleaned
        assert "thinking" in cleaned

    def test_clean_content_unchanged_by_think_step(self, polisher):
        """无思维链的干净内容不应因该步骤被破坏。"""
        raw = "# 干净标题\n这是正常内容，没有任何思维链。"
        cleaned, stats = polisher.polish(raw)
        assert "# 干净标题" in cleaned
        assert "正常内容" in cleaned
