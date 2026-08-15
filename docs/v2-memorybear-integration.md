# V2 MemoryBear 集成说明

## 集成边界

V1 的 `backend/app/services/memorybear.py` 是 Learn2Earn 内置的确定性适配实现，不是官方 MemoryBear 仓库本体。官方仓库依赖独立 FastAPI 服务、PostgreSQL、Neo4j、Redis、Elasticsearch 和 Python 3.12+，不能把 ZIP 直接复制到本地 SQLite 演示应用后声称已经集成。

V2 已把用户提供的官方仓库解压到 `vendor/MemoryBear`，保留其 API、Web、数据库迁移、测试、README 和 Apache-2.0 许可证。`memorybear_official_adapter.py` 会验证该源码目录，并在设置 `LEARN2EARN_MEMORYBEAR_ENDPOINT` 与 `LEARN2EARN_MEMORYBEAR_TOKEN` 后调用官方 `/api/memory/read/sync`；未设置或调用失败时继续使用本地实现，保证离线演示可用。原始 ZIP 仍不提交进 Git。

“源码已集成”与“官方服务已运行”是两个状态。官方服务运行还需要按其 README 配置 PostgreSQL、Neo4j、Redis、Elasticsearch、Celery 和 Python 3.12+；Learn2Earn 不会静默伪造这些依赖已就绪。

## MemoryBear 与 RAG

8:2 不是普适正确比例。V1 原逻辑在历史笔记达到两篇或已有产品时固定返回 0.8/0.2；V2 改为基于历史笔记和产品数量动态计算，并在外部知识查询词出现时提高 RAG 权重。当前 RAG 仍是外部知识补丁接口，尚未连接真实向量数据库，因此该比例不是经过准确率实验验证的科学结论。

## 记忆层计数

工作记忆固定为当前笔记元数据，隐性记忆最多一条；情景记忆和显性记忆现在是上限而非必须填满的配额，并根据候选数量自适应。此前大量笔记显示相同的 `工作 ×1、情景 ×6、显性 ×3、隐性 ×1`，主要由固定配额和低阈值共同造成，属于本地路由策略缺陷，不代表官方 MemoryBear 算法存在同样问题。

## 后续验收

- 对单笔记、同科目多笔记、跨科目相似笔记分别检查候选和最终注入内容。
- 验证当前笔记不会把无关笔记正文作为当前记忆重复注入。
- 验证官方服务不可用时的本地 fallback。
- 真实 HTTP/GUI 验收通过前，不把 V2 标记为发布版。
