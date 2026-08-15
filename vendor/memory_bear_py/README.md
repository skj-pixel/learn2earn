---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 5f2e305c0b06635c70f7a516f4562563_1f0ae45294bc11f181ac525400f8a581
    ReservedCode1: TQfNBQ5+3WOF0+w4X8FyIcdKEAOGmydalN0jp1Tw+MFnw014qLQ1TB2Nva7C65rlJFH1NUsucyyHZ0BpS+WWdYjklv9kdcTf+/f0RdIb3Z0p43OC9pqoQiOyid/NfHAkMToK3iJPmzdJ5EwFWveNxvBRwP5nfyB+4/Iv+JTgHWY3veUd7s3heWpgd1s=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 5f2e305c0b06635c70f7a516f4562563_1f0ae45294bc11f181ac525400f8a581
    ReservedCode2: TQfNBQ5+3WOF0+w4X8FyIcdKEAOGmydalN0jp1Tw+MFnw014qLQ1TB2Nva7C65rlJFH1NUsucyyHZ0BpS+WWdYjklv9kdcTf+/f0RdIb3Z0p43OC9pqoQiOyid/NfHAkMToK3iJPmzdJ5EwFWveNxvBRwP5nfyB+4/Iv+JTgHWY3veUd7s3heWpgd1s=
---

# MemoryBear - 类脑分层记忆引擎

基于红熊AI MemoryBear 技术原理的 Python 开源实现。

## 核心特性

| 特性 | 说明 |
|------|------|
| 分层记忆架构 | 工作记忆（LRU缓存）+ 短期记忆（SQLite/TTL）+ 长期记忆（SQLite/持久化） |
| 艾宾浩斯遗忘曲线 | 激活度随时间自然衰减，被访问时恢复 |
| 智能语义剪枝 | 自动清理低激活度冗余记忆，存 储成本降低60-70% |
| 动态知识图谱 | 实体-关系-实体三元组存储，支持多跳推理 |
| 自我反思引擎 | 事实合并 → 冲突消解 → 模式抽象 → 摘要回写 |
| 记忆路由器 | QUICK（<1s关键词命中）和 DEEP（全层+KG推理）双模式 |

## 快速开始

### 环境要求
- Python 3.8+
- 零额外依赖（纯标准库实现）

### 运行演示

```bash
python main.py
```

### API 使用

```python
from memory_bear import MemoryBear

# 初始化
bear = MemoryBear(db_path="my_memory.db")

# 写入记忆
bear.remember("用户偏好使用Python开发", tags=["preference"], importance=0.9)

# 召回记忆（快速模式）
results = bear.recall("Python开发", mode="quick")

# 召回记忆（深度模式 + 知识图谱推理）
results = bear.recall("项目技术栈", mode="deep")

# 构建LLM上下文
context = bear.recall_with_context("帮我写代码", mode="deep")

# 手动剪枝
bear.prune()

# 自我反思
bear.reflect()

# 系统统计
stats = bear.get_stats()
print(stats)
```

## 架构

```
┌─────────────────────────────────────────────────┐
│                  MemoryBear 引擎                  │
├───────────┬──────────┬──────────┬───────────────┤
│ 工作记忆   │ 短期记忆  │ 长期记忆  │   知识图谱     │
│ (LRU缓存)  │ (SQLite) │ (SQLite) │ (三元组存储)   │
├───────────┴──────────┴──────────┴───────────────┤
│  ActivationManager │ PruningEngine │ ReflectionEngine │
│   (艾宾浩斯衰减)    │  (智能剪枝)    │   (自我反思)      │
├─────────────────────────────────────────────────┤
│              MemoryRouter (QUICK / DEEP)          │
└─────────────────────────────────────────────────┘
```

## 目录结构

```
memory_bear/
├── memory_bear/
│   ├── __init__.py    # 包入口
│   └── engine.py      # 核心引擎（全部模块）
├── main.py            # 演示入口
├── requirements.txt   # 依赖（空，纯标准库）
├── README.md          # 本文档
└── start.bat          # Windows 一键启动
```

## 评测参考（论文数据）

| 指标 | MemoryBear | RAG | 提升 |
|------|-----------|-----|------|
| LongMemEval | 95.0% | 89.89% | 5.6% |
| LoCoMo | 91.54% | 38.44% | 138% |
| 幻觉率 | 0.2% | 15-20% | 75-100倍 |
| Token消耗 | 基线5% | 基线100% | 20倍 |
| 响应延迟 | 0.637s | 1.2-2.0s | 48-69% |
*（内容由AI生成，仅供参考）*
