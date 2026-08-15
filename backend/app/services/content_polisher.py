# 🔍 [语法] 模块级 docstring（占位）
# 🔍 [作用] 标记模块用途——内容抛光器
"""
把学习过程变成赚钱过程的app/backend/app/services/content_polisher.py 模块

模块用途: TODO 自动扫描生成的占位说明,需要人工补全。
"""
# =============================================================================
# content_polisher.py - 内容抛光器（生成后自动清洗+格式化）
# =============================================================================
# 解决两个核心问题：
#   1. AI 思考过程泄漏到产品中（"Here is the article..." 等）
#   2. Markdown 格式缺陷（代码块未闭合、列表不一致、多余空行等）
# =============================================================================

# 🔍 [语法] import re
# 🔍 [作用] 正则表达式（模式匹配 + 替换）
import re

# 🔍 [语法] import textwrap
# 🔍 [作用] 文本智能排版（本文件未直接使用）
import textwrap

# 🔍 [语法] typing 导入
# 🔍 [作用] 类型注解
from typing import List, Tuple, Optional, Dict

# 🔍 [语法] dataclasses 导入
# 🔍 [作用] 数据类（自动生成 __init__ / __repr__）
from dataclasses import dataclass, field

# 🔍 [语法] 同级模块导入
# 🔍 [作用] 复用推理思维链"只读检测"能力（F02 兜底校验）
# 🔍 [陷阱] reasoning_scrubber 只依赖 re/typing，无循环依赖风险
from .reasoning_scrubber import detect_reasoning


# =============================================================================
# AI 思考过程/解释前缀模式（需要去除）
# =============================================================================
# LLM 常常在生成产品内容之前输出"解释性文字"。这些文字不是产品内容的一部分。

# 🔍 [语法] 模块级 list
# 🔍 [作用] 25+ 前缀正则模式
# 🔍 [陷阱] 顺序敏感（前缀越长越先匹配）
AI_PREFIX_PATTERNS = [
    # ---- 英文模式 ----
    r'^Here\s+is\s+(the|a)\s+.*?[:：]\s*\n',         # "Here is the article:"
    r'^Here\s+are\s+.*?[:：]\s*\n',                   # "Here are the SOPs:"
    r"^I['']ll\s+(create|generate|write|draft).*?[:：]\s*\n",  # "I'll create..."
    r'^Let\s+me\s+(create|generate|write|explain).*?[:：]\s*\n',
    r'^Sure[!，,].*?[:：]\s*\n',
    r'^Certainly[!，,].*?[:：]\s*\n',
    r'^Of\s+course[!，,].*?[:：]\s*\n',
    r'^No\s+problem[!，,].*?[:：]\s*\n',
    r'^Below\s+is\s+.*?[:：]\s*\n',
    # ---- 中文模式 ----
    r'^以下是.*?[：:]\s*\n',
    r'^下面(是|给|为).*?[：:]\s*\n',
    r'^我来.*?(生成|编写|创作).*?[：:]\s*\n',
    r'^这是.*?(生成|编写|创作).*?[：:]\s*\n',
    r'^好的[，,].*?[：:]\s*\n',
    r'^没问题[，,].*?[：:]\s*\n',
    r'^根据.*?[：:]\s*\n',
    r'^为您.*?[：:]\s*\n',
    # ---- 自述/自我思考模式 ----
    r'^备注[：:].*\n',
    r'^注[：:].*\n',
    r'^说明[：:].*\n',
    r'^(\*\*)?注意[：:]\s*.*\n',
    # ---- 无分隔符的元思考 ----
    r'^(好的|当然|没问题|OK|Alright)(\s*[,，。.!！])?\s*$',
]


# 🔍 [语法] 模块级 list
# 🔍 [作用] 末尾 AI 客套话模式
AI_SUFFIX_PATTERNS = [
    r'\n\s*希望.*?(对你|您|你)\s*(有[用所]帮助|有帮助).*$',
    r'\n\s*如果.*?(问题|疑问|需要).*?(随时|请).*$',
    r'\n\s*以上.*?(内容|生成|总结).*$',
    r'\n\s*如有.*?(不当|错误|疏漏).*$',
]


# =============================================================================
# Markdown 格式缺陷修复规则
# =============================================================================

# 🔍 [语法] class
# 🔍 [作用] 内容抛光器（10 步流水线）
class ContentPolisher:
    """内容抛光器：清洗AI解释 + 修复格式缺陷"""

    # 🔍 [语法] __init__
    # 🔍 [作用] 预编译正则（性能优化）
    def __init__(self):
        # 🔍 [语法] 列表推导式 + re.compile
        # 🔍 [作用] 编译为 Pattern 对象（避免每次匹配重新编译）
        self._prefix_patterns = [re.compile(p, re.MULTILINE | re.IGNORECASE) for p in AI_PREFIX_PATTERNS]
        self._suffix_patterns = [re.compile(p, re.MULTILINE | re.IGNORECASE) for p in AI_SUFFIX_PATTERNS]

        # 🔍 [语法] dict 字面量
        # 🔍 [作用] 6 维统计计数
        self.stats = {
            "ai_stripped": 0, "code_fixed": 0, "blank_cleaned": 0,
            "list_fixed": 0, "heading_fixed": 0, "table_fixed": 0,
        }

    # 🔍 [语法] def + Tuple 返回
    # 🔍 [作用] 去除 <think> 块（推理模型）
    def _strip_reasoning_blocks(self, content: str) -> Tuple[str, int]:
        """
        清除推理模型输出的思维链，覆盖三种形态：
          1. 闭合块：<think>...</think>
          2. 未闭合的开头块：<think 在开头但缺 </think>
          3. 残留的孤立标签：<think / </think
        """
        count = 0

        # ---- 形态 1：闭合的 <think...</think> ----
        # 🔍 [语法] re.DOTALL
        # 🔍 [作用] 让 . 匹配换行
        closed = re.compile(r'<think\b[^>]*>.*?</think\s*>', re.DOTALL | re.IGNORECASE)
        # 🔍 [语法] subn 返回 (新内容, 替换次数)
        content, n1 = closed.subn('', content)
        count += n1

        # ---- 形态 2：未闭合的开头块 ----
        # 🔍 [语法] lstrip() 后正则
        # 🔍 [作用] 处理首部空格
        stripped = content.lstrip()
        # 🔍 [语法] 嵌套判断
        # 🔍 [作用] 检测未闭合的 <think
        if re.match(r'<think', stripped, re.IGNORECASE) and not re.search(r'</think', stripped, re.IGNORECASE):
            # 🔍 [语法] 三段优先切
            # 🔍 [作用] 优先切到第一个 # 标题，否则切到第一个空行，否则全切
            heading = re.search(r'(?m)^#{1,6}\s', stripped)
            blank = re.search(r'\n\s*\n', stripped)
            cut = None
            if heading:
                cut = heading.start()
            elif blank:
                cut = blank.end()
            if cut is not None:
                content = stripped[cut:]
            else:
                content = ''  # 全是思维链
            count += 1

        # ---- 形态 3：残留孤立标签 ----
        # 🔍 [语法] [^>\n]*
        # 🔍 [作用] 避免无 > 时吞掉正文
        content, n3 = re.subn(r'</?think[^>\n]*>', '', content, flags=re.IGNORECASE)
        count += n3

        return content, count

    # 🔍 [语法] def 主入口
    # 🔍 [作用] 10 步抛光流水线
    def polish(self, content: str, product_type: str = "", title: str = "") -> Tuple[str, Dict]:
        """
        对生成内容进行全链路抛光（10 步）：
            1. 去除 <think> 块
            2. 去除 AI 解释前缀
            3. 去除 AI 解释后缀
            4. 修复代码块
            5. 清理多余空行
            6. 标准化列表标记
            7. 确保第一行是标题
            8. 去除行尾空白
            9. 修复转义字符
            10. 压缩开头空行 + trim
        """
        # 🔍 [语法] dict 重置
        # 🔍 [作用] 每次抛光前重置统计
        self.stats = {k: 0 for k in self.stats}

        result = content

        # === Step 0: 去除大模型思维链 ===
        # 🔍 [语法] 必须最先执行
        # 🔍 [作用] 思维链常含"用户要求..."等自述
        result, think_count = self._strip_reasoning_blocks(result)
        self.stats["ai_stripped"] += think_count

        # === Step 1: 去除 AI 解释前缀 ===
        # 🔍 [语法] 调用方法
        # 🔍 [作用] 去掉 "Here is..." 等开头套话
        result, prefix_count = self._strip_ai_prefix(result)
        self.stats["ai_stripped"] += prefix_count

        # === Step 2: 去除 AI 解释后缀 ===
        result, suffix_count = self._strip_ai_suffix(result)
        self.stats["ai_stripped"] += suffix_count

        # === Step 3: 修复代码块（未闭合的 ```） ===
        result, code_fixed = self._fix_code_blocks(result)
        self.stats["code_fixed"] += code_fixed

        # === Step 4: 清理多余空行 ===
        result, blank_cleaned = self._normalize_blank_lines(result)
        self.stats["blank_cleaned"] += blank_cleaned

        # === Step 5: 标准化列表标记 ===
        result, list_fixed = self._normalize_list_markers(result)
        self.stats["list_fixed"] += list_fixed

        # === Step 6: 确保第一行是标题 ===
        if title:
            result, heading_fixed = self._ensure_first_heading(result, title)
            self.stats["heading_fixed"] += heading_fixed

        # === Step 7: 去除行尾空白 ===
        result = "\n".join(line.rstrip() for line in result.split("\n"))

        # === Step 8: 修复转义字符 ===
        result = self._fix_escape_artifacts(result)

        # === Step 9: 压缩开头空行 + Step 10: trim ===
        result = result.lstrip("\n").strip()

        return result, dict(self.stats)

    # 🔍 [语法] def
    # 🔍 [作用] 去除 AI 解释前缀
    def _strip_ai_prefix(self, content: str) -> Tuple[str, int]:
        stripped_count = 0
        result = content

        # 🔍 [语法] for + break
        # 🔍 [作用] 只去除一个前缀（避免过度清洗）
        for pattern in self._prefix_patterns:
            before = result
            # 🔍 [语法] count=1
            # 🔍 [作用] 只替换首个匹配
            result = pattern.sub("", result, count=1)
            if result != before:
                stripped_count += 1
                break  # 去除一个前缀后即停止

        # 🔍 [语法] 第一行二次检查
        # 🔍 [作用] 检查首行是否还是 AI 口语化表达
        first_line = result.strip().split("\n")[0].strip() if result.strip() else ""
        if first_line and len(first_line) < 80:
            # 🔍 [语法] 关键词列表
            # 🔍 [作用] 二次检测 AI 套话
            ai_telltales = ["好的", "当然", "没问题", "稍等", "OK", "Alright", "Sure", "Let me", "I'll", "Here is", "Here are"]
            if any(t in first_line for t in ai_telltales):
                lines = result.split("\n", 1)
                if len(lines) > 1:
                    result = lines[1].lstrip("\n")
                    stripped_count += 1

        return result, stripped_count

    # 🔍 [语法] def
    # 🔍 [作用] 去除末尾 AI 客套话
    def _strip_ai_suffix(self, content: str) -> Tuple[str, int]:
        stripped_count = 0
        result = content
        # 🔍 [语法] for 循环
        # 🔍 [作用] 可去除多个后缀
        for pattern in self._suffix_patterns:
            before = result
            result = pattern.sub("", result)
            if result != before:
                stripped_count += 1
        return result, stripped_count

    # 🔍 [语法] def
    # 🔍 [作用] 修复未闭合的代码块
    def _fix_code_blocks(self, content: str) -> Tuple[str, int]:
        # 🔍 [语法] ^``` + MULTILINE
        # 🔍 [作用] 统计行首的 ``` 数量
        backtick_count = len(re.findall(r'^```', content, re.MULTILINE))
        fixed = 0
        # 🔍 [语法] 奇偶判断
        # 🔍 [作用] 奇数个 ``` → 补一个闭合
        if backtick_count % 2 != 0:
            content = content.rstrip() + "\n```"
            fixed = 1
        return content, fixed

    # 🔍 [语法] def
    # 🔍 [作用] 标准化空行（3+ → 1）
    def _normalize_blank_lines(self, content: str) -> Tuple[str, int]:
        result = content
        cleaned = 0
        # 🔍 [语法] re.sub \n{4,}
        # 🔍 [作用] 4+ 连续换行 → 3 换行
        result = re.sub(r'\n{4,}', '\n\n\n', result)
        if result != content:
            cleaned += 1
        # 🔍 [语法] 5+ → 2 换行
        result = re.sub(r'\n{5,}', '\n\n', result)
        return result, cleaned

    # 🔍 [语法] def
    # 🔍 [作用] 标准化无序列表标记（* → -）
    def _normalize_list_markers(self, content: str) -> Tuple[str, int]:
        lines = content.split("\n")
        in_code = False  # 是否在代码块内
        fixed = 0

        for i, line in enumerate(lines):
            # 🔍 [语法] 代码块边界检测
            # 🔍 [作用] 跳过代码块内容
            if line.strip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue

            stripped = line.lstrip()
            # 🔍 [语法] 正则匹配 * 开头
            # 🔍 [作用] 检测 * 开头的列表项
            if re.match(r'^\*\s+', stripped) and not stripped.startswith("**"):
                # 🔍 [语法] 保留缩进
                indent = line[:len(line) - len(stripped)]
                lines[i] = indent + "- " + stripped[2:].lstrip()
                fixed += 1

        return "\n".join(lines), fixed

    # 🔍 [语法] def
    # 🔍 [作用] 确保第一行是标题（如果没有）
    def _ensure_first_heading(self, content: str, title: str) -> Tuple[str, int]:
        stripped = content.strip()
        if not stripped:
            return content, 0

        first_line = stripped.split("\n")[0].strip()

        # 🔍 [语法] 已是标题跳过
        if first_line.startswith("#"):
            return content, 0

        # 🔍 [语法] 引用/表格开头跳过
        if first_line.startswith(">") or first_line.startswith("|"):
            return content, 0
        if not title:
            return content, 0

        # 🔍 [语法] 清除 emoji
        clean_title = title.replace("📝", "").replace("📊", "").replace("📋", "")
        clean_title = clean_title.replace("💡", "").replace("🎓", "")
        clean_title = clean_title.replace("❓", "").replace("💻", "")
        # 🔍 [语法] 清除 [xxx] 标记
        clean_title = re.sub(r'\[.*?\]\s*', '', clean_title).strip()

        # 🔍 [语法] 添加标题
        result = f"# {clean_title}\n\n{stripped}"
        return result, 1

    # 🔍 [语法] def
    # 🔍 [作用] 修复 HTML 实体
    def _fix_escape_artifacts(self, content: str) -> str:
        # 🔍 [语法] replace 链式
        # 🔍 [作用] 5 种常见 HTML 实体
        result = content.replace("&amp;", "&")
        result = result.replace("&lt;", "<")
        result = result.replace("&gt;", ">")
        result = result.replace("&quot;", '"')
        result = result.replace("&#39;", "'")
        return result

    # 🔍 [语法] @staticmethod
    # 🔍 [作用] 静态方法（无需实例化）
    @staticmethod
    def polish_product(content: str, product_type: str, title: str = "") -> Tuple[str, Dict]:
        """对单个产品内容进行抛光（静态方便方法）"""
        polisher = ContentPolisher()
        return polisher.polish(content, product_type, title)

    # 🔍 [语法] def
    # 🔍 [作用] 校验（找问题列表）
    def validate(self, content: str) -> List[str]:
        """快速校验内容是否有明显的格式缺陷"""
        issues = []

        # 🔍 [语法] 检查代码块闭合
        backtick_count = len(re.findall(r'^```', content, re.MULTILINE))
        if backtick_count % 2 != 0:
            issues.append(f"代码块未闭合（{backtick_count}个```）")

        # 🔍 [语法] AI 残余检查
        first_200 = content[:200]
        ai_telltales = ["Here is the", "Here are the", "I'll create", "Let me generate",
                       "以下是", "我来生成", "为您生成", "根据您的要求"]
        for t in ai_telltales:
            if t in first_200:
                issues.append(f"检测到AI解释残余：'{t}'")
                break

        # 🔍 [语法] 长度检查
        if len(content) < 200:
            issues.append(f"内容过短（{len(content)}字）")

        # 🔍 [语法] F02 兜底：推理思维链残留检测（只读，不修改内容）
        # 🔍 [作用] 在多轮抛光之后再次确认没有漏网的思考过程
        # 🔍 [陷阱] 与清洗解耦，只负责"告警"，避免 validate 承担双重职责
        reasoning_issues = detect_reasoning(content)
        if reasoning_issues:
            issues.extend(reasoning_issues)

        return issues
