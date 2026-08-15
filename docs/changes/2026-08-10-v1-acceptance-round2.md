# 2026-08-10 V1 第二轮验收修复记录

## 验收状态

- 当前状态：**Agent 自测通过，等待用户人工验收**。
- 分支：`fix/v1-acceptance-round2`；候选交付分支：`release/v1`。
- 用户已明确上一轮 V1 未通过验收，因此本记录不得标记为“人工验收通过”。

## 历史检索与不可退化行为

- `docs/changes/2026-08-09-skill-import-database-integrity.md` 已修复生成线程数据库路径漂移和 `unable to open database file`；本轮保留固定绝对数据库路径、有限连接池和瞬时数据库错误重试。
- `docs/changes/2026-08-10-v1-polish.md` 已保护科目详情使用独立过滤状态；本轮不回滚该实现，并进一步减少列表响应体积。
- 现有用户科目、笔记、产品、Skill 和生成任务均为受保护数据。本轮真实 HTTP 验证全部只读，没有删除或重建用户数据。

## BUG-V1R2-01：存量科目间歇加载笔记失败

- 状态：Agent 自测通过。
- 现象：进入“大模型”或“AI Agent 产品化实战”时偶发“加载笔记失败/请求失败”，新建的小科目不易触发。
- 根因：生产数据库使用 `StaticPool`，所有请求线程共享同一个 SQLite 连接。React 开发模式会产生并发请求，存量大笔记又延长查询和传输时间，导致共享连接间歇失败。
- 修复：`backend/app/database.py` 改为容量为 3、禁止无限溢出的 `QueuePool`；`backend/app/cloud_db.py` 仅为无写副作用的本地表读取增加 `unable to open database file` 短重试；笔记列表增加 `summary=true`，科目页和工作台只获取摘要与 `content_length`，进入编辑器时仍按 ID 获取全文。
- 回归测试：`backend/tests/test_launcher_database_path.py`、`backend/tests/test_local_table_retry.py`、`backend/tests/test_routers.py::test_notes_summary_list_truncates_large_content`、`frontend/src/utils/regressionSurfaces.test.js`。
- 修复后真实 HTTP 证据：标准 BAT 启动后，对真实账号的科目 ID 1、7、46 分别并发请求 20 次 `/api/notes?subject_id=<id>&summary=true`，共 60 次全部返回 HTTP 200。

## BUG-V1R2-02：生成任务间歇失败且没有可诊断错误

- 状态：Agent 自测通过，真实外部 LLM 完整生成仍待用户验收。
- 现象：任务 24 成功，任务 25 失败，任务 25 的错误字段为空。
- 根因：任务 25 运行约 227 秒后失败，符合外部 LLM 请求超时；`TimeoutError` 的字符串为空，旧代码直接保存 `str(exc)`，因而用户看不到原因；瞬时网络/限流也没有一次受控重试。
- 修复：`backend/app/services/llm_service.py` 对超时、网络错误、429 和 5xx 至多重试一次；`backend/app/services/generation_task_service.py` 统一生成包含异常类型的非空错误说明。
- 幂等保护：数据库错误不再从头重放整项生成任务，避免前序产品已提交后被重复创建；只读数据库访问在更低层有限重试。
- 回归测试：`backend/tests/test_llm_empty_response_retry.py`、`backend/tests/test_workspace_features.py::test_exception_detail_never_returns_blank_message`，并保留既有生成数据库重试测试。
- 已知边界：持续不可用的模型服务仍应失败，不能伪造产品；此时任务必须显示可诊断错误。

## BUG-V1R2-03：生成任务无法删除

- 状态：Agent 自测通过。
- 行为：完成或失败的任务提供垃圾桶图标和确认框，删除任务不会删除其已生成产品；排队中或运行中任务返回 HTTP 409，避免后台线程继续写入已删除任务。
- 并发保护：前端保存已确认删除的任务 ID，忽略删除前已经发出的旧轮询响应，防止任务在页面中复活。
- ID 复用保护：SQLite 删除最高 ID 后可能复用该 ID；创建新任务成功时会清除同 ID 删除标记，避免新任务被误隐藏。
- 修复：新增 `DELETE /api/tasks/{task_id}`、前端 API/store 删除动作和任务列表删除入口。
- 回归测试：`backend/tests/test_workspace_features.py::test_terminal_generation_task_can_be_deleted_without_deleting_products`、`test_active_generation_task_cannot_be_deleted`、前端 `generation tasks expose a confirmed delete action`。

## V1 专用启动器

- 新增 `启动Learn2Earn-V1验收版.bat`。它只允许在 `release/v1` 分支启动，避免用户误验其他分支；实际启动仍复用仓库标准启动器。
- 切换命令：`git switch release/v1`。若工作区有未提交修改，应先提交或暂存，禁止用强制重置丢弃数据。

## 自动化证据

- `python -m pytest -q backend/tests`：359 passed。
- `npm test -- --run`：19 passed。
- `npm run build`：成功；保留既有大 chunk 警告。
- `git diff --check -- backend frontend docs/changes 启动Learn2Earn-V1验收版.bat`：通过。

## 数据保护

- 未删除、重建、改名或清空任何现有科目、笔记、产品、Skill 或任务。
- 自动化删除测试使用隔离测试数据库；真实账号验证只执行登录和 GET 请求。
- “大模型”“AI Agent 产品化实战”“一人公司方法论”“赚钱”“自媒体变现方法论”均不得作为自动化清理对象。

## 提交与人工验收

- 关联提交：待提交后补充。
- 人工验收建议：在 `release/v1` 运行专用启动器，反复进入两个存量科目；确认失败任务显示非空错误；确认终态任务可删除且对应产品仍保留。
- 验收人及结论：等待用户填写。

## 独立复核

- 第一轮发现并关闭：删除任务可能被旧轮询响应复活；整段生成任务重试可能重复产品；写操作重试不具幂等性；V1 BAT 缺少契约测试。
- 第二轮发现并关闭：SQLite 复用已删除最高任务 ID 时，永久删除标记可能误隐藏新任务。
- 修正后复核结论：上述 P1 均关闭，未发现剩余阻断项。
