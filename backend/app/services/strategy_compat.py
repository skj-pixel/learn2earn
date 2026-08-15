# 🔍 [语法] 模块级 docstring
# 🔍 [作用] skill × 生成算法 × 质量技术的自由组合兼容层
"""
strategy_compat.py - 策略兼容矩阵与校验（F04）

设计原则：本系统的 skill / 生成算法 / 质量技术 三轴是**正交解耦**的
（详见 docs/算法自由组合架构.md）。任意组合都允许，本模块不做硬性阻断，
只做两件事：
    1. 登记三轴已知的策略标识（供前端发现 / 文档对齐）；
    2. 对组合做**只读、咨询式**校验，返回 (errors, warnings)：
       - errors   仅包含结构性错误（如 algorithms 为空 / 类型非法）；
       - warnings 仅作提示（未知策略、未实装策略、需要 LLM 但未配置等），
         绝不阻止生成，从而保障"自由组合"的能力不被破坏。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


# =============================================================================
# 生成算法轴（Generation Algorithms）
# =============================================================================

# 🔍 [语法] dict literal
# 🔍 [作用] 已知生成算法登记；implemented 标记是否已在 AgenticProductGenerator 实装
# 🔍 [陷阱] 仅 hierarchical_planning / iterative_refinement 为当前实装算法；
#          其余为规划中的候选，validate 时按"未实装"给出咨询警告而非报错
GENERATION_ALGORITHMS: Dict[str, Dict] = {
    "hierarchical_planning": {
        "name": "分层规划",
        "description": "先生成章节大纲再逐层展开，结构稳定、适合长文",
        "implemented": True,
        "needs_llm": True,
    },
    "iterative_refinement": {
        "name": "迭代精炼",
        "description": "生成→自评→改进循环，质量更高但更慢",
        "implemented": True,
        "needs_llm": True,
    },
    "chunked_generation": {
        "name": "分块生成",
        "description": "历史任务兼容 ID；当前会作为生成提示透传并回退到标准生成链",
        "implemented": False,
        "needs_llm": True,
    },
    "parallel_drafting": {
        "name": "并行草拟",
        "description": "历史任务兼容 ID；当前会作为生成提示透传并回退到标准生成链",
        "implemented": False,
        "needs_llm": True,
    },
    "single_pass": {
        "name": "单次直出",
        "description": "一次生成全文，速度最快，结构一致性较弱",
        "implemented": False,
        "needs_llm": True,
    },
    "chunked_parallel": {
        "name": "分块并行",
        "description": "按章节分块并行生成后拼接，适合超长内容",
        "implemented": False,
        "needs_llm": True,
    },
    "reflexion": {
        "name": "反思式自修",
        "description": "基于自我反思轨迹修正错误，事实准确性高",
        "implemented": False,
        "needs_llm": True,
    },
}


# =============================================================================
# 质量技术轴（Quality Techniques）
# =============================================================================

# 🔍 [语法] 延迟导入
# 🔍 [作用] 直接复用 quality_enhancer 的权威登记，避免两份真相
try:
    from .quality_enhancer import QUALITY_TECHNIQUES  # type: ignore
except Exception:  # pragma: no cover
    QUALITY_TECHNIQUES: Dict[str, Dict] = {}

# 🔍 [作用] 登记由任务编排层实现的知识增强技术；它们不属于 quality_enhancer，
# 但必须出现在同一兼容性注册表中，避免把已实现的 MemoryBear 误报为未知技术。
COMPOSITION_TECHNIQUES: Dict[str, Dict] = {
    "source_grounding": {
        "name": "源笔记约束", "description": "以当前笔记原文作为生成依据", "implemented": True,
    },
    "memorybear": {
        "name": "MemoryBear 长期记忆", "description": "注入用户长期记忆，可与 RAG 并行或独立使用", "implemented": True,
    },
    "rag_grounding": {
        "name": "RAG 外部检索", "description": "尚未接入真实向量检索后端", "implemented": False,
    },
}

ALGORITHM_CONFLICTS = {
    frozenset(("single_pass", "iterative_refinement")): "单次直出不会进入迭代精炼循环",
    frozenset(("single_pass", "hierarchical_planning")): "单次直出与分层规划的执行模型冲突",
}
# Quality techniques run after generation. They are not compared with algorithms,
# Skills, or generation-time context techniques. Add only quality-vs-quality rules here.
TECHNIQUE_CONFLICTS: dict[frozenset, str] = {}


def compatibility_matrices(skills: list[dict] | None = None) -> dict:
    generation_names = {
        **{f"algorithm:{key}": value.get("name", key) for key, value in GENERATION_ALGORITHMS.items()},
        **{f"skill:{item.get('id')}": item.get("name") or f"Skill #{item.get('id')}" for item in (skills or [])},
    }
    generation_conflicts = {
        frozenset((f"algorithm:{left}", f"algorithm:{right}")): reason
        for pair, reason in ALGORITHM_CONFLICTS.items()
        for left, right in [tuple(pair)]
    }
    technique_names = {key: value.get("name", key) for key, value in QUALITY_TECHNIQUES.items()}
    generation_rows = []
    for pair, reason in generation_conflicts.items():
        left, right = sorted(pair)
        generation_rows.append({
            "left": left, "right": right,
            "left_name": generation_names.get(left, left), "right_name": generation_names.get(right, right),
            "status": "conflict", "reason": reason,
        })
    quality_rows = []
    for pair, reason in TECHNIQUE_CONFLICTS.items():
        left, right = sorted(pair)
        quality_rows.append({
            "left": left, "right": right,
            "left_name": technique_names.get(left, left), "right_name": technique_names.get(right, right),
            "status": "conflict", "reason": reason,
        })
    return {
        "generation": generation_rows,
        "quality": quality_rows,
    }


def pair_conflicts(values: list[str], conflicts: dict[frozenset, str]) -> list[str]:
    selected = list(dict.fromkeys(values))
    found = []
    for index, left in enumerate(selected):
        for right in selected[index + 1:]:
            reason = conflicts.get(frozenset((left, right)))
            if reason:
                found.append(f"{left} + {right}: {reason}")
    return found


# =============================================================================
# skill 轴
# =============================================================================

# 🔍 [语法] 注释
# 🔍 [作用] skill 由用户安装（InstalledSkill 表），无法在静态模块登记；
#          校验时通过 available_skill_ids 动态传入已安装 id 集合。


# =============================================================================
# 校验结果
# =============================================================================

# 🔍 [语法] @dataclass
# 🔍 [作用] 结构化返回 errors（硬错误）/ warnings（咨询警告）
@dataclass
class StrategyCompatResult:
    """策略组合校验结果（只读、咨询式）"""

    # 🔍 [语法] field(default_factory=list)
    # 🔍 [作用] 每个元素为字符串描述
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    # 🔍 [语法] Dict 字段
    # 🔍 [作用] 归一化后的策略（去除重复、过滤未知项不在此丢弃，仅警告）
    normalized: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        # 🔍 [语法] dataclasses asdict 替代
        return {
            "ok": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "normalized": self.normalized,
        }


# =============================================================================
# 核心校验函数
# =============================================================================

# 🔍 [语法] def + StrategyCompatResult 返回
# 🔍 [作用] 对 (skill_ids, algorithms, techniques) 组合做咨询式校验
def validate_combination(
    skill_ids: Optional[List[int]] = None,
    algorithms: Optional[List[str]] = None,
    techniques: Optional[List[str]] = None,
    *,
    available_skill_ids: Optional[Set[int]] = None,
    llm_ready: bool = True,
) -> StrategyCompatResult:
    """
    校验三轴组合是否"结构合法 + 可运行"，返回咨询式结果。

    参数：
        skill_ids          用户选中的 skill id 列表（int）
        algorithms         生成算法标识列表（str）
        techniques         质量技术标识列表（str）
        available_skill_ids 当前用户已安装的 skill id 集合（用于核对存在性）
        llm_ready          当前 LLM 是否已配置就绪

    约定：
        - errors 仅含结构性问题（类型非法 / algorithms 为空），会阻断；
        - warnings 不阻断，仅提示（未知策略 / 未实装 / 缺 LLM 等）。
    """
    result = StrategyCompatResult()

    # 🔍 [语法] 默认值归一
    skill_ids = skill_ids or []
    algorithms = algorithms or []
    techniques = techniques or []

    # 🔍 [语法] 类型校验
    # 🔍 [作用] 结构性错误才进 errors
    if not isinstance(algorithms, list):
        result.errors.append("algorithms 必须是字符串列表")
    if not isinstance(techniques, list):
        result.errors.append("techniques 必须是字符串列表")
    if not isinstance(skill_ids, list):
        result.errors.append("skill_ids 必须是整数列表")

    # 🔍 [语法] 早返回（结构性错误时不再做后续咨询校验）
    if result.errors:
        return result

    # 🔍 [作用] algorithms 至少需有一个，否则无法生成
    if len(algorithms) == 0:
        result.errors.append("至少需要选择一种生成算法")
        return result

    # ------------------------------------------------------------------
    # 生成算法轴：未知 / 未实装 / 需 LLM
    # ------------------------------------------------------------------
    for algo in algorithms:
        meta = GENERATION_ALGORITHMS.get(algo)
        if meta is None:
            # 🔍 [陷阱] 自由组合：未知算法不报错，仅提示（可能来自未来扩展）
            result.warnings.append(f"生成算法 '{algo}' 不在已知登记中，将按原样透传")
            continue
        if not meta.get("implemented"):
            result.warnings.append(f"生成算法 '{algo}' 尚未实装，实际可能回退为默认算法")
        if meta.get("needs_llm") and not llm_ready:
            result.warnings.append(f"生成算法 '{algo}' 需要 LLM，但当前未配置/未启用")

    # ------------------------------------------------------------------
    # 质量技术轴：未知 / 未实装
    # ------------------------------------------------------------------
    all_techniques = {**QUALITY_TECHNIQUES, **COMPOSITION_TECHNIQUES}
    if all_techniques:
        for tech in techniques:
            meta = all_techniques.get(tech)
            if meta is None:
                result.warnings.append(f"质量技术 '{tech}' 不在已知登记中，将被忽略")
                continue
            if not meta.get("implemented"):
                result.warnings.append(f"质量技术 '{tech}' 尚未实装（{meta.get('name', tech)}），暂不生效")
    else:
        # 🔍 [作用] 质量模块不可用时，未知技术仅提示
        for tech in techniques:
            if not tech:
                continue
            result.warnings.append(f"质量技术 '{tech}' 已记录，但质量模块暂不可用")

    # ------------------------------------------------------------------
    # skill 轴：存在性核对（需传入 available_skill_ids）
    # ------------------------------------------------------------------
    if available_skill_ids is not None:
        avail = set(available_skill_ids)
        for sid in skill_ids:
            if sid not in avail:
                result.warnings.append(f"skill id {sid} 不在当前用户已安装列表中，可能被忽略")

    # 🔍 [语法] 去重归一
    result.normalized = {
        "skill_ids": sorted(set(int(s) for s in skill_ids)),
        "algorithms": list(dict.fromkeys(algorithms)),
        "techniques": list(dict.fromkeys(techniques)),
    }
    result.errors.extend(pair_conflicts(result.normalized["algorithms"], ALGORITHM_CONFLICTS))
    result.errors.extend(pair_conflicts(result.normalized["techniques"], TECHNIQUE_CONFLICTS))
    return result


# =============================================================================
# 对外暴露：三轴登记（供 API / 前端发现）
# =============================================================================

# 🔍 [语法] def + Dict 返回
# 🔍 [作用] 汇总三轴登记，供前端渲染"可选策略"与兼容提示
def list_strategies() -> Dict:
    # 🔍 [作用] 质量增强与知识增强采用同一份前端发现协议。
    all_techniques = {**QUALITY_TECHNIQUES, **COMPOSITION_TECHNIQUES}
    return {
        "algorithms": [
            {"id": k, **v} for k, v in GENERATION_ALGORITHMS.items()
        ],
        "techniques": [
            {"id": k, **v} for k, v in all_techniques.items()
        ],
        "compatibility": compatibility_matrices(),
        # 🔍 [语法] skill 不在此静态登记
        "note": "skill 由用户安装，运行时通过 available_skill_ids 动态校验",
    }
