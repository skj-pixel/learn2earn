from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RubricDimension:
    name: str
    weight: int
    description: str


HANGZHOU_RUBRIC = [
    RubricDimension("行业场景价值", 25, "真实行业问题、目标用户、核心痛点、现实收益、复制推广潜力"),
    RubricDimension("Agent 能力与任务闭环", 25, "理解、规划、工具调用、知识增强、上下文记忆、验证交付"),
    RubricDimension("产品体验与 Demo 完成度", 20, "自然交互、清晰流程、及时反馈、稳定可运行、快速验证"),
    RubricDimension("技术实现深度", 15, "大模型、Agent、知识库、工具、多模态、工作流、工程架构"),
    RubricDimension("安全、合规与可追溯", 10, "数据来源、使用边界、风险提示、审计记录、合规约束"),
    RubricDimension("开放 / 复用贡献", 5, "模板、示例数据、文档、复用接口、开源计划、依赖说明"),
]


QUALITY_CHECKS = {
    "structure": ["目标用户", "痛点", "输入", "步骤", "输出", "证据", "下一步"],
    "agent_loop": ["理解", "计划", "执行", "验证", "交付"],
    "evidence": ["数据来源", "依据", "引用", "日志", "截图", "结果"],
    "safety": ["风险", "边界", "合规", "人工确认", "免责声明"],
    "reuse": ["模板", "示例", "导出", "复用", "接口"],
}


def _hit_count(text: str, words: Iterable[str]) -> int:
    return sum(1 for word in words if word.lower() in text.lower())


def evaluate_interaction_artifact(user_input: str, agent_output: str, trace: str = "") -> dict:
    """Score an interaction artifact against the Hangzhou contest rubric.

    The evaluator is deterministic and offline. It is meant for pre-demo quality gating:
    before showing an AI-generated artifact to a judge or user, pass the prompt, output,
    and visible execution trace through this function. Low-scoring dimensions become
    concrete improvement suggestions.
    """
    text = "\n".join([user_input or "", agent_output or "", trace or ""])
    scores = {}
    suggestions = []

    structure_hits = _hit_count(text, QUALITY_CHECKS["structure"])
    agent_hits = _hit_count(text, QUALITY_CHECKS["agent_loop"])
    evidence_hits = _hit_count(text, QUALITY_CHECKS["evidence"])
    safety_hits = _hit_count(text, QUALITY_CHECKS["safety"])
    reuse_hits = _hit_count(text, QUALITY_CHECKS["reuse"])
    length_bonus = min(len(agent_output) / 1200, 1.0)

    scores["行业场景价值"] = min(25, round(8 + structure_hits * 2.2 + length_bonus * 4, 1))
    scores["Agent 能力与任务闭环"] = min(25, round(7 + agent_hits * 3.0 + evidence_hits * 0.8, 1))
    scores["产品体验与 Demo 完成度"] = min(20, round(7 + structure_hits * 1.3 + ("导出" in text) * 2 + ("反馈" in text) * 2, 1))
    scores["技术实现深度"] = min(15, round(5 + _hit_count(text, ["模型", "知识库", "工具", "工作流", "多轮", "多模态", "架构"]) * 1.4, 1))
    scores["安全、合规与可追溯"] = min(10, round(2 + safety_hits * 1.6 + evidence_hits * 0.7, 1))
    scores["开放 / 复用贡献"] = min(5, round(1 + reuse_hits * 0.8, 1))

    if structure_hits < 4:
        suggestions.append("补充目标用户、痛点、输入、步骤、输出、证据和下一步，让产物更像可交付方案。")
    if agent_hits < 4:
        suggestions.append("展示 Agent 从理解、计划、执行、验证到交付的闭环，而不是只展示一次性生成。")
    if evidence_hits < 3:
        suggestions.append("为关键结论增加数据来源、引用、日志、截图或验证结果。")
    if safety_hits < 2:
        suggestions.append("补充风险边界、合规提示和需要人工确认的场景。")
    if reuse_hits < 2:
        suggestions.append("补充模板、示例数据、导出格式或 API/工作流复用说明。")

    return {
        "total": round(sum(scores.values()), 1),
        "scores": scores,
        "suggestions": suggestions,
        "rubric": [dimension.__dict__ for dimension in HANGZHOU_RUBRIC],
    }


def build_improved_prompt(raw_prompt: str, scenario: str = "") -> str:
    """Wrap a raw prompt so the product output is closer to contest judging expectations."""
    return f"""请围绕杭州创业大赛评分标准完成任务。

行业场景：{scenario or "请先识别最匹配的真实行业场景"}
用户原始需求：{raw_prompt}

输出要求：
1. 明确目标用户、真实痛点、业务收益和可推广性。
2. 展示 Agent 的理解、计划、执行、验证、交付闭环。
3. 给出结构化产物，并说明数据来源、证据、使用边界和风险提示。
4. 给出可复用模板、示例数据、导出形式和下一步行动。
5. 最后用 6 个杭州赛评分维度自评，并说明如何继续提升。
"""
