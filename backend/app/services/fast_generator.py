# 🔍 [语法] 模块级 docstring（占位）
# 🔍 [作用] 标记模块用途——快速生成器
"""
把学习过程变成赚钱过程的app/backend/app/services/fast_generator.py 模块

模块用途: TODO 自动扫描生成的占位说明,需要人工补全。
"""
# =============================================================================
# fast_generator.py - 快速一键生成器
# =============================================================================
# 核心思想：将"规划 + 生成"两个阶段合并为单次 LLM 调用
#   旧流程: 规划(1次) + 生成N个产品(N次) = N+1 次
#   快模式: 1次调用直接输出全部
# =============================================================================

# 🔍 [语法] 标准库
# 🔍 [作用] re 正则（解析 LLM 输出）；time 计时；json 序列化
import re
import time
import json

# 🔍 [语法] typing
# 🔍 [作用] 类型注解
from typing import Dict, Optional

# 🔍 [语法] 相对导入
# 🔍 [作用] LLM 服务 + 产品类型常量 + 主生成器
from .llm_service import LLMService, get_llm_service
from .product_generator import PRODUCT_TYPES, product_generator


# =============================================================================
# FastGenerator - 快速生成器
# =============================================================================
class FastGenerator:
    """快速一键生成器：规划+全部产品 → 一次 LLM 调用完成"""

    # ---- 分隔标记常量 ----
    # 🔍 [语法] 4 个类常量
    # 🔍 [作用] 提示 LLM 输出结构化分隔符
    PLAN_START = "---PLAN---"                    # 规划开始
    PLAN_END = "---PRODUCTS---"                  # 规划结束
    PRODUCT_MARKER = "---PRODUCT "               # 单个产品前缀
    ALL_END = "---END---"                        # 全部结束
    # 🔍 [陷阱] 设计理由：这些分隔符在 Markdown 中不太可能出现，安全用作边界

    # 🔍 [语法] __init__
    # 🔍 [作用] 构造时获取 LLM 服务
    def __init__(self, llm: LLMService = None):
        # 🔍 [语法] 默认参数 + or
        # 🔍 [作用] 传入或自动获取单例
        self.llm = llm or get_llm_service()

    # 🔍 [语法] async def
    # 🔍 [作用] 快速生成主入口
    async def generate_all(self, note_title: str, note_content: str, subject_name: str = "") -> Dict:
        """
        一次性完成规划+全部产品生成

        Returns:
            dict: {
                "success": True/False,
                "plan": {...},
                "products": [...],
                "total_time_ms": 耗时,
                "token_saved_pct": 节省百分比,
            }
        """
        # 🔍 [语法] 计时
        start = time.time()

        # ---- 步骤 1: 检查 LLM 是否可用 ----
        # 🔍 [语法] 早返回
        # 🔍 [作用] 未配置 LLM 直接返回错误
        if not self.llm.is_ready():
            return {
                "success": False,
                "error": "LLM 未配置。快速模式需要 LLM API。",
                "total_time_ms": 0,
            }

        # ---- 步骤 2: 构建合并 prompt ----
        prompt = self._build_combined_prompt(note_title, note_content, subject_name)

        # ---- 步骤 3: 单次 LLM 调用 ----
        try:
            # 🔍 [语法] max_tokens=8192
            # 🔍 [作用] 足够大以容纳多个产品
            response = await self.llm.chat(
                user_message=prompt,
                max_tokens=8192,
                timeout=180,
                # 🔍 [语法] temperature=0.6
                # 🔍 [作用] 略低于 0.7 保证规划稳定
                temperature=0.6,
            )
        except Exception as e:
            # 🔍 [语法] 错误捕获
            # 🔍 [作用] LLM 调用失败不影响返回结构
            return {
                "success": False,
                "error": f"LLM调用失败: {e}",
                "total_time_ms": int((time.time() - start) * 1000),
            }

        # ---- 步骤 4: 解析 LLM 返回的多产品内容 ----
        plan_data, products = self._parse_response(response, note_title)

        # 🔍 [语法] 计时结束
        total_time_ms = int((time.time() - start) * 1000)

        # ---- 步骤 5: 估算节省的 token ----
        # 🔍 [语法] 估算函数
        # 🔍 [作用] 对比旧流程节省的 token 百分比
        token_saved_pct = self._estimate_token_saving(products)

        return {
            "success": True,
            "plan": plan_data,
            "products": products,
            "product_count": len(products),
            "total_time_ms": total_time_ms,
            "token_saved_pct": token_saved_pct,
            "mode": "fast",
        }

    # 🔍 [语法] def + 返回 str
    # 🔍 [作用] 构建合并 prompt（规划 + 全部产品）
    def _build_combined_prompt(self, note_title: str, note_content: str, subject_name: str) -> str:
        """
        构建"规划+全部产品"的合并 prompt

        设计要点：
            1. 先让 LLM 做一次规划（输出 JSON）
            2. 然后按顺序输出每个产品的完整内容
            3. 用分隔标记区分各个部分，便于程序解析
        """
        # ---- 列出所有产品类型供 LLM 选择 ----
        product_list = "\n".join([
            f"  - {info['icon']} {key} ({info['name']})"
            for key, info in list(PRODUCT_TYPES.items())
        ])

        # 🔍 [语法] f-string 多行
        # 🔍 [作用] 完整的 prompt 模板
        # 🔍 [陷阱] 提示中明确"严格遵循"输出格式
        return f"""你是知识付费产品创作专家。请根据以下学习笔记，一次性完成产品规划和生成。

## 笔记信息
- 标题：{note_title}
- 科目：{subject_name or '通用'}

## 笔记内容
{note_content[:4000]}

## 可用产品类型（从中选择3-6个最合适的）
{product_list}

## 输出格式（严格遵循）

首先输出规划摘要：
---PLAN---
{{"target_audience":"目标受众","unique_value":"独特价值","selected_products":["article","sop","mindmap"],"total_revenue":估算总收入}}
---PRODUCTS---

然后依次输出每个选中产品的完整Markdown内容：
---PRODUCT article---
[完整的文章Markdown内容]
---PRODUCT sop---
[完整的SOP Markdown内容]
... (继续输出其他选中产品)
---END---

## 要求
1. 从可用产品类型中选择3-6个最适合的产品（不要选太多，精选优于数量）
2. 每个产品必须是完整的、可直接发布的Markdown内容
3. 产品间内容互补不重复
4. 规划JSON中的selected_products顺序 = 产品输出顺序
5. 每个产品末尾加上"---"分隔，再输出下一个
6. 直接输出内容，不要额外解释"""

    # 🔍 [语法] def + tuple 返回
    # 🔍 [作用] 解析 LLM 返回的多产品内容
    def _parse_response(self, response: str, note_title: str) -> tuple:
        """
        解析 LLM 返回的多产品内容：
            1. 提取 ---PLAN--- 到 ---PRODUCTS--- 之间的 JSON
            2. 用 ---PRODUCT type--- 分割每个产品
        """
        # 🔍 [语法] 默认空结构
        plan_data = {"target_audience": "", "unique_value": "", "selected_products": []}
        products = []

        # ---- 步骤 1: 提取规划 JSON ----
        # 🔍 [语法] re.escape
        # 🔍 [作用] 转义 ---PLAN--- 等正则特殊字符
        plan_match = re.search(
            re.escape(self.PLAN_START) + r'\s*(.*?)\s*' + re.escape(self.PLAN_END),
            response, re.DOTALL  # 🔍 [语法] DOTALL 让 . 匹配换行
        )
        if plan_match:
            try:
                # 🔍 [语法] json.loads
                # 🔍 [作用] 解析规划 JSON
                plan_data = json.loads(plan_match.group(1).strip())
            # 🔍 [语法] 静默失败
            # 🔍 [作用] JSON 解析失败用默认空结构
            except json.JSONDecodeError:
                pass

        # ---- 步骤 2: 提取各产品内容 ----
        # 🔍 [语法] products_section
        products_section = ""
        products_match = re.search(
            re.escape(self.PLAN_END) + r'(.*?)' + re.escape(self.ALL_END),
            response, re.DOTALL
        )
        if products_match:
            products_section = products_match.group(1)
        else:
            # 🔍 [语法] fallback
            # 🔍 [作用] 没有 END 标记则取 PRODUCTS 之后全部
            idx = response.find(self.PLAN_END)
            if idx >= 0:
                products_section = response[idx + len(self.PLAN_END):]

        # ---- 步骤 3: 按 ---PRODUCT type--- 分割 ----
        # 🔍 [语法] re.split + 捕获组
        # 🔍 [作用] 返回 [text_before, type1, content1, type2, content2, ...]
        product_blocks = re.split(r'---PRODUCT\s+(\w+)\s*---', products_section)

        # 🔍 [语法] for step=2 遍历
        # 🔍 [作用] 跳过第一个 text_before，步长 2 取 type+content 对
        for i in range(1, len(product_blocks), 2):
            if i + 1 < len(product_blocks):
                # 🔍 [语法] strip()
                # 🔍 [作用] 去除首尾空白
                ptype = product_blocks[i].strip()
                content = product_blocks[i + 1].strip()

                # 🔍 [语法] 长度过滤
                # 🔍 [作用] 跳过空内容或过短内容
                if not content or len(content) < 50:
                    continue

                # 🔍 [语法] 清理末尾分隔线
                content = re.sub(r'\n?---\s*$', '', content)

                # ---- 内容抛光 ----
                # 🔍 [语法] 局部 import 避免循环依赖
                from .content_polisher import ContentPolisher
                polished, polish_stats = ContentPolisher.polish_product(content, ptype, note_title)
                # 🔍 [语法] 有实质修复才用
                if polish_stats.get("ai_stripped", 0) > 0 or polish_stats.get("code_fixed", 0) > 0:
                    content = polished

                # ---- 查找产品类型元信息 ----
                info = PRODUCT_TYPES.get(ptype, {
                    "name": ptype, "icon": "📦",
                    "price_range": (0, 0), "platforms": [],
                })

                # ---- 构造产品数据 ----
                products.append({
                    "type": ptype,
                    "name": info["name"],
                    "icon": info["icon"],
                    # 🔍 [语法] f-string
                    # 🔍 [作用] 自动生成标题
                    "title": f"{info['icon']} {note_title} - {info['name']}",
                    "content": content,
                    # 🔍 [语法] 价格区间下限
                    "price_suggestion": info["price_range"][0],
                    # 🔍 [语法] 切片前 3 个平台
                    "platform_suggestion": info["platforms"][:3],
                })

        # ---- 步骤 4: fallback 解析 ----
        # 🔍 [语法] 兜底逻辑
        # 🔍 [作用] 没解析到产品时整个响应作为 article
        if not products and len(response) > 500:
            products.append({
                "type": "article",
                "name": "技术文章",
                "icon": "📝",
                "title": f"📝 {note_title}",
                "content": response[:5000],
                "price_suggestion": PRODUCT_TYPES["article"]["price_range"][0],
                "platform_suggestion": PRODUCT_TYPES["article"]["platforms"][:3],
            })

        return plan_data, products

    # 🔍 [语法] def + int 返回
    # 🔍 [作用] 估算 token 节省百分比
    def _estimate_token_saving(self, products: list) -> int:
        """
        估算快速模式相比分步模式节省的 token 百分比

        旧流程：1 + N*4 次调用
        快模式：1 次调用

        每减少一次调用就省一次 prompt 开销（约 500 tokens 的固定开销）。
        """
        if not products:
            return 0

        n = len(products)
        # 🔍 [语法] 旧流程调用次数（1 规划 + N*4 分块）
        old_calls = 1 + n * 4
        # 🔍 [语法] 快模式调用次数
        new_calls = 1

        # 🔍 [语法] 估算公式
        # 🔍 [作用] 总 token = 内容 + prompt 开销
        total_est = 2000 * n + (old_calls - 1) * 500
        saved = (old_calls - new_calls) * 500

        # 🔍 [语法] min 90 防止超过 100%
        # 🔍 [作用] 实际节省不超过 90%
        pct = int(min(90, saved / max(1, total_est) * 100))

        return pct


# =============================================================================
# 模块级单例
# =============================================================================
# 🔍 [语法] 模块级实例
# 🔍 [作用] 单例（避免重复实例化）
fast_generator = FastGenerator()
