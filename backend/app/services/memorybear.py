"""MemoryBear-inspired long-term memory (5 layers + Ebbinghaus + 3D反熵增).

本模块实现基于《Super Memory 技术调研》提炼的 MemoryBear 核心机制，
与现有 RAG（外部知识检索）并存：MemoryBear 是权威记忆来源（处理历史笔记 /
历史产品 / 用户偏好），RAG 退化为外部知识补丁（techniques 仍保留 rag_grounding
标签，但本次实现不实装真实向量检索）。

核心创新点（与 PDF 对齐）：
1. 五层记忆体系：感知 / 工作 / 情景 / 显性 / 隐性
2. 艾宾浩斯遗忘曲线：分段衰减（1d/7d/30d/90d）
3. 重要性评分：基于编辑次数 + 标签数 + 产品引用
4. 3D 反熵增引擎：事实合并 → 冲突解决 → 模式抽象
5. 记忆路由器：智能分块 + token 限制
6. 场景路由器：根据 query 类型决定 MemoryBear vs RAG 权重
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone


# 中英混合分词：
# - ASCII 词（≥2 字符）
# - CJK 单字（unigram）
# - CJK 二元组（bigram）：解决中文无空格导致整句被当成一个 token 的问题，
#   使重叠度 / 合并 / 冲突检测在中文语料下可正常工作。
def _tokens(text: str) -> set[str]:
    text = text or ""
    words = re.findall(r"[a-zA-Z0-9_]{2,}", text)
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    bigrams = [cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1)]
    return {w.lower() for w in words} | set(cjk) | set(bigrams)


# ---------------------------------------------------------------------------
# 1. 艾宾浩斯遗忘曲线：分段衰减
# 0-1d = 1.0（强记） / 1-7d = 0.7 / 7-30d = 0.4 / 30-90d = 0.2 / >90d = 0.1
# ---------------------------------------------------------------------------
def ebbinghaus_recency(age_days: float) -> float:
    """艾宾浩斯遗忘曲线（分段衰减）。age_days 越大记忆强度越低。"""
    if age_days < 0:
        age_days = 0.0
    if age_days <= 1.0:
        return 1.0
    if age_days <= 7.0:
        return 0.7
    if age_days <= 30.0:
        return 0.4
    if age_days <= 90.0:
        return 0.2
    return 0.1


# ---------------------------------------------------------------------------
# 2. 重要性评分：编辑次数 + 标签数 + 产品引用
# ---------------------------------------------------------------------------
@dataclass
class ImportanceSignals:
    edit_count: int = 0
    tag_count: int = 0
    product_ref_count: int = 0

    def score(self) -> float:
        # 三项加权：编辑 0.5 + 标签 0.2 + 产品引用 0.3
        e = math.tanh(self.edit_count / 5.0)        # 编辑 5 次趋近 1
        t = math.tanh(self.tag_count / 6.0)         # 标签 6 个趋近 1
        p = math.tanh(self.product_ref_count / 3.0)  # 3 个产品引用趋近 1
        return round(0.5 * e + 0.2 * t + 0.3 * p, 4)


def importance_score(item: dict) -> float:
    """从 dict 抽取 importance 信号并打分（0~1）。"""
    return ImportanceSignals(
        edit_count=item.get("edit_count", 0) or 0,
        tag_count=len(item.get("tags") or []),
        product_ref_count=item.get("product_ref_count", 0) or 0,
    ).score()


# ---------------------------------------------------------------------------
# 3. 五层记忆数据类
# ---------------------------------------------------------------------------
@dataclass
class MemoryItem:
    layer: str  # perception / working / episodic / explicit / implicit
    title: str
    content: str
    timestamp: datetime | None = None
    activation: float = 0.0
    relevance: float = 0.0
    recency: float = 0.0
    importance: float = 0.0

    def to_dict(self) -> dict:
        return {
            "layer": self.layer,
            "title": self.title,
            "content": self.content[:1200],  # 单条不超过 1200 字
            "activation": round(self.activation, 4),
            "relevance": round(self.relevance, 4),
            "recency": round(self.recency, 4),
            "importance": round(self.importance, 4),
        }


# ---------------------------------------------------------------------------
# 4. 激活度计算：relevance × recency × importance 三维加权
# ---------------------------------------------------------------------------
WEIGHTS = {"relevance": 0.5, "recency": 0.3, "importance": 0.2}
ACTIVATION_THRESHOLD = 0.08


def compute_activation(relevance: float, recency: float, importance: float) -> float:
    return (
        WEIGHTS["relevance"] * relevance
        + WEIGHTS["recency"] * recency
        + WEIGHTS["importance"] * importance
    )


# ---------------------------------------------------------------------------
# 5. 隐性记忆（用户偏好）：从产品历史 + 标签频次推断
# ---------------------------------------------------------------------------
def derive_implicit_memory(notes: list[dict], products: list[dict]) -> dict:
    """根据用户历史行为推断隐性偏好：常用产品类型 / 常用标签 / 高频科目。"""
    type_counter: Counter[str] = Counter()
    tag_counter: Counter[str] = Counter()
    subject_counter: Counter[str] = Counter()
    for row in products:
        pt = row.get("product_type")
        if pt:
            type_counter[pt] += 1
        for kw in row.get("keywords") or []:
            tag_counter[str(kw)] += 1
        sid = row.get("subject_id")
        if sid is not None:
            subject_counter[str(sid)] += 1
    for row in notes:
        for tag in row.get("tags") or []:
            tag_counter[str(tag)] += 1
    return {
        "top_product_types": [t for t, _ in type_counter.most_common(3)],
        "top_tags": [t for t, _ in tag_counter.most_common(8)],
        "top_subjects": [t for t, _ in subject_counter.most_common(3)],
    }


# ---------------------------------------------------------------------------
# 6. 3D 反熵增引擎：事实合并 → 冲突解决 → 模式抽象
# ---------------------------------------------------------------------------
@dataclass
class EntropyReductionReport:
    merged_groups: int = 0
    conflicts_detected: int = 0
    patterns_abstracted: int = 0
    notes: list[str] = field(default_factory=list)


def fact_merge(episodic_items: list[MemoryItem]) -> list[dict]:
    """事实合并：按标题 token 重叠度把同主题的多条 episodic 聚合成组。

    使用标题而非全文计算重叠度，避免正文稀释主题相似度；
    重叠度 ≥ 0.5（Jaccard on title tokens）即判定为同主题合并。
    """
    if not episodic_items:
        return []
    title_tokens: list[set[str]] = [_tokens(item.title) for item in episodic_items]
    parent = list(range(len(episodic_items)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for i in range(len(episodic_items)):
        for j in range(i + 1, len(episodic_items)):
            a, b = title_tokens[i], title_tokens[j]
            if not a or not b:
                continue
            overlap = len(a & b) / min(len(a), len(b))
            if overlap >= 0.5:  # 50% 标题主题重叠 → 合并
                union(i, j)

    groups: dict[int, list[int]] = {}
    for idx in range(len(episodic_items)):
        groups.setdefault(find(idx), []).append(idx)

    merged: list[dict] = []
    for root_idx, members in groups.items():
        if len(members) == 1:
            item = episodic_items[members[0]]
            merged.append({"topic": item.title, "items": [item.title]})
        else:
            merged.append({
                "topic": episodic_items[root_idx].title,
                "items": [episodic_items[m].title for m in members],
            })
    return merged


def conflict_detect(episodic_items: list[MemoryItem]) -> list[str]:
    """冲突解决：检测同主题不同笔记的明显冲突（标题前缀相同但内容差异大）。

    用 token 集合的对称差 / 并集比例衡量差异，比例 > 0.5 视为冲突。
    """
    conflicts: list[str] = []
    token_sets = [_tokens(f"{i.title} {i.content}") for i in episodic_items]
    for i in range(len(episodic_items)):
        for j in range(i + 1, len(episodic_items)):
            a, b = episodic_items[i], episodic_items[j]
            if a.title.split(" - ")[0] != b.title.split(" - ")[0]:
                continue
            ta, tb = token_sets[i], token_sets[j]
            if not ta or not tb:
                continue
            sym = len(ta ^ tb)
            union = len(ta | tb)
            if union and sym / union > 0.5:
                conflicts.append(f"{a.title!r} 与 {b.title!r} 内容存在差异")
    return conflicts


def pattern_abstract(episodic_items: list[MemoryItem]) -> list[str]:
    """模式抽象：从高频 episodic title 中抽取共同主题关键词。"""
    title_tokens: list[set[str]] = [_tokens(item.title) for item in episodic_items]
    common: set[str] = set(title_tokens[0]) if title_tokens else set()
    for ts in title_tokens[1:]:
        common &= ts
    # 至少 2 条笔记共有的 token 才视为"模式"
    if len(episodic_items) >= 2:
        return sorted(common)[:5]
    return []


def run_entropy_engine(episodic_items: list[MemoryItem]) -> EntropyReductionReport:
    """3D 反熵增引擎主入口：事实合并 → 冲突解决 → 模式抽象。"""
    merged = fact_merge(episodic_items)
    conflicts = conflict_detect(episodic_items)
    patterns = pattern_abstract(episodic_items)
    notes: list[str] = []
    if len(merged) < len(episodic_items):
        notes.append(f"事实合并：{len(episodic_items)} 条 → {len(merged)} 组")
    if conflicts:
        notes.append(f"冲突检测：发现 {len(conflicts)} 处差异")
    if patterns:
        notes.append(f"模式抽象：抽出共同主题 {patterns[:3]}")
    return EntropyReductionReport(
        merged_groups=len(merged),
        conflicts_detected=len(conflicts),
        patterns_abstracted=len(patterns),
        notes=notes,
    )


# ---------------------------------------------------------------------------
# 7. 记忆路由器：智能分块 + token 限制
# ---------------------------------------------------------------------------
@dataclass
class MemoryRouterConfig:
    """路由器配置：每层最大条目数 + 总 token 上限。"""
    max_per_layer: dict[str, int] = field(default_factory=lambda: {
        "perception": 0,    # 本次不实装感知层
        "working": 1,
        "episodic": 6,
        "explicit": 4,
        "implicit": 1,
    })
    max_total_chars: int = 10000  # prompt 注入字符上限


def route_memory(items: list[MemoryItem], config: MemoryRouterConfig | None = None) -> list[MemoryItem]:
    """记忆路由器：按层限额 + 总字符上限裁剪。"""
    cfg = config or MemoryRouterConfig()
    by_layer: dict[str, list[MemoryItem]] = {}
    for item in items:
        by_layer.setdefault(item.layer, []).append(item)
    selected: list[MemoryItem] = []
    for layer, group in by_layer.items():
        configured = cfg.max_per_layer.get(layer, 0)
        if layer in {"episodic", "explicit"}:
            adaptive = max(1, (len(group) + 1) // 2) if group else 0
            limit = min(configured, adaptive)
        else:
            limit = configured
        group_sorted = sorted(group, key=lambda x: x.activation, reverse=True)
        selected.extend(group_sorted[:limit])
    selected.sort(key=lambda x: x.activation, reverse=True)
    # 总字符上限裁剪
    total = 0
    pruned: list[MemoryItem] = []
    for item in selected:
        projected = total + len(item.content[:1200])
        if projected > cfg.max_total_chars:
            continue
        pruned.append(item)
        total = projected
    return pruned


# ---------------------------------------------------------------------------
# 8. 场景路由器：决定 MemoryBear vs RAG 权重
# ---------------------------------------------------------------------------
@dataclass
class SceneRouterDecision:
    memorybear_weight: float  # 0~1
    rag_weight: float         # 0~1
    reason: str


def route_scene(note: dict, notes: list[dict], products: list[dict]) -> SceneRouterDecision:
    """根据任务特征决定 MemoryBear vs RAG 权重。

    启发式：
    - 有 ≥ 2 条历史笔记或 ≥ 1 个产品 → MemoryBear 主导（0.8 / 0.2）
    - 笔记很新 + 知识库查询关键词明显 → RAG 主导（0.3 / 0.7）
    - 其他 → 平衡（0.5 / 0.5）
    """
    external_keywords = {"定义", "是什么", "原理", "教程", "入门", "API", "manual", "spec"}
    query = f"{note.get('title', '')} {note.get('raw_content') or note.get('content', '')}".lower()
    if any(kw.lower() in query for kw in external_keywords):
        return SceneRouterDecision(0.3, 0.7, "外部知识查询，RAG 主导")
    history_signal = min(1.0, (len(notes) / 4) + min(0.4, len(products) * 0.2))
    memory_weight = round(max(0.2, min(0.8, 0.2 + history_signal * 0.6)), 2)
    return SceneRouterDecision(memory_weight, round(1.0 - memory_weight, 2), "按历史记忆量动态混合")


# ---------------------------------------------------------------------------
# 9. 主入口：build_memory_context（升级版，5 层 + 3D 反熵增）
# ---------------------------------------------------------------------------
def build_memory_context(
    note: dict,
    subject: dict | None,
    notes: list[dict],
    products: list[dict],
    limit: int = 8,
) -> tuple[str, dict]:
    """构建五层记忆上下文（升级版），与 RAG 并存。

    Returns:
        (context_str, meta_dict) — context_str 已路由+裁剪，meta_dict 含各层统计。
    """
    query_tokens = _tokens(f"{note.get('title', '')} {note.get('raw_content') or note.get('content', '')}")
    # 注意：cloud_db 存储的 created_at/updated_at 为 naive 本地 ISO 字符串，
    # 故 now 也用 naive 本地时间，避免 aware/naive 相减报错。
    now = datetime.now()

    items: list[MemoryItem] = []

    # ---- 工作记忆：当前笔记主题（始终 1 条）----
    # 注意：工作记忆只放"结构化元数据"（标题/科目/标签/学习阶段），
    # 不放正文全量——正文由生成器的 source_brief（_build_source_memory）单一负责注入，
    # 避免同一篇笔记正文被 MemoryBear 与 source_brief 双重注入导致产品内容重复。
    working_content = (
        f"标题：{note.get('title', '当前笔记')}\n"
        f"科目：{(subject or {}).get('name', '')}\n"
        f"学习阶段：{note.get('learning_stage', 'stage1')}\n"
        f"标签：{', '.join(note.get('tags') or [])}\n"
        f"正文字符数：{len((note.get('raw_content') or note.get('content', '')) or '')}"
    )
    items.append(MemoryItem(
        layer="working",
        title=note.get("title", "当前笔记"),
        content=working_content,
        timestamp=_parse_ts(note.get("updated_at") or note.get("created_at")),
        activation=1.0,
    ))

    # ---- 情景记忆：其他历史笔记 ----
    for row in notes:
        if row.get("id") == note.get("id"):
            continue
        item = _score_item("episodic", row, query_tokens, now)
        if item and item.activation >= ACTIVATION_THRESHOLD:
            items.append(item)

    # ---- 显性记忆：历史产品 ----
    for row in products:
        item = _score_item("explicit", row, query_tokens, now)
        if item and item.activation >= ACTIVATION_THRESHOLD:
            items.append(item)

    # ---- 隐性记忆：用户偏好 ----
    implicit = derive_implicit_memory(notes, products)
    if implicit and (implicit["top_product_types"] or implicit["top_tags"]):
        items.append(MemoryItem(
            layer="implicit",
            title="用户偏好",
            content=(
                f"常用产品类型：{', '.join(implicit['top_product_types'])}\n"
                f"常用标签：{', '.join(implicit['top_tags'])}\n"
                f"高频科目：{', '.join(implicit['top_subjects'])}"
            ),
            timestamp=now,
            activation=0.5,
        ))

    # ---- 3D 反熵增引擎 ----
    episodic_items = [i for i in items if i.layer == "episodic"]
    entropy = run_entropy_engine(episodic_items)

    # ---- 记忆路由器 ----
    routed = route_memory(items)

    # ---- 场景路由器 ----
    scene = route_scene(note, notes, products)

    # ---- 组装 prompt ----
    # 工作记忆仅含结构化元数据（标题/科目/阶段/标签/字符数），正文由 source_brief 单独注入，
    # 这里不再重复正文，避免生成时同一笔记内容被双重注入产生重复。
    sections = []
    if routed:
        sections.append(f"## 工作记忆（当前主题）\n{routed[0].content}")
    for item in routed[1:]:
        sections.append(f"## {item.layer}记忆：{item.title}\n{item.content}")

    entropy_notes = entropy.notes or (
        [f"情景记忆 {len(episodic_items)} 条，已压缩为 {entropy.merged_groups} 组"]
        if episodic_items else []
    )
    if entropy_notes:
        sections.append("## 3D 反熵增引擎（已压缩记忆）\n" + "\n".join(entropy_notes))

    sections.append(
        f"## 场景路由\nMemoryBear 权重={scene.memorybear_weight} | RAG 权重={scene.rag_weight}\n"
        f"原因：{scene.reason}\n"
        f"说明：MemoryBear 为权威记忆来源，RAG 仅作外部知识补丁（暂未实装真实 KB 检索）"
    )

    meta = {
        "layers": {
            "working": 1 if any(i.layer == "working" for i in routed) else 0,
            "episodic": sum(1 for i in routed if i.layer == "episodic"),
            "explicit": sum(1 for i in routed if i.layer == "explicit"),
            "implicit": sum(1 for i in routed if i.layer == "implicit"),
        },
        "pruned": max(0, len(items) - len(routed)),
        "entropy": {
            "merged_groups": entropy.merged_groups,
            "conflicts_detected": entropy.conflicts_detected,
            "patterns_abstracted": entropy.patterns_abstracted,
            "notes": entropy.notes,
        },
        "scene_router": {
            "memorybear_weight": scene.memorybear_weight,
            "rag_weight": scene.rag_weight,
            "reason": scene.reason,
        },
    }
    return "\n\n".join(sections)[:10000], meta


# ---------------------------------------------------------------------------
# 10. 辅助：打分 + 时间解析
# ---------------------------------------------------------------------------
def _score_item(layer: str, row: dict, query_tokens: set[str], now: datetime) -> MemoryItem | None:
    title = row.get("title", f"历史{layer}")
    content = row.get("raw_content") or row.get("content", "")
    if not content:
        return None
    words = _tokens(f"{title} {content}")
    if not words:
        return None
    relevance = len(query_tokens & words) / max(1, len(query_tokens))
    timestamp = _parse_ts(row.get("updated_at") or row.get("created_at"))
    if timestamp is None:
        return None
    age_days = max(0.0, (now - timestamp).total_seconds() / 86400)
    recency = ebbinghaus_recency(age_days)
    importance = importance_score(row)
    # 相关性门控：零相关记忆（与当前主题无关）应被修剪，仅当极近且重要才保留。
    # 这就是 MemoryBear 的"遗忘无关噪音"机制——relevance=0 时激活度被打到很低。
    if relevance <= 0.0:
        activation = 0.1 * recency * (0.3 + 0.7 * importance)
    else:
        activation = compute_activation(relevance, recency, importance)
    return MemoryItem(
        layer=layer,
        title=title,
        content=content,
        timestamp=timestamp,
        activation=activation,
        relevance=relevance,
        recency=recency,
        importance=importance,
    )


def _parse_ts(value) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        # 统一返回 naive 本地时间，避免与 naive now 相减报错。
        return dt.replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 11. 统计接口（供 router 调用）
# ---------------------------------------------------------------------------
def memorybear_stats(notes: list[dict], products: list[dict]) -> dict:
    """聚合统计：各层条目数 + 重要性分布 + 冲突点。"""
    now = datetime.now()
    layers = {"working": 0, "episodic": 0, "explicit": 0, "implicit": 0}
    importance_distribution = {"high": 0, "medium": 0, "low": 0}
    conflict_points: list[str] = []
    episodic_items: list[MemoryItem] = []

    for row in notes:
        timestamp = _parse_ts(row.get("updated_at") or row.get("created_at"))
        if not timestamp:
            continue
        layers["episodic"] += 1
        item = MemoryItem(
            layer="episodic",
            title=row.get("title", "笔记"),
            content=row.get("raw_content") or row.get("content", ""),
            timestamp=timestamp,
            importance=importance_score(row),
        )
        episodic_items.append(item)
        bucket = "high" if item.importance >= 0.6 else "medium" if item.importance >= 0.3 else "low"
        importance_distribution[bucket] += 1

    for row in products:
        layers["explicit"] += 1

    if implicit := derive_implicit_memory(notes, products):
        if implicit["top_product_types"] or implicit["top_tags"]:
            layers["implicit"] = 1

    entropy = run_entropy_engine(episodic_items)
    conflict_points = conflict_detect(episodic_items)[:5]  # 最多 5 条

    return {
        "layers": layers,
        "total_items": sum(layers.values()),
        "importance_distribution": importance_distribution,
        "entropy": {
            "merged_groups": entropy.merged_groups,
            "conflicts_detected": entropy.conflicts_detected,
            "patterns_abstracted": entropy.patterns_abstracted,
        },
        "conflict_points": conflict_points,
        "timestamp": now.isoformat(),
    }
