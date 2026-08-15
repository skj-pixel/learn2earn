# MemoryBear 与 RAG 混合检索架构

> 适用版本：F04 `strategy_compat` 引入后（与《自由组合策略原理》互为姊妹篇）
> 目标：说明 Learn2Earn 的「长期记忆」是怎么设计的——为什么 MemoryBear 是**权威记忆来源**，而 RAG 退化为**外部知识补丁**；二者如何共存、如何被策略路由、如何注入生成管线。

---

## 1. 一句话结论

Learn2Earn 把"记忆"拆成两条互补通道：

- **MemoryBear（权威记忆来源）**：处理**用户自己的、已验证过的知识资产**——历史笔记、历史产品、用户偏好。它是"自己脑子里的东西"，优先级最高。
- **RAG（外部知识补丁）**：处理**外部、需实时检索的常识 / 百科 / 文档**（如"什么是 X""API 文档"）。它是"临时查的参考资料"，优先级低、仅作补充。

两条通道在 `techniques` 维度上以独立的开关存在（`memorybear` 与 `rag_grounding`），由**场景路由器**动态决定权重。**本仓库当前实装了 MemoryBear 全链路，RAG 仅保留接口与路由占位，未接入真实向量库**——这是有意为之：参赛演示场景下，用户自己的学习资产远比外部检索更有说服力。

```
        ┌──────────────────────────┐      ┌──────────────────────────┐
        │   MemoryBear 长期记忆       │      │   RAG 外部知识检索        │
        │  （权威记忆来源 / 高权重）  │      │  （外部知识补丁 / 低权重） │
        │                            │      │                            │
        │  历史笔记 / 历史产品 / 偏好  │      │  定义 / 原理 / 教程 / API  │
        └────────────┬───────────────┘      └─────────────┬──────────────┘
                     │                                     │
                     └──────────────┬──────────────────────┘
                                    ▼
                         route_scene() 场景路由器
                         （MemoryBear 0.8 / RAG 0.2 等）
                                    ▼
                    build_memory_context() 五层组装 + 3D 反熵增
                                    ▼
          prompt 注入：## MemoryBear 长期记忆（权威记忆来源）
```

---

## 2. MemoryBear 的五层记忆体系

模块 `backend/app/services/memorybear.py` 实现了一套受《Super Memory 技术调研》启发的分层记忆模型。每一层回答一个问题：**"这条记忆属于什么性质？该给它多少注意力？"**

| 层（layer） | 含义 | 数据来源 | 路由上限 |
|---|---|---|---|
| `perception` 感知 | 原始感官输入（本次未实装） | — | 0 |
| `working` 工作 | 当前正在处理的笔记主题（结构化元数据） | 当前 note 的标题/科目/阶段/标签 | 1 |
| `episodic` 情景 | 其他历史笔记（与当前主题相关者） | `notes`（排除当前） | 6 |
| `explicit` 显性 | 历史已生成的产品 | `products` | 4 |
| `implicit` 隐性 | 从行为推断出的用户偏好 | `derive_implicit_memory()` | 1 |

**关键设计决策**：工作记忆**只放结构化元数据，不放笔记正文**。正文由生成器的 `_build_source_memory()` → `source_brief` **单一负责注入**。这样能避免"同一篇笔记正文被 MemoryBear 与 source_brief 双重注入导致产品内容重复"——这是早期版本的一个真实 bug，已通过职责分离根治。

---

## 3. 三维激活度：相关性 × 近因 × 重要性

记忆不是"存了就有用"，而是"相关才激活"。MemoryBear 用三维加权打分，决定一条记忆最终是否进 prompt、排第几位。

### 3.1 近因（recency）—— 艾宾浩斯遗忘曲线

`ebbinghaus_recency(age_days)` 用**分段衰减**而非连续指数，模拟"刚学完最牢、一周后快速下滑、三个月后基本定型"：

```
0–1d  = 1.0   (刚记，强)
1–7d  = 0.7   (一周内)
7–30d = 0.4   (一月内)
30–90d= 0.2   (一季内)
>90d  = 0.1   (久远的)
```

### 3.2 重要性（importance）—— 行为信号打分

`importance_score(item)` 从 dict 抽取三类信号，经 `tanh` 压缩到 0~1 后加权：

- 编辑次数 `edit_count`（×0.5，5 次编辑趋近 1）
- 标签数 `tag_count`（×0.2，6 个标签趋近 1）
- 产品引用数 `product_ref_count`（×0.3，3 次引用趋近 1）

```python
def score(self) -> float:
    e = math.tanh(self.edit_count / 5.0)
    t = math.tanh(self.tag_count / 6.0)
    p = math.tanh(self.product_ref_count / 3.0)
    return round(0.5 * e + 0.2 * t + 0.3 * p, 4)
```

### 3.3 相关性（relevance）—— 与当前主题的 token 重叠

`relevance = |query_tokens ∩ item_tokens| / |query_tokens|`。

**遗忘无关噪音机制**：当 `relevance == 0`（与当前主题毫无交集）时，激活度被打到 `0.1 × recency × (0.3 + 0.7×importance)`——极低，保证"再重要也别来打扰当前主题"。这对应人类"需要时想得起来、不需要时不占用注意力"的特性。

### 3.4 三维加权汇总

```python
WEIGHTS = {"relevance": 0.5, "recency": 0.3, "importance": 0.2}
ACTIVATION_THRESHOLD = 0.08

def compute_activation(relevance, recency, importance) -> float:
    return 0.5*relevance + 0.3*recency + 0.2*importance
```

- 相关性权重最高（0.5）：记忆首先得"对题"。
- 低于 `ACTIVATION_THRESHOLD=0.08` 的记忆在 `_score_item` 阶段直接丢弃，不进后续路由。

---

## 4. 3D 反熵增引擎：事实合并 → 冲突解决 → 模式抽象

记忆会随时间"熵增"（碎片化、互相矛盾、淹没重点）。`run_entropy_engine()` 是压缩记忆、对抗熵增的核心。

### 4.1 事实合并 `fact_merge`

按**标题 token 重叠度（Jaccard）≥ 0.5** 把同主题的多条情景记忆聚合成组（并查集实现）。用标题而非全文算重叠，避免正文稀释主题相似度。

```python
overlap = len(a & b) / min(len(a), len(b))
if overlap >= 0.5:  # 50% 标题主题重叠 → 合并
    union(i, j)
```

### 4.2 冲突解决 `conflict_detect`

检测"标题前缀相同但内容差异大"的明显矛盾：对同组记忆算 token 对称差 / 并集，比例 > 0.5 视为冲突，返回人类可读的告警文本。

```python
sym = len(ta ^ tb); union = len(ta | tb)
if union and sym / union > 0.5:
    conflicts.append(f"{a.title!r} 与 {b.title!r} 内容存在差异")
```

### 4.3 模式抽象 `pattern_abstract`

从高频情景标题中抽取"≥2 条笔记共有的 token"，得到共同主题关键词（最多 5 个），用于给 LLM 提示"用户反复在学什么"。

### 4.4 报告 `EntropyReductionReport`

```python
@dataclass
class EntropyReductionReport:
    merged_groups: int = 0         # 合并后组数
    conflicts_detected: int = 0    # 检出冲突数
    patterns_abstracted: int = 0   # 抽象出模式数
    notes: list[str] = ...         # 人类可读摘要
```

---

## 5. 记忆路由器与场景路由器

### 5.1 记忆路由器 `route_memory`

按层限额（`MemoryRouterConfig.max_per_layer`）+ 总字符上限（`max_total_chars=10000`）裁剪。先按层内激活度排序取 top-N，再按激活度全局排序，最后做字符预算裁剪，保证 prompt 不爆。

### 5.2 场景路由器 `route_scene` —— MemoryBear vs RAG 的权重开关

这是"混合检索"的指挥中枢。启发式规则：

| 触发条件 | MemoryBear 权重 | RAG 权重 | 原因 |
|---|---|---|---|
| 历史笔记 ≥ 2 或 已有产品 | 0.8 | 0.2 | 历史记忆充足，用户自己的资产主导 |
| query 含外部关键词（定义/原理/教程/API…） | 0.3 | 0.7 | 明显在查外部知识，RAG 主导 |
| 其他 | 0.5 | 0.5 | 平衡混合 |

```python
@dataclass
class SceneRouterDecision:
    memorybear_weight: float
    rag_weight: float
    reason: str
```

> 注意：本仓库 RAG 分支当前是**占位**。即使路由判定 RAG=0.7，也只是把"RAG 权重"写进 `scene_router.meta` 供前端展示；真正的内容仍由 MemoryBear + `source_brief` 提供。后续接入真实向量库时，只需在 `route_scene` 返回高 RAG 权重的分支里补一段 KB 检索，架构无需改动。

---

## 6. 与质量增强技术（techniques）的关系

`techniques` 维度上有三个与"记忆/检索"相关的开关，它们**彼此独立、正交叠加**：

| technique | 性质 | 在管线中的位置 |
|---|---|---|
| `memorybear` | 长期记忆（权威来源） | `generation_task_service`：若包含 `memorybear`，调用 `build_memory_context()` 拼到 prompt 头部 |
| `source_grounding` | 源笔记约束（反幻觉锚点） | `agentic_product_generator._build_source_memory()` → `source_brief`，把**当前笔记正文**作为强约束注入 |
| `rag_grounding` | RAG 原文检索（外部补丁） | 已在 `DEFAULT_STRATEGIES` 注册为可选 technique，但本仓库未实装真实检索 |

**三者分工不冲突**：

- `source_grounding` = "**锁死原文**"（当前这篇笔记不能胡编）—— 反幻觉的地基。
- `memorybear` = "**带上历史**"（你以前学过/做过什么、你的偏好）—— 让产品有连续性与个人味。
- `rag_grounding` = "**补外部常识**"（这概念的定义/原理）—— 仅在用户明显在查外部知识时加权。

代码注入点（`generation_task_service.py`）：

```python
if "memorybear" in techniques:
    memory_context, memory_meta = build_memory_context(
        note, subject, table("notes", user).list(), table("products", user).list()
    )
    prompt = f"{prompt}\n\n## MemoryBear 长期记忆（权威记忆来源，优先遵循用户历史偏好与已验证知识）\n{memory_context}"
```

注入位置刻意放在 prompt **头部**并标注"权威记忆来源"，使 LLM 倾向于**优先遵循用户历史**而非凭空发挥——这是 MemoryBear 对抗幻觉的第二道保险（第一道是 `source_grounding` 锁死原文）。

---

## 7. 对外接口

`backend/app/routers/memorybear.py` 暴露：

- `POST /api/memorybear/context` —— 给定 note 返回 `build_memory_context()` 的 `context` + `meta`（各层统计、反熵增报告、场景路由决策）。
- `POST /api/memorybear/stats` —— `memorybear_stats()` 聚合各层条目数、重要性分布、冲突点。
- `POST /api/memorybear/route` —— 仅返回 `SceneRouterDecision`（权重 + 原因），供前端做可视化。

这些接口让前端可以实时展示"当前产品生成参考了你的哪些历史记忆、MemoryBear 与 RAG 的占比、是否检出冲突"，是参赛演示时体现"AI 真的记住了你"的关键卖点。

---

## 8. 设计取舍小结

| 决策 | 选择 | 理由 |
|---|---|---|
| 记忆主体 | MemoryBear 主导，RAG 补丁化 | 用户自有资产比外部检索更有说服力、更安全 |
| 工作记忆内容 | 仅元数据，正文交 `source_brief` | 避免同一笔记正文双重注入导致重复 |
| 近因曲线 | 分段衰减而非连续指数 | 与艾宾浩斯实证曲线一致，可解释 |
| 相关性门控 | `relevance==0` 强制低激活 | 实现"遗忘无关噪音" |
| RAG 实装 | 暂留接口与路由占位 | 演示场景不需要真实 KB，架构已预留扩展点 |
| 注入位置 | MemoryBear 置于 prompt 头部 | 引导 LLM 优先遵循用户历史 |

**一句话**：MemoryBear 负责"你是谁、你学过什么"，`source_grounding` 负责"这篇笔记说了什么"，`rag_grounding` 预留"外面的世界是什么样"。三者正交、可自由组合，由场景路由器在每次生成时动态调和——这正是《自由组合策略原理》中"三维正交"理念在记忆子系统的落地。
