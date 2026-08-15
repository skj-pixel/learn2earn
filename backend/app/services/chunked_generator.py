# 🔍 [语法] 模块级 docstring（占位）
# 🔍 [作用] 标记模块用途——分块生成器
"""
把学习过程变成赚钱过程的app/backend/app/services/chunked_generator.py 模块

模块用途: TODO 自动扫描生成的占位说明,需要人工补全。
"""
# =============================================================================
# chunked_generator.py - 分块式高质量产品生成引擎
# =============================================================================
# 将每个产品拆分成多个 chunk，每块独立 LLM 调用，最后组装
# 设计理念：单次大 prompt 质量不可控，分块小 prompt 质量可控
# =============================================================================

# 🔍 [语法] import asyncio
# 🔍 [作用] 异步 I/O（用于并行调用多个 chunk）
import asyncio

# 🔍 [语法] import time
# 🔍 [作用] 计时统计
import time

# 🔍 [语法] typing 导入
from typing import List, Dict, Optional

# 🔍 [语法] 相对导入
# 🔍 [作用] LLM API 调用服务
from .llm_service import LLMService
from .product_generator import PRODUCT_TYPES


# =============================================================================
# CHUNK_DEFINITIONS - 每种产品类型的分块定义
# =============================================================================
# 每个产品类型拆分为多个 chunk：
#   id               - 唯一标识
#   title            - 展示名称
#   prompt_template  - 针对该块的精准提示词模板
#   order            - 组装时的排序序号
#   heading_level    - Markdown 标题级别
# 占位符：{note_title} / {note_content} / {subject_name} / {difficulty} / {keywords} / {prev_chunks}
CHUNK_DEFINITIONS = {

    # =========================================================================
    # article - 技术文章（6 个块）
    # =========================================================================
    "article": [
        {
            "id": "meta", "title": "标题优化与元信息", "order": 1, "heading_level": "##",
            "prompt_template": """你是一位资深技术编辑。请根据以下笔记内容，生成一篇技术文章的「标题优化版」和「元信息区」。

笔记主题：{note_title}
所属科目：{subject_name}
难度等级：{difficulty}
关键词：{keywords}

要求：
1. 优化标题，使其更具吸引力（保留原意，增加搜索友好度）
2. 写一行副标题（15字以内）
3. 标注适用人群和阅读时间
4. 列出5个核心标签

输出格式：
# [优化后的标题]
> 📌 适用人群：xxx | ⏱️ 阅读时间：约x分钟 | 🏷️ 标签：xxx, xxx""",
        },
        {
            "id": "intro", "title": "引言与背景", "order": 2, "heading_level": "##",
            "prompt_template": """你是一位技术博主。请为以下笔记内容撰写一个引人入胜的引言段落。

笔记主题：{note_title}
所属科目：{subject_name}
难度等级：{difficulty}

要求：
1. 用一个真实场景或痛点引入（150-200字）
2. 说明读者看完本文能获得什么
3. 简介本文的内容结构（2-3句话）

直接用 ## 引言 开头，输出纯 Markdown。""",
        },
        {
            "id": "core_concept", "title": "核心概念详解", "order": 3, "heading_level": "##",
            "prompt_template": """你是一位资深{subject_name}专家。请根据笔记内容，详细阐述核心概念。

笔记主题：{note_title}
已有内容摘要：{prev_chunks}

要求：
1. 用清晰的层级结构（H2/H3）组织
2. 每个概念给出定义、原理、示例
3. 用表格对比易混淆概念
4. 不少于500字

直接输出 Markdown。""",
        },
        {
            "id": "examples", "title": "代码示例", "order": 4, "heading_level": "##",
            "prompt_template": """你是一位资深开发者。请根据笔记内容生成 3-5 个代码示例。

笔记主题：{note_title}
已有内容：{prev_chunks}

要求：
1. 示例由浅入深
2. 每个示例包含完整代码 + 注释 + 运行结果说明
3. 使用 ```python 代码块包裹
4. 指出常见错误

直接输出 Markdown。""",
        },
        {
            "id": "pitfalls", "title": "常见陷阱", "order": 5, "heading_level": "##",
            "prompt_template": """你是一位资深{subject_name}专家。请列出本主题的 5 个常见陷阱。

笔记主题：{note_title}
已有内容：{prev_chunks}

要求：
1. 每个陷阱包括：表现 / 原因 / 解决方案
2. 真实场景（不要泛泛而谈）
3. 用列表组织

直接输出 Markdown。""",
        },
        {
            "id": "summary", "title": "总结与延伸", "order": 6, "heading_level": "##",
            "prompt_template": """你是一位资深作者。请为本文撰写总结段落。

笔记主题：{note_title}
已有内容：{prev_chunks}

要求：
1. 总结 3-5 个核心要点
2. 推荐 3 个延伸阅读方向
3. 引导读者下一步行动

直接输出 Markdown。""",
        },
    ],

    # =========================================================================
    # 其他产品类型（每个 4-6 个块，简化展示）
    # =========================================================================
    "ppt": [
        {"id": "cover", "title": "封面页", "order": 1, "heading_level": "#", "prompt_template": "为{subject_name}的{note_title}设计PPT封面页内容。"},
        {"id": "toc", "title": "目录页", "order": 2, "heading_level": "#", "prompt_template": "基于{prev_chunks}，生成PPT的目录结构。"},
        {"id": "chapters", "title": "章节详解", "order": 3, "heading_level": "##", "prompt_template": "请围绕笔记《{note_title}》的内容，为每个章节写3-5个slide的内容。\n原始内容：{note_content}"},
        {"id": "summary", "title": "总结页", "order": 4, "heading_level": "##", "prompt_template": "为PPT写总结页。"},
    ],

    "sop": [
        {"id": "overview", "title": "概述", "order": 1, "heading_level": "#", "prompt_template": "SOP概述：{note_title}，所属{subject_name}。"},
        {"id": "prerequisites", "title": "前置准备", "order": 2, "heading_level": "##", "prompt_template": "列出SOP的前置条件和工具。"},
        {"id": "steps", "title": "操作步骤", "order": 3, "heading_level": "##", "prompt_template": "详细的分步骤操作指南（5-10步）。"},
        {"id": "qa", "title": "常见问题", "order": 4, "heading_level": "##", "prompt_template": "SOP执行中可能遇到的常见问题和解决方案。"},
    ],

    "prompt_template": [
        {"id": "meta", "title": "模板元信息", "order": 1, "heading_level": "#", "prompt_template": "为{subject_name}的{note_title}生成AI提示词模板的元信息。"},
        {"id": "template", "title": "核心模板", "order": 2, "heading_level": "##", "prompt_template": "生成可复用的AI提示词核心模板。"},
        {"id": "examples", "title": "使用示例", "order": 3, "heading_level": "##", "prompt_template": "给3个使用示例。"},
        {"id": "tips", "title": "使用技巧", "order": 4, "heading_level": "##", "prompt_template": "使用该模板的技巧和注意事项。"},
    ],

    "course_outline": [
        {"id": "objectives", "title": "课程目标", "order": 1, "heading_level": "#", "prompt_template": "为{subject_name}的{note_title}课程设计学习目标。"},
        {"id": "structure", "title": "章节结构", "order": 2, "heading_level": "##", "prompt_template": "设计课程章节结构（5-10章）。"},
        {"id": "schedule", "title": "教学进度", "order": 3, "heading_level": "##", "prompt_template": "制定教学进度（每周计划）。"},
        {"id": "assessment", "title": "考核方式", "order": 4, "heading_level": "##", "prompt_template": "设计考核方式和评分标准。"},
    ],

    "interview_qa": [
        {"id": "basics", "title": "基础题", "order": 1, "heading_level": "#", "prompt_template": "为{subject_name}的{note_title}生成5道基础面试题。"},
        {"id": "advanced", "title": "进阶题", "order": 2, "heading_level": "##", "prompt_template": "生成5道进阶面试题（涉及原理）。"},
        {"id": "scenario", "title": "场景题", "order": 3, "heading_level": "##", "prompt_template": "生成3道场景应用题。"},
        {"id": "answers", "title": "答案解析", "order": 4, "heading_level": "##", "prompt_template": "为前面所有题目写详细答案解析。"},
    ],

    "workflow": [
        {"id": "overview", "title": "流程概述", "order": 1, "heading_level": "#", "prompt_template": "概述{subject_name}的{note_title}工作流程。"},
        {"id": "steps", "title": "步骤详解", "order": 2, "heading_level": "##", "prompt_template": "详细描述每个步骤。"},
        {"id": "tools", "title": "工具清单", "order": 3, "heading_level": "##", "prompt_template": "列出执行流程所需的工具和资源。"},
        {"id": "checklist", "title": "检查清单", "order": 4, "heading_level": "##", "prompt_template": "流程执行完毕的检查清单。"},
    ],

    "quiz": [
        {"id": "single", "title": "单选题", "order": 1, "heading_level": "#", "prompt_template": "为{subject_name}的{note_title}生成10道单选题。"},
        {"id": "multi", "title": "多选题", "order": 2, "heading_level": "##", "prompt_template": "生成5道多选题。"},
        {"id": "judge", "title": "判断题", "order": 3, "heading_level": "##", "prompt_template": "生成5道判断题。"},
        {"id": "answers", "title": "答案解析", "order": 4, "heading_level": "##", "prompt_template": "为所有题目写答案和详细解析。"},
    ],

    "mindmap": [
        {"id": "root", "title": "中心主题", "order": 1, "heading_level": "#", "prompt_template": "为{subject_name}的{note_title}设计思维导图的中心主题。"},
        {"id": "branches", "title": "主要分支", "order": 2, "heading_level": "##", "prompt_template": "设计5-8个主要分支。"},
        {"id": "subpoints", "title": "子节点", "order": 3, "heading_level": "###", "prompt_template": "为每个分支填充2-4个子节点。"},
        {"id": "examples", "title": "实例", "order": 4, "heading_level": "##", "prompt_template": "给出3个实际应用例子。"},
    ],

    "checklist": [
        {"id": "preparation", "title": "准备清单", "order": 1, "heading_level": "#", "prompt_template": "为{subject_name}的{note_title}生成准备阶段清单。"},
        {"id": "execution", "title": "执行清单", "order": 2, "heading_level": "##", "prompt_template": "生成执行阶段的关键检查项。"},
        {"id": "pitfalls", "title": "避坑指南", "order": 3, "heading_level": "##", "prompt_template": "列出常见错误和避坑指南。"},
    ],

    "flashcard": [
        {"id": "concept", "title": "概念卡", "order": 1, "heading_level": "#", "prompt_template": "为{subject_name}的{note_title}生成10张概念卡（正面问题+背面答案）。"},
        {"id": "formula", "title": "公式卡", "order": 2, "heading_level": "##", "prompt_template": "生成5张关键公式卡（含应用场景）。"},
        {"id": "comparison", "title": "对比卡", "order": 3, "heading_level": "##", "prompt_template": "生成5张易混淆概念对比卡。"},
    ],

    "script": [
        {"id": "hook", "title": "开场钩子", "order": 1, "heading_level": "#", "prompt_template": "为{subject_name}的{note_title}写视频开场（前30秒抓住注意力）。"},
        {"id": "structure", "title": "内容结构", "order": 2, "heading_level": "##", "prompt_template": "设计视频主体结构（3-5个段落）。"},
        {"id": "ending", "title": "结尾引导", "order": 3, "heading_level": "##", "prompt_template": "写视频结尾CTA。"},
    ],

    "product_intro": [
        {"id": "hook", "title": "吸引钩子", "order": 1, "heading_level": "#", "prompt_template": "为{subject_name}的{note_title}产品写吸引人的开头。"},
        {"id": "value", "title": "核心价值", "order": 2, "heading_level": "##", "prompt_template": "说明产品的3大核心价值。"},
        {"id": "testimonials", "title": "使用场景", "order": 3, "heading_level": "##", "prompt_template": "列出3个使用场景和适用人群。"},
        {"id": "cta", "title": "购买引导", "order": 4, "heading_level": "##", "prompt_template": "写强有力的CTA（购买引导）。"},
    ],
}


# New product categories receive a complete four-stage default chunk plan.
for _product_type, _info in PRODUCT_TYPES.items():
    CHUNK_DEFINITIONS.setdefault(_product_type, [
        {"id": "positioning", "title": "定位与目标", "order": 1, "heading_level": "#", "prompt_template": f"为{{note_title}}规划一份可售卖的{_info['name']}，明确用户、痛点、承诺和边界。\n源笔记：{{note_content}}"},
        {"id": "delivery", "title": "核心交付", "order": 2, "heading_level": "##", "prompt_template": f"基于源笔记生成{_info['name']}的完整核心内容，要求具体、可执行、有验收标准。\n{{note_content}}"},
        {"id": "examples", "title": "示例与模板", "order": 3, "heading_level": "##", "prompt_template": "补充可直接复用的示例、模板和常见错误。已有内容：{prev_chunks}"},
        {"id": "quality", "title": "质量与交付", "order": 4, "heading_level": "##", "prompt_template": "给出使用说明、检查清单、风险边界和最终交付清单。主题：{note_title}"},
    ])

# =============================================================================
# ChunkedGenerator - 分块生成器主类
# =============================================================================
# Keep every chunk prompt contextualized.  A few legacy definitions were
# authored without placeholders, which made them ignore the supplied note.
for _chunks in CHUNK_DEFINITIONS.values():
    for _chunk in _chunks:
        _prompt = _chunk.get("prompt_template", "")
        if not any(token in _prompt for token in ("{note_title}", "{note_content}", "{subject_name}", "{prev_chunks}")):
            _chunk["prompt_template"] = _prompt + "\n\nNote: {note_title}\n{note_content}"


class ChunkedGenerator:
    """分块式生成器（按 CHUNK_DEFINITIONS 逐块生成）"""

    # 🔍 [语法] __init__
    # 🔍 [作用] 接受 LLM 服务
    def __init__(self, llm_service: LLMService = None):
        self.llm = llm_service
        self._chunk_cache = {}

    @staticmethod
    def _build_chunk_prompt(chunk_def: Dict, context: Dict, prev_summary: str = "") -> str:
        values = dict(context)
        values["prev_chunks"] = prev_summary
        return chunk_def["prompt_template"].format(**values)

    @staticmethod
    def _summarize_chunks(chunks: List[Dict]) -> str:
        return "\n".join(
            f"{chunk.get('title', '')}: {chunk.get('content', '')[:200]}"
            for chunk in sorted(chunks, key=lambda item: item.get("order", 0))
            if chunk.get("content")
        )

    @staticmethod
    def _assemble_document(product_type: str, chunks: List[Dict], note_title: str) -> str:
        body = "\n\n---\n\n".join(
            chunk.get("content", "")
            for chunk in sorted(chunks, key=lambda item: item.get("order", 0))
            if chunk.get("content")
        )
        return f"# {note_title}\n\n{body}\n\n---\n\nGenerated by Learn2Earn"

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 列出支持的产品类型
    @staticmethod
    def list_supported_types() -> List[Dict]:
        return [
            {
                "type": product_type,
                "chunk_count": len(chunks),
                "chunk_names": [chunk["title"] for chunk in sorted(chunks, key=lambda item: item["order"])],
            }
            for product_type, chunks in CHUNK_DEFINITIONS.items()
        ]

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 获取指定类型的分块数量
    @staticmethod
    def get_chunk_count(product_type: str) -> int:
        return len(CHUNK_DEFINITIONS.get(product_type, []))

    # 🔍 [语法] async def + Dict 返回
    # 🔍 [作用] 分块生成主入口
    async def generate_chunked(
        self, note_title: str, note_content: str, product_type: str,
        subject_name: str = "", difficulty: str = "intermediate",
        keywords: List[str] = None,
    ) -> Dict:
        """
        分块生成主入口：
            1. 获取该产品类型的 chunks
            2. 按 order 顺序调用 LLM 生成每块（串行，因为后续块依赖前块上下文）
            3. 拼接所有块
            4. 过 ContentPolisher
        """
        # 🔍 [语法] 早返回
        # 🔍 [作用] 不支持的产品类型
        chunks = CHUNK_DEFINITIONS.get(product_type, [])
        if not chunks:
            return {"success": False, "error": f"不支持的产品类型: {product_type}"}

        # 🔍 [语法] 关键词默认值
        keywords = keywords or []

        # 🔍 [语法] 计时
        start = time.time()

        chunk_results = []
        prev_summary = ""

        # 🔍 [语法] for 循环（按 order 排序）
        # 🔍 [作用] 串行生成每块（顺序很重要）
        for chunk_def in sorted(chunks, key=lambda c: c["order"]):
            # 🔍 [语法] .format(**kwargs)
            # 🔍 [作用] 替换 prompt 中的占位符
            prompt = chunk_def["prompt_template"].format(
                note_title=note_title,
                note_content=note_content,
                subject_name=subject_name,
                difficulty=difficulty,
                keywords=", ".join(keywords),
                prev_chunks=prev_summary,  # 🔍 [语法] 前块摘要作为上下文
            )

            # 🔍 [语法] try/except
            # 🔍 [作用] 单块失败不中断整体
            try:
                content = await self.llm.chat(prompt, max_tokens=2048, timeout=120)
                chunk_results.append({
                    "id": chunk_def["id"],
                    "title": chunk_def["title"],
                    "content": content,
                })
                # 🔍 [语法] prev_summary = content[:200]
                # 🔍 [作用] 下块摘要作上下文（避免太长）
                prev_summary = content[:200]
            except Exception as e:
                chunk_results.append({
                    "id": chunk_def["id"],
                    "error": str(e),
                })

        # 🔍 [语法] 拼接所有块
        # 🔍 [作用] 按 order 排序后拼接
        final_content = "\n\n".join(
            c.get("content", "") for c in sorted(chunk_results, key=lambda x: x.get("order", 0))
        )

        # 🔍 [语法] 内容抛光
        # 🔍 [作用] 清洗 AI 解释 + 修复格式
        from .content_polisher import ContentPolisher
        final_content, polish_stats = ContentPolisher.polish_product(
            final_content, product_type, note_title
        )

        return {
            "success": True,
            "content": final_content,
            "chunks": chunk_results,
            "chunk_count": len(chunk_results),
            "polish_stats": polish_stats,
            "total_time_ms": int((time.time() - start) * 1000),
        }
