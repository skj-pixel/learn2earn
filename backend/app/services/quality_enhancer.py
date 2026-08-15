# 🔍 [语法] 模块级 docstring（占位）
# 🔍 [作用] 标记模块用途——质量增强引擎
"""
把学习过程变成赚钱过程的app/backend/app/services/quality_enhancer.py 模块

模块用途: TODO 自动扫描生成的占位说明,需要人工补全。
"""
# =============================================================================
# quality_enhancer.py - 知识付费产品质量增强引擎
# =============================================================================
# 已实现 8 大技巧 + 全链路 enhance()
# 设计模式：每个技巧独立类，通过 unified_enhance() 编排
# =============================================================================

import re
import json
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from .llm_service import LLMService


# =============================================================================
# QualityReport - 质量报告数据类
# =============================================================================
@dataclass
class QualityReport:
    """产品质量综合评分报告"""
    overall_score: float = 0.0
    scores: Dict[str, float] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    checks_passed: int = 0
    checks_total: int = 0
    refinement_rounds: int = 0
    hallucination_count: int = 0
    seo_keywords: List[str] = field(default_factory=list)
    processing_time_ms: int = 0

    # 🔍 [语法] def 方法
    # 🔍 [作用] 转字典（JSON 序列化）
    def to_dict(self) -> Dict:
        return {
            "overall_score": self.overall_score,
            "scores": self.scores,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "checks_passed": self.checks_passed,
            "checks_total": self.checks_total,
            "refinement_rounds": self.refinement_rounds,
            "hallucination_count": self.hallucination_count,
            "seo_keywords": self.seo_keywords,
            "processing_time_ms": self.processing_time_ms,
        }


# =============================================================================
# 全量技巧枚举文档
# =============================================================================
# ✅ = 已实现   ⬜ = 已设计未实现
# T1 迭代精炼 ✅
# T2 多维度评分 ✅
# T3 少样本示例 ✅
# T4 反幻觉校验 ✅
# T5 SEO 优化 ✅
# T6 温度调度 ✅
# T7 连贯性验证 ✅
# T8 自动重组 ✅
# T9-T11 已由其他模块实现
QUALITY_TECHNIQUES = {
    "quality_scoring": {
        "name": "多维度质量评分", "description": "完整性/可读性/专业度/变现力",
        "priority": 2, "implemented": True,
    },
    "few_shot": {
        "name": "少样本示例注入", "description": "每次生成附带 1-2 个高质量示例",
        "priority": 3, "implemented": True,
    },
    "hallucination_check": {
        "name": "反幻觉校验", "description": "检查生成事实是否在源笔记中存在",
        "priority": 4, "implemented": True,
    },
    "seo_optimization": {
        "name": "SEO 元信息优化", "description": "关键词提取/描述生成/标题优化",
        "priority": 5, "implemented": True,
    },
    "temperature_scheduling": {
        "name": "温度调度策略", "description": "不同阶段用不同 temperature 参数",
        "priority": 6, "implemented": True,
    },
    "coherence_validation": {
        "name": "连贯性验证", "description": "前后 chunk 风格统一、过渡自然",
        "priority": 7, "implemented": True,
    },
    "auto_restructuring": {
        "name": "自动分段重组", "description": "检测并修复段落顺序/H2 层级",
        "priority": 8, "implemented": True,
    },
    "audience_role_injection": {
        "name": "受众角色注入", "description": "根据受众画像定制语气和深度（未实现）",
        "priority": 9, "implemented": False,
    },
    "competitor_differentiation": {
        "name": "竞品差异化分析", "description": "分析竞品→建议差异化角度（未实现）",
        "priority": 10, "implemented": False,
    },
}


# 🔍 [语法] def + 返回 list
# 🔍 [作用] 列出所有技巧（前端展示）
def list_all_techniques() -> List[Dict]:
    """返回所有质量技巧（已实现 + 未实现）"""
    return [
        {"id": k, **v} for k, v in QUALITY_TECHNIQUES.items()
    ]


# =============================================================================
# T1 迭代精炼
# =============================================================================
class IterativeRefiner:
    """生成→自评→改，最多 3 轮"""

    # 🔍 [语法] __init__
    # 🔍 [作用] 接收 LLM 服务
    def __init__(self, llm_service: LLMService = None, max_rounds: int = 3):
        self.llm = llm_service
        self.max_rounds = max_rounds

    # 🔍 [语法] async def
    # 🔍 [作用] 迭代精炼
    async def refine(self, content: str, product_type: str, max_rounds: int = None) -> Tuple[str, int]:
        """返回 (精炼后内容, 实际轮数)"""
        # 🔍 [语法] 早返回
        if not self.llm or not self.llm.is_ready():
            return content, 0

        # 🔍 [语法] for 循环 + break
        # 🔍 [作用] 最多 3 轮，直到无问题
        rounds_limit = self.max_rounds if max_rounds is None else max_rounds
        for i in range(rounds_limit):
            issues = await self._self_critique(content, product_type)
            if not issues:
                break
            content = await self._improve(content, issues, product_type)
        return content, i + 1

    # 🔍 [语法] async def
    # 🔍 [作用] 自批评（LLM 评审）
    async def _self_critique(self, content: str, product_type: str) -> List[str]:
        """LLM 评审内容并列出问题"""
        prompt = f"作为资深编辑，请评审以下{product_type}内容的问题（如逻辑不通/术语错误/缺少示例等）。只输出问题列表，每行一个，没有问题就输出 'OK'：\n\n{content[:3000]}"
        try:
            response = await self.llm.chat(prompt, max_tokens=512, temperature=0.3)
            if "OK" in response.upper():
                return []
            return [line.strip("- •").strip() for line in response.split("\n") if line.strip()]
        except Exception:
            return []

    # 🔍 [语法] async def
    # 🔍 [作用] 改进内容
    async def _improve(self, content: str, issues: List[str], product_type: str) -> str:
        """根据问题改进内容"""
        prompt = f"请根据以下问题改进这段{product_type}内容：\n问题：\n{chr(10).join(issues)}\n\n原文：\n{content[:3000]}"
        try:
            return await self.llm.chat(prompt, max_tokens=2048)
        except Exception:
            return content


# =============================================================================
# T2 多维评分
# =============================================================================
class QualityScorer:
    """Five-dimensional deterministic quality scorer."""

    # 🔍 [语法] async def + QualityReport 返回
    # 🔍 [作用] 评分主入口
    async def score(
        self, content: str, product_type: str,
        note_title: str = "", subject_name: str = "", note_content: str = "",
    ) -> QualityReport:
        """返回质量报告"""
        report = QualityReport()

        structure = min(100, 30 + content.count("\n## ") * 12 + content.count("\n### ") * 5)
        report.scores = {
            "content_completeness": self._score_completeness(content),
            "readability": self._score_readability(content),
            "professionalism": self._score_professionalism(content, note_title, subject_name),
            "monetization_value": self._score_monetization(content),
            "structure_quality": structure,
        }
        # 🔍 [语法] sum + len
        # 🔍 [作用] 计算平均分
        report.overall_score = sum(report.scores.values()) / max(1, len(report.scores))
        report.checks_total = 5
        report.checks_passed = sum(1 for s in report.scores.values() if s >= 50)

        # ---- 生成建议 ----
        report.suggestions = self._generate_suggestions(report)
        report.issues = [f"{dim}不足" for dim, score in report.scores.items() if score < 50]

        return report

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 完整性评分
    @staticmethod
    def _score_completeness(content: str) -> float:
        # 🔍 [语法] 长度评估
        score = min(100, 35 + len(content) / 12)
        return score

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 可读性评分
    @staticmethod
    def _score_readability(content: str) -> float:
        # 🔍 [语法] 段落数
        paragraphs = content.count("\n\n") + 1
        return min(100, 45 + paragraphs * 5)

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 专业度评分（关键词命中）
    @staticmethod
    def _score_professionalism(content: str, title: str, subject: str) -> float:
        keywords = [title, subject] if subject else [title]
        hits = sum(1 for k in keywords if k in content)
        return min(100, 45 + hits * 25 + (15 if "```" in content else 0))

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 变现力评分
    @staticmethod
    def _score_monetization(content: str) -> float:
        # 🔍 [语法] 关键词命中
        # 🔍 [作用] 检测变现相关词
        money_words = ["价格", "购买", "订阅", "免费", "折扣", "限时", "优惠", "价值"]
        hits = sum(1 for w in money_words if w in content)
        return min(100, 25 + hits * 18)

    @staticmethod
    def _generate_suggestions(report: QualityReport) -> List[str]:
        labels = {
            "content_completeness": "补充案例、边界和结论",
            "readability": "缩短段落并增加小标题",
            "professionalism": "补充术语定义、代码或数据证据",
            "monetization_value": "补充目标用户、价格和交付方式",
            "structure_quality": "修正标题层级和章节顺序",
        }
        return [labels.get(dim, f"改进 {dim}") for dim, score in report.scores.items() if score < 60]


# =============================================================================
# T3 少样本示例
# =============================================================================
class FewShotProvider:
    """为每种产品提供高质量示例"""

    # 🔍 [语法] 模块级 dict（简化）
    # 🔍 [作用] 各产品类型的 Few-shot 示例
    EXAMPLES = {
        "article": "示例结构参考：\n标题《Python装饰器10分钟精通》\n引言→核心概念→案例→总结",
        "sop": "示例结构参考：\n标题《Git协作标准操作流程》\n输入→操作步骤→检查点→交付",
        # 其他类型省略
    }

    # 🔍 [语法] def
    # 🔍 [作用] 获取示例
    @classmethod
    def get_example(cls, product_type: str) -> str:
        return cls.EXAMPLES.get(product_type, "")

    # 🔍 [语法] def
    # 🔍 [作用] 构造带示例的 prompt
    @classmethod
    def build_prompt_with_example(cls, base_prompt: str, product_type: str) -> str:
        example = cls.get_example(product_type)
        if not example:
            return base_prompt
        return f"{base_prompt}\n\n## 参考示例\n{example}\n\n请按此风格生成："


# =============================================================================
# T4 反幻觉校验（纯规则）
# =============================================================================
class HallucinationChecker:
    """检查生成内容是否存在幻觉（无需 LLM）"""

    # 🔍 [语法] def
    # 🔍 [作用] 校验内容是否在源笔记中存在
    def check(self, content: str, source_note: str) -> Dict:
        terms = self._extract_terms(content)
        if not terms:
            return {"match_rate": 100.0, "hallucination_count": 0, "missing": [], "score": 100.0}
        source_terms = set(self._extract_terms(source_note))
        matched = [term for term in terms if term in source_terms or term.lower() in source_note.lower()]
        missing = [term for term in terms if term not in matched]
        match_rate = round(len(matched) / len(terms) * 100, 1)
        return {
            "match_rate": match_rate,
            "hallucination_count": len(missing),
            "missing": missing[:10],
            "score": match_rate,
            "count": len(missing),
        }

    @staticmethod
    def _extract_terms(content: str) -> List[str]:
        without_code = re.sub(r'```.*?```', ' ', content or '', flags=re.DOTALL)
        terms = re.findall(r'[A-Za-z][A-Za-z0-9_+#.-]*|[\u4e00-\u9fff]{2,}', without_code)
        seen = set()
        return [term for term in terms if not (term.lower() in seen or seen.add(term.lower()))]

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 提取事实声明
    @staticmethod
    def _extract_claims(content: str) -> List[str]:
        # 🔍 [语法] 简单按句号分割
        # 🔍 [陷阱] 不处理英文缩写、感叹号等
        sentences = re.split(r'[。！？\n]+', content)
        return [s.strip() for s in sentences if len(s.strip()) > 10][:20]


# =============================================================================
# T5 SEO 优化
# =============================================================================
class SEOOptimizer:
    """关键词提取 + 描述生成 + 标题优化"""

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 提取 SEO 关键词（基于词频）
    @staticmethod
    def extract_keywords(content: str, top_k: int = 5) -> List[str]:
        """返回 top_k 关键词"""
        # 🔍 [语法] 正则提取中文/英文词
        words = re.findall(r'[a-zA-Z一-龥]{2,}', content)
        # 🔍 [语法] Counter + most_common
        from collections import Counter
        counter = Counter(words)
        return [w for w, _ in counter.most_common(top_k)]

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 优化标题（加关键词）
    @staticmethod
    def optimize_title(title: str, keywords: List[str]) -> str:
        """返回优化后的标题"""
        # 🔍 [语法] 前缀式关键词插入
        for kw in keywords[:2]:
            if kw not in title:
                return f"{kw}：{title}"
        return title

    _optimize_title = optimize_title

    @staticmethod
    def _generate_description(content: str, title: str) -> str:
        plain = re.sub(r'[#>`*|\[\]]', ' ', content)
        plain = re.sub(r'\s+', ' ', plain).strip()
        description = f"{title}：{plain}" if title else plain
        return description[:150] + ("..." if len(description) > 150 else "")

    @staticmethod
    def _check_heading_structure(content: str) -> List[str]:
        issues = []
        previous = 0
        for match in re.finditer(r'^(#{1,6})\s+', content, re.MULTILINE):
            level = len(match.group(1))
            if previous and level > previous + 1:
                issues.append(f"标题从 H{previous} 越级到 H{level}")
            previous = level
        return issues

    def optimize(self, content: str, title: str, subject: str = "") -> Dict:
        keywords = self.extract_keywords(f"{title}\n{subject}\n{content}", top_k=8)
        return {
            "keywords": keywords,
            "description": self._generate_description(content, title),
            "title": self._optimize_title(title, keywords),
            "heading_issues": self._check_heading_structure(content),
        }


# =============================================================================
# T6 温度调度
# =============================================================================
class TemperatureScheduler:
    """不同阶段用不同 temperature"""

    # 🔍 [语法] 类常量
    # 🔍 [作用] 各阶段温度
    TEMPERATURES = {
        "outline": 0.7,    # 规划：较高温度增加多样性
        "detail": 0.5,    # 细节：中等温度
        "polish": 0.3,    # 抛光：低温度保证准确
    }
    DEFAULT_TEMP = 0.6
    CHUNK_TEMPERATURES = {
        "intro": 0.8, "meta": 0.8, "summary": 0.65,
        "core_concept": 0.4, "pitfalls": 0.3,
    }

    # 🔍 [语法] @classmethod
    # 🔍 [作用] 获取阶段温度
    @classmethod
    def get(cls, stage: str) -> float:
        return cls.TEMPERATURES.get(stage, cls.DEFAULT_TEMP)

    @classmethod
    def get_temperature(cls, chunk_id: str) -> float:
        return cls.CHUNK_TEMPERATURES.get(chunk_id, cls.DEFAULT_TEMP)


# =============================================================================
# T7 连贯性验证
# =============================================================================
class CoherenceValidator:
    """验证前后 chunk/batch 间风格统一"""

    # 🔍 [语法] async def
    # 🔍 [作用] 验证连贯性
    def validate(self, content) -> Dict:
        chunks = content if isinstance(content, list) else [
            {"content": part} for part in str(content).split("\n\n") if part.strip()
        ]
        combined = "\n".join(str(chunk.get("content", "")) for chunk in chunks)
        issues = []
        if "你" in combined and "您" in combined:
            issues.append("人称混用：同时出现‘你’和‘您’")
        lengths = [len(str(chunk.get("content", ""))) for chunk in chunks] or [0]
        avg = sum(lengths) / len(lengths)
        imbalance = max(lengths) - min(lengths) if len(lengths) > 1 else 0
        score = max(0, 100 - len(issues) * 25 - (15 if avg and imbalance > avg * 2 else 0))
        return {"score": score, "issues": issues}


# =============================================================================
# T8 自动分段重组
# =============================================================================
class AutoRestructurer:
    """检测并修复段落顺序/层级问题"""

    # 🔍 [语法] def
    # 🔍 [作用] 重组内容
    def restructure(self, content: str) -> Tuple[str, List[str]]:
        fixes = []
        lines = content.splitlines()
        seen_h2 = False
        for index, line in enumerate(lines):
            if line.startswith("## "):
                seen_h2 = True
            elif line.startswith("### ") and not seen_h2:
                lines[index] = line[1:]
                seen_h2 = True
                fixes.append("将越级 H3 提升为 H2")
        normalized = "\n".join(lines)
        paragraphs = normalized.split("\n\n")
        rebuilt = []
        for paragraph in paragraphs:
            if len(paragraph) > 500 and not paragraph.lstrip().startswith("#"):
                rebuilt.append("\n\n".join(paragraph[i:i + 300] for i in range(0, len(paragraph), 300)))
                fixes.append("拆分超过 500 字的长段落")
            else:
                rebuilt.append(paragraph)
        return "\n\n".join(rebuilt), fixes


# =============================================================================
# QualityEnhancer - 主编排器
# =============================================================================
class QualityEnhancer:
    """全链路质量增强编排（按顺序执行 T1-T8）"""

    # 🔍 [语法] __init__
    # 🔍 [作用] 实例化所有 8 大技巧
    def __init__(self, llm_service: LLMService = None):
        self.refiner = IterativeRefiner(llm_service)
        self.scorer = QualityScorer()
        self.few_shot = FewShotProvider()
        self.hallucination = HallucinationChecker()
        self.seo = SEOOptimizer()
        self.temp_scheduler = TemperatureScheduler()
        self.coherence = CoherenceValidator()
        self.restructurer = AutoRestructurer()

    # 🔍 [语法] async def
    # 🔍 [作用] 全链路增强主入口
    async def enhance(
        self, content: str, product_type: str,
        note_title: str = "", subject_name: str = "", note_content: str = "",
    ) -> Tuple[str, QualityReport, Dict]:
        """执行全链路质量增强（按 T1 → T2 → T4 → T5 → T7 → T8）"""
        report = QualityReport()
        enhancements = {}
        start = time.time()

        # ---- T1 迭代精炼 ----
        content, rounds = await self.refiner.refine(content, product_type)
        report.refinement_rounds = rounds
        enhancements["T1_iterative"] = rounds

        # ---- T2 多维评分 ----
        report = await self.scorer.score(content, product_type, note_title, subject_name, note_content)

        # ---- T4 反幻觉 ----
        h_result = self.hallucination.check(content, note_content)
        report.hallucination_count = h_result["count"]
        enhancements["T4_hallucination"] = h_result

        # ---- T5 SEO ----
        report.seo_keywords = self.seo.extract_keywords(content)

        # ---- T7 连贯性 ----
        coherence_result = self.coherence.validate(content)
        coherence_score = coherence_result["score"]
        enhancements["T7_coherence"] = coherence_result

        # ---- T8 自动重组 ----
        content, structure_fixes = self.restructurer.restructure(content)
        enhancements["T8_restructured"] = structure_fixes

        # ---- 综合评分 ----
        report.overall_score = (
            report.overall_score * 0.6
            + (100 - h_result["count"] * 10) * 0.2
            + coherence_score * 0.2
        )
        report.processing_time_ms = int((time.time() - start) * 1000)

        return content, report, enhancements
