# 2026-08-08 fix/0808-regression-guard 交付记录

## 范围

- 修复批量安装中单个 Skill ZIP 仍受 20MB 限制的问题。
- 修复产品策略偏好概览遗漏 Skill 状态的问题。
- 恢复笔记编辑器截图粘贴及历史 Python 代码围栏渲染。
- 修复产品生成中心与产品库后台重新生成共同出现的任务创建失败。
- 保证科目笔记数按真实笔记列表统计，并在保存笔记后刷新科目数据。
- 产品编辑器统一使用与笔记编辑器相同的 BlockNote，支持 Markdown、截图粘贴、块菜单、表格、代码块和 Mermaid 围栏。

## 根因与修改

1. `skill_service.py` 遗留 `MAX_ARCHIVE_BYTES = 20MB` 硬限制。删除压缩包字节上限，继续保留 ZIP 路径穿越校验和 2000 文件数量保护。
2. 旧 SQLite 数据库的 `generation_tasks` 表缺少 `product_strategies`，两个生成入口创建任务时都会写入该字段并失败。启动迁移现在会为旧表补列，同时提供独立 SQL 迁移文件。
3. `RichTextEditor` 回退后缺少 BlockNote `uploadFile`，且不能按 Markdown 输入/输出。恢复图片 Data URL 上传和格式转换，并修复跨段及单段历史 fenced code。
4. `ProductViewer` 错把 Markdown 当 HTML 解析和保存。改用 Markdown 输入/输出，并以 `useRef` 持有编辑器实例；编辑区使用与笔记相同的 `note-document` 布局。
5. 策略概览只枚举算法与技术。概览改为统一显示“已自定义生成策略”，判定同时覆盖算法、技术和 Skill；点击卡片仍进入对应详细配置。
6. 笔记保存后只刷新笔记列表，科目卡片可能保留旧计数。保存成功后同步刷新科目列表；后端科目列表和详情继续依据实际笔记实时计数。

## 提交

- `6f442a1` `fix(skills): 移除压缩包20MB限制`
- `439553b` `fix(tasks): 兼容旧库生成策略字段`
- `a9aedb8` `fix(editor): 恢复统一BlockNote富文本能力`
- `85835da` `fix(subjects): 保存笔记后刷新科目计数`
- `3bc849b` `fix(strategy): 完整标识产品自定义策略`
- `efdd7cf` `fix(editor): 兼容单段历史代码围栏`

## 自动化验证

- `pytest -q backend/tests`: 340 passed。
- `pytest -q tests_minimal`: 22 passed，1 个既有 `PytestReturnNotNoneWarning`。
- `npm test`: 9 passed。
- `npm run build`: 构建通过；仅有既有的大 chunk 提示。
- 新增回归覆盖：超过 21MB 的单个 ZIP、旧任务表迁移、Python/Mermaid 围栏、单段历史围栏、仅 Skill 自定义时的策略摘要。

## 真实接口与 GUI 验收

- 启动当前分支后确认旧库已出现 `generation_tasks.product_strategies`。
- 通过真实 HTTP 上传 22,020,420 字节 Skill ZIP，返回 200、安装 1 个 Skill，随后删除该临时 Skill。
- 产品生成中心组合任务请求与产品后台重新生成任务请求均返回 200；临时任务已清理。
- 临时科目创建 1 篇笔记后，科目详情返回 `note_count = 1`。
- Playwright 验证笔记编辑器：Python 代码块渲染成功，模拟剪贴板截图粘贴后出现图片。
- Playwright 验证产品编辑器：Python 与 Mermaid 两个代码块均存在，模拟截图粘贴后出现图片。
- Playwright 临时为 PPT 增加仅 Skill 覆盖，概览显示“已自定义生成策略”；验收后恢复原策略 JSON。
- 截图保存在 `output/playwright/0808-note-editor.png`、`0808-product-editor.png`、`0808-strategy-summary.png`（该目录被忽略，不进入提交）。

## 数据保护

- 验收数据均使用 `__codex_...` 唯一前缀，完成后已清理；数据库中无该前缀临时科目或临时任务。
- 未执行清库、重置或种子覆盖。
- “自媒体变现方法论”同名科目及其笔记未删除、未修改；验收前后保持原记录。

## 防回退约束

- 不得恢复 Skill ZIP 的 20MB 上限。
- 不得移除旧库 `product_strategies` 迁移。
- 笔记和产品编辑器必须继续共用 `RichTextEditor`/BlockNote，并保留 `uploadFile`、Markdown 输入输出和 fenced code 修复测试。
- 策略概览的自定义判定必须继续包含 `skill_keywords`。
