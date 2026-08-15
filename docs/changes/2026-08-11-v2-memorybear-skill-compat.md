# V2 MemoryBear、Skill 标签与兼容矩阵

日期：2026-08-11
分支：feature/v2-memorybear-compat
状态：Agent 自测通过，尚未人工验收或发布。

## 实现

- 官方 MemoryBear 源码解压并纳入 `vendor/MemoryBear`，保留上游许可证。
- 生成任务在配置官方 endpoint/token 时调用官方同步读取 API；不可用时回退本地实现并记录 provider。
- MemoryBear/RAG 权重改为连续动态函数，记忆层配额改为候选数量自适应。
- 14 种知识产品建立稳定编号 0-13，Skill API 返回匹配编号，Skills 仓库以紧凑数字标签显示。
- 算法、质量技术、Skill 分别生成两两兼容矩阵。明确冲突会在前端提示并由后端拒绝；没有声明的 Skill 组合标为 unknown，不伪报兼容。
- 产品策略偏好页展示三张矩阵摘要。

## 数据保护

未删除或修改用户科目、笔记、产品、任务和已安装 Skill。测试使用隔离测试数据库。

## 验证

- 后端聚焦测试：59 项通过。
- 前端测试：23 项通过。
- 前端生产构建：通过。
- 官方 MemoryBear 外部依赖栈未在本机启动，因此真实官方 HTTP 调用仍需集成环境验收。
