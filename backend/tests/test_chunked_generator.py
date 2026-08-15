# =============================================================================
# tests/test_chunked_generator.py - 分块生成器单元测试
# =============================================================================
# 测试 ChunkedGenerator 和 CHUNK_DEFINITIONS 的核心功能：
#   1. 所有产品类型都有分块定义
#   2. 每块定义完整性验证（id/title/prompt/order 不能为空）
#   3. _build_chunk_prompt 占位符替换
#   4. _summarize_chunks 摘要生成
#   5. _assemble_document 文档组装
#   6. get_chunk_count / list_supported_types
#   7. _sanitize_filename 文件名安全处理
# =============================================================================

import pytest
from app.services.chunked_generator import (
    ChunkedGenerator, CHUNK_DEFINITIONS
)
from app.services.llm_service import LLMService
from app.services.llm_config import LLMConfig


# =============================================================================
# Fixture: 模拟 LLM 服务（不真正调用 API）
# =============================================================================
@pytest.fixture
def mock_llm():
    """
    创建一个模拟的 LLM 服务（is_ready=True，但 chat 方法用 mock）

    用于测试分块引擎的组装逻辑，不真正调用外部 API
    """
    config = LLMConfig(
        provider="test",
        api_key="test-key-12345678",
        base_url="http://test.local/v1",
        model="test-model",
        is_enabled=True,
    )
    return LLMService(config)


# =============================================================================
# 测试 CHUNK_DEFINITIONS 数据结构
# =============================================================================
class TestChunkDefinitions:
    """分块定义数据结构测试"""

    def test_all_product_types_have_chunks(self):
        """
        测试用例：所有 PRODUCT_TYPES 中的产品类型都有分块定义
        验证点：共14种产品类型的分块定义齐全
        """
        from app.services.product_generator import PRODUCT_TYPES

        for ptype in PRODUCT_TYPES:
            assert ptype in CHUNK_DEFINITIONS, \
                f"产品类型 '{ptype}' 缺少分块定义"

    def test_each_chunk_has_required_fields(self):
        """
        测试用例：每个分块都有必需的字段
        验证点：id, title, order, prompt_template 不为空
        """
        required = ["id", "title", "order", "prompt_template"]
        for ptype, chunks in CHUNK_DEFINITIONS.items():
            for chunk in chunks:
                for field in required:
                    assert field in chunk, \
                        f"产品类型 {ptype} 的块缺少字段 '{field}'"
                    assert chunk[field] is not None
                    assert chunk[field] != "", \
                        f"产品类型 {ptype} 的块字段 '{field}' 为空"

    def test_chunk_orders_are_sequential(self):
        """
        测试用例：每个产品类型的分块 order 是连续的
        验证点：order 从 1 开始递增，无跳跃无重复
        """
        for ptype, chunks in CHUNK_DEFINITIONS.items():
            orders = [c["order"] for c in chunks]
            # 从1开始
            assert orders[0] == 1, \
                f"产品类型 {ptype} 的第一个分块 order 应为1"
            # 连续递增
            for i in range(1, len(orders)):
                assert orders[i] == orders[i-1] + 1, \
                    f"产品类型 {ptype} 的分块 order 不连续: {orders}"

    def test_chunk_prompts_contain_placeholders(self):
        """
        测试用例：分块提示词包含必要的占位符
        验证点：prompt_template 中包含 {note_title} 或 {note_content}
        """
        for ptype, chunks in CHUNK_DEFINITIONS.items():
            for chunk in chunks:
                prompt = chunk["prompt_template"]
                # 每块的提示词应至少包含一个上下文占位符
                has_placeholder = (
                    "{note_title}" in prompt
                    or "{note_content}" in prompt
                    or "{subject_name}" in prompt
                    or "{prev_chunks}" in prompt
                )
                assert has_placeholder, \
                    f"产品类型 {ptype} 的块 '{chunk['id']}' 缺少上下文占位符"

    def test_article_has_6_chunks(self):
        """
        测试用例：文章类型有6个分块（最复杂的产品类型）
        验证点：article 分块数 = 6
        """
        assert len(CHUNK_DEFINITIONS["article"]) == 6

    def test_chunk_prompts_are_unique_within_type(self):
        """
        测试用例：同一产品类型的各分块提示词不尽相同
        验证点：不存在两个完全相同的 prompt_template
        """
        for ptype, chunks in CHUNK_DEFINITIONS.items():
            prompts = [c["prompt_template"] for c in chunks]
            # 去重后数量不应变化（除非本来就有重复）
            unique = set(prompts)
            assert len(unique) == len(prompts), \
                f"产品类型 {ptype} 存在重复的 prompt_template"


# =============================================================================
# 测试 ChunkedGenerator 方法
# =============================================================================
class TestChunkedGeneratorMethods:
    """ChunkedGenerator 方法测试"""

    def test_init(self, mock_llm):
        """
        测试用例：创建 ChunkedGenerator 实例
        验证点：实例创建成功，llm 属性正确
        """
        gen = ChunkedGenerator(mock_llm)
        assert gen is not None
        assert gen.llm is mock_llm
        assert gen._chunk_cache == {}

    def test_build_chunk_prompt_replaces_placeholders(self, mock_llm):
        """
        测试用例：_build_chunk_prompt 正确替换占位符
        验证点：{note_title}/{note_content}/{subject_name} 等被替换为实际值
        """
        gen = ChunkedGenerator(mock_llm)

        chunk_def = {
            "id": "test",
            "title": "测试",
            "prompt_template": "标题：{note_title}，科目：{subject_name}，内容：{note_content}，上文：{prev_chunks}",
            "order": 1,
        }
        context = {
            "note_title": "Python入门",
            "note_content": "学习print函数",
            "subject_name": "Python",
            "difficulty": "beginner",
            "keywords": "Python, 基础",
            "prev_chunks": "",
        }

        prompt = gen._build_chunk_prompt(chunk_def, context, "前文摘要")

        # 验证替换
        assert "Python入门" in prompt              # title 已替换
        assert "学习print函数" in prompt            # content 已替换
        assert "Python" in prompt                   # subject 已替换
        assert "前文摘要" in prompt                  # prev_summary 已替换
        assert "{note_title}" not in prompt         # 占位符已被替换
        assert "{note_content}" not in prompt

    def test_summarize_chunks(self, mock_llm):
        """
        测试用例：_summarize_chunks 生成摘要
        验证点：每块的标题和内容片段都出现在摘要中
        """
        gen = ChunkedGenerator(mock_llm)

        chunks = [
            {"id": "meta", "title": "标题优化", "content": "这是第一块的内容，介绍标题优化。", "order": 1},
            {"id": "intro", "title": "引言", "content": "这是引言部分的内容。", "order": 2},
        ]

        summary = gen._summarize_chunks(chunks)

        assert "标题优化" in summary
        assert "引言" in summary
        assert "这是第一块的内容" in summary

    def test_assemble_document(self, mock_llm):
        """
        测试用例：_assemble_document 组装文档
        验证点：
            1. 文档以标题开头
            2. 各分块内容按 order 排序
            3. 分块间有分隔线
            4. 结尾有标记
        """
        gen = ChunkedGenerator(mock_llm)

        chunks = [
            {"id": "meta", "title": "元信息", "content": "# 标题\n\n元信息内容", "order": 1},
            {"id": "core", "title": "核心概念", "content": "## 核心概念\n\n核心内容", "order": 2},
        ]

        doc = gen._assemble_document("article", chunks, "测试笔记")

        # 验证结构
        assert doc.startswith("# 测试笔记")          # 文档以标题开头
        assert "元信息内容" in doc                   # 第一块内容
        assert "核心内容" in doc                     # 第二块内容
        assert "---" in doc                          # 分隔线
        assert "Learn2Earn" in doc                   # 结尾标记

    def test_assemble_document_orders_chunks(self, mock_llm):
        """
        测试用例：文档组装时按 order 排序
        验证点：即使 chunks 列表乱序，文档中仍是 order 顺序
        """
        gen = ChunkedGenerator(mock_llm)

        # 故意乱序输入
        chunks = [
            {"id": "core", "title": "核心", "content": "核心内容", "order": 2},
            {"id": "meta", "title": "元信息", "content": "元信息内容", "order": 1},
            {"id": "end", "title": "结尾", "content": "结尾内容", "order": 3},
        ]

        doc = gen._assemble_document("article", chunks, "测试")

        # 验证顺序：meta(1) 应在 core(2) 之前
        meta_pos = doc.find("元信息内容")
        core_pos = doc.find("核心内容")
        end_pos = doc.find("结尾内容")
        assert meta_pos < core_pos < end_pos

    def test_get_chunk_count(self):
        """
        测试用例：get_chunk_count 返回正确的分块数
        验证点：article=6, sop=4, flashcard=3
        """
        assert ChunkedGenerator.get_chunk_count("article") == 6
        assert ChunkedGenerator.get_chunk_count("sop") == 4
        assert ChunkedGenerator.get_chunk_count("flashcard") == 3
        assert ChunkedGenerator.get_chunk_count("nonexistent") == 0  # 不存在=0

    def test_list_supported_types(self):
        """
        测试用例：list_supported_types 返回完整列表
        验证点：包含14种产品类型，各有 chunk_count
        """
        types = ChunkedGenerator.list_supported_types()
        assert len(types) >= 14                    # 支持扩展后的产品类型
        for t in types:
            assert "type" in t
            assert "chunk_count" in t
            assert "chunk_names" in t
            assert t["chunk_count"] > 0            # 每种至少有1个分块


# =============================================================================
# 测试 _sanitize_filename
# =============================================================================
class TestSanitizeFilename:
    """文件名安全处理测试"""

    def test_sanitize_replaces_illegal_chars(self):
        """
        测试用例：替换非法字符
        验证点：<>:"/\|?* 被替换为 _
        """
        from app.services.batch_generator import BatchGenerator

        result = BatchGenerator._sanitize_filename('test<file>:name?*.txt')
        assert '<' not in result
        assert '>' not in result
        assert ':' not in result
        assert '"' not in result
        assert '/' not in result
        assert '\\' not in result
        assert '|' not in result
        assert '?' not in result
        assert '*' not in result

    def test_sanitize_truncates_long_name(self):
        """
        测试用例：文件名超过50字符时截断
        验证点：结果不超过50字符
        """
        from app.services.batch_generator import BatchGenerator

        long_name = "A" * 80
        result = BatchGenerator._sanitize_filename(long_name)
        assert len(result) <= 50

    def test_sanitize_keeps_safe_name(self):
        """
        测试用例：安全名称不变
        验证点：纯中文/英文数字/-_不变化
        """
        from app.services.batch_generator import BatchGenerator

        safe = "Python装饰器实战笔记"
        result = BatchGenerator._sanitize_filename(safe)
        assert result == safe
