# Learn2Earn V2.0.0 发布说明

- 发布提交：`8675c81`
- 发布分支：`release/v2`
- 不可移动标签：`release-v2.0.0`
- 基线：V1.0.2 `9423c59`

V2 在 V1 已验收行为上增加官方 MemoryBear 源码与可选 HTTP 适配、Skill 产品编号标签 0-13、生成策略兼容规则和独立启动器。启动入口为 `启动Learn2Earn-V2官方MemoryBear版.bat`。

发布前证据：后端聚焦测试 59 项通过，前端 23 项通过，Vite 构建通过。官方源码位于 `vendor/MemoryBear`，V2 未配置官方服务地址和令牌时使用本地回退实现。

已知边界：仓库没有配置 Git remote，本次只能生成本地发布分支、标签和说明，不能执行 `git push` 或创建托管平台 Release。标签创建后禁止移动或删除。
