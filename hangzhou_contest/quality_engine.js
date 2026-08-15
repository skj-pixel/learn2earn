// 🔍 [语法] const 数组
// 🔍 [作用] 6 维度评分表（与 Python 版同结构）
const RUBRIC = [
  // 🔍 [语法] [名称, 权重, 描述]
  ["行业场景价值", 25, "真实行业问题、目标用户、核心痛点、现实收益、复制推广潜力"],
  ["Agent 能力与任务闭环", 25, "理解、规划、工具调用、知识增强、上下文记忆、验证交付"],
  ["产品体验与 Demo 完成度", 20, "自然交互、清晰流程、及时反馈、稳定可运行、快速验证"],
  ["技术实现深度", 15, "大模型、Agent、知识库、工具、多模态、工作流、工程架构"],
  ["安全、合规与可追溯", 10, "数据来源、使用边界、风险提示、审计记录、合规约束"],
  ["开放 / 复用贡献", 5, "模板、示例数据、文档、复用接口、开源计划、依赖说明"],
];

// 🔍 [语法] const 对象（关键词分类）
// 🔍 [作用] 5 维关键词检测
const CHECKS = {
  structure: ["目标用户", "痛点", "输入", "步骤", "输出", "证据", "下一步"],
  agentLoop: ["理解", "计划", "执行", "验证", "交付"],
  evidence: ["数据来源", "依据", "引用", "日志", "截图", "结果"],
  safety: ["风险", "边界", "合规", "人工确认", "免责声明"],
  reuse: ["模板", "示例", "导出", "复用", "接口"],
};

// 🔍 [语法] 箭头函数
// 🔍 [作用] 关键词命中计数
function hitCount(text, words) {
  // 🔍 [语法] filter().length
  // 🔍 [作用] 统计 text 中包含的关键词数
  return words.filter((word) => text.toLowerCase().includes(word.toLowerCase())).length;
}

// 🔍 [语法] export function
// 🔍 [作用] 前端评分主入口（供 scorecard.html 调用）
export function evaluateInteractionArtifact(userInput, agentOutput, trace = "") {
  // 🔍 [语法] 字符串拼接
  // 🔍 [作用] 三段合并
  const text = `${userInput || ""}\n${agentOutput || ""}\n${trace || ""}`;

  // 🔍 [语法] 5 维计数
  const structureHits = hitCount(text, CHECKS.structure);
  const agentHits = hitCount(text, CHECKS.agentLoop);
  const evidenceHits = hitCount(text, CHECKS.evidence);
  const safetyHits = hitCount(text, CHECKS.safety);
  const reuseHits = hitCount(text, CHECKS.reuse);

  // 🔍 [语法] 长度奖励
  // 🔍 [作用] 鼓励详细回答
  const lengthBonus = Math.min((agentOutput || "").length / 1200, 1);

  // 🔍 [语法] 6 维度计算
  const scores = {
    "行业场景价值": Math.min(25, +(8 + structureHits * 2.2 + lengthBonus * 4).toFixed(1)),
    "Agent 能力与任务闭环": Math.min(25, +(7 + agentHits * 3.0 + evidenceHits * 0.8).toFixed(1)),
    "产品体验与 Demo 完成度": Math.min(20, +(7 + structureHits * 1.3 + (text.includes("导出") ? 2 : 0) + (text.includes("反馈") ? 2 : 0)).toFixed(1)),
    "技术实现深度": Math.min(15, +(5 + hitCount(text, ["模型", "知识库", "工具", "工作流", "多轮", "多模态", "架构"]) * 1.4).toFixed(1)),
    "安全、合规与可追溯": Math.min(10, +(2 + safetyHits * 1.6 + evidenceHits * 0.7).toFixed(1)),
    "开放 / 复用贡献": Math.min(5, +(1 + reuseHits * 0.8).toFixed(1)),
  };

  // 🔍 [语法] 改进建议
  const suggestions = [];
  // 🔍 [语法] 阈值建议
  // 🔍 [作用] 不足项给出具体改进方向
  if (structureHits < 4) suggestions.push("补充目标用户、痛点、输入、步骤、输出、证据和下一步。");
  if (agentHits < 4) suggestions.push("展示 Agent 从理解、计划、执行、验证到交付的闭环。");
  if (evidenceHits < 3) suggestions.push("为关键结论增加数据来源、引用、日志、截图或验证结果。");
  if (safetyHits < 2) suggestions.push("补充风险边界、合规提示和需要人工确认的场景。");
  if (reuseHits < 2) suggestions.push("补充模板、示例数据、导出格式或 API/工作流复用说明。");

  return {
    // 🔍 [语法] Object.values().reduce()
    // 🔍 [作用] 求和
    total: Object.values(scores).reduce((a, b) => +(a + b).toFixed(1), 0),
    scores,
    suggestions,
    rubric: RUBRIC,
  };
}

// 🔍 [语法] export function
// 🔍 [作用] 包装用户 prompt（按 6 维度评分标准生成）
export function buildImprovedPrompt(rawPrompt, scenario = "") {
  return `请围绕杭州创业大赛评分标准完成任务。

行业场景：${scenario || "请先识别最匹配的真实行业场景"}
用户原始需求：${rawPrompt}

输出要求：
1. 明确目标用户、真实痛点、业务收益和可推广性。
2. 展示 Agent 的理解、计划、执行、验证、交付闭环。
3. 给出结构化产物，并说明数据来源、证据、使用边界和风险提示。
4. 给出可复用模板、示例数据、导出形式和下一步行动。
5. 最后用 6 个杭州赛评分维度自评，并说明如何继续提升。`;
}
