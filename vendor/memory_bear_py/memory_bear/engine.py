"""
MemoryBear - 类脑分层记忆引擎
================================
基于红熊AI MemoryBear技术原理的Python开源实现。

核心特性:
- 三层/五层类脑分层记忆架构
- 艾宾浩斯遗忘曲线驱动的智能语义剪枝
- 动态知识图谱
- 自我反思引擎
- 记忆路由器（QUICK/DEEP双模式检索）
"""

import os
import sqlite3
import json
import time
import math
import hashlib
import threading
import re
from dataclasses import dataclass, field
from typing import Any, Optional
from collections import OrderedDict
from enum import Enum


# ── 常量 ──────────────────────────────────────────────

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_bear.db")
WORKING_MEMORY_CAPACITY = 10          # 工作记忆容量
SHORT_TERM_TTL_SECONDS = 3600         # 短期记忆 TTL（1小时）
PRUNING_THRESHOLD = 0.05              # 激活度低于此值触发剪枝
REFLECTION_INTERVAL = 300             # 自我反思间隔（秒）
DEFAULT_ACTIVATION = 1.0              # 新记忆初始激活度
DECAY_LAMBDA = 0.0001                 # 艾宾浩斯衰减系数


# ── 数据结构 ──────────────────────────────────────────

@dataclass
class MemoryItem:
    """单条记忆的数据结构"""
    memory_id: str
    content: str
    layer: str = "short_term"      # working / short_term / long_term
    activation: float = DEFAULT_ACTIVATION
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    tags: list = field(default_factory=list)
    source: str = ""               # 来源标注
    importance: float = 1.0        # 初始重要性权重
    embedding: Optional[list] = None  # 可选向量（简化版用关键词代替）

    def to_dict(self) -> dict:
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "layer": self.layer,
            "activation": self.activation,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "tags": json.dumps(self.tags),
            "source": self.source,
            "importance": self.importance,
        }

    @staticmethod
    def from_row(row: tuple) -> "MemoryItem":
        return MemoryItem(
            memory_id=row[0],
            content=row[1],
            layer=row[2],
            activation=row[3],
            created_at=row[4],
            last_accessed=row[5],
            access_count=row[6],
            tags=json.loads(row[7]) if row[7] else [],
            source=row[8] or "",
            importance=row[9] or 1.0,
        )


class RetrievalMode(Enum):
    QUICK = "quick"    # 快速命中（仅搜索工作+短期记忆）
    DEEP = "deep"      # 深度检索（全层搜索+知识图谱推理）


# ── 激活度管理 ────────────────────────────────────────

class ActivationManager:
    """
    基于艾宾浩斯遗忘曲线的激活度管理。
    
    激活度公式: A(t) = A0 * e^(-λ * t)
    其中 t = 当前时间 - 上次访问时间（秒）
    
    被重新访问时：A_new = min(1.0, A_current + boost * importance)
    """

    def __init__(self, decay_lambda: float = DECAY_LAMBDA):
        self.decay_lambda = decay_lambda

    def compute_activation(self, item: MemoryItem, now: float = None) -> float:
        """计算当前激活度"""
        if now is None:
            now = time.time()
        elapsed = max(0, now - item.last_accessed)
        activation = item.activation * math.exp(-self.decay_lambda * elapsed * (1.0 - 0.3 * item.importance))
        return max(0.0, min(1.0, activation))

    def boost(self, item: MemoryItem, boost_amount: float = 0.15) -> float:
        """重新激活记忆"""
        current = self.compute_activation(item)
        new_activation = min(1.0, current + boost_amount * item.importance)
        item.activation = new_activation
        item.last_accessed = time.time()
        item.access_count += 1
        return new_activation

    def should_promote(self, item: MemoryItem, threshold: float = 0.3) -> bool:
        """判断短期记忆是否应提升为长期记忆"""
        return item.access_count >= 3 and self.compute_activation(item) > threshold

    def should_prune(self, item: MemoryItem, threshold: float = PRUNING_THRESHOLD) -> bool:
        """判断记忆是否应被剪枝"""
        return self.compute_activation(item) < threshold


# ── 存储层 ────────────────────────────────────────────

class MemoryStore:
    """基于SQLite的记忆存储"""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_conn()
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    layer TEXT NOT NULL DEFAULT 'short_term',
                    activation REAL DEFAULT 1.0,
                    created_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    tags TEXT DEFAULT '[]',
                    source TEXT DEFAULT '',
                    importance REAL DEFAULT 1.0
                );
                CREATE INDEX IF NOT EXISTS idx_layer ON memories(layer);
                CREATE INDEX IF NOT EXISTS idx_activation ON memories(activation);
                CREATE TABLE IF NOT EXISTS knowledge_graph (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    memory_id TEXT,
                    confidence REAL DEFAULT 1.0,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_kg_subject ON knowledge_graph(subject);
                CREATE INDEX IF NOT EXISTS idx_kg_object ON knowledge_graph(object);
                CREATE TABLE IF NOT EXISTS reflection_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    detail TEXT,
                    created_at REAL NOT NULL
                );
            """)
            conn.commit()
            conn.close()

    def insert(self, item: MemoryItem):
        with self._lock:
            conn = self._get_conn()
            d = item.to_dict()
            conn.execute(
                """INSERT OR REPLACE INTO memories
                   (memory_id, content, layer, activation, created_at,
                    last_accessed, access_count, tags, source, importance)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (d["memory_id"], d["content"], d["layer"], d["activation"],
                 d["created_at"], d["last_accessed"], d["access_count"],
                 d["tags"], d["source"], d["importance"])
            )
            conn.commit()
            conn.close()

    def get(self, memory_id: str) -> Optional[MemoryItem]:
        with self._lock:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT * FROM memories WHERE memory_id=?", (memory_id,)
            ).fetchone()
            conn.close()
            return MemoryItem.from_row(row) if row else None

    def update(self, item: MemoryItem):
        self.insert(item)

    def delete(self, memory_id: str):
        with self._lock:
            conn = self._get_conn()
            conn.execute("DELETE FROM memories WHERE memory_id=?", (memory_id,))
            conn.commit()
            conn.close()

    def list_by_layer(self, layer: str, limit: int = 100) -> list:
        with self._lock:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT * FROM memories WHERE layer=? ORDER BY last_accessed DESC LIMIT ?",
                (layer, limit)
            ).fetchall()
            conn.close()
            return [MemoryItem.from_row(r) for r in rows]

    def list_all(self, limit: int = 500) -> list:
        with self._lock:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY activation DESC LIMIT ?",
                (limit,)
            ).fetchall()
            conn.close()
            return [MemoryItem.from_row(r) for r in rows]

    def search_keyword(self, keyword: str, limit: int = 50) -> list:
        with self._lock:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT * FROM memories WHERE content LIKE ? ORDER BY activation DESC LIMIT ?",
                (f"%{keyword}%", limit)
            ).fetchall()
            conn.close()
            return [MemoryItem.from_row(r) for r in rows]

    def promote_to_long_term(self, item: MemoryItem):
        item.layer = "long_term"
        item.activation = DEFAULT_ACTIVATION
        item.last_accessed = time.time()
        self.update(item)

    def demote_to_short_term(self, item: MemoryItem):
        item.layer = "short_term"
        self.update(item)

    def count(self) -> int:
        with self._lock:
            conn = self._get_conn()
            count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            conn.close()
            return count

    # ── 知识图谱操作 ──

    def add_triple(self, subject: str, predicate: str, obj: str,
                   memory_id: str = "", confidence: float = 1.0):
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                """INSERT INTO knowledge_graph (subject, predicate, object, memory_id, confidence, created_at)
                   VALUES (?,?,?,?,?,?)""",
                (subject, predicate, obj, memory_id, confidence, time.time())
            )
            conn.commit()
            conn.close()

    def query_triples(self, subject: str = None, obj: str = None, limit: int = 20) -> list:
        with self._lock:
            conn = self._get_conn()
            if subject and obj:
                rows = conn.execute(
                    "SELECT * FROM knowledge_graph WHERE subject=? AND object=? LIMIT ?",
                    (subject, obj, limit)
                ).fetchall()
            elif subject:
                rows = conn.execute(
                    "SELECT * FROM knowledge_graph WHERE subject=? LIMIT ?",
                    (subject, limit)
                ).fetchall()
            elif obj:
                rows = conn.execute(
                    "SELECT * FROM knowledge_graph WHERE object=? LIMIT ?",
                    (obj, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM knowledge_graph ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            conn.close()
            return [dict(r) for r in rows]

    def multi_hop(self, start_subject: str, max_hops: int = 2) -> list:
        """多跳推理：从起始实体出发沿知识图谱遍历"""
        results = []
        visited = set()
        current = {start_subject}
        for hop in range(max_hops):
            next_entities = set()
            for entity in current:
                if entity in visited:
                    continue
                visited.add(entity)
                triples = self.query_triples(subject=entity, limit=20)
                for t in triples:
                    results.append({"hop": hop, **t})
                    next_entities.add(t["object"])
            current = next_entities
            if not current:
                break
        return results

    # ── 反思日志 ──

    def log_reflection(self, action: str, detail: str = ""):
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO reflection_log (action, detail, created_at) VALUES (?,?,?)",
                (action, detail, time.time())
            ).fetchone()
            conn.commit()
            conn.close()


# ── 知识图谱 ──────────────────────────────────────────

class KnowledgeGraph:
    """动态知识图谱管理器"""

    def __init__(self, store: MemoryStore):
        self.store = store

    def extract_and_store(self, text: str, memory_id: str = ""):
        """
        从文本中提取实体关系三元组（简化版：基于规则）
        格式: "X 是 Y", "X 的 Z 是 Y", "X 喜欢 Y" 等
        """
        patterns = [
            (r"(.+?)是(.+?)[。，,;；\n]", "是"),
            (r"(.+?)的(.+?)是(.+?)[。，,;；\n]", "property"),
            (r"(.+?)属于(.+?)[。，,;；\n]", "属于"),
            (r"(.+?)位于(.+?)[。，,;；\n]", "位于"),
            (r"(.+?)包含(.+?)[。，,;；\n]", "包含"),
            (r"(.+?)需要(.+?)[。，,;；\n]", "需要"),
            (r"(.+?)偏好(.+?)[。，,;；\n]", "偏好"),
        ]

        for pattern, pred in patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                if pred == "property" and len(m) == 3:
                    self.store.add_triple(
                        m[0].strip(), f"的{m[1].strip()}是", m[2].strip(),
                        memory_id=memory_id
                    )
                elif len(m) == 2:
                    self.store.add_triple(
                        m[0].strip(), pred, m[1].strip(),
                        memory_id=memory_id
                    )

    def multi_hop_infer(self, query_subject: str, max_hops: int = 2) -> list:
        return self.store.multi_hop(query_subject, max_hops)


# ── 剪枝引擎 ──────────────────────────────────────────

class PruningEngine:
    """智能语义剪枝引擎"""

    def __init__(self, store: MemoryStore, act_mgr: ActivationManager):
        self.store = store
        self.act_mgr = act_mgr

    def prune(self, threshold: float = PRUNING_THRESHOLD, dry_run: bool = False) -> list:
        """扫描所有记忆，剪除激活度过低的冗余记忆"""
        all_memories = self.store.list_all(limit=1000)
        pruned = []
        now = time.time()

        for item in all_memories:
            activation = self.act_mgr.compute_activation(item, now)

            # 长期记忆保护：高重要性长期记忆使用更低的剪枝阈值
            effective_threshold = threshold
            if item.layer == "long_term" and item.importance > 0.7:
                effective_threshold = threshold * 0.3

            if activation < effective_threshold:
                pruned.append(item)
                if not dry_run:
                    self.store.delete(item.memory_id)

        return pruned

    def get_stats(self) -> dict:
        """获取记忆统计信息"""
        all_memories = self.store.list_all(limit=1000)
        now = time.time()
        layers = {"working": [], "short_term": [], "long_term": []}
        for item in all_memories:
            item._current_activation = self.act_mgr.compute_activation(item, now)
            if item.layer in layers:
                layers[item.layer].append(item)

        return {
            "total": len(all_memories),
            "by_layer": {k: len(v) for k, v in layers.items()},
            "avg_activation": (
                sum(item._current_activation for item in all_memories) / len(all_memories)
                if all_memories else 0
            ),
            "prunable_count": sum(
                1 for item in all_memories
                if item._current_activation < PRUNING_THRESHOLD
            ),
        }


# ── 自我反思引擎 ──────────────────────────────────────

class ReflectionEngine:
    """
    3D 自我反思引擎。
    四步加工流程：事实合并 → 冲突消解 → 模式抽象 → 摘要回写
    """

    def __init__(self, store: MemoryStore, act_mgr: ActivationManager):
        self.store = store
        self.act_mgr = act_mgr

    def reflect(self):
        """
        在低负载时触发自我反思流程
        """
        memories = self.store.list_all(limit=500)
        if len(memories) < 5:
            return {"merged": 0, "conflicts": 0, "patterns": 0, "abstracted": 0}

        # 1. 事实合并：相似内容合并
        merged = self._merge_similar(memories)

        # 2. 冲突消解：矛盾内容标记
        conflicts = self._resolve_conflicts(memories)

        # 3. 模式抽象：从多次交互中提取行为模式
        patterns = self._abstract_patterns(memories)
        if patterns:
            self.store.log_reflection("patterns_abstracted",
                                      json.dumps(patterns, ensure_ascii=False))

        # 4. 摘要回写：生成高阶摘要记忆
        abstracted = self._write_abstract(memories, patterns)

        return {
            "merged": len(merged),
            "conflicts": len(conflicts),
            "patterns": len(patterns),
            "abstracted": abstracted,
        }

    def _merge_similar(self, memories: list) -> list:
        """合并内容高度相似的记忆（基于Jaccard相似度简化版）"""
        merged = []
        seen = set()
        for i, m1 in enumerate(memories):
            if m1.memory_id in seen:
                continue
            words1 = set(m1.content.lower().split())
            if len(words1) < 3:
                continue
            for j, m2 in enumerate(memories):
                if i >= j or m2.memory_id in seen:
                    continue
                words2 = set(m2.content.lower().split())
                if not words2:
                    continue
                jaccard = len(words1 & words2) / len(words1 | words2)
                if jaccard > 0.7:
                    # 合并：保留较新的那条，提升激活度
                    newer = m1 if m1.created_at > m2.created_at else m2
                    older = m2 if newer is m1 else m1
                    newer.activation = min(1.0, newer.activation + older.activation * 0.3)
                    newer.access_count += older.access_count
                    self.store.update(newer)
                    self.store.delete(older.memory_id)
                    seen.add(older.memory_id)
                    merged.append({"kept": newer.memory_id, "removed": older.memory_id})
        return merged

    def _resolve_conflicts(self, memories: list) -> list:
        """检测矛盾信息并降低冲突记忆的置信度"""
        conflicts = []
        # 简化实现：检查同一实体的互斥描述
        entity_map = {}
        for m in memories:
            kg_triples = self.store.query_triples(subject=m.memory_id, limit=5)
            for t in kg_triples:
                key = (t["subject"], t["predicate"])
                if key not in entity_map:
                    entity_map[key] = []
                entity_map[key].append(t)

        for key, triples in entity_map.items():
            objects = set(t["object"] for t in triples)
            if len(objects) > 1:
                conflicts.append({"entity": key, "conflicting_values": list(objects)})
                # 降低这些三元组的置信度
                for t in triples:
                    self.store.add_triple(
                        t["subject"], t["predicate"], t["object"],
                        confidence=0.5
                    )
        return conflicts

    def _abstract_patterns(self, memories: list) -> list:
        """从记忆序列中抽象行为模式"""
        patterns = []
        memory_texts = [(m.created_at, m.content) for m in memories
                        if m.layer in ("long_term", "short_term")]
        memory_texts.sort(key=lambda x: x[0])

        # 简单模式：检测重复出现的主题
        topic_count = {}
        for _, text in memory_texts[-50:]:
            words = text.lower().split()
            for w in words:
                if len(w) >= 2:
                    topic_count[w] = topic_count.get(w, 0) + 1

        frequent_topics = [(w, c) for w, c in topic_count.items() if c >= 3]
        if frequent_topics:
            frequent_topics.sort(key=lambda x: -x[1])
            top_3 = [t[0] for t in frequent_topics[:3]]
            patterns.append({
                "type": "frequent_topic",
                "topics": top_3,
                "summary": f"用户经常涉及以下主题：{', '.join(top_3)}"
            })

        return patterns

    def _write_abstract(self, memories: list, patterns: list) -> int:
        """将抽象出的模式写回为长期记忆"""
        count = 0
        for p in patterns:
            summary = p.get("summary", "")
            if not summary:
                continue
            mid = hashlib.md5(f"abstract_{summary}".encode()).hexdigest()
            existing = self.store.get(mid)
            if not existing:
                item = MemoryItem(
                    memory_id=mid,
                    content=f"[高阶摘要] {summary}",
                    layer="long_term",
                    importance=0.8,
                    tags=["abstract", "reflection"],
                    source="reflection_engine",
                )
                self.store.insert(item)
                count += 1
        return count


# ── 记忆路由器 ────────────────────────────────────────

class MemoryRouter:
    """
    记忆路由器：智能管理记忆的分块、token限制和上下文。
    支持 QUICK（快速命中）和 DEEP（深度检索）两种模式。
    """

    MAX_CONTEXT_ITEMS = 20
    MAX_CONTEXT_CHARS = 4000

    def __init__(self, store: MemoryStore, act_mgr: ActivationManager):
        self.store = store
        self.act_mgr = act_mgr
        self._context_cache = []

    def route(self, query: str, mode: RetrievalMode = RetrievalMode.QUICK,
              max_items: int = None) -> list:
        """
        根据查询路由到不同记忆层并检索相关记忆。

        QUICK模式：仅搜索工作记忆 + 短期记忆（关键词匹配）
        DEEP模式：全层搜索 + 知识图谱多跳推理
        """
        if max_items is None:
            max_items = self.MAX_CONTEXT_ITEMS

        results = []

        if mode == RetrievalMode.QUICK:
            # 快速命中：关键词搜索短期记忆
            keywords = self._extract_keywords(query)
            for kw in keywords:
                hits = self.store.search_keyword(kw, limit=5)
                for item in hits:
                    if item.layer in ("short_term", "long_term"):
                        item.activation = self.act_mgr.compute_activation(item)
                        results.append(item)
        else:
            # 深度检索：全层搜索 + 知识图谱
            keywords = self._extract_keywords(query)
            for kw in keywords:
                hits = self.store.search_keyword(kw, limit=10)
                for item in hits:
                    item.activation = self.act_mgr.compute_activation(item)
                    results.append(item)
            # 知识图谱多跳推理
            kg_results = self.store.multi_hop(query[:30], max_hops=2)
            for kr in kg_results[:5]:
                if kr.get("memory_id"):
                    mem = self.store.get(kr["memory_id"])
                    if mem:
                        mem.activation = self.act_mgr.compute_activation(mem)
                        results.append(mem)

        # 去重
        seen = set()
        unique = []
        for item in results:
            if item.memory_id not in seen:
                seen.add(item.memory_id)
                unique.append(item)

        # 按激活度排序
        unique.sort(key=lambda x: x.activation, reverse=True)
        return unique[:max_items]

    def build_context(self, retrieved: list, query: str = "") -> str:
        """将检索到的记忆构建为上下文"""
        lines = []
        total_chars = 0
        for item in retrieved:
            text = f"[记忆 | 激活度:{item.activation:.2f}] {item.content}"
            if total_chars + len(text) > self.MAX_CONTEXT_CHARS:
                break
            lines.append(text)
            total_chars += len(text)

        if lines:
            return "### 相关记忆 ###\n" + "\n".join(lines)
        return ""

    @staticmethod
    def _extract_keywords(text: str) -> list:
        """简单关键词提取"""
        stopwords = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
                     "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有",
                     "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些", "什么", "怎么"}
        words = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]+', text)
        keywords = []
        for w in words:
            if w.lower() not in stopwords and len(w) >= 2:
                keywords.append(w)
        # 返回最长的几个关键词（更有区分度）
        keywords.sort(key=len, reverse=True)
        return keywords[:5]


# ── 主引擎 ────────────────────────────────────────────

class MemoryBear:
    """
    MemoryBear 主引擎。
    整合分层记忆存储、激活度管理、知识图谱、剪枝和反思五大模块。
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH, auto_prune: bool = True):
        self.db_path = db_path
        self.store = MemoryStore(db_path)
        self.act_mgr = ActivationManager()
        self.kg = KnowledgeGraph(self.store)
        self.pruner = PruningEngine(self.store, self.act_mgr)
        self.reflector = ReflectionEngine(self.store, self.act_mgr)
        self.router = MemoryRouter(self.store, self.act_mgr)

        # 工作记忆：内存LRU缓存
        self._working_memory = OrderedDict()

        self._auto_prune = auto_prune
        self._last_reflection = time.time()
        self._lock = threading.Lock()

    # ── 记忆写入 ──

    def remember(self, content: str, tags: list = None, importance: float = 1.0,
                 source: str = "", memory_id: str | None = None,
                 layer: str = "short_term") -> MemoryItem:
        """
        存入一条记忆。自动走完整生命周期：
        工作记忆 → 短期记忆 → 长期记忆（条件满足时提升）
        """
        with self._lock:
            if layer not in {"working", "short_term", "long_term"}:
                raise ValueError(f"Unsupported memory layer: {layer}")
            mid = memory_id or hashlib.md5(f"{content}{time.time()}".encode()).hexdigest()[:16]

            item = MemoryItem(
                memory_id=mid,
                content=content,
                layer=layer,
                importance=importance,
                tags=tags or [],
                source=source,
            )

            # 存入短期记忆（SQLite）
            self.store.insert(item)

            # 加入工作记忆缓存
            self._add_to_working(mid, item)

            # 提取知识图谱三元组
            self.kg.extract_and_store(content, mid)

            # 自动剪枝检查
            if self._auto_prune and self.store.count() > 100:
                self.pruner.prune(dry_run=False)

            # 定期自我反思
            if time.time() - self._last_reflection > REFLECTION_INTERVAL:
                self.reflector.reflect()
                self._last_reflection = time.time()

            return item

    def _add_to_working(self, mid: str, item: MemoryItem):
        """加入工作记忆LRU缓存"""
        if mid in self._working_memory:
            self._working_memory.move_to_end(mid)
        else:
            self._working_memory[mid] = item
            if len(self._working_memory) > WORKING_MEMORY_CAPACITY:
                # 淘汰最旧的
                evicted_id, evicted_item = self._working_memory.popitem(last=False)
                # 如果激活度够高，保留在短期记忆中（已经在SQLite里了所以不需要额外操作）

    # ── 记忆召回 ──

    def recall(self, query: str, mode: str = "quick", max_items: int = 10) -> list:
        """
        召回相关记忆。

        Args:
            query: 查询文本
            mode: "quick" 或 "deep"
            max_items: 最大返回条数
        """
        retrieval_mode = RetrievalMode.DEEP if mode == "deep" else RetrievalMode.QUICK
        with self._lock:
            results = self.router.route(query, retrieval_mode, max_items)

            # 提升被命中记忆的激活度
            for item in results:
                self.act_mgr.boost(item)
                self.store.update(item)

                # 检查是否需要提升为长期记忆
                if item.layer == "short_term" and self.act_mgr.should_promote(item):
                    self.store.promote_to_long_term(item)

            return results

    def recall_with_context(self, query: str, mode: str = "quick") -> str:
        """召回记忆并组装为上下文字符串"""
        results = self.recall(query, mode)
        return self.router.build_context(results, query)

    # ── 主动维护 ──

    def prune(self) -> list:
        """手动触发剪枝"""
        with self._lock:
            return self.pruner.prune(dry_run=False)

    def reflect(self) -> dict:
        """手动触发自我反思"""
        with self._lock:
            result = self.reflector.reflect()
            self._last_reflection = time.time()
            return result

    def get_stats(self) -> dict:
        """获取记忆系统统计"""
        with self._lock:
            stats = self.pruner.get_stats()
            stats["working_memory_size"] = len(self._working_memory)
            kg_count = len(self.store.query_triples(limit=1000))
            stats["kg_triples"] = kg_count
            return stats

    # ── 管理接口 ──

    def forget(self, memory_id: str) -> bool:
        """主动遗忘某条记忆"""
        with self._lock:
            item = self.store.get(memory_id)
            if item:
                self.store.delete(memory_id)
                self._working_memory.pop(memory_id, None)
                return True
            return False

    def list_all_memories(self, limit: int = 50) -> list:
        """列出所有记忆"""
        return self.store.list_all(limit)

    def search_memories(self, keyword: str, limit: int = 20) -> list:
        """按关键词搜索记忆"""
        return self.store.search_keyword(keyword, limit)

    def export_stats(self) -> dict:
        """导出完整统计"""
        stats = self.get_stats()
        memories = self.list_all_memories(100)
        stats["memory_sample"] = [
            {"id": m.memory_id, "content": m.content[:80], "layer": m.layer,
             "activation": round(self.act_mgr.compute_activation(m), 3)}
            for m in memories[:10]
        ]
        return stats
