# =============================================================================
# tests/test_reasoning_scrubber.py - F02 推理思维链清除器单元测试
# =============================================================================
# 对应模块：app/services/reasoning_scrubber.py
#
# 测试目标：
#   1. 标签类思维链（<think>/<thinking> 闭合块、孤儿闭标签、畸形缺尖括号、围栏块）
#      必须被彻底清除（修复 B1）。
#   2. 无标签的自然语言推理序言（"首先，我需要理解…" / "I need to…"）
#      必须被清除，但只在标题之前的序言区（修复 B3）。
#   3. 正文里的合法内容（"硬性要求："、rethink/thinking 词、Python 代码块、
#      表格、第一人称题干）必须原样保留——杜绝 B4 式内容销毁。
#   4. 永不清空：整篇都是思维链时回退原文并置 fallback 标记。
#   5. 空串安全返回。
#   6. detect_reasoning 只读检测能力。
# =============================================================================

import pytest
from app.services.reasoning_scrubber import scrub_reasoning, detect_reasoning


# =============================================================================
# 一、标签类思维链清洗（B1 修复）
# =============================================================================
class TestTagBlocks:
    """标签形态的思维链必须被清除，且正文标题/内容保留。"""

    def test_think_closed_block_removed(self):
        content = "<think>用户让我为「Redis 持久化」出一套面试题库。</think>\n# Redis 持久化面试题库\n\n## 基础题\n1. 请解释 RDB 与 AOF。"
        out, stats = scrub_reasoning(content)
        assert "<think" not in out
        assert "Redis 持久化面试题库" in out
        assert "请解释 RDB 与 AOF" in out
        assert stats["tag_blocks"] >= 1

    def test_thinking_tag_closed_block_removed(self):
        # B1 核心：<thinking> 原来因 \b 边界漏匹配，现在必须清掉
        content = "<thinking>我需要先梳理 RDB 和 AOF 的区别。</thinking>\n# Kafka 面试题库\n\n## 基础题\n内容"
        out, stats = scrub_reasoning(content)
        assert "<thinking>" not in out
        assert "Kafka 面试题库" in out
        assert stats["tag_blocks"] >= 1

    def test_stray_tags_removed(self):
        # 孤立开/闭标签残留
        content = "## 小节\n正文<think>废话</think>继续</think>结尾"
        out, stats = scrub_reasoning(content)
        assert "<think" not in out
        assert "正文" in out and "继续" in out and "结尾" in out
        assert stats["stray_tags"] >= 1

    def test_orphan_close_cut(self):
        # 有 </think> 却无配对 <think> → 文首到闭标签整段是思维链残骸
        content = "我需要先分析需求</think>\n# Kafka 面试题库\n\n## 基础题\n内容"
        out, stats = scrub_reasoning(content)
        assert stats["orphan_cut"] == 1
        assert out.startswith("# Kafka 面试题库")
        assert "我需要先分析需求" not in out

    def test_malformed_open_no_gt(self):
        # 畸形：<think 后缺失 >（如 "<think用户…"）
        content = "<think用户让我为「SPI」整理一份知识导图\n# SPI 知识导图\n\n## 概念\n内容"
        out, stats = scrub_reasoning(content)
        assert stats["unclosed_cut"] >= 1
        assert out.startswith("# SPI 知识导图")
        assert "用户让我" not in out

    def test_fenced_thinking_block_removed(self):
        # ```thinking … ``` 把思维链塞进代码块
        content = "```thinking\n我应该先列出常考知识点。\n然后再出追问。\n```\n# 题库\n\n## 基础\n1. 问题一\n"
        out, stats = scrub_reasoning(content)
        assert stats["fenced_blocks"] >= 1
        assert "我应该先列出" not in out
        assert "题库" in out


# =============================================================================
# 二、无标签的自然语言推理序言（B3 修复）
# =============================================================================
class TestPreambleNaturalLanguage:
    """无冒号的自然语言推理段只在序言区清除。"""

    def test_preamble_chinese_metacognition(self):
        content = (
            "首先，我需要理解用户提供的笔记内容。\n"
            "让我先看看都有哪些关键点。\n"
            "我觉得应该分层出题。\n"
            "# MySQL 索引面试题库\n\n## 基础题\n1. 什么是回表？\n"
        )
        out, stats = scrub_reasoning(content)
        assert stats["preamble_lines"] >= 1
        assert "首先，我需要理解" not in out
        assert "让我先看看" not in out
        assert "MySQL 索引面试题库" in out
        assert "什么是回表" in out

    def test_preamble_english_cot(self):
        content = (
            "I need to analyze the user's notes first.\n"
            "Let me think about the structure.\n"
            "# Interview Bank\n\n## Questions\n1. Explain X.\n"
        )
        out, stats = scrub_reasoning(content)
        assert stats["preamble_lines"] >= 1
        assert "Interview Bank" in out
        assert "Explain X" in out


# =============================================================================
# 三、回归：正文合法内容不得误删（B4 防御）
# =============================================================================
class TestNoFalseDeletion:
    """正文里合法出现的关键词/结构必须保留。"""

    def test_body_hard_requirement_preserved(self):
        # B4 修复：正文"硬性要求："绝不能被腰斩误删
        content = (
            "# 高级后端面试题库\n\n"
            "## 基础题\n1. 请解释 TCP 三次握手。\n\n"
            "## 评分说明\n硬性要求：候选人必须答出全部三次握手状态迁移。\n"
        )
        out, stats = scrub_reasoning(content)
        assert "硬性要求：候选人必须答出全部三次握手状态迁移" in out
        assert "# 高级后端面试题库" in out
        assert "请解释 TCP 三次握手" in out
        assert stats["preamble_lines"] == 0

    def test_rethink_thinking_words_preserved(self):
        content = "# 标题\n正文里偶然提到 rethink 或 thinking 这些词，属于正常内容。"
        out, stats = scrub_reasoning(content)
        assert "rethink" in out and "thinking" in out
        assert stats["preamble_lines"] == 0

    def test_python_code_block_preserved(self):
        content = "```python\nprint('Here is the output')\n```"
        out, stats = scrub_reasoning(content)
        assert "print(" in out
        assert "Here is" in out  # 不是 thinking 围栏，必须保留

    def test_table_preserved(self):
        content = "# 标题\n\n| 项目 | 内容 |\n|------|------|\n| 测试 | 数据 |"
        out, stats = scrub_reasoning(content)
        assert "| 项目 | 内容 |" in out
        assert "| 测试 | 数据 |" in out

    def test_first_person_in_body_question_preserved(self):
        # 正文里的第一人称题干（"假如我需要…"）不算思考过程
        content = "# 面试题库\n\n## 场景题\n1. 假如我需要把 QPS 提升 10 倍，我应该怎么做？"
        out, stats = scrub_reasoning(content)
        assert "假如我需要把 QPS 提升 10 倍，我应该怎么做" in out
        assert stats["preamble_lines"] == 0

    def test_clean_content_unchanged(self):
        content = "# 干净标题\n这是正常内容，没有任何思维链。"
        out, stats = scrub_reasoning(content)
        assert out == content
        assert all(v == 0 for v in stats.values())


# =============================================================================
# 四、安全阀：永不清空
# =============================================================================
class TestSafetyValve:
    def test_all_reasoning_triggers_fallback(self):
        # 整篇都是思维链 → 不能交付空产品，回退原文
        content = "<think>\n我需要想想。\n让我分析一下。\n"
        out, stats = scrub_reasoning(content)
        assert out == content
        assert stats["fallback"] == 1

    def test_empty_string(self):
        out, stats = scrub_reasoning("")
        assert out == ""
        assert all(v == 0 for v in stats.values())


# =============================================================================
# 五、detect_reasoning 只读检测
# =============================================================================
class TestDetectReasoning:
    def test_detects_tag_residue(self):
        issues = detect_reasoning("<thinking>废话</think>\n# 标题\n正文")
        assert any("思维链标签" in i for i in issues)

    def test_detects_preamble_reasoning(self):
        issues = detect_reasoning("我需要先理解需求。\n# 标题\n正文")
        assert any("思考过程" in i for i in issues)

    def test_clean_returns_empty(self):
        assert detect_reasoning("# 标题\n正常正文") == []

    def test_body_first_person_not_flagged(self):
        body = "# 面试题库\n\n## 场景题\n1. 假如我需要把 QPS 提升 10 倍，我应该怎么做？"
        assert detect_reasoning(body) == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
