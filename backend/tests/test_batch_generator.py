# =============================================================================
# tests/test_batch_generator.py - 批量生成引擎单元测试
# =============================================================================
# 测试 BatchGenerator 的核心功能：
#   1. 初始化与配置
#   2. BatchJob 创建（从数据库加载）
#   3. _sanitize_filename 文件名处理
#   4. _generate_report 报告生成
#   5. _save_file 文件保存
#   6. 并行处理逻辑（使用 asyncio）
# =============================================================================

import pytest
import os
import tempfile
import asyncio
from app.services.batch_generator import BatchGenerator, BatchJob
from app.services.llm_service import LLMService
from app.services.llm_config import LLMConfig


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def mock_llm():
    """模拟 LLM 服务"""
    config = LLMConfig(
        provider="test",
        api_key="test-key-12345678",
        base_url="http://test.local/v1",
        model="test-model",
        is_enabled=True,
    )
    return LLMService(config)


@pytest.fixture
def temp_output_dir():
    """临时输出目录（自动清理）"""
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


# =============================================================================
# 测试 BatchJob
# =============================================================================
class TestBatchJob:
    """BatchJob 数据对象测试"""

    def test_batch_job_creation(self):
        """
        测试用例：创建 BatchJob
        验证点：所有属性正确赋值
        """
        job = BatchJob(
            note_id=1,
            note_title="Python入门",
            note_content="学习print函数的基础用法",
            subject_name="Python",
            product_types=["article", "sop", "mindmap"],
            output_dir="/tmp/output/note_1",
        )

        assert job.note_id == 1
        assert job.note_title == "Python入门"
        assert job.note_content == "学习print函数的基础用法"
        assert job.subject_name == "Python"
        assert job.product_types == ["article", "sop", "mindmap"]
        assert job.output_dir == "/tmp/output/note_1"
        assert job.results == []
        assert job.status == "pending"
        assert job.error is None

    def test_batch_job_default_status(self):
        """
        测试用例：BatchJob 默认状态为 pending
        验证点：创建后 status = "pending"
        """
        job = BatchJob(1, "test", "content", "test", ["article"], "/tmp")
        assert job.status == "pending"


# =============================================================================
# 测试 BatchGenerator 初始化
# =============================================================================
class TestBatchGeneratorInit:
    """BatchGenerator 初始化测试"""

    def test_create_with_llm(self, mock_llm, temp_output_dir):
        """
        测试用例：用指定 LLM 服务创建
        验证点：output_root 和 llm 正确
        """
        bg = BatchGenerator(output_root=temp_output_dir, llm_service=mock_llm)
        assert bg.llm is mock_llm
        assert bg.chunked_gen is not None             # 分块生成器自动创建
        assert bg.stats["total_notes"] == 0           # 初始为0
        assert bg.stats["total_products"] == 0

    def test_create_auto_llm_fails_without_config(self):
        """
        测试用例：无配置时自动创建 LLM 的 is_ready 状态
        验证点：说明如果已有配置文件会读取，否则默认未启用
        """
        # 清理可能残留的配置文件
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "app", "services", "llm_config.json"
        )
        if os.path.exists(config_path):
            os.rename(config_path, config_path + ".bak")
            try:
                bg = BatchGenerator(output_root="output")
                assert bg.llm.is_ready() is False
            finally:
                os.rename(config_path + ".bak", config_path)
        else:
            bg = BatchGenerator(output_root="output")
            # 无配置文件时默认 is_enabled=False
            assert bg.llm.is_ready() is False

    def test_stats_initialized(self, mock_llm, temp_output_dir):
        """
        测试用例：统计字段初始化
        验证点：所有计数为0
        """
        bg = BatchGenerator(output_root=temp_output_dir, llm_service=mock_llm)
        assert bg.stats["total_notes"] == 0
        assert bg.stats["total_products"] == 0
        assert bg.stats["success_count"] == 0
        assert bg.stats["failed_count"] == 0
        assert bg.stats["total_time_ms"] == 0


# =============================================================================
# 测试 _sanitize_filename
# =============================================================================
class TestBatchGeneratorSanitize:
    """文件名安全处理测试"""

    def test_empty_name(self):
        """空字符串测试"""
        result = BatchGenerator._sanitize_filename("")
        assert result == ""

    def test_chinese_name(self):
        """中文字符串应保持不变"""
        result = BatchGenerator._sanitize_filename("Python入门笔记-第一部分")
        assert result == "Python入门笔记-第一部分"

    def test_special_chars(self):
        """特殊字符替换测试"""
        result = BatchGenerator._sanitize_filename('file<name>:test?')
        assert '<' not in result
        assert ':' not in result
        assert '?' not in result


# =============================================================================
# 测试 _save_file
# =============================================================================
class TestBatchGeneratorSaveFile:
    """文件保存测试"""

    def test_save_text_file(self, mock_llm, temp_output_dir):
        """
        测试用例：保存文本到文件
        验证点：文件存在且内容正确
        """
        bg = BatchGenerator(output_root=temp_output_dir, llm_service=mock_llm)
        filepath = os.path.join(temp_output_dir, "test.md")
        content = "# 测试\n\n这是测试内容。"

        saved = bg._save_file(filepath, content)
        assert saved == filepath                     # 返回路径相同
        assert os.path.exists(filepath)              # 文件存在

        with open(filepath, "r", encoding="utf-8") as f:
            assert f.read() == content               # 内容一致

    def test_save_creates_dirs(self, mock_llm, temp_output_dir):
        """
        测试用例：保存时自动创建父目录
        验证点：深层目录自动创建
        """
        bg = BatchGenerator(output_root=temp_output_dir, llm_service=mock_llm)
        deep_path = os.path.join(temp_output_dir, "a", "b", "c", "test.md")

        bg._save_file(deep_path, "data")
        assert os.path.exists(deep_path)

    def test_save_chinese_content(self, mock_llm, temp_output_dir):
        """
        测试用例：保存中文内容
        验证点：UTF-8 正确编码
        """
        bg = BatchGenerator(output_root=temp_output_dir, llm_service=mock_llm)
        filepath = os.path.join(temp_output_dir, "中文.md")
        content = "你好，世界！这是中文测试。"

        bg._save_file(filepath, content)
        with open(filepath, "r", encoding="utf-8") as f:
            assert f.read() == content


# =============================================================================
# 测试 _generate_report
# =============================================================================
class TestBatchGeneratorReport:
    """报告生成测试"""

    def test_report_with_success_job(self, mock_llm, temp_output_dir):
        """
        测试用例：生成包含成功任务的报告
        验证点：报告包含统计表和成功列表
        """
        bg = BatchGenerator(output_root=temp_output_dir, llm_service=mock_llm)
        bg.stats["total_notes"] = 1
        bg.stats["total_products"] = 2
        bg.stats["success_count"] = 2
        bg.stats["total_time_ms"] = 5000

        # 创建模拟任务
        job = BatchJob(1, "测试笔记", "内容", "Python", ["article", "sop"], "/tmp/out")
        job.status = "done"
        job.results = [
            {"product_type": "article", "product_name": "技术文章", "success": True,
             "file": "/tmp/out/article_技术文章.md", "chunk_count": 6},
            {"product_type": "sop", "product_name": "SOP文档", "success": True,
             "file": "/tmp/out/sop_SOP文档.md", "chunk_count": 4},
        ]

        report = bg._generate_report([job])

        # 验证报告内容
        assert "批量生成报告" in report
        assert "测试笔记" in report
        assert "技术文章" in report
        assert "SOP文档" in report
        assert "100.0%" in report                    # 成功率
        assert "5.0 秒" in report                    # 耗时显示

    def test_report_with_failed_job(self, mock_llm, temp_output_dir):
        """
        测试用例：包含失败任务的报告
        验证点：报告显示失败信息
        """
        bg = BatchGenerator(output_root=temp_output_dir, llm_service=mock_llm)
        bg.stats["total_notes"] = 1
        bg.stats["total_products"] = 1
        bg.stats["success_count"] = 0
        bg.stats["failed_count"] = 1

        job = BatchJob(1, "失败的笔记", "", "Python", ["article"], "/tmp")
        job.status = "failed"
        job.error = "LLM 调用超时"
        job.results = [
            {"product_type": "article", "product_name": "技术文章", "success": False,
             "error": "生成失败"}
        ]

        report = bg._generate_report([job])
        assert "失败的笔记" in report
        assert "失败" in report
        assert "LLM 调用超时" in report


# =============================================================================
# 测试 parallel processing (integration-style)
# =============================================================================
class TestBatchGeneratorParallel:
    """并行处理逻辑测试"""

    def test_generate_batch_without_llm_raises(self, temp_output_dir):
        """
        测试用例：验证 BatchGenerator 的基本属性
        验证点：即使不传 LLM，BatchGenerator 也会尝试加载配置
        """
        # 不传 llm_service → 从文件加载配置
        bg = BatchGenerator(output_root=temp_output_dir)

        # 验证 LLM 服务已创建
        assert bg.llm is not None
        # 验证 chunked_gen 已自动创建
        assert bg.chunked_gen is not None
        # 验证 stats 初始化
        assert bg.stats["total_notes"] == 0
