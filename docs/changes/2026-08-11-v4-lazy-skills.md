# V4 Skill 标签与策略页性能优化

## 需求和状态

- V4-01：所有 Skill 选择矩形框显示适配产品编号 0-13。状态：Agent 自测通过。
- V4-02：优化产品策略偏好页面加载速度。状态：Agent 自测通过。
- V4-03：分析 MemoryBear 与 Skill 数量对性能的影响。状态：Agent 自测通过。

## 根因

策略偏好页不调用 MemoryBear。V3 首屏并发读取全部 Skill；`/api/tasks/strategies` 又读取一次全部 Skill，并为算法和 Skill 构造完整 O(n²) 兼容配对。Skill 数量增加时，数据库读取、产品映射 JSON 重复解析、响应体积和浏览器渲染共同增长。MemoryBear 只在后台生成任务启用该技术时执行，不是本页面根因。

## 修改

- `skill_service.load_product_type_skill_map` 使用单项进程缓存，静态映射只解析一次。
- `GET /api/skills` 增加向后兼容的 `limit`、`offset`，默认调用仍返回原数组全集。
- 策略偏好首屏不请求 Skill；用户展开选择器后请求 20 条，搜索防抖并支持加载更多。
- 隐藏兼容数据改为稀疏冲突规则，只返回真实冲突，不生成兼容组合。
- Skills 仓库、产品生成中心、单产品策略弹窗和策略偏好搜索结果均显示 0-13 标签。精确映射优先；未知 Skill 按名称和摘要做保守关键词分类；仍无法判断的通用 Skill 归入 13（LLM Skill），保证每张卡至少有一个标签。
- 新增 V4 独立启动器，明确继承 V3 MemoryBear。

## 不可回退行为与数据保护

保留 V3 用户隔离 MemoryBear、隐藏冲突矩阵、具体冲突提示、Skill 搜索、批量安装、编辑器和任务生成行为。未删除、重建、迁移或修改用户科目、笔记、产品、Skill 和数据库。分页参数为可选，旧调用保持兼容。

## 自动化验证

- `pytest backend/tests/test_workspace_features.py -q`：30 passed。
- `npm test -- --run`：26 passed。
- `npm run build`：通过。
- `pytest backend/tests -q`：371 passed。
- `pytest vendor/memory_bear_py/tests -q`：64 passed。

性能复杂度验证：旧实现对 1000 个 Skill 和 7 个算法需要物化约 506,521 个两两组合；稀疏规则实现只返回当前登记的 2 条算法冲突。新增测试 `test_sparse_rules_do_not_grow_quadratically_with_skill_count` 保证规则数量不随无冲突 Skill 数量平方增长。

## 人工验收建议

启动 V4，进入产品策略偏好，确认首屏先出现策略内容；展开 Skill 选择器后才出现网络请求。输入名称或摘要关键词，确认结果和加载更多可用，卡片显示 0-13 标签。进入产品生成中心和单产品配置，确认 Skill 选项同样显示标签。本文未将自动化结果标记为人工验收通过。

## 真实 GUI 证据

使用本地 `http://127.0.0.1:9000/strategy-preferences` 和 Playwright CLI 验收。重启后端以避免旧进程混入验收：策略页首屏显示“选择或搜索 Skill”，未渲染 Skill 列表；点击后只显示首批结果和“加载更多”；已映射 Skill 显示数字标签。截图位于本地忽略目录 `output/playwright/v4-strategy-skills.png`。该证据属于 Agent GUI 自测，不代表用户人工验收。
