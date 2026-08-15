# 🔍 [语法] 模块级 docstring
# 🔍 [作用] 声明模块用途——大模型"思考过程"清除器
"""
把学习过程变成赚钱过程的app/backend/app/services/reasoning_scrubber.py 模块

模块用途:
    专职清除推理型大模型（DeepSeek-R1 / MiniMax M3 / Qwen-QwQ 等）泄漏到
    对外交付产品正文里的"思考过程"（Chain-of-Thought）。

背景（F02 缺陷复盘）:
    面试题库（interview_qa）等产品出现"大模型把自己的思考过程写进产品"的严重
    质量问题。根因经脏样本复现共 4 条：

    B1. content_polisher._strip_reasoning_blocks 的闭合块正则写作 `<think\\b[^>]*>`，
        `\\b` 是**词边界**；对 `<thinking>` 而言 "think" 后面紧跟单词字符 "i"，
        不构成边界 → 闭合块**匹配失败**。而"孤立标签清理"那一步却能删掉
        `<thinking>` / `</thinking>` 这两个标签本身，于是标签没了、
        **思考过程正文原封不动留在产品里**。

    B2. agentic_product_generator._strip_prompt_leakage 用 `(?is)^.*?(...|硬性要求：)`
        做"腰斩式"清洗。当思维链里复述了提示词关键词时，会从开头斩到该关键词，
        留下**半截思维链** + 一个孤立的 `</think>`；后者被当作"孤立标签"删除，
        思维链残段就此永久留在正文中。

    B3. AI_PREFIX_PATTERNS 的 25 条正则**全部要求以冒号+换行结尾**，因此
        "首先，我需要理解用户提供的笔记内容。" 这类**无标签、无冒号的自然语言
        推理段**一条都命中不了，整段留在产品里。

    B4. 同样是 B2 的腰斩正则：当**产品正文合法地**包含"硬性要求："
        （面试题库的"评分说明"章节极易出现）时，标题和前面所有章节会被
        **整段删除**——这是内容销毁级缺陷，比泄漏更严重。

设计原则:
    1. 分层清洗：标签块 → 孤立闭合标签 → 未闭合开标签 → 残留标签 → 围栏块 → 自然语言序言。
    2. 作用域收敛：自然语言推理只在**首个 Markdown 标题之前的序言区**清洗，
       正文一旦进入标题层级就绝不改动，从根上杜绝 B4 式误删。
    3. 永不清空：清洗后若正文为空而原文非空，则回退原文并置 fallback 标记，
       宁可漏清也不能交付空产品。
"""

# 🔍 [语法] import re
# 🔍 [作用] 正则表达式引擎（本模块全部清洗规则的基础）
import re

# 🔍 [语法] typing 导入
# 🔍 [作用] 类型注解，便于 IDE 与静态检查
from typing import Dict, List, Tuple


# =============================================================================
# 一、推理标签词表
# =============================================================================

# 🔍 [语法] 模块级 tuple（不可变常量）
# 🔍 [作用] 枚举各家推理模型使用的思维链标签名
# 🔍 [陷阱] **顺序极其关键**：正则 `|` 交替是"最左优先"而非"最长优先"。
#          若 "think" 排在 "thinking" 前面，`<thinking>` 会先被 "think" 匹配掉，
#          导致后续 `(?![A-Za-z0-9_-])` 边界断言失败而整体漏匹配。
#          因此**共享前缀的词必须长的在前**：thinking > think、thoughts > thought。
REASONING_TAGS: Tuple[str, ...] = (
    "inner_monologue",   # 部分开源模型使用的"内心独白"标签
    "inner-monologue",   # 同上，连字符变体
    "scratchpad",        # Anthropic 系提示工程常用的草稿纸标签
    "reflection",        # 自反思类模型（Reflection-70B 等）
    "reasoning",         # OpenAI o1 / DeepSeek 兼容层常见
    "rationale",         # 部分评测框架使用
    "thinking",          # ⚠️ 必须排在 "think" 之前
    "thoughts",          # ⚠️ 必须排在 "thought" 之前
    "thought",           # 单数形式
    "analysis",          # gpt-oss harmony 格式的分析通道
    "think",             # DeepSeek-R1 / QwQ 标准标签（最短，放最后）
)

# 🔍 [语法] str.join 生成正则交替分支
# 🔍 [作用] 把词表拼成 "inner_monologue|scratchpad|...|think"
_TAG_ALT = "|".join(REASONING_TAGS)

# 🔍 [语法] 负向先行断言 (?!...)
# 🔍 [作用] 确保标签名后面不再跟"单词字符"，防止 `<thinkx>` 被误判为 `<think>`
# 🔍 [陷阱] 这里**不能**用 `\b`：`\b` 在 `<think用户` 这类"标签名紧跟中文"的畸形
#          输出上表现不稳定（中文是非单词字符，边界成立），而在 `<thinking>` 上
#          又会漏匹配——正是 B1 的成因。改用显式字符类断言，语义清晰可控。
_TAG_BOUNDARY = r"(?![A-Za-z0-9_-])"

# 🔍 [语法] 完整开标签正则：<think ...>
# 🔍 [作用] 匹配带尖括号闭合的规范开标签
_OPEN_TAG = rf"<\s*(?:{_TAG_ALT}){_TAG_BOUNDARY}[^>]*>"

# 🔍 [语法] 完整闭标签正则：</think>
# 🔍 [作用] 匹配规范闭标签
_CLOSE_TAG = rf"<\s*/\s*(?:{_TAG_ALT}){_TAG_BOUNDARY}\s*>"

# 🔍 [语法] re.compile + DOTALL
# 🔍 [作用] 闭合思维链块：<think>……</think>（含换行）
# 🔍 [陷阱] 必须用非贪婪 `.*?`，否则多个思维链块之间的正文会被一起吞掉
_CLOSED_BLOCK_RE = re.compile(rf"{_OPEN_TAG}.*?{_CLOSE_TAG}", re.DOTALL | re.IGNORECASE)

# 🔍 [语法] 预编译
# 🔍 [作用] 单独定位开/闭标签，用于"孤儿标签"判定
_OPEN_TAG_RE = re.compile(_OPEN_TAG, re.IGNORECASE)
_CLOSE_TAG_RE = re.compile(_CLOSE_TAG, re.IGNORECASE)

# 🔍 [语法] 宽松开标签（**不要求**有 `>`）
# 🔍 [作用] 捕捉 `<think用户要求我…` 这类缺失 `>` 的畸形输出
# 🔍 [陷阱] 因为不要求 `>`，误伤面较大，**只允许在文首使用**
_LOOSE_OPEN_RE = re.compile(rf"<\s*(?:{_TAG_ALT}){_TAG_BOUNDARY}", re.IGNORECASE)

# 🔍 [语法] 残留标签清理
# 🔍 [作用] 删除任何形态的孤立推理标签（开或闭）
# 🔍 [陷阱] `[^>\n]*` 而非 `[^>]*`——避免缺 `>` 时跨行吞掉正文
_STRAY_TAG_RE = re.compile(rf"<\s*/?\s*(?:{_TAG_ALT}){_TAG_BOUNDARY}[^>\n]*>?", re.IGNORECASE)

# 🔍 [语法] 围栏代码块
# 🔍 [作用] 删除 ```thinking … ``` 这类"把思维链塞进代码块"的输出
# 🔍 [陷阱] 语言标识必须精确取自词表，绝不能误删 ```python / ```json
_FENCED_BLOCK_RE = re.compile(
    rf"^[ \t]*(?:```|~~~)[ \t]*(?:{_TAG_ALT}){_TAG_BOUNDARY}[^\n]*\n.*?^[ \t]*(?:```|~~~)[ \t]*$",
    re.DOTALL | re.IGNORECASE | re.MULTILINE,
)


# =============================================================================
# 二、自然语言推理信号（无标签思维链）
# =============================================================================

# 🔍 [语法] 模块级 list
# 🔍 [作用] 识别"第一人称元认知"和"复述用户指令"两类推理话术
# 🔍 [陷阱] 这些词在正文里也可能合法出现（例如面试题干"请你说说我们如何优化"），
#          所以**只在序言区生效**，绝不下探到标题之后的正文
NL_REASONING_SIGNALS: List[str] = [
    # ---- 中文：第一人称元认知 ----
    r"我(?:需要|应该|先|来|得|要|打算|会|可以|觉得|认为|想到|想想|考虑|分析|理解|梳理)",
    r"让我(?:们)?(?:想|看|来|先|试|分析|梳理|理一理|捋一捋)",
    r"(?:首先|其次|然后|接下来|最后|那么|现在|所以)[，,]?\s*我",
    # ---- 中文：复述用户/任务指令 ----
    r"用户(?:让我|要我|要求|想要|希望|需要|提到|提供|给出|可能|应该|大概)",
    r"(?:题目|任务|笔记|提示词|指令|prompt)\s*(?:要求|说明|里说|中说|提到)",
    # ---- 中文：元认知自述 ----
    r"(?:思考过程|推理过程|我的思路|解题思路|内心独白|先理一下|整理一下思路)",
    # ---- 中文：口语化起手式（必须在行首） ----
    r"^\s*(?:嗯|唔|哦|噢|好的|好吧|行吧|OK|Okay)\s*[，,、。.!！:：]",
    # ---- 英文：第一人称元认知 ----
    r"\b(?:I|we)\s+(?:need|should|will|must|can|could|have)\s+to\b",
    r"\bI(?:'ll| will| am going to| think| believe| should)\b",
    r"\bLet(?:'s|\s+me|\s+us)\b",
    # ---- 英文：复述用户指令 ----
    r"\bthe user\s+(?:wants|asked|is asking|said|provided|requested|would like)\b",
    # ---- 英文：口语化起手式 ----
    r"^\s*(?:Okay|OK|Alright|Hmm+|Well|So)\s*[,，]",
    r"\bmy\s+(?:plan|approach|thinking|reasoning|strategy)\s+(?:is|here|would be)\b",
]

# 🔍 [语法] 列表推导 + re.compile
# 🔍 [作用] 预编译提升性能（生成任务是批量并发调用）
_NL_SIGNAL_RES = [re.compile(p, re.IGNORECASE) for p in NL_REASONING_SIGNALS]

# 🔍 [语法] 首个 Markdown 标题定位
# 🔍 [作用] 划定"序言区"的右边界——标题之后一律视为正文，不再清洗
_HEADING_RE = re.compile(r"(?m)^#{1,6}\s+\S")

# 🔍 [语法] Markdown 结构行识别
# 🔍 [作用] 表格/列表/引用/代码围栏等结构行**永不删除**，避免破坏真实内容
_STRUCTURAL_LINE_RE = re.compile(r"^\s*(?:#{1,6}\s|[-*+]\s|\d+[.)]\s|>\s|\||```|~~~|!\[|\[)")


# =============================================================================
# 三、对外 API
# =============================================================================

# 🔍 [语法] def + 关键字限定参数（* 之后必须具名传参）
# 🔍 [作用] 主入口：清除内容中的一切"思考过程"痕迹
def scrub_reasoning(content: str, *, scrub_preamble: bool = True) -> Tuple[str, Dict[str, int]]:
    """清除大模型思维链，返回 (清洗后内容, 命中统计)。

    Args:
        content: 大模型原始输出。
        scrub_preamble: 是否清洗"无标签的自然语言推理序言"。
            批量摘要等中间产物可传 False，只做标签级清洗。

    Returns:
        (cleaned, stats)。stats 各键含义见 `_new_stats`。
        当清洗把正文清空时自动回退原文，并置 stats["fallback"] = 1。
    """
    # 🔍 [语法] dict 初始化
    # 🔍 [作用] 建立本次清洗的统计账本
    stats = _new_stats()

    # 🔍 [语法] 短路返回
    # 🔍 [作用] 空串/None 直接原样返回，避免后续正则空转
    if not content:
        return content or "", stats

    # 🔍 [语法] 保留原文引用
    # 🔍 [作用] 供"永不清空"安全阀回退使用
    original = content
    result = content

    # ---- Stage 1：围栏式思维链（```thinking … ```） ----
    # 🔍 [语法] subn 返回 (新串, 替换次数)
    result, n = _FENCED_BLOCK_RE.subn("", result)
    stats["fenced_blocks"] += n

    # ---- Stage 2：闭合标签块（<think>…</think>） ----
    # 🔍 [作用] 修复 B1——显式词表 + 边界断言，<thinking> 不再漏匹配
    result, n = _CLOSED_BLOCK_RE.subn("", result)
    stats["tag_blocks"] += n

    # ---- Stage 3：孤儿闭标签（有 </think> 却没有配对的 <think>） ----
    # 🔍 [作用] 修复 B2——此前腰斩留下的思维链残段，从文首一直切到该闭标签为止
    result, n = _cut_orphan_close(result)
    stats["orphan_cut"] += n

    # ---- Stage 4：文首未闭合开标签（含缺 `>` 的畸形写法） ----
    result, n = _cut_unclosed_open(result)
    stats["unclosed_cut"] += n

    # ---- Stage 5：清理任何残留的孤立标签 ----
    result, n = _STRAY_TAG_RE.subn("", result)
    stats["stray_tags"] += n

    # ---- Stage 6：无标签的自然语言推理序言 ----
    # 🔍 [作用] 修复 B3——"首先，我需要理解…"这类无冒号推理段
    if scrub_preamble:
        result, n = _scrub_preamble(result)
        stats["preamble_lines"] += n

    # ---- Stage 7：安全阀——永不交付空产品 ----
    # 🔍 [语法] 条件回退
    # 🔍 [陷阱] 若清洗规则过激把正文清空，宁可漏清也要回退原文；
    #          调用方可通过 stats["fallback"] 感知并转人工复核
    if not result.strip() and original.strip():
        return original, {**stats, "fallback": 1}

    # 🔍 [语法] strip
    # 🔍 [作用] 去掉清洗留下的首尾空白
    return result.strip(), stats


# 🔍 [语法] def
# 🔍 [作用] 只检测不修改——供 validate() 生成质量问题清单
def detect_reasoning(content: str, *, preamble_only: bool = True) -> List[str]:
    """检测内容中残留的思维链痕迹，返回人类可读的问题描述列表。"""
    # 🔍 [语法] list 初始化
    issues: List[str] = []

    # 🔍 [语法] 空值短路
    if not content:
        return issues

    # 🔍 [语法] 标签检测
    # 🔍 [作用] 只要出现任一推理标签即判定泄漏
    if _STRAY_TAG_RE.search(content):
        issues.append("检测到思维链标签残留（如 <think>/<thinking>）")

    # 🔍 [语法] 序言区切分
    # 🔍 [作用] 自然语言推理只在序言区判定，避免误报正文
    region = _split_preamble(content)[0] if preamble_only else content

    # 🔍 [语法] for + next
    # 🔍 [作用] 命中任一信号即报告一次，不重复刷屏
    for pattern in _NL_SIGNAL_RES:
        match = pattern.search(region)
        if match:
            issues.append(f"检测到未清洗的思考过程：'{match.group(0)[:20]}'")
            break

    return issues


# =============================================================================
# 四、内部实现
# =============================================================================

# 🔍 [语法] def
# 🔍 [作用] 生成统计账本初值（集中定义，避免各处键名写错）
def _new_stats() -> Dict[str, int]:
    return {
        "fenced_blocks": 0,   # 围栏式思维链块数
        "tag_blocks": 0,      # 闭合标签块数
        "orphan_cut": 0,      # 孤儿闭标签腰斩次数
        "unclosed_cut": 0,    # 文首未闭合开标签截断次数
        "stray_tags": 0,      # 残留孤立标签数
        "preamble_lines": 0,  # 被删除的自然语言推理行数
        "fallback": 0,        # 是否触发"永不清空"回退
    }


# 🔍 [语法] def
# 🔍 [作用] 判断"孤儿闭标签之前的内容"是否像未被开标签包裹的思维链残骸
def _looks_like_reasoning_prefix(prefix: str) -> bool:
    """仅当闭标签之前的内容本身像思考过程时，才允许腰斩。"""
    # 🔍 [语法] 空值短路
    stripped = prefix.strip()
    if not stripped:
        return False
    # 🔍 [语法] 还含有开标签变体 → 视为推理
    if _LOOSE_OPEN_RE.search(stripped):
        return True
    # 🔍 [语法] any + 生成器
    # 🔍 [作用] 命中任一自然语言推理信号 → 判定为思维链残骸
    return any(p.search(stripped) for p in _NL_SIGNAL_RES)


# 🔍 [语法] def + Tuple 返回
# 🔍 [作用] 处理"有闭标签、无开标签"的孤儿情况
def _cut_orphan_close(content: str) -> Tuple[str, int]:
    """若首个 </think> 之前不存在 <think>，且该段内容像思维链残骸，则从文首腰斩到该闭标签。"""
    # 🔍 [语法] search 取首个闭标签
    close = _CLOSE_TAG_RE.search(content)
    # 🔍 [语法] 提前返回
    if not close:
        return content, 0

    prefix = content[: close.start()]

    # 🔍 [语法] 在闭标签之前的区间里找开标签
    # 🔍 [作用] 找得到说明是正常配对（Stage 2 已处理过的残余），不做腰斩
    if _OPEN_TAG_RE.search(prefix):
        return content, 0

    # 🔍 [语法] 仅当前缀"本身像思考过程"才腰斩
    # 🔍 [陷阱] 这是 B4 防御的关键：若孤儿闭标签出现在**正文之后**
    #          （如标题/段落里夹杂 </think>），前缀含合法内容，绝不能腰斩，
    #          应交由 Stage 5 仅删标签，避免误删正文
    if _looks_like_reasoning_prefix(prefix):
        return content[close.end():], 1
    return content, 0


# 🔍 [语法] def
# 🔍 [作用] 处理"文首有开标签但全文无闭标签"的截断情况
def _cut_unclosed_open(content: str) -> Tuple[str, int]:
    """文首出现 <think（可能缺 `>`）且无闭合时，切到首个标题或首个空行。"""
    # 🔍 [语法] lstrip
    # 🔍 [作用] 容忍模型在标签前输出的空白
    stripped = content.lstrip()

    # 🔍 [语法] match（锚定开头）+ search（全文）
    # 🔍 [作用] 仅当"开头是推理标签"且"全文无闭标签"时才动手
    if not _LOOSE_OPEN_RE.match(stripped):
        return content, 0
    if _CLOSE_TAG_RE.search(stripped):
        return content, 0

    # 🔍 [语法] 三级降级定位切点
    # 🔍 [作用] 优先切到首个 Markdown 标题（正文最可靠的起点）
    heading = _HEADING_RE.search(stripped)
    if heading:
        return stripped[heading.start():], 1

    # 🔍 [作用] 退而求其次：切到首个空行之后（段落分隔）
    blank = re.search(r"\n\s*\n", stripped)
    if blank:
        return stripped[blank.end():], 1

    # 🔍 [作用] 全文都是思维链——返回空串，由上层安全阀决定是否回退
    return "", 1


# 🔍 [语法] def
# 🔍 [作用] 把内容切成"序言区 / 正文区"两段
def _split_preamble(content: str) -> Tuple[str, str]:
    """以首个 Markdown 标题为界切分；无标题时整篇视为序言区。"""
    # 🔍 [语法] search
    heading = _HEADING_RE.search(content)
    # 🔍 [语法] 条件表达式
    # 🔍 [作用] 有标题 → (标题前, 标题起)；无标题 → (全文, "")
    if heading:
        return content[: heading.start()], content[heading.start():]
    return content, ""


# 🔍 [语法] def
# 🔍 [作用] 清洗序言区里的自然语言推理行
def _scrub_preamble(content: str) -> Tuple[str, int]:
    """删除首个标题之前的推理话术行；正文区一行不动。"""
    # 🔍 [语法] 解包
    preamble, body = _split_preamble(content)

    # 🔍 [语法] 空序言短路
    # 🔍 [作用] 内容本身就以标题开头（绝大多数正常产品）→ 零开销直接返回
    if not preamble.strip():
        return content, 0

    # 🔍 [语法] 分支：无标题时启用保守模式
    # 🔍 [作用] 没有标题就无法界定正文边界，只删"开头连续的推理行"，
    #          遇到第一行正常内容立即停手，防止误删整篇无标题产品
    conservative = not body

    # 🔍 [语法] splitlines(keepends=False)
    lines = preamble.split("\n")
    kept: List[str] = []
    removed = 0
    # 🔍 [语法] 布尔开关
    # 🔍 [作用] 保守模式下，一旦遇到正常内容行就停止清洗
    still_leading = True

    # 🔍 [语法] for 遍历
    for line in lines:
        # 🔍 [语法] 空行处理
        # 🔍 [作用] 空行不参与判定，也不终止保守模式的"前导段"
        if not line.strip():
            kept.append(line)
            continue

        # 🔍 [语法] 结构行保护
        # 🔍 [作用] 表格/列表/引用/代码围栏一律保留，并终止保守模式
        if _STRUCTURAL_LINE_RE.match(line):
            kept.append(line)
            still_leading = False
            continue

        # 🔍 [语法] 保守模式判定
        # 🔍 [作用] 已经越过前导段就不再清洗
        if conservative and not still_leading:
            kept.append(line)
            continue

        # 🔍 [语法] any + 生成器
        # 🔍 [作用] 命中任一推理信号即判定为思考过程
        if any(p.search(line) for p in _NL_SIGNAL_RES):
            removed += 1
            continue

        # 🔍 [作用] 正常内容行：保留，并关闭保守模式的前导窗口
        kept.append(line)
        still_leading = False

    # 🔍 [语法] 未命中直接返回原串
    # 🔍 [作用] 避免无谓的字符串重建
    if removed == 0:
        return content, 0

    # 🔍 [语法] join + lstrip("\n")
    # 🔍 [作用] 重组序言区并压掉删行留下的前导空行
    new_preamble = "\n".join(kept).lstrip("\n")

    # 🔍 [语法] 拼回正文
    # 🔍 [陷阱] 序言区非空时必须补回段落分隔，否则会和标题粘连成一行
    if new_preamble.strip():
        return f"{new_preamble.rstrip()}\n\n{body}", removed
    return body, removed
