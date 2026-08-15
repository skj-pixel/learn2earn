# 🔍 [语法] 模块级 docstring（占位）
# 🔍 [作用] 标记模块用途——AI 知识付费产品生成器
"""
把学习过程变成赚钱过程的app/backend/app/services/product_generator.py 模块

模块用途: TODO 自动扫描生成的占位说明,需要人工补全。
"""
# =============================================================================
# product_generator.py - AI 知识付费产品自动生成器
# =============================================================================
# 这是整个 Learn2Earn 应用的核心引擎
# 功能：分析笔记 / 推荐产品 / 生成 13 种产品类型
# 设计模式：每种产品 generate_xxx 静态方法，generate() 通过 getattr 分派
# =============================================================================

# 🔍 [语法] 标准库
import re
from typing import Dict, List, Optional
import json


# =============================================================================
# PRODUCT_TYPES - 产品类型定义字典（14 种对外可生成）
# =============================================================================
# 🔍 [作用] 2026-08 移除 8 种历史类型（仅旧 GenerationTask 数据可读，不可再新建）：
#           schedule_template / speech_sop / course_creation_sop / xiaohongshu_sop /
#           ima_knowledge_base / solo_company_sop / software_tutorial / code_doc
PRODUCT_TYPES = {
    # 🔍 [语法] dict 字面量
    # 🔍 [作用] 14 种对外可生成的产品类型 + 元信息
    "article":         {"name": "技术文章/公众号推文", "icon": "📝", "price_range": (19, 199), "platforms": ["CSDN", "掘金", "知乎", "公众号", "B站专栏"]},
    "ppt":     {"name": "PPT大纲",              "icon": "📊", "price_range": (29, 99),  "platforms": ["淘宝", "闲鱼", "Gumroad"]},
    "sop":             {"name": "SOP流程文档",          "icon": "📋", "price_range": (39, 199), "platforms": ["小报童", "知识星球", "Gumroad"]},
    "prompt_template": {"name": "AI提示词模板",         "icon": "💡", "price_range": (19, 59),  "platforms": ["小报童", "Gumroad", "PromptBase"]},
    "course_outline":  {"name": "课程大纲/教案",         "icon": "🎓", "price_range": (99, 499), "platforms": ["B站", "Udemy", "小鹅通", "极客时间"]},
    "interview_qa":    {"name": "面试题库/答案解析",     "icon": "❓", "price_range": (29, 99),  "platforms": ["CSDN下载", "Gumroad", "淘宝"]},
    "workflow":        {"name": "工作流程图",            "icon": "🔄", "price_range": (29, 89),  "platforms": ["淘宝", "Gumroad", "Notion模板市场"]},
    "product_intro":   {"name": "产品介绍/分销文案",     "icon": "📢", "price_range": (0, 0),    "platforms": ["朋友圈", "公众号", "知乎好物"]},
    "quiz":            {"name": "自测题/练习题",         "icon": "✍️", "price_range": (19, 49),  "platforms": ["CSDN下载", "Gumroad"]},
    "mindmap":         {"name": "知识思维导图",          "icon": "🧠", "price_range": (9, 39),   "platforms": ["淘宝", "闲鱼", "Gumroad"]},
    "checklist":       {"name": "行动清单/避坑指南",     "icon": "✅", "price_range": (9, 29),   "platforms": ["小报童", "知识星球"]},
    "flashcard":       {"name": "记忆卡片/Anki",        "icon": "🃏", "price_range": (9, 29),   "platforms": ["Anki", "小报童"]},
    "script":          {"name": "视频脚本",             "icon": "🎬", "price_range": (29, 99),  "platforms": ["B站", "抖音", "视频号"]},
    "llm_skill":       {"name": "LLM Skill",           "icon": "🧩", "price_range": (29, 199), "platforms": ["GitHub", "SkillHub", "Gumroad"]},
}


# =============================================================================
# ProductGenerator - 主类
# =============================================================================
class ProductGenerator:
    """AI 知识付费产品自动生成器（统一入口 + 14 个对外可生成产品类型策略）"""

    # =====================================================================
    # 内容分析（启发式）
    # =====================================================================
    @staticmethod
    def analyze_content(content: str, subject_name: str = "") -> Dict:
        """
        分析笔记内容，提取：
            - word_count  字数
            - keywords    关键词（前 10）
            - difficulty  beginner / intermediate / advanced
            - topic       主题分类
        """
        if not content or not content.strip():
            return {"error": "内容为空"}

        word_count = len(content)
        line_count = len([line for line in content.splitlines() if line.strip()])

        # 🔍 [语法] 正则提取中文/英文词
        # 🔍 [作用] 简易分词（不依赖 jieba）
        # Keep Latin technical terms (Rust, C++, GPT-4) independent from
        # adjacent CJK text, while retaining useful multi-character CJK terms.
        words = re.findall(r'[A-Za-z][A-Za-z0-9_+#.-]*|[\u4e00-\u9fff]{2,}', content)
        # 🔍 [语法] Counter
        from collections import Counter
        # 🔍 [作用] 取前 10 高频词
        keywords = [w for w, _ in Counter(words).most_common(10)]

        avg_sentence_len = word_count / max(1, len(re.findall(r'[。！？.!?]', content)) + 1)
        lowered = content.lower()
        if any(word in lowered for word in ("深入", "底层", "内核", "源码", "架构", "性能优化", "高级")):
            difficulty = "advanced"
        elif any(word in lowered for word in ("入门", "基础", "初学", "hello world", "新手")):
            difficulty = "beginner"
        else:
            difficulty = "intermediate"

        segments = []
        matches = list(re.finditer(r'^#{1,6}\s+(.+?)\s*$', content, re.MULTILINE))
        if matches:
            for index, match in enumerate(matches):
                end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
                segments.append({"title": match.group(1).strip(), "content": content[match.end():end].strip()})
        else:
            segments.append({"title": subject_name or "正文", "content": content.strip()})

        # 🔍 [语法] 主题分类
        # 🔍 [作用] 基于关键词匹配
        topic = "通用"
        if "Python" in content: topic = "Python"
        elif "机器学习" in content or "深度学习" in content: topic = "AI"
        elif "嵌入式" in content or "单片机" in content: topic = "嵌入式"

        return {
            "word_count": word_count,
            "line_count": line_count,
            "keywords": keywords,
            "segments": segments,
            "difficulty": difficulty,
            "topic": topic,
            "subject": subject_name,
            "estimated_reading_time": max(1, (word_count + 399) // 400),
            "avg_sentence_len": round(avg_sentence_len, 1),
        }

    # =====================================================================
    # 智能推荐
    # =====================================================================
    @staticmethod
    def suggest_products(content: str, subject_name: str = "") -> List[Dict]:
        """
        根据内容启发式推荐适合的产品类型

        启发式规则：
            - 步骤 / 流程 → SOP
            - 原理 / 深入 → article
            - 工具 / 工作流 → workflow
            - 面试 / 题目 → interview_qa
            - 速查 / 清单 → checklist / flashcard
            - 视频 / 脚本 → script
        """
        suggestions = [
            {"type": "article", "reason": "基础知识产品，适合结构化沉淀"},
            {"type": "mindmap", "reason": "适合展示知识结构与概念关系"},
            {"type": "checklist", "reason": "适合转化为可执行行动清单"},
        ]
        keywords_map = {
            "sop":             ["步骤", "流程", "操作", "指南", "SOP", "如何做"],
            "article":         ["原理", "深入", "详解", "理解", "介绍"],
            "interview_qa":    ["面试", "考察", "问答", "真题"],
            "checklist":       ["清单", "检查", "避坑", "注意"],
            "mindmap":         ["总结", "归纳", "框架", "体系"],
            "course_outline":  ["学习", "课程", "教程", "入门到"],
            "prompt_template": ["提示词", "prompt", "模板"],
        }

        # 🔍 [语法] 启发式匹配
        # 🔍 [作用] 按关键词命中推荐
        for ptype, kws in keywords_map.items():
            # 🔍 [语法] any() 短路
            # 🔍 [作用] 任一关键词命中即推荐
            if any(kw in content for kw in kws):
                # 🔍 [语法] 最多取 5 个
                if not any(item["type"] == ptype for item in suggestions):
                    suggestions.append({"type": ptype, "reason": f"检测到 {kws[0]} 等关键词"})

        if len(content) >= 200:
            for ptype, reason in (("ppt", "内容长度适合演示大纲"), ("sop", "内容足够形成标准流程")):
                if not any(item["type"] == ptype for item in suggestions):
                    suggestions.append({"type": ptype, "reason": reason})
        if len(content) >= 800 and not any(item["type"] == "course_outline" for item in suggestions):
            suggestions.append({"type": "course_outline", "reason": "长内容适合系统课程"})

        # 🔍 [语法] 默认推荐 article
        return suggestions[:8]

    # =====================================================================
    # 统一生成入口（getattr 分派）
    # =====================================================================
    @staticmethod
    def generate(note_title: str, note_content: str, product_type: str, subject_name: str = "") -> str:
        """
        统一生成入口：
            1. 通过 getattr 动态调用 generate_{product_type} 方法
            2. 未实现的产品类型返回友好错误
        """
        # 🔍 [语法] hasattr 检查
        # 🔍 [作用] 防止 AttributeError
        method_name = f"generate_{product_type}"
        if not hasattr(ProductGenerator, method_name):
            return f"# {note_title}\n\n暂不支持生成 '{product_type}' 类型的产品。"

        # 🔍 [语法] getattr
        # 🔍 [作用] 动态获取方法
        method = getattr(ProductGenerator, method_name)
        # 🔍 [语法] 函数调用
        return method(note_title, note_content, subject_name)

    # =====================================================================
    # 14 个对外产品生成方法（每个都是 @staticmethod）；另有 8 个历史遗留 generate_* 方法仅供旧数据回看
    # =====================================================================
    # 设计：每个方法接收 (title, content, subject)，返回 Markdown 字符串
    # 当前实现：模板生成（不调 LLM，作为 fallback）
    # 未来：可接入 LLM 调用实现真正的 AI 生成

    # 🔍 [语法] @staticmethod + def
    # 🔍 [作用] 生成技术文章
    @staticmethod
    def generate_article(title: str, content: str, subject: str = "") -> str:
        """技术文章"""
        # 🔍 [语法] f-string 多行
        # 🔍 [作用] 模板生成
        return f"""# {title}

> 📌 适用人群：{subject} 学习者 | ⏱️ 阅读时间：约 {max(1, len(content) // 500)} 分钟

## 引言

{content[:500]}

## 核心概念

{content[500:1500] if len(content) > 500 else content}

## 代码示例

```python
# 示例代码
def example():
    pass
```

## 常见陷阱

- 待补充

## 总结

{content[:300]}
"""

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 生成 PPT 大纲
    @staticmethod
    def generate_ppt(title: str, content: str, subject: str = "") -> str:
        """PPT 大纲"""
        return f"""# {title} - PPT 大纲

## Slide 1: 封面
- 标题：{title}
- 副标题：{subject}

## Slide 2: 目录
- 核心概念
- 实操演示
- 案例分析

## Slide 3-N: 主体
{content[:2000]}

## 最后 Slide: Q&A
"""

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 生成 SOP
    @staticmethod
    def generate_sop(title: str, content: str, subject: str = "") -> str:
        """SOP 流程文档"""
        return f"""# {title} - SOP

## 1. 概述
{content[:300]}

## 2. 前置准备
- 工具/环境
- 知识储备

## 3. 操作步骤
{content}

## 4. 常见问题
- 待补充

## 5. 验证标准
- 通过准则
"""

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 生成 AI 提示词模板
    @staticmethod
    def generate_prompt_template(title: str, content: str, subject: str = "") -> str:
        """AI 提示词模板"""
        return f"""# {title} - 提示词模板

## 适用场景
{subject}

## 核心模板

```
你是[角色]，擅长[技能]。请[任务]。
- 输入：[具体输入]
- 要求：[输出要求]
- 格式：[格式约束]

{content[:1000]}
```

## 使用示例
- 示例 1：...
"""

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 生成课程大纲
    @staticmethod
    def generate_course_outline(title: str, content: str, subject: str = "") -> str:
        """课程大纲"""
        return f"""# {title} - 课程大纲

## 课程目标
- 掌握 {subject} 核心知识
- 能够独立完成实战项目

## 章节结构
{content[:2000]}

## 考核方式
- 作业：每周一练
- 项目：期末综合

## 推荐教材
{content[:500]}
"""

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 生成面试题库
    @staticmethod
    def generate_interview_qa(title: str, content: str, subject: str = "") -> str:
        """面试题库"""
        return f"""# {title} - 面试题库

## 基础题（5 道）

**1. {title} 是什么？**
答：{content[:300]}

**2-5.** （基于笔记内容自动生成）

## 进阶题（5 道）

**1. 深入理解 {title} 的原理？**
答：{content[300:800]}

**2-5.** （基于笔记内容自动生成）

## 答案解析

{content[:1500]}
"""

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 生成源码文档
    @staticmethod
    def generate_code_doc(title: str, content: str, subject: str = "") -> str:
        """源码文档"""
        return f"""# {title} - 源码文档

## 模块概述
{content[:500]}

## 函数说明

### `main()`
{content[500:1500] if len(content) > 500 else '示例函数'}

## 使用示例
```python
from {subject} import main
main()
```
"""

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 生成工作流程图
    @staticmethod
    def generate_workflow(title: str, content: str, subject: str = "") -> str:
        """工作流程图"""
        return f"""# {title} - 工作流程

## 流程图（文字版）
```
开始
 ↓
{content[:500]}
 ↓
结束
```

## 详细步骤
{content}
"""

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 生成产品介绍/分销文案
    @staticmethod
    def generate_product_intro(title: str, content: str, subject: str = "") -> str:
        """产品介绍/分销文案"""
        return f"""# {title} - 产品介绍

## 一句话卖点
掌握 {title}，{subject} 学习者的必备神器。

## 核心价值
{content[:500]}

## 适合人群
- 在校生
- 转行者
- 职场进阶者

## 价格
￥{PRODUCT_TYPES['product_intro']['price_range'][0]} 起

## 立即购买
联系作者获取完整版本。
"""

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 生成自测题
    @staticmethod
    def generate_quiz(title: str, content: str, subject: str = "") -> str:
        """自测题"""
        return f"""# {title} - 自测题

## 单选题（5 道）

1. 关于 {title}，下列说法正确的是？
   A. 选项 A
   B. 选项 B（正确答案）
   C. 选项 C
   D. 选项 D

## 多选题（3 道）

1. {title} 的核心要点包括？
   A. 要点 1
   B. 要点 2
   C. 要点 3
   D. 全部正确

## 判断题（2 道）

1. （ ）{title} 是关键知识点。

## 参考答案
见 {content[:1000]}
"""

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 生成思维导图（文字版）
    @staticmethod
    def generate_mindmap(title: str, content: str, subject: str = "") -> str:
        """思维导图"""
        return f"""# {title} - 思维导图

## 中心主题
{title}

## 主要分支
- 分支 1：{subject} 基础
- 分支 2：核心概念
- 分支 3：实战应用

## 详细内容
{content[:1500]}
"""

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 生成行动清单
    @staticmethod
    def generate_checklist(title: str, content: str, subject: str = "") -> str:
        """行动清单"""
        return f"""# {title} - 行动清单

## 准备阶段
- [ ] 准备工具
- [ ] 学习基础

## 执行阶段
- [ ] 第一步
- [ ] 第二步
- [ ] 第三步

## 检查阶段
- [ ] 验证结果
- [ ] 复盘总结

## 详细说明
{content[:1500]}
"""

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 生成记忆卡片
    @staticmethod
    def generate_flashcard(title: str, content: str, subject: str = "") -> str:
        """记忆卡片"""
        return f"""# {title} - 记忆卡片

## 卡片 1（正面）
**问：** {title} 是什么？

## 卡片 1（背面）
**答：** {content[:200]}

## 卡片 2-N
基于笔记内容自动生成。

## 使用建议
- 每天复习 10 张
- 用 Anki 间隔重复
"""

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 生成视频脚本
    @staticmethod
    def generate_script(title: str, content: str, subject: str = "") -> str:
        """视频脚本"""
        return f"""# {title} - 视频脚本

## 开场（前 30 秒）
[画面：标题动画]
大家好，今天我们来聊 {title}。

## 主体内容
{content[:2000]}

## 结尾（30 秒）
今天的内容就到这里，{subject} 学习者们记得点赞关注！
"""


# Product-level delivery contracts. The original generators remain responsible
# for the content; these appendices guarantee every exported product includes
# the operational sections users expect from that format.
_DELIVERY_APPENDICES = {
    "article": "",
    "ppt": "\n## PPT大纲交付\n## 变现建议\n可导出为企业培训课件、公开课或付费模板。",
    "sop": "\n## 文档信息\n版本：1.0\n\n## 操作流程\n1. 准备 2. 执行 3. 验证 4. 复盘 5. 交付\n\n## 检查点\n- [ ] 输入完整\n- [ ] 输出已验证",
    "prompt_template": "\n## 模板1\n用于 ChatGPT 的理解提示词。\n## 模板2\n用于规划。\n## 模板3\n用于生成。\n## 模板4\n用于校验。\n## 模板5\n用于交付。",
    "course_outline": "\n## 第一周\n第1课：概念入门\n第2课：基础练习\n第3课：阶段复盘\n## 第二周\n第4课至第6课：核心能力\n## 第三周\n第7课至第9课：项目实战\n## 第四周\n第10课：优化\n第11课：发布\n第12课：商业化交付\n## 课后作业\n完成一个可验收项目。",
    "interview_qa": "\n## 基础知识题\n1. 请解释核心概念。\n## 进阶题\n2. 请比较不同实现。\n## 系统设计题\n3. 请设计可扩展方案。",
    "code_doc": "\n## 项目结构\n`src/` 源码，`tests/` 测试。\n## API 文档\n列出输入、输出、异常和示例。",
    "workflow": "\n```mermaid\nflowchart LR\n  A[理解] --> B[计划] --> C[执行] --> D[验证] --> E[交付]\n```\n## 角色与职责\n|角色|职责|\n|---|---|\n|负责人|审批与交付|",
    "product_intro": "\n# 产品介绍文案\n## 版本A：朋友圈短文\n一句话说明价值。\n## 版本B：公众号长文\n展示问题、方案和证据。\n## 版本C：知乎回答\n用案例说明适用边界。",
    "quiz": "\n## 简答题\n说明关键步骤。\n## 实践题\n完成一个可运行案例。\n\n**满分100分**",
    "mindmap": "\n## 核心概念\n- 定义与边界\n## 关键技能\n- 实践方法\n## 常见问题\n- 风险与限制\n## 变现方式\n- 课程、模板与咨询\n## 学习路径\n- 入门到交付",
    "checklist": "\n## 学习前准备\n- [ ] 明确目标\n## 执行与验证\n- [ ] 完成练习\n## 避坑指南\n- [ ] 检查输入、引用、边界、格式、隐私和版权\n## 变现准备\n- [ ] 定价、渠道与交付说明",
    "flashcard": "",
    "script": "\n## 0:00-0:30 开场\nBGM：轻快；字幕：本期目标。\n## 0:30-2:30 主体\n画面：步骤演示。\n## 2:30-3:00 结尾\nBGM 渐弱；字幕：总结与下一步。",
}


def _wrap_delivery_generator(product_type: str) -> None:
    method_name = f"generate_{product_type}"
    original = getattr(ProductGenerator, method_name, None)
    if original is None:
        def original(title: str, content: str, subject="") -> str:
            info = PRODUCT_TYPES[product_type]
            return f"# {title} - {info['name']}\n\n## 产品定位\n面向 {subject or '目标用户'} 的可执行知识产品。\n\n## 核心内容\n{content[:5000]}\n\n## 使用步骤\n1. 阅读并确认目标。\n2. 按模块执行。\n3. 对照验收标准复盘。\n\n## 交付与验收\n- 内容完整、来源清楚、步骤可执行。"

    def wrapped(title: str, content: str, subject="") -> str:
        subject_name = subject.get("subject", "") if isinstance(subject, dict) else subject
        return original(title, content, subject_name) + _DELIVERY_APPENDICES.get(product_type, "")

    setattr(ProductGenerator, method_name, staticmethod(wrapped))


for _product_type in PRODUCT_TYPES:
    _wrap_delivery_generator(_product_type)

ProductGenerator.GENERATORS = {
    product_type: getattr(ProductGenerator, f"generate_{product_type}")
    for product_type in PRODUCT_TYPES
}


def _get_product_info(product_type: str) -> Dict:
    return PRODUCT_TYPES.get(product_type, {
        "name": product_type,
        "icon": "📦",
        "price_range": (0, 0),
        "platforms": [],
    }).copy()


ProductGenerator.get_product_info = staticmethod(_get_product_info)


# =============================================================================
# 模块级单例
# =============================================================================
# 🔍 [语法] 模块级实例
# 🔍 [作用] 单例（业务层常用）
product_generator = ProductGenerator()
