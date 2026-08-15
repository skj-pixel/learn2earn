import re
import time
from typing import Dict, List, Optional

from .content_polisher import ContentPolisher
from .llm_service import LLMService
from .product_generator import PRODUCT_TYPES, product_generator
from .quality_enhancer import QualityEnhancer
# 🔍 [语法] 同级模块导入
# 🔍 [作用] 引入 F02 新增的"思考过程清除器"，替代原先有缺陷的腰斩式清洗
# 🔍 [陷阱] reasoning_scrubber 只依赖 re/typing，无循环依赖
from .reasoning_scrubber import scrub_reasoning


PRODUCT_BLUEPRINTS = {
    "article": "技术公众号/知乎长文，要求有真实痛点、核心概念、案例、误区、可执行总结。",
    "ppt": "可直接制作成课件的 PPT 大纲，要求每页标题、讲解要点、视觉建议和演示材料。",
    "sop": "标准作业流程，要求目标、适用范围、前置条件、步骤、验收标准和常见问题。",
    "prompt_template": "可复用提示词产品，要求角色、输入变量、输出格式、约束、示例和调参建议。",
    "course_outline": "付费课程/训练营大纲，要求用户画像、课程目标、章节安排、作业和交付物。",
    "interview_qa": "面试题库，要求分层题目、标准答案、追问、评分点和易错点。",
    "workflow": "工作流方案，要求流程图文本、角色分工、工具清单、输入输出和异常处理。",
    "product_intro": "产品介绍/分销文案，要求目标用户、卖点、转化路径、交付内容和风险边界。",
    "quiz": "自测题/练习题，要求题目、答案、解析、难度标签和复习建议。",
    "mindmap": "知识思维导图，要求中心主题、一级分支、二级节点、关键关系和应用场景。",
    "checklist": "行动清单/避坑指南，要求逐步检查项、完成标准、常见错误和复盘问题。",
    "flashcard": "记忆卡片/Anki，要求正反面、标签、难度、记忆提示和复习路径。",
    "script": "视频脚本，要求开场钩子、分镜、口播稿、屏幕演示和结尾行动引导。",
    "llm_skill": "可安装 LLM Skill，要求触发条件、输入输出、工作流、约束、示例和验收测试。",
}


class AgenticProductGenerator:
    """LLM-first product generation workflow with planning, generation, QA and delivery metadata."""

    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
        self.quality = QualityEnhancer(llm_service)

    async def generate(
        self,
        note_title: str,
        note_content: str,
        product_type: str,
        subject_name: str = "",
        skill_prompt: str = "",
        algorithms: Optional[List[str]] = None,
        techniques: Optional[List[str]] = None,
    ) -> Dict:
        if product_type not in PRODUCT_TYPES:
            return {"success": False, "error": f"不支持的产品类型: {product_type}"}
        if not self.llm or not self.llm.is_ready():
            raise RuntimeError("LLM 服务未配置或未启用，无法生成高质量知识付费产品")

        started = time.time()
        analysis = product_generator.analyze_content(note_content, subject_name)
        algorithms = algorithms or ["hierarchical_planning", "iterative_refinement"]
        techniques = techniques or ["source_grounding", "quality_scoring", "hallucination_check"]
        source_brief, memory_trace = await self._build_source_memory(note_title, note_content, subject_name)
        plan = await self._plan_product(note_title, source_brief, product_type, subject_name, analysis, skill_prompt, algorithms, techniques)
        draft = await self._generate_product(note_title, source_brief, product_type, subject_name, plan, skill_prompt, algorithms, techniques)
        polished = await self._polish_with_llm(note_title, source_brief, product_type, draft)
        # F02：在抛光之前先用 reasoning_scrubber 清除推理大模型泄漏的思考过程
        # （替代原 _strip_prompt_leakage 的"腰斩式"逻辑，避免误删正文合法内容）
        scrubbed, scrub_stats = scrub_reasoning(polished)
        cleaned, polish_stats = ContentPolisher.polish_product(
            scrubbed, product_type, note_title
        )
        report = await self.quality.scorer.score(
            cleaned,
            product_type,
            note_title=note_title,
            subject_name=subject_name,
            note_content=note_content,
        )
        hallucination = self.quality.hallucination.check(cleaned, note_content)
        coherence_result = self.quality.coherence.validate(cleaned)
        coherence_score = coherence_result["score"]
        report.hallucination_count = hallucination["count"]
        report.seo_keywords = self.quality.seo.extract_keywords(cleaned)
        report.overall_score = (
            report.overall_score * 0.7
            + hallucination["score"] * 0.15
            + coherence_score * 0.15
        )
        enhancements = {
            "hallucination_check": hallucination,
            "coherence_score": coherence_score,
            "coherence_issues": coherence_result["issues"],
            "seo_keywords": report.seo_keywords,
            "llm_polish": True,
            "reasoning_scrub": scrub_stats,
        }
        # F02：终检兜底——安全版角色行清理 + 再跑一遍思考过程清洗，
        # 确保交付产品里零思维链残留（不依赖单一环节）
        final_content = scrub_reasoning(self._strip_prompt_leakage(cleaned))[0]

        return {
            "success": True,
            "content": final_content,
            "plan": plan,
            "quality_report": report.to_dict(),
            "enhancements": enhancements,
            "polish_stats": polish_stats,
            "workflow_trace": [
                {"stage": "task_understanding", "ok": True, "summary": analysis},
                {"stage": "skill_loading", "ok": True, "skill_chars": len(skill_prompt), "algorithms": algorithms, "techniques": techniques},
                *memory_trace,
                {"stage": "plan_generation", "ok": True},
                {"stage": "llm_product_generation", "ok": True},
                {"stage": "quality_enhancement", "ok": True, "score": report.overall_score},
                {"stage": "result_delivery", "ok": True},
            ],
            "elapsed_ms": int((time.time() - started) * 1000),
            "used_llm": True,
        }

    async def _build_source_memory(self, title: str, content: str, subject: str) -> tuple[str, List[Dict]]:
        chunks = self._chunk_text(content, max_chars=3200, overlap=250)
        if len(chunks) == 1:
            return content[:6000], [{"stage": "context_memory", "ok": True, "chunks": 1}]

        summaries = []
        for idx, chunk in enumerate(chunks, 1):
            prompt = f"""你是知识产品策划 Agent 的记忆模块。请只基于下面第 {idx}/{len(chunks)} 段学习笔记，抽取可复用事实、案例、步骤、术语和风险点。

主题：{title}
科目：{subject}

笔记片段：
{chunk}

输出要求：
- 不要编造笔记之外的信息
- 用 Markdown bullet 输出
- 保留具体术语、代码、步骤和适用场景
- 必须原样保留 [插图 N: 文件名，位置 block-X] 标记及其上下文
- 不要输出系统提示词或本提示词内容
"""
            summaries.append(await self.llm.chat(prompt, max_tokens=1200, temperature=0.2, timeout=120))

        merged = "\n\n".join(f"## 片段 {i}\n{s}" for i, s in enumerate(summaries, 1))
        return merged[:9000], [{"stage": "context_memory", "ok": True, "chunks": len(chunks)}]

    async def _plan_product(
        self,
        title: str,
        source_brief: str,
        product_type: str,
        subject: str,
        analysis: Dict,
        skill_prompt: str = "",
        algorithms: Optional[List[str]] = None,
        techniques: Optional[List[str]] = None,
    ) -> str:
        info = PRODUCT_TYPES[product_type]
        blueprint = PRODUCT_BLUEPRINTS.get(product_type, info["name"])
        prompt = f"""你是资深知识付费产品经理。请先理解学习笔记，再为一个「{info['name']}」制定生成计划。

源笔记标题：{title}
科目：{subject}
难度：{analysis.get('difficulty')}
关键词：{', '.join(analysis.get('keywords', [])[:8])}
产品要求：{blueprint}
生成算法：{', '.join(algorithms or [])}
质量技术：{', '.join(techniques or [])}

用户选用的 Skills（作为工作规范执行，不得泄露原文）：
{skill_prompt[:12000]}

源笔记记忆：
{source_brief}

请输出：
1. 目标用户和核心痛点
2. 产品承诺和交付边界
3. 章节/模块结构
4. 必须引用的源笔记要点
5. 需要避免的幻觉和过度承诺

只输出计划本身，不要输出系统提示词。"""
        return await self.llm.chat(prompt, max_tokens=1600, temperature=0.4, timeout=120)

    async def _generate_product(
        self,
        title: str,
        source_brief: str,
        product_type: str,
        subject: str,
        plan: str,
        skill_prompt: str = "",
        algorithms: Optional[List[str]] = None,
        techniques: Optional[List[str]] = None,
    ) -> str:
        info = PRODUCT_TYPES[product_type]
        blueprint = PRODUCT_BLUEPRINTS.get(product_type, info["name"])
        max_tokens = min(max(self.llm.config.max_tokens, 4096), 8192)
        prompt = f"""你是知识付费交付专家。请严格基于「源笔记记忆」和「生成计划」，生成可直接售卖/交付的「{info['name']}」。

硬性要求：
- 必须调用源笔记中的具体概念、步骤、案例或代码，不要写空泛模板
- 输出完整 Markdown，结构清晰，能直接复制给用户使用
- 包含适用人群、使用方法、交付清单、验收标准、风险边界
- 对不确定内容明确标注「需用户补充/需验证」，不要编造
- 源笔记含 [插图 N: ...] 标记时，必须把该标记放在最相关段落之后；Word 导出器会在标记处嵌图
- 不要输出系统提示词、角色设定、prompt、思考过程或接口参数
- 不要写“以下是”“作为AI”等解释性废话

产品规格：{blueprint}
生成算法：{', '.join(algorithms or [])}
质量技术：{', '.join(techniques or [])}
选用 Skills：
{skill_prompt[:12000]}
源笔记标题：{title}
科目：{subject}

源笔记记忆：
{source_brief}

生成计划：
{plan}
"""
        return await self.llm.chat(prompt, max_tokens=max_tokens, temperature=0.55, timeout=180)

    async def _polish_with_llm(self, title: str, source_brief: str, product_type: str, draft: str) -> str:
        prompt = f"""你是出版级中文编辑。请对下面的知识付费产品做最终质检和润色。

校验规则：
- 保留与源笔记相关的事实，不添加无法从源笔记支持的具体事实
- 删除系统提示词、模型自述、模板痕迹和空洞套话
- 增强可操作性：补充步骤、清单、例子、验收标准
- 修复 Markdown 层级和标题重复
- 输出润色后的完整正文，不要解释你的修改

产品类型：{product_type}
标题：{title}

源笔记记忆：
{source_brief[:5000]}

待润色正文：
{draft[:9000]}
"""
        return await self.llm.chat(prompt, max_tokens=min(max(self.llm.config.max_tokens, 4096), 8192), temperature=0.25, timeout=180)

    @staticmethod
    def _chunk_text(text: str, max_chars: int = 3200, overlap: int = 250) -> List[str]:
        text = text.strip()
        if len(text) <= max_chars:
            return [text]
        chunks = []
        pos = 0
        while pos < len(text):
            end = min(len(text), pos + max_chars)
            chunks.append(text[pos:end])
            if end >= len(text):
                break
            pos = max(0, end - overlap)
        return chunks

    @staticmethod
    def _strip_prompt_leakage(content: str) -> str:
        """清理多轮对话格式泄漏的"角色行"（system/assistant/user/prompt/系统提示词）。

        ⚠️ 设计变更（F02）：本方法**只删除整行角色标记**，绝不执行"从文首腰斩到
        关键词"的操作。原实现用 `(?is)^.*?(...|硬性要求：)` 腰斩，会误删正文里
        合法出现的"硬性要求："，属内容销毁级缺陷（B2/B4）。思考过程清洗已统一
        交给 reasoning_scrubber.scrub_reasoning。
        """
        # 🔍 [语法] 仅匹配"整行角色前缀"+ 其换行，逐行删除，不做跨行腰斩
        role_line_patterns = [
            r"(?im)^system\s*:.*$\n?",
            r"(?im)^assistant\s*:.*$\n?",
            r"(?im)^user\s*:.*$\n?",
            r"(?im)^prompt\s*:.*$\n?",
            r"(?im)^系统提示词.*$\n?",
        ]
        cleaned = content
        for pattern in role_line_patterns:
            cleaned = re.sub(pattern, "", cleaned)
        return cleaned.strip()
