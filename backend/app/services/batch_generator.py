# 🔍 [语法] 模块级 docstring（占位）
# 🔍 [作用] 标记模块用途——批量生成器
"""
把学习过程变成赚钱过程的app/backend/app/services/batch_generator.py 模块

模块用途: TODO 自动扫描生成的占位说明,需要人工补全。
"""
# =============================================================================
# batch_generator.py - 批量并行生成引擎
# =============================================================================
# 接收多个笔记 ID 列表 → 并行处理 → 产出独立文件夹
# =============================================================================

# 🔍 [语法] 标准库
import os
import asyncio
import time
import json
from pathlib import Path

# 🔍 [语法] typing
from typing import List, Dict, Optional, Callable

# 🔍 [语法] SQLAlchemy Session
# 🔍 [作用] 数据库会话（用于查询笔记）
from sqlalchemy.orm import Session

# 🔍 [语法] 相对导入 ORM
# 🔍 [作用] 数据库模型
from ..models import Note, Subject, Product

# 🔍 [语法] 相对导入 LLM
# 🔍 [作用] LLM 服务
from .llm_service import LLMService

# 🔍 [语法] 相对导入配置
# 🔍 [作用] LLM 配置加载
from .llm_config import LLMConfig, load_config

# 🔍 [语法] 相对导入其他服务
# 🔍 [作用] 分块生成器 + 智能推荐
from .chunked_generator import ChunkedGenerator
from .product_generator import product_generator, PRODUCT_TYPES


# =============================================================================
# BatchJob - 单条批量任务
# =============================================================================
class BatchJob:
    """单条笔记的批量生成任务"""

    # 🔍 [语法] __init__
    # 🔍 [作用] 封装单笔记的处理信息
    def __init__(
        self,
        note_id: int,
        note_title: str,
        note_content: str,
        subject_name: str,
        product_types: List[str],
        output_dir: str,
    ):
        self.note_id = note_id
        self.note_title = note_title
        self.note_content = note_content
        self.subject_name = subject_name
        self.product_types = product_types
        self.output_dir = output_dir
        self.results: List[Dict] = []  # 每个产品的生成结果
        # 🔍 [语法] 状态字段
        # 🔍 [作用] pending/running/done/failed
        self.status = "pending"
        self.error = None


# =============================================================================
# BatchGenerator - 批量生成器主类
# =============================================================================
class BatchGenerator:
    """批量并行生成器（多篇笔记并行 + 每篇内部分块生成）"""

    # 🔍 [语法] __init__
    # 🔍 [作用] 初始化（output_root + LLM 服务）
    def __init__(self, output_root: str = "output", llm_service: LLMService = None, user_id: str | None = None):
        project_root = Path(__file__).resolve().parents[3]
        raw_root = Path(output_root)
        root = raw_root if raw_root.is_absolute() else project_root / raw_root
        resolved = root.resolve()
        self.output_root = str(resolved)
        self.llm = llm_service or LLMService()
        self.user_id = user_id
        self.chunked_gen = ChunkedGenerator(llm_service=self.llm)
        self.stats = {
            "total_notes": 0,
            "total_products": 0,
            "success_count": 0,
            "failed_count": 0,
            "total_time_ms": 0,
        }

    # 🔍 [语法] async def
    # 🔍 [作用] 批量生成主入口
    async def generate_batch(
        self,
        note_ids: List[int],
        db_session: Session,
        product_types: Optional[List[str]] = None,
    ) -> Dict:
        """
        批量并行生成多篇笔记的产品：
            1. 从数据库读取所有 note
            2. 为每篇笔记创建 BatchJob
            3. asyncio.gather 并行执行
            4. 生成汇总报告
        """
        # 🔍 [语法] 计时
        start = time.time()

        # ---- 步骤 1: 读取所有 note ----
        # 🔍 [语法] SQLAlchemy IN 查询
        # 🔍 [作用] 一次查所有 note
        notes_query = db_session.query(Note).filter(Note.id.in_(note_ids))
        if self.user_id and hasattr(Note, "user_id"):
            notes_query = notes_query.filter(Note.user_id == self.user_id)
        notes = notes_query.all()

        # 🔍 [语法] 早返回
        if not notes:
            return {"success": False, "error": "未找到任何笔记", "total_time_ms": 0}

        # 🔍 [语法] 批量读取 subjects
        # 🔍 [作用] 避免 N+1 查询
        subject_ids = list(set(n.subject_id for n in notes))
        subjects = {
            s.id: s
            for s in db_session.query(Subject).filter(Subject.id.in_(subject_ids)).all()
        }

        # ---- 步骤 2: 创建 BatchJob ----
        # 🔍 [语法] 列表推导式
        # 🔍 [作用] 每篇笔记一个任务
        jobs = []
        for note in notes:
            subject = subjects.get(note.subject_id)
            subject_name = subject.name if subject else ""
            # 🔍 [语法] 输出目录命名
            # 🔍 [作用] note_{id}_{标题}
            output_dir = os.path.join(
                self.output_root,
                # 🔍 [语法] 安全文件名（替换非法字符）
                f"note_{note.id}_{self._safe_filename(note.title)}",
            )
            # 🔍 [语法] product_types 默认值
            # 🔍 [作用] None → 自动推荐
            types = product_types
            if not types:
                # 🔍 [语法] suggest_products
                # 🔍 [作用] 启发式推荐（不调 LLM）
                suggestions = product_generator.suggest_products(note.raw_content or "", subject_name)
                types = [s["type"] for s in suggestions]

            jobs.append(BatchJob(
                note_id=note.id,
                note_title=note.title,
                note_content=note.raw_content or "",
                subject_name=subject_name,
                product_types=types,
                output_dir=output_dir,
            ))

        # ---- 步骤 3: 并行执行 ----
        # 🔍 [语法] asyncio.gather
        # 🔍 [作用] 并发运行所有任务
        results = await asyncio.gather(
            *[self._process_job(job) for job in jobs],
            return_exceptions=True  # 🔍 [语法] 收集异常而非中断
        )

        # ---- 步骤 4: 生成汇总报告 ----
        # 🔍 [语法] enumerate
        # 🔍 [作用] 索引 + 结果
        total_products = 0
        success_count = 0
        failed_count = 0
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                failed_count += 1
                jobs[i].status = "failed"
                jobs[i].error = str(r)
            else:
                total_products += r.get("product_count", 0)
                if r.get("success"):
                    success_count += 1
                else:
                    failed_count += 1

        self.stats.update({
            "total_notes": len(notes),
            "total_products": total_products,
            "success_count": success_count,
            "failed_count": failed_count,
            "total_time_ms": int((time.time() - start) * 1000),
        })

        # 🔍 [语法] 生成汇总文件
        # 🔍 [作用] 顶层 batch_report.md
        report_path = os.path.join(self.output_root, "batch_report.md")
        self._write_summary_report(report_path, jobs, results)

        return {
            "success": True,
            "total_notes": len(notes),
            "success_notes": success_count,
            "failed_notes": failed_count,
            "total_products": total_products,
            "results": results,
            "report_path": report_path,
            "total_time_ms": int((time.time() - start) * 1000),
        }

    # 🔍 [语法] async def
    # 🔍 [作用] 处理单个任务
    async def _process_job(self, job: BatchJob) -> Dict:
        """处理单个 BatchJob（创建目录 + 串行生成各产品）"""
        job.status = "running"

        # 🔍 [语法] makedirs + exist_ok
        # 🔍 [作用] 创建输出目录
        try:
            os.makedirs(job.output_dir, exist_ok=True)
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            return {"success": False, "note_id": job.note_id, "error": str(e)}

        # 🔍 [语法] try/except
        # 🔍 [作用] 整体任务异常捕获
        try:
            # 🔍 [语法] 每种产品生成
            for ptype in job.product_types:
                if ptype not in PRODUCT_TYPES:
                    continue
                # 🔍 [语法] 内容抛光
                # 🔍 [作用] 清洗 + 修复
                from .content_polisher import ContentPolisher
                polished, _ = ContentPolisher.polish_product(
                    self._generate_one(job, ptype), ptype, job.note_title
                )
                # 🔍 [语法] 保存到文件
                self._save_product(job.output_dir, ptype, polished, job)

            job.status = "done"
            return {
                "success": True,
                "note_id": job.note_id,
                "product_count": len(job.product_types),
                "output_dir": job.output_dir,
            }
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            return {"success": False, "note_id": job.note_id, "error": str(e)}

    # 🔍 [语法] def
    # 🔍 [作用] 生成单个产品
    def _generate_one(self, job: BatchJob, ptype: str) -> str:
        """调用分块生成器生成单个产品"""
        # 🔍 [语法] asyncio.run
        # 🔍 [作用] 在同步函数中调用 async
        result = asyncio.run(self.chunked_gen.generate_chunked(
            note_title=job.note_title,
            note_content=job.note_content,
            product_type=ptype,
            subject_name=job.subject_name,
        ))
        # 🔍 [语法] .get 链式
        # 🔍 [作用] 失败时回退到笔记内容
        return result.get("content", job.note_content)

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 保存产品到文件
    @staticmethod
    def _save_product(output_dir: str, ptype: str, content: str, job: BatchJob):
        """保存单个产品到 Markdown 文件"""
        # 🔍 [语法] PRODUCT_TYPES.get
        # 🔍 [作用] 获取产品类型信息
        info = PRODUCT_TYPES.get(ptype, {})
        # 🔍 [语法] 构造文件名
        # 🔍 [作用] 简短文件名（如 article.md）
        filename = f"{ptype}_{info.get('name', ptype)}.md"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            # 🔍 [语法] 写文件 + 头注释
            # 🔍 [作用] 包含元数据
            f.write(f"# {info.get('icon', '📦')} {job.note_title} - {info.get('name', ptype)}\n\n")
            f.write(f"> 来源：{job.note_title}\n")
            f.write(f"> 类型：{info.get('name', ptype)}\n\n")
            f.write("---\n\n")
            f.write(content)

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 安全文件名（去除非法字符）
    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Backward-compatible public name for filename sanitization."""
        return BatchGenerator._safe_filename(name)

    @staticmethod
    def _save_file(filepath: str, content: str) -> str:
        """Write UTF-8 text, creating missing parent directories."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(filepath)

    def _generate_report(self, jobs: List[BatchJob]) -> str:
        """Build a human-readable report from the current batch statistics."""
        total = self.stats["total_products"]
        success = self.stats["success_count"]
        rate = (success / total * 100) if total else 0.0
        lines = [
            "# \u6279\u91cf\u751f\u6210\u62a5\u544a",
            "",
            f"- \u603b\u7b14\u8bb0: {self.stats['total_notes']}",
            f"- \u603b\u4ea7\u54c1: {total}",
            f"- \u6210\u529f\u7387: {rate:.1f}%",
            f"- \u8017\u65f6: {self.stats['total_time_ms'] / 1000:.1f} \u79d2",
            "",
        ]
        for job in jobs:
            lines.append(f"## {job.note_title} ({job.status})")
            if job.error:
                lines.append(f"- \u5931\u8d25: {job.error}")
            for result in job.results:
                name = result.get("product_name", result.get("product_type", ""))
                status = "\u6210\u529f" if result.get("success") else "\u5931\u8d25"
                detail = result.get("error") or result.get("file", "")
                lines.append(f"- {name}: {status} {detail}".rstrip())
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _safe_filename(name: str) -> str:
        """将标题转为合法文件名"""
        # 🔍 [语法] 替换非法字符
        # 🔍 [作用] 文件系统安全
        safe = name.replace("/", "_").replace("\\", "_").replace(":", "_")
        safe = safe.replace("*", "_").replace("?", "_").replace('"', "_")
        safe = safe.replace("<", "_").replace(">", "_").replace("|", "_")
        # 🔍 [语法] 长度限制
        return safe[:50]  # 避免太长

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 写汇总报告
    @staticmethod
    def _write_summary_report(report_path: str, jobs: List[BatchJob], results: List):
        """生成 batch_report.md 汇总"""
        # 🔍 [语法] with open
        # 🔍 [作用] 写文件
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# 批量生成汇总报告\n\n")
            f.write(f"共 {len(jobs)} 篇笔记\n\n")
            f.write("| 笔记 ID | 标题 | 状态 | 产品数 |\n")
            f.write("|---------|------|------|--------|\n")
            for i, job in enumerate(jobs):
                product_count = results[i].get("product_count", 0) if not isinstance(results[i], Exception) else 0
                f.write(f"| {job.note_id} | {job.note_title} | {job.status} | {product_count} |\n")
            f.write(f"\n报告生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
