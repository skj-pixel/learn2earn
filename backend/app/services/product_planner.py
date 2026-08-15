# 🔍 [语法] 模块级 docstring（占位）
# 🔍 [作用] 标记模块用途——产品规划引擎
"""
把学习过程变成赚钱过程的app/backend/app/services/product_planner.py 模块

模块用途: TODO 自动扫描生成的占位说明,需要人工补全。
"""
# =============================================================================
# product_planner.py - 知识付费产品架构规划引擎
# =============================================================================
# 在生成前先输出一份详细的产品架构方案
# 用户审核 → 调整 → 确认后再生成
# =============================================================================

# 🔍 [语法] 标准库
import json
import time
from typing import List, Dict, Optional

# 🔍 [语法] 相对导入
# 🔍 [作用] 核心生成器和产品类型
from .product_generator import product_generator, PRODUCT_TYPES, ProductGenerator
from .llm_service import LLMService


# =============================================================================
# ProductPlan - 产品架构方案数据模型
# =============================================================================

class ProductPlan:
    """产品架构方案"""

    # 🔍 [语法] __init__
    # 🔍 [作用] 初始化 5 大模块
    def __init__(self, note_title: str, subject_name: str, difficulty: str):
        # ---- 全局概览 ----
        self.overview = {
            "topic": note_title,
            "subject": subject_name,
            "difficulty": difficulty,
            "target_audience": "",
            "unique_value": "",
            "monetization_goal": "",
            "total_potential_revenue": 0,
        }

        # ---- 产品蓝图列表 ----
        # 🔍 [语法] List[Dict]
        # 🔍 [作用] 每个元素 = {"type", "priority", ...}
        self.product_items: List[Dict] = []

        # ---- 内容策略 ----
        self.content_strategy = {
            "generation_order": [],
            "cross_references": "",
            "free_vs_paid": "",
        }

        # ---- 定价策略 ----
        self.pricing_strategy = {
            "individual_prices": {},
            "bundle_price": 0,
            "premium_price": 0,
            "pricing_rationale": "",
        }

        # ---- 时间线 ----
        self.timeline = {
            "estimated_minutes": 0,
            "chunk_count_total": 0,
            "suggested_schedule": "",
        }

    # 🔍 [语法] def
    # 🔍 [作用] 转字典（JSON 序列化）
    def to_dict(self) -> Dict:
        return {
            "overview": self.overview,
            "product_items": self.product_items,
            "content_strategy": self.content_strategy,
            "pricing_strategy": self.pricing_strategy,
            "timeline": self.timeline,
        }

    # 🔍 [语法] def + str 返回
    # 🔍 [作用] 转 Markdown（前端展示）
    def to_markdown(self) -> str:
        md = []

        # ---- 头部 ----
        md.append(f"# 📐 知识付费产品架构方案")
        md.append(f"")
        md.append(f"> **主题**: {self.overview['topic']}")
        md.append(f"> **科目**: {self.overview['subject']}")
        md.append(f"> **难度**: {self.overview['difficulty']}")
        md.append(f"> **受众**: {self.overview['target_audience']}")
        md.append(f"")

        # ---- 独特价值 ----
        md.append(f"## 🎯 独特价值主张")
        md.append(f"")
        md.append(f"{self.overview['unique_value']}")
        md.append(f"")

        # ---- 变现目标 ----
        md.append(f"## 💰 变现目标")
        md.append(f"")
        md.append(f"{self.overview['monetization_goal']}")
        md.append(f"")
        md.append(f"**预估总收入**: ¥{self.overview['total_potential_revenue']}")
        md.append(f"")

        # ---- 产品蓝图 ----
        md.append(f"## 📦 推荐产品蓝图（{len(self.product_items)}个）")
        md.append(f"")
        md.append(f"| 优先级 | 产品类型 | 建议标题 | 定价 | 推荐平台 |")
        md.append(f"|--------|----------|----------|------|----------|")
        for item in sorted(self.product_items, key=lambda x: x.get("priority", 99)):
            info = PRODUCT_TYPES.get(item["type"], {})
            icon = info.get("icon", "📦")
            name = info.get("name", item["type"])
            md.append(
                f"| {item.get('priority', '?')} "
                f"| {icon} {name} "
                f"| {item.get('suggested_title', '')} "
                f"| ¥{item.get('estimated_price', 0)} "
                f"| {', '.join(item.get('platforms', [])[:2])} |"
            )
        md.append(f"")

        # ---- 每个产品的详细大纲 ----
        for item in sorted(self.product_items, key=lambda x: x.get("priority", 99)):
            info = PRODUCT_TYPES.get(item["type"], {})
            md.append(f"### {info.get('icon', '📦')} {item.get('suggested_title', item['type'])}")
            md.append(f"")
            md.append(f"- **定位**: {item.get('angle', '')}")
            md.append(f"- **售价**: ¥{item.get('estimated_price', 0)}")
            md.append(f"- **平台**: {', '.join(item.get('platforms', []))}")
            md.append(f"- **大纲**:")
            if item.get("outline"):
                for ol in item["outline"]:
                    md.append(f"  - {ol}")
            md.append(f"")

        # ---- 内容策略 ----
        md.append(f"## 🔗 内容策略")
        md.append(f"")
        md.append(f"**建议生成顺序**: {' → '.join(self.content_strategy['generation_order'])}")
        md.append(f"")
        md.append(f"**产品互链策略**: {self.content_strategy['cross_references']}")
        md.append(f"")
        md.append(f"**免费 vs 付费**: {self.content_strategy['free_vs_paid']}")
        md.append(f"")

        # ---- 定价策略 ----
        md.append(f"## 🏷️ 定价策略")
        md.append(f"")
        md.append(f"| 定价方式 | 价格 |")
        md.append(f"|----------|------|")
        for ptype, price in self.pricing_strategy.get("individual_prices", {}).items():
            info = PRODUCT_TYPES.get(ptype, {})
            md.append(f"| {info.get('icon','📦')} {info.get('name', ptype)} | ¥{price} |")
        md.append(f"| 📦 打包价 | ¥{self.pricing_strategy['bundle_price']} |")
        md.append(f"| 🏆 高端版（含1v1） | ¥{self.pricing_strategy['premium_price']} |")
        md.append(f"")
        md.append(f"**定价理由**: {self.pricing_strategy['pricing_rationale']}")
        md.append(f"")

        # ---- 时间线 ----
        md.append(f"## ⏱️ 时间线预估")
        md.append(f"")
        md.append(f"- 预估总耗时: **{self.timeline['estimated_minutes']} 分钟**")
        md.append(f"- 总分块数: **{self.timeline['chunk_count_total']} 块**")
        md.append(f"- 建议发布节奏: {self.timeline['suggested_schedule']}")
        md.append(f"")

        md.append(f"---")
        md.append(f"*规划由 Learn2Earn 产品架构引擎自动生成*")

        return "\n".join(md)


# =============================================================================
# ProductPlanner - 产品架构规划器
# =============================================================================

class ProductPlanner:
    """产品架构规划器（LLM 增强 + 模板回退）"""

    # 🔍 [语法] __init__
    # 🔍 [作用] 接受可选 LLM 服务
    def __init__(self, llm_service: LLMService = None):
        self.llm = llm_service

    # 🔍 [语法] async def
    # 🔍 [作用] 规划主入口（LLM 优先 + 模板回退）
    async def plan(self, note_title: str, note_content: str, subject_name: str = "") -> ProductPlan:
        """
        策略：
            1. 内置分析（不依赖 LLM）
            2. LLM 可用 → LLM 规划；否则 → 模板回退
        """
        # 🔍 [语法] 内置分析
        # 🔍 [作用] 启发式分析（不调 LLM）
        analysis = product_generator.analyze_content(note_content, subject_name)
        difficulty = analysis.get("difficulty", "intermediate")
        suggestions = product_generator.suggest_products(note_content, subject_name)

        # 🔍 [语法] LLM 优先
        # 🔍 [作用] 可用时用 LLM
        if self.llm and self.llm.is_ready():
            try:
                return await self._plan_with_llm(note_title, note_content, subject_name, difficulty, suggestions)
            except Exception:
                pass  # LLM 失败 → 回退到模板

        # 🔍 [语法] 回退
        return self._plan_with_template(note_title, note_content, subject_name, difficulty, suggestions)

    # 🔍 [语法] async def
    # 🔍 [作用] LLM 增强规划
    async def _plan_with_llm(self, note_title, note_content, subject_name, difficulty, suggestions) -> ProductPlan:
        """使用 LLM 生成详细的产品架构规划"""
        suggestion_text = "\n".join([
            f"- {s['type']}: {s.get('name', '')} ({s.get('reason', '')})"
            for s in suggestions
        ])

        # 🔍 [语法] f-string prompt
        # 🔍 [作用] LLM 生成 JSON
        prompt = f"""你是一位资深的知识付费产品架构师。请根据以下学习笔记，制定一份完整的产品架构方案。

笔记标题：{note_title}
所属科目：{subject_name}
难度等级：{difficulty}

已有的产品类型推荐：
{suggestion_text}

笔记内容：
---
{note_content}
---

请输出以下 JSON 格式的架构方案（不要添加任何解释，只输出纯 JSON）：

{{
  "overview": {{
    "target_audience": "目标受众描述（50-100字）",
    "unique_value": "独特价值主张（50-100字）- 为什么别人要买你的产品",
    "monetization_goal": "变现目标描述（30-80字）"
  }},
  "product_items": [
    {{
      "type": "产品类型标识（article/sop等）",
      "priority": 数字(1=最重要),
      "suggested_title": "建议的产品标题",
      "angle": "独特的切入角度（20-40字）",
      "estimated_price": 数字(元),
      "platforms": ["平台1", "平台2"],
      "outline": ["大章节1", "大章节2", "大章节3"]
    }}
  ],
  "content_strategy": {{
    "generation_order": ["type1", "type2"],
    "cross_references": "如何在产品间互相引流和交叉推荐（50-100字）",
    "free_vs_paid": "哪些免费引流，哪些直接付费（30-60字）"
  }},
  "pricing_strategy": {{
    "individual_prices": {{"product_type": 价格}},
    "bundle_price": 打包总价,
    "premium_price": 高端版价格(含1v1服务),
    "pricing_rationale": "定价理由（30-80字）"
  }},
  "timeline": {{
    "estimated_minutes": 预估总耗时(分钟),
    "chunk_count_total": 预估总分块数,
    "suggested_schedule": "建议发布节奏（30-60字）"
  }}
}}

重要：product_items 只包含最推荐的产品类型（最多8个），类型标识必须使用已有的推荐列表中的值。
JSON 必须是合法的，可以直接用 json.loads 解析。"""

        # 🔍 [语法] await chat
        # 🔍 [作用] 调用 LLM
        response = await self.llm.chat(prompt, max_tokens=4096, timeout=120)

        # 🔍 [语法] 调用解析函数
        # 🔍 [作用] 提取 LLM 返回的 JSON
        plan_data = self._parse_llm_response(response)

        # 🔍 [语法] 构造 ProductPlan
        # 🔍 [作用] 填充所有字段
        plan = ProductPlan(note_title, subject_name, difficulty)

        # ---- 填充 overview ----
        plan.overview["target_audience"] = plan_data.get("overview", {}).get("target_audience", "")
        plan.overview["unique_value"] = plan_data.get("overview", {}).get("unique_value", "")
        plan.overview["monetization_goal"] = plan_data.get("overview", {}).get("monetization_goal", "")

        # ---- 填充 product_items ----
        for item in plan_data.get("product_items", []):
            ptype = item.get("type", "")
            # 🔍 [语法] 跳过无效类型
            if ptype not in PRODUCT_TYPES:
                continue
            info = PRODUCT_TYPES[ptype]
            plan.product_items.append({
                "type": ptype,
                "icon": info["icon"],
                "name": info["name"],
                "priority": item.get("priority", 99),
                "suggested_title": item.get("suggested_title", f"{note_title} - {info['name']}"),
                "angle": item.get("angle", ""),
                "estimated_price": item.get("estimated_price", info["price_range"][0]),
                "platforms": item.get("platforms", info["platforms"]),
                "outline": item.get("outline", []),
            })

        # ---- 填充 content_strategy ----
        plan.content_strategy["generation_order"] = plan_data.get("content_strategy", {}).get("generation_order", [])
        plan.content_strategy["cross_references"] = plan_data.get("content_strategy", {}).get("cross_references", "")
        plan.content_strategy["free_vs_paid"] = plan_data.get("content_strategy", {}).get("free_vs_paid", "")

        # ---- 填充 pricing_strategy ----
        plan.pricing_strategy["individual_prices"] = plan_data.get("pricing_strategy", {}).get("individual_prices", {})
        plan.pricing_strategy["bundle_price"] = plan_data.get("pricing_strategy", {}).get("bundle_price", 0)
        plan.pricing_strategy["premium_price"] = plan_data.get("pricing_strategy", {}).get("premium_price", 0)
        plan.pricing_strategy["pricing_rationale"] = plan_data.get("pricing_strategy", {}).get("pricing_rationale", "")

        # ---- 填充 timeline ----
        plan.timeline["estimated_minutes"] = plan_data.get("timeline", {}).get("estimated_minutes", 30)
        plan.timeline["chunk_count_total"] = plan_data.get("timeline", {}).get("chunk_count_total", 8)
        plan.timeline["suggested_schedule"] = plan_data.get("timeline", {}).get("suggested_schedule", "")

        # ---- 计算总收入 ----
        total = sum(item.get("estimated_price", 0) for item in plan.product_items)
        plan.overview["total_potential_revenue"] = total

        return plan

    # 🔍 [语法] def（非 async）
    # 🔍 [作用] 模板规划（无 LLM）
    def _plan_with_template(self, note_title, note_content, subject_name, difficulty, suggestions) -> ProductPlan:
        """使用模板引擎生成基础规划（不依赖 LLM）"""
        # 🔍 [语法] 局部 import 避免循环依赖
        from .chunked_generator import ChunkedGenerator

        # 🔍 [语法] 难度映射
        # 🔍 [作用] 英文 → 中文
        diff_map = {"beginner": "初级", "intermediate": "中级", "advanced": "高级"}
        diff_cn = diff_map.get(difficulty, "中级")

        plan = ProductPlan(note_title, subject_name, difficulty)

        # ---- 填充 overview ----
        plan.overview["target_audience"] = (
            f"正在学习{subject_name or '该领域'}的{diff_cn}开发者，"
            f"希望通过系统化学习提升技能并实现技术变现。"
        )
        plan.overview["unique_value"] = (
            f"将零散的{note_title}学习笔记转化为成体系的知识付费产品矩阵，"
            f"从入门到实战全覆盖，每个产品解决一个具体的学习痛点。"
        )
        plan.overview["monetization_goal"] = (
            f"通过内容变现 + 产品售卖 + 咨询服务的组合模式，"
            f"实现知识复利增长。月目标：¥500-2000（持续积累）。"
        )

        # ---- 填充 product_items ----
        for idx, s in enumerate(suggestions, 1):
            info = PRODUCT_TYPES.get(s["type"], {})
            plan.product_items.append({
                "type": s["type"],
                "icon": info.get("icon", "📦"),
                "name": info.get("name", s["type"]),
                "priority": idx,
                "suggested_title": f"{note_title} - {info.get('name', s['type'])}",
                "angle": s.get("reason", ""),
                "estimated_price": info.get("price_range", (0, 0))[0],
                "platforms": info.get("platforms", [])[:3],
                "outline": [
                    "核心概念与背景（来自笔记主体内容）",
                    "实战演示与操作步骤",
                    "常见问题与避坑指南",
                    "总结回顾与进阶建议",
                ],
            })

        # ---- 填充 content_strategy ----
        plan.content_strategy["generation_order"] = [
            item["type"] for item in plan.product_items
        ]
        plan.content_strategy["cross_references"] = (
            "在每个产品中引用其他产品的链接，形成内容矩阵。"
            "例如：文章末尾推荐课程大纲，SOP文档中引用思维导图。"
        )
        plan.content_strategy["free_vs_paid"] = (
            "技术文章免费发布引流 → PPT模板/提示词模板低价走量 → "
            "课程大纲/SOP文档中价精品 → 训练营/咨询高价服务"
        )

        # ---- 填充 pricing_strategy ----
        for item in plan.product_items:
            plan.pricing_strategy["individual_prices"][item["type"]] = item["estimated_price"]

        # 🔍 [语法] 打包价 = 单品 × 75%
        # 🔍 [作用] 给批量购买 25% 折扣
        total_individual = sum(plan.pricing_strategy["individual_prices"].values())
        plan.pricing_strategy["bundle_price"] = int(total_individual * 0.75)
        # 🔍 [语法] 高端价 = 打包价 × 3
        # 🔍 [作用] 含 1v1 答疑
        plan.pricing_strategy["premium_price"] = plan.pricing_strategy["bundle_price"] * 3
        plan.pricing_strategy["pricing_rationale"] = (
            "打包价给予 75 折优惠促进批量购买； "
            "高端版含 1v1 答疑和项目评审服务，适合愿意为效率付费的用户。"
        )

        # ---- 填充 timeline ----
        # 🔍 [语法] sum(get_chunk_count)
        # 🔍 [作用] 计算总分块数
        chunk_total = sum(
            ChunkedGenerator.get_chunk_count(item["type"])
            for item in plan.product_items
        )
        plan.timeline["estimated_minutes"] = max(5, chunk_total * 2)
        plan.timeline["chunk_count_total"] = chunk_total
        plan.timeline["suggested_schedule"] = (
            "首日发布文章引流 → 3天内上传低价产品 → 1周内上架中价精品 → "
            "2周后开放高端咨询服务。保持每周至少更新一篇免费文章。"
        )

        # ---- 计算总收入 ----
        plan.overview["total_potential_revenue"] = sum(
            item["estimated_price"] for item in plan.product_items
        )

        return plan

    # 🔍 [语法] def
    # 🔍 [作用] 解析 LLM 返回的 JSON
    def _parse_llm_response(self, response: str) -> Dict:
        """从 LLM 的文本回复中提取 JSON（处理 ```json``` 包裹）"""
        text = response.strip()

        # ---- 移除 Markdown 代码块 ----
        # 🔍 [语法] startswith("```")
        # 🔍 [作用] 处理 ```json ... ``` 包裹
        if text.startswith("```"):
            lines = text.split("\n")
            # 🔍 [语法] 切片去头尾
            # 🔍 [作用] 去掉 ``` 行
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        # ---- 找 JSON 边界 ----
        # 🔍 [语法] find / rfind
        # 🔍 [作用] 第一个 { 到最后一个 }
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]

        try:
            return json.loads(text)
        # 🔍 [语法] 解析失败返回空
        except json.JSONDecodeError:
            return {
                "overview": {},
                "product_items": [],
                "content_strategy": {},
                "pricing_strategy": {},
                "timeline": {},
            }

    # 🔍 [语法] def + return
    # 🔍 [作用] 同步版本（供非 async 代码使用）
    def plan_sync(self, note_title: str, note_content: str, subject_name: str = "") -> ProductPlan:
        """同步方式生成规划"""
        # 🔍 [语法] import asyncio 局部
        # 🔍 [作用] 在同步函数中运行 async
        import asyncio
        try:
            # 🔍 [语法] asyncio.get_running_loop()
            # 🔍 [作用] Python 3.7+ 推荐方式
            loop = asyncio.get_running_loop()
            # 🔍 [语法] ThreadPoolExecutor
            # 🔍 [作用] 在新线程中执行避免循环嵌套
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.plan(note_title, note_content, subject_name)
                )
                return future.result(timeout=120)
        except RuntimeError:
            # 🔍 [语法] 没有运行中循环
            # 🔍 [作用] 直接用 asyncio.run（自动管理生命周期）
            return asyncio.run(self.plan(note_title, note_content, subject_name))
