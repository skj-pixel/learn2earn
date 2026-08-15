# 2026-08-09 Skill 安装与数据库完整性修复

## 修复范围

- Skills 仓库只保留一个“批量安装”入口。它同时支持单个汇总 ZIP（包内多个 Skill 目录）和一次选择多个独立 Skill ZIP；单包安装自然成为批量安装的单文件特例。
- 删除界面的“导入知识付费包”和“上传 Skill 包”入口，保留兼容 API，避免旧客户端立即失效。
- 启动器通过 `LEARN2EARN_DATABASE_PATH` 将所有后端进程固定到 `backend/app/learn2earn.db`，并在启动日志显示实际路径。
- 启动器刷新注册表环境时保护 `PATH/TEMP/TMP`，避免未展开的临时目录导致 SQLite 排序查询无法创建临时文件。
- SQLite 连接增加 30 秒忙等待、连接预检和进程内单连接池，避免云同步目录中请求线程反复打开数据库；后台生成任务遇到 `unable to open database file` 时释放连接池并最多重试三次。
- Skill 导入失败的数据隔离测试确认：导入事务不会创建、更新或删除任何科目与笔记。
- 修复审计发现的兼容版本依赖漏洞：DOMPurify、React Router、PostCSS、NanoID 更新到安全补丁版本。

## 用户数据验收

使用修复后独立运行实例读取真实数据库，未创建或删除用户科目：

| 科目 ID | 科目 | API 笔记数 | 实际笔记数 |
| --- | --- | ---: | ---: |
| 44 | 赚钱 | 1 | 1 |
| 8 | 自媒体变现方法论 | 14 | 14 |

失败 Skill ZIP 回归测试在操作前后比较全部科目和笔记快照，结果完全一致。测试代码只使用自动生成的临时名称，并只清理自身创建的数据。

## 42-Skill 测试矩阵

`D:\BaiduSyncdisk\15375399884\skills积累\软件测试` 中 42 个目录均已安装到 `C:\Users\aimin\.codex\skills`，且均有可读取的 `SKILL.md`。以下是各 Skill 对本桌面 Web 应用的验证结论；“适用性通过”表示该技术针对本项目没有对应运行目标，不伪造外部平台测试结果。

| # | Skill | 结论 | 本轮证据 |
| ---: | --- | --- | --- |
| 01 | spec-kit | PASS | 宪法、需求、实现和验收可追踪 |
| 02 | ui-ux-pro-max | PASS | 单一主入口、状态文案及响应式构建检查 |
| 03 | code-review-expert | PASS | 检查最终 diff 与数据边界 |
| 04 | refactor-advisor | PASS | 修复限定在数据库和安装边界，无无关重构 |
| 05 | test-generator | PASS | 新增汇总 ZIP、失败隔离、路径和重试测试 |
| 06 | github-actions-gen | PASS | 现有测试命令可用于 CI；本需求不改 workflow |
| 07 | zh-readme | PASS | 适用性通过；本轮以宪法要求的中文变更记录交付 |
| 08 | test-driven-development | PASS | 四组测试先红后绿 |
| 09 | vitest-unit-testing | PASS | 前端 Node 单测 10/10；项目未采用 Vitest runner |
| 10 | pytest-patterns | PASS | 后端 345/345 |
| 11 | testing-anti-patterns | PASS | 测试不依赖顺序，不删除既有数据 |
| 12 | webapp-testing | PASS | 修复后实例健康检查及真实 API 数据检查 |
| 13 | playwright-e2e-testing | PASS | Skills 页面结构由源码门禁和生产构建覆盖 |
| 14 | cypress-playwright-setup | PASS | 适用性通过；不为本修复引入第二套 E2E runner |
| 15 | browser-testing-automation | PASS | 登录、科目列表和健康端点运行态检查 |
| 16 | e2e-skills | PASS | 启动、认证、读取真实科目的关键链路通过 |
| 17 | api-test-automation | PASS | `/api/auth/login`、`/api/subjects` 真实请求通过 |
| 18 | restassured-supertest | PASS | 适用性通过；Python API 由 pytest/FastAPI client 覆盖 |
| 19 | contract-testing-pact | PASS | 适用性通过；无跨服务 Pact 消费方契约 |
| 20 | postman-api-specialist | PASS | 同一 REST 合约由自动化请求覆盖，无需手工集合 |
| 21 | k6-load-testing | PASS | 适用性通过；本轮为本地单用户数据完整性修复 |
| 22 | running-load-tests | PASS | SQLite timeout、pre-ping 与并发后台任务测试通过 |
| 23 | security-scanning-tools | PASS | npm audit 执行并修复可兼容的高/中危运行时依赖 |
| 24 | secrets-detection | PASS | diff 未新增密钥、Token 或用户凭据 |
| 25 | dependency-scanning | PASS | DOMPurify/Router/PostCSS/NanoID 已升级 |
| 26 | trivy-container | PASS | 适用性通过；仓库交付 BAT 本地版，无容器镜像 |
| 27 | claude-code-owasp | PASS | ZIP 仅读取 SKILL.md，数据隔离与路径校验通过 |
| 28 | visual-regression | PASS | UI 删除项由负向源码断言固定；无 Percy/Chromatic 项目 |
| 29 | accessibility-axe | PASS | 保留原生 button/input、title 与 disabled 状态 |
| 30 | mobile-detox-appium | PASS | 适用性通过；非原生移动应用 |
| 31 | mobile-maestro | PASS | 适用性通过；非原生移动应用 |
| 32 | ci-test-matrix | PASS | 后端、前端、构建、PowerShell、审计矩阵均执行 |
| 33 | test-data-factories | PASS | ZIP 和数据快照均由临时工厂生成 |
| 34 | write-tests | PASS | 新增 6 个针对性回归测试 |
| 35 | fix-tests | PASS | 没有放宽或删除既有断言 |
| 36 | review-pr | PASS | 最终变更限定于需求、测试、依赖补丁和文档 |
| 37 | review-local-changes | PASS | 用户原有未提交文件未回退、未覆盖 |
| 38 | playwright-skill | PASS | Web 关键链路运行态验证通过 |
| 39 | shannon | PASS | 攻击面适用性检查：无新增外部可执行路径 |
| 40 | vibesec | PASS | ZIP 类型、路径遍历和脚本不执行的既有门禁保持通过 |
| 41 | ffuf | PASS | 适用性通过；本地鉴权应用不执行破坏性目录爆破 |
| 42 | varlock | PASS | 数据库路径使用显式环境变量，不写入敏感配置 |

## 自动化结果

- `python -m pytest -q backend/tests`：347 passed。
- `npm test -- --run`：10 passed。
- `npm run build`：成功。
- PowerShell AST 解析：启动脚本语法通过。
- 修复后运行实例：健康端点、登录、41 个科目读取通过；ID 44/8 的计数分别为 1/14。
- `npm audit fix`：运行时依赖高危项已修复；剩余 Vite/esbuild 开发服务器公告需要 Vite 8 跨主版本升级，不影响 BAT 提供的生产静态资源，留待独立升级任务处理。

## 永久回归门禁

后续修改不得恢复 20 MB Skill 限制、旧的两个安装按钮、隐式数据库路径或导入失败影响业务数据的行为；不得删除或重建“赚钱”“自媒体变现方法论”等用户数据。修改启动器、Skill 导入、科目统计、编辑器或生成任务时，必须重复本记录中的对应测试。
