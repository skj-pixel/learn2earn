# Learn2Earn Git 发布流程

## 1. 冻结候选提交

确认当前分支只包含目标版本修改，保留用户未提交数据，不使用 `git reset --hard`。执行 `git status --short`、`git log -1 --oneline`，记录候选提交。发布分支只能指向已经通过门禁的提交。

## 2. 执行发布门禁

```powershell
work_verify_venv\Scripts\python.exe -m pytest backend\tests -q
Set-Location frontend
npm test -- --run
npm run build
```

涉及独立引擎时还要运行引擎原生测试。涉及 UI 时应补真实浏览器验收。测试结果写入版本发布说明和 `docs/changes`，自动化通过只能标记为“Agent 自测通过”，不能冒充人工验收。

## 3. 固定发布分支

```powershell
git branch -f release/v2 <V2_COMMIT>
git branch -f release/v3 <V3_COMMIT>
```

这里只移动尚未对外承诺为不可变的发布分支。已发布标签永远不移动。分支便于继续检查和启动，标签才是不可变版本事实。

## 4. 创建带注释标签

```powershell
git tag -a release-v2.0.0 <V2_COMMIT> -m "Learn2Earn V2.0.0"
git tag -a release-v3.0.0 <V3_COMMIT> -m "Learn2Earn V3.0.0"
```

创建后用 `git show --no-patch release-vX.Y.Z` 和 `git rev-parse release-vX.Y.Z^{commit}` 核对。禁止删除、重建或强制移动发布标签；修复只能发布新的补丁版本，例如 `release-v3.0.1`。

## 5. 远程发布

仓库配置 remote 后执行：

```powershell
git push origin release/v2 release/v3
git push origin release-v2.0.0 release-v3.0.0
```

禁止 `git push --force`。在 GitHub、Gitee 或 GitLab 创建 Release 时，标题、标签、提交、测试证据、启动入口、升级说明和已知风险必须与仓库内发布说明一致。当前仓库没有 remote，所以本轮停在本地发布完成状态。

## 6. 复现与回退

查看固定版本使用 `git switch --detach release-v3.0.0`。继续开发必须从标签创建新分支，例如 `git switch -c feature/v4 release-v3.0.0`。不要在 detached HEAD 上直接长期开发。回退应切换标签或创建修复分支，不覆盖当前工作树中的用户数据。
