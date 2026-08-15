# Learn2Earn V3.0.0 发布说明

- 发布提交：以 `release-v3.0.0` 标签为准
- 发布分支：`release/v3`
- 不可移动标签：`release-v3.0.0`
- 基线：V2.0.0 `8675c81`

V3 保留 V2 的产品能力，仅将重型官方 MemoryBear 运行栈替换为 `memory_bear_py.zip` 的标准库 Python 实现，并补充稳定记忆 ID、幂等写入、用户级 SQLite 隔离、五类官方语义映射和独立启动器。V3 后续修正把兼容规则合并为两个隐藏规则组：算法与 Skill 共用生成阶段规则，质量手段只做质量阶段内部检查；页面不展示矩阵，仅在用户实际选择冲突配对时显示名称、配对和原因。

启动入口为 `启动Learn2Earn-V3轻量MemoryBear版.bat`。详细实现见 `docs/V3算法与质量控制及MemoryBear技术白皮书.md` 和 `docs/v3-python-memorybear.md`。

发布门禁：轻量 MemoryBear 原生测试 64 项通过；后端 369 项通过；前端 25 项通过；Vite 生产构建通过。用户现有科目、笔记、产品、Skill 和数据库不参与发布提交。

已知边界：仓库没有配置 Git remote，本次不能执行远程推送或创建托管平台 Release。标签创建后禁止移动或删除。
